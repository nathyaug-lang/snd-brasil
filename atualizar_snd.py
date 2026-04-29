"""
atualizar_snd.py
================
Sistema dinâmico de atualização de Supply and Demand (SnD) - Soja e Milho Brasil.
Innovagro Brasil - Research & Market Intelligence.

Fontes consumidas:
  - Conab (RSS de notícias oficiais)
  - CEPEA (RSS ESALQ/USP)
  - ComexStat (API POST - MDIC)
  - IBGE SIDRA (API REST)
  - USDA PSD / FAS (opcional, requer chave API)

Fluxo:
  1. Carrega snapshot atual (dados/snd_dados.json)
  2. Coleta cada fonte (com timeout e fallback)
  3. Faz diff contra o snapshot
  4. Aplica regras de prioridade (Conab > USDA > IBGE)
  5. Recalcula derivadas (oferta total, estoque/uso, %exp/prod)
  6. Gera HTML atualizado
  7. Loga tudo em logs/atualizacoes.log

Execução:
    python atualizar_snd.py
    python atualizar_snd.py --apenas-feeds   # só atualiza notícias
    python atualizar_snd.py --dry-run        # simula, não grava
"""

from __future__ import annotations
import argparse
import json
import logging
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

try:
    import requests  # preferido para POST ComexStat
    TEM_REQUESTS = True
except ImportError:
    TEM_REQUESTS = False

BASE = Path(__file__).resolve().parent
ARQ_DADOS = BASE / "dados" / "snd_dados.json"
ARQ_DADOS_ANT = BASE / "dados" / "snd_dados_anterior.json"
ARQ_DADOS_ONTEM = BASE / "dados" / "snd_dados_ontem.json"
ARQ_HTML = BASE / "output" / "SnD_Brasil_Soja_Milho_Dinamico.html"
ARQ_HTML_ALERTAS = BASE / "output" / "Market_Change_Detection.html"
ARQ_HTML_UNIFIED = BASE / "output" / "SnD_Brasil_Unified.html"
ARQ_LOG = BASE / "logs" / "atualizacoes.log"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/122.0.0.0 Safari/537.36")
TIMEOUT = 15

# ---------- logging ----------
ARQ_LOG.parent.mkdir(exist_ok=True, parents=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ARQ_LOG, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("snd")


# =====================================================================
# HTTP helpers
# =====================================================================
def http_get(url: str, headers: dict | None = None, timeout: int = TIMEOUT) -> str:
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8",
                                errors="replace")


def http_post_json(url: str, payload: dict, timeout: int = TIMEOUT) -> dict:
    if TEM_REQUESTS:
        r = requests.post(url, json=payload, timeout=timeout,
                          headers={"User-Agent": UA,
                                   "Content-Type": "application/json"})
        r.raise_for_status()
        return r.json()
    # fallback puro
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


# =====================================================================
# Coletores por fonte
# =====================================================================
def coletar_rss(url: str, limite: int = 10) -> list[dict]:
    """Parser genérico de RSS/Atom."""
    try:
        xml = http_get(url)
    except Exception as e:
        log.warning(f"RSS falhou [{url}]: {e}")
        return []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        log.warning(f"RSS inválido [{url}]: {e}")
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    itens = root.findall(".//item") or root.findall(".//atom:entry", ns)
    saida = []
    for it in itens[:limite]:
        def txt(tag):
            el = it.find(tag) or it.find(f"atom:{tag}", ns)
            return (el.text or "").strip() if el is not None and el.text else ""
        saida.append({
            "titulo": txt("title"),
            "data": txt("pubDate") or txt("updated") or txt("published"),
            "link": txt("link"),
        })
    return saida


def coletar_conab() -> list[dict]:
    """Feed oficial Conab. Tentar múltiplos endpoints conhecidos."""
    urls = [
        "https://www.conab.gov.br/ultimas-noticias/feed",
        "https://www.conab.gov.br/index.php?format=feed&type=rss",
        "https://www.gov.br/conab/pt-br/assuntos/noticias/RSS",
    ]
    for u in urls:
        r = coletar_rss(u)
        if r:
            log.info(f"Conab: {len(r)} notícias coletadas de {u}")
            return [{**x, "fonte": "Conab"} for x in r]
    log.warning("Conab: nenhum endpoint RSS respondeu")
    return []


def coletar_cepea() -> list[dict]:
    urls = [
        "https://www.cepea.esalq.usp.br/br/rss.aspx",
        "https://www.cepea.org.br/br/rss.aspx",
    ]
    for u in urls:
        r = coletar_rss(u)
        if r:
            log.info(f"CEPEA: {len(r)} notícias coletadas de {u}")
            return [{**x, "fonte": "CEPEA"} for x in r]
    log.warning("CEPEA: nenhum endpoint RSS respondeu")
    return []


def coletar_ibge_area_plantada(produto_cod: str) -> dict | None:
    """
    IBGE SIDRA tabela 6588 (LSPA - Levantamento Sistemático Produção Agrícola).
    produto_cod (classificação c48): 2713 soja em grão; 2711 milho em grão.
    Variáveis: 109 área plantada, 216 área colhida, 214 produção, 112 rendimento.
    IBGE LSPA publica mensalmente (previsão do ano civil corrente).
    """
    url = (f"https://apisidra.ibge.gov.br/values/t/6588/n1/all/"
           f"v/109,216,214,112/p/last%201/c48/{produto_cod}")
    try:
        raw = http_get(url)
        dados = json.loads(raw)
    except Exception as e:
        log.warning(f"IBGE SIDRA falhou ({produto_cod}): {e}")
        # fallback: tenta v/all
        try:
            url2 = (f"https://apisidra.ibge.gov.br/values/t/6588/n1/all/"
                    f"v/all/p/last%201/c48/{produto_cod}")
            dados = json.loads(http_get(url2))
        except Exception as e2:
            log.warning(f"IBGE SIDRA fallback falhou ({produto_cod}): {e2}")
            return None
    if len(dados) < 2:
        return None
    res = {"periodo": None}
    for row in dados[1:]:
        var = row.get("D2N", "")
        val = row.get("V", "")
        res["periodo"] = row.get("D3N")
        if val in ("...", "-", ""):
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        if "plantada" in var.lower():
            res["area_ha"] = v
        elif "colhida" in var.lower() and "area_ha" not in res:
            res["area_ha"] = v
        elif "produção" in var.lower() or "producao" in var.lower():
            res["producao_t"] = v
        elif "rendimento" in var.lower() or "produtividade" in var.lower():
            res["produtividade_kg_ha"] = v
    log.info(f"IBGE {produto_cod}: {res}")
    return res if len(res) > 1 else None


def coletar_ibge_estados(produto_cod: str) -> dict | None:
    """
    IBGE SIDRA tabela 6588 (LSPA) por UF (n3=all).
    Retorna {UF: {area_ha, producao_t, produtividade_kg_ha, periodo}}.
    Use produto_cod 2713 (soja) ou 2711 (milho).
    """
    url = (f"https://apisidra.ibge.gov.br/values/t/6588/n3/all/"
           f"v/all/p/last%201/c48/{produto_cod}")
    try:
        raw = http_get(url)
        dados = json.loads(raw)
    except Exception as e:
        log.warning(f"IBGE estados falhou ({produto_cod}): {e}")
        return None
    if len(dados) < 2:
        return None
    out: dict[str, dict] = {}
    # Mapeia código UF do IBGE -> sigla
    cod_uf = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
        "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
        "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
        "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
        "52": "GO", "53": "DF",
    }
    for row in dados[1:]:
        uf_cod = row.get("D1C", "")
        var = row.get("D2N", "")
        val = row.get("V", "")
        if val in ("...", "-", ""):
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        sigla = cod_uf.get(uf_cod)
        if not sigla:
            continue
        bloco = out.setdefault(sigla, {"periodo": row.get("D3N")})
        var_l = var.lower()
        if "plantada" in var_l:
            bloco["area_ha"] = v
        elif "colhida" in var_l and "area_ha" not in bloco:
            bloco["area_ha"] = v
        elif "produção" in var_l or "producao" in var_l:
            bloco["producao_t"] = v
        elif "rendimento" in var_l or "produtividade" in var_l:
            bloco["produtividade_kg_ha"] = v
    log.info(f"IBGE UF {produto_cod}: {len(out)} estados com dados")
    return out or None


def coletar_comexstat(produto_ncm: str, anos: list[int]) -> dict | None:
    """
    ComexStat POST /general?filter=... .
    NCMs úteis:
      - Soja em grão: 12019000
      - Milho grão: 10059010
      - Farelo soja: 23040010 / 23040090
      - Óleo soja bruto: 15071000
    Retorna {ano: {volume_kg, valor_fob_usd}} apenas para exportação.
    """
    url = "https://api-comexstat.mdic.gov.br/general"
    payload = {
        "flow": "export",
        "monthDetail": False,
        "period": {"from": f"{min(anos)}-01", "to": f"{max(anos)}-12"},
        "filters": [{"filter": "ncm", "values": [produto_ncm]}],
        "details": ["year"],
        "metrics": ["metricFOB", "metricKG"],
    }
    try:
        js = http_post_json(url, payload)
    except Exception as e:
        log.warning(f"ComexStat falhou ({produto_ncm}): {e}")
        return None
    linhas = (js.get("data") or {}).get("list") or js.get("list") or []
    saida = {}
    for row in linhas:
        ano = int(row.get("year") or row.get("coAno") or 0)
        if not ano:
            continue
        saida[ano] = {
            "volume_kg": float(row.get("metricKG") or row.get("vlFob") or 0),
            "fob_usd": float(row.get("metricFOB") or row.get("vlFob") or 0),
        }
    log.info(f"ComexStat NCM {produto_ncm}: {len(saida)} anos coletados")
    return saida or None


def coletar_usda_psd(produto: str, chave: str | None) -> dict | None:
    """
    USDA PSD Online API (requer chave FAS).
    produto: 'Soybeans', 'Corn', 'Soybean Meal', 'Soybean Oil'.
    """
    if not chave:
        log.info("USDA PSD: chave não configurada, pulando.")
        return None
    url = ("https://apps.fas.usda.gov/psdonline/psdDataApi/commodity/"
           f"{produto}/country/BR")
    try:
        js = json.loads(http_get(url, headers={"API-KEY": chave}))
    except Exception as e:
        log.warning(f"USDA PSD falhou ({produto}): {e}")
        return None
    log.info(f"USDA {produto}: {len(js)} registros")
    return js


# =====================================================================
# Lógica de atualização / diff
# =====================================================================
def _get_safra(ds: list[dict], nome: str) -> dict | None:
    for s in ds:
        if s["safra"] == nome:
            return s
    return None


def filtrar_noticias_relevantes(feed: list[dict]) -> list[dict]:
    kw = re.compile(r"soja|milho|safra|gr[ãa]o|conab|usda|export|estoque|"
                    r"plantio|colheita|farelo|\bóleo\b", re.IGNORECASE)
    return [n for n in feed if kw.search(n.get("titulo", ""))]


def aplicar_ibge(dados: dict, produto_cod: str, chave_alvo: str,
                 mudancas: list) -> None:
    """
    produto_cod IBGE -> atualiza a safra-corrente (marcada projecao=True).
    Conversão: IBGE publica em hectares / toneladas; convertemos para Mi ha / Mt.
    IBGE é usado como 'sinal' — Conab prevalece em conflito.
    """
    r = coletar_ibge_area_plantada(produto_cod)
    if not r:
        return
    bloco = dados[chave_alvo]
    safra_proj = [s for s in bloco["safras"] if s.get("projecao")]
    if not safra_proj:
        return
    s = safra_proj[-1]
    if "area_ha" in r:
        novo = round(r["area_ha"] / 1_000_000, 2)
        if abs(novo - s["area"]) >= 0.1:
            mudancas.append({
                "bloco": chave_alvo, "safra": s["safra"], "campo": "area",
                "anterior": s["area"], "novo": novo, "fonte": "IBGE/LSPA",
                "periodo": r.get("periodo"),
            })
            s["area"] = novo
            s["fonte"] = "Conab/IBGE"
    if "producao_t" in r:
        novo = round(r["producao_t"] / 1_000_000, 2)
        if abs(novo - s["producao"]) >= 0.5:
            mudancas.append({
                "bloco": chave_alvo, "safra": s["safra"], "campo": "producao",
                "anterior": s["producao"], "novo": novo, "fonte": "IBGE/LSPA",
                "periodo": r.get("periodo"),
            })
            s["producao"] = novo
            s["fonte"] = "Conab/IBGE"


def aplicar_comexstat(dados: dict, ncm: str, chave_alvo: str,
                      mudancas: list) -> None:
    """
    Atualiza exportação da safra-corrente com dados ComexStat (ano civil).
    Para soja: safra T/T+1 ~ ano civil T+1 (Jan-Dez).
    """
    anos = [datetime.now().year - 1, datetime.now().year]
    r = coletar_comexstat(ncm, anos)
    if not r:
        return
    bloco = dados[chave_alvo]
    # mapeia ano civil -> safra (safra X/X+1 principal fluxo é em X+1)
    for ano, info in r.items():
        vol_mt = round(info["volume_kg"] / 1_000_000_000, 2)
        safra_nome = f"{str(ano-1)[-2:]}/{str(ano)[-2:]}"
        s = _get_safra(bloco["safras"], safra_nome)
        if not s:
            continue
        if abs(vol_mt - s["exportacao"]) >= 0.3:
            mudancas.append({
                "bloco": chave_alvo, "safra": safra_nome, "campo": "exportacao",
                "anterior": s["exportacao"], "novo": vol_mt,
                "fonte": "ComexStat", "periodo": f"ano {ano}",
            })
            s["exportacao"] = vol_mt


def recalcular_derivadas(dados: dict) -> None:
    """
    Recalcula:
      - oferta_total = producao + importacao + estoque_inicial
      - estoque_uso = estoques / (consumo + exportacao) * 100
      - %exp/prod, %cons/prod (farelo e óleo)
    Armazena as derivadas em cada dict de safra.
    """
    for chave in ("soja_grao", "milho"):
        bloco = dados[chave]
        safras = bloco["safras"]
        for i, s in enumerate(safras):
            est_ini = safras[i-1]["estoques"] if i > 0 else 0.0
            s["oferta_total"] = round(
                s["producao"] + s["importacao"] + est_ini, 1)
            uso = s["consumo"] + s["exportacao"]
            s["estoque_uso_pct"] = round(s["estoques"] / uso * 100, 1) \
                if uso > 0 else None

    for chave in ("farelo_soja", "oleo_soja"):
        for s in dados[chave]["safras"]:
            p = s["producao"] or 0.0
            s["pct_consumo"] = round(s["consumo"] / p * 100, 1) if p else None
            s["pct_exportacao"] = round(s["exportacao"] / p * 100, 1) if p else None


# =====================================================================
# Pipeline principal
# =====================================================================
def carregar() -> dict:
    return json.loads(ARQ_DADOS.read_text(encoding="utf-8"))


def carregar_anterior() -> dict | None:
    if not ARQ_DADOS_ANT.exists():
        return None
    try:
        return json.loads(ARQ_DADOS_ANT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Snapshot anterior ilegivel: {e}")
        return None


def promover_para_anterior(dados_atuais: dict) -> None:
    """Antes de gravar novo snapshot, copia o atual como 'anterior'."""
    ARQ_DADOS_ANT.write_text(
        json.dumps(dados_atuais, ensure_ascii=False, indent=2),
        encoding="utf-8")


def rotacionar_diario(dados_atuais: dict) -> None:
    """
    Modo daily refresh: mantém um snapshot específico de 'ontem'.
    Só é promovido se a data mudou (execução em dia diferente).
    """
    hoje = datetime.now().date().isoformat()
    dev_mais_recente = None
    if ARQ_DADOS_ONTEM.exists():
        try:
            prev = json.loads(ARQ_DADOS_ONTEM.read_text(encoding="utf-8"))
            dev_mais_recente = prev.get("meta", {}).get("data_snapshot")
        except (json.JSONDecodeError, OSError):
            pass
    # Se ainda não existe ou é de outro dia, grava o atual como 'ontem'
    if dev_mais_recente != hoje:
        payload = dict(dados_atuais)
        payload.setdefault("meta", {})["data_snapshot"] = \
            dados_atuais.get("meta", {}).get("data_snapshot", hoje)
        ARQ_DADOS_ONTEM.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def carregar_ontem() -> dict | None:
    if not ARQ_DADOS_ONTEM.exists():
        return None
    try:
        return json.loads(ARQ_DADOS_ONTEM.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def gravar(dados: dict) -> None:
    ARQ_DADOS.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def executar(apenas_feeds: bool = False, dry_run: bool = False,
             usda_key: str | None = None) -> dict:
    log.info("="*70)
    log.info("Iniciando atualização SnD Brasil - Soja e Milho")
    log.info("="*70)
    # Carrega snapshot anterior ANTES de qualquer modificação do atual
    snapshot_anterior = carregar_anterior()
    dados = carregar()
    # Guarda cópia do "pré-atualização" para comparação posterior
    snapshot_pre = json.loads(json.dumps(dados))  # deep copy
    mudancas: list[dict] = []

    # --- Feeds de notícias ---
    feed = []
    feed += coletar_conab()
    feed += coletar_cepea()
    feed = filtrar_noticias_relevantes(feed)
    dados["noticias_feed"] = feed[:15]
    log.info(f"Notícias filtradas (soja/milho/safra/etc): {len(feed)}")

    if not apenas_feeds:
        # --- IBGE ---
        aplicar_ibge(dados, "2713", "soja_grao", mudancas)
        aplicar_ibge(dados, "2711", "milho", mudancas)

        # --- ComexStat ---
        aplicar_comexstat(dados, "12019000", "soja_grao", mudancas)
        aplicar_comexstat(dados, "10059010", "milho", mudancas)
        aplicar_comexstat(dados, "23040010", "farelo_soja", mudancas)
        aplicar_comexstat(dados, "15071000", "oleo_soja", mudancas)

        # --- USDA PSD (opcional) ---
        if usda_key:
            for prod, chave in [("Soybeans", "soja_grao"), ("Corn", "milho"),
                                ("Soybean Meal", "farelo_soja"),
                                ("Soybean Oil", "oleo_soja")]:
                coletar_usda_psd(prod, usda_key)

        # --- Recálculos ---
        recalcular_derivadas(dados)
    else:
        recalcular_derivadas(dados)  # garante derivadas no baseline

    # --- Registrar atualização ---
    agora = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    dados["meta"]["atualizado_em"] = agora
    dados["atualizacoes_recentes"] = mudancas + dados.get(
        "atualizacoes_recentes", [])[:40]

    log.info(f"Total de campos modificados: {len(mudancas)}")
    for m in mudancas:
        log.info(
            f"  - {m['bloco']} {m['safra']} {m['campo']}: "
            f"{m['anterior']} -> {m['novo']} ({m['fonte']})")

    # === Market Change Detection ===
    # Base de comparação: snapshot_anterior (externo) > snapshot_pre (este run)
    base_comp = snapshot_anterior or snapshot_pre
    try:
        from detector_mudancas import detectar
        diag = detectar(base_comp, dados)
        log.info(f"Detector: {len(diag.mudancas)} mudanças, "
                 f"{len(diag.alertas)} alertas. {diag.resumo}")
    except Exception as e:
        log.exception(f"Detector falhou: {e}")
        diag = None

    if not dry_run:
        # Antes de sobrescrever, promove atual para "anterior"
        promover_para_anterior(snapshot_pre)
        # Rotaciona snapshot diário (preserva 'ontem' até virar o dia)
        rotacionar_diario(snapshot_pre)
        # Atualiza carimbo de data no atual
        dados.setdefault("meta", {})["data_snapshot"] = datetime.now().date().isoformat()
        gravar(dados)
        # Gera HTMLs
        from gerar_html import gerar
        gerar(dados, ARQ_HTML)
        log.info(f"HTML SnD: {ARQ_HTML}")
        if diag is not None:
            from gerar_alertas_html import gerar as gerar_alertas
            gerar_alertas(diag, dados.get("meta", {}),
                          base_comp.get("meta") if base_comp else None,
                          ARQ_HTML_ALERTAS)
            log.info(f"HTML Alertas: {ARQ_HTML_ALERTAS}")
            # HTML UNIFICADO (duas visões + toggle)
            from gerar_unified_html import gerar_unified
            gerar_unified(dados, diag, dados.get("meta", {}),
                          base_comp.get("meta") if base_comp else None,
                          ARQ_HTML_UNIFIED)
            log.info(f"HTML Unificado: {ARQ_HTML_UNIFIED}")
    else:
        log.info("[dry-run] Nenhum arquivo foi gravado.")

    return {"mudancas": mudancas, "noticias": len(feed),
            "diagnostico": diag}


def main() -> int:
    ap = argparse.ArgumentParser(description="Atualizador SnD Soja/Milho Brasil")
    ap.add_argument("--apenas-feeds", action="store_true",
                    help="Coleta apenas notícias, não tenta APIs de SnD.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Simula execução sem gravar JSON/HTML.")
    ap.add_argument("--usda-key", default=None,
                    help="Chave API USDA PSD (opcional).")
    args = ap.parse_args()
    try:
        r = executar(apenas_feeds=args.apenas_feeds, dry_run=args.dry_run,
                     usda_key=args.usda_key)
        diag = r.get("diagnostico")
        n_det = len(diag.mudancas) if diag else 0
        n_alt = len(diag.alertas) if diag else 0
        print(f"\n[OK] Mudancas coletor: {len(r['mudancas'])} | "
              f"Noticias: {r['noticias']} | "
              f"Detector: {n_det} mudancas / {n_alt} alertas")
        if diag and diag.resumo:
            print(f"     -> {diag.resumo}")
        return 0
    except Exception as e:
        log.exception(f"Falha na execucao: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
