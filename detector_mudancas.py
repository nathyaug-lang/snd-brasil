"""
detector_mudancas.py
====================
Módulo de Market Change Detection.
Compara snapshot anterior vs atual do SnD e produz:
  - lista estruturada de mudanças
  - classificação (irrelevante / relevante / estrutural)
  - impactos em oferta / demanda / estoques
  - sinais de mercado (altista / baixista / neutro)
  - alertas de trader

Uso:
    from detector_mudancas import detectar
    mudancas = detectar(anterior, atual)
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


# =====================================================================
# Thresholds (configurável)
# =====================================================================
# Variação absoluta ou percentual que separa irrelevante/relevante/estrutural
THR = {
    "producao":     {"rel": 2.0, "str": 5.0},     # % a/a
    "area":         {"rel": 2.0, "str": 5.0},
    "produtividade":{"rel": 3.0, "str": 7.0},
    "exportacao":   {"rel": 3.0, "str": 8.0},
    "importacao":   {"rel": 15.0, "str": 30.0},
    "consumo":      {"rel": 2.0, "str": 4.0},
    "estoques":     {"rel": 5.0, "str": 15.0},
    "estoque_uso":  {"rel": 0.5, "str": 1.5},     # pp (pontos percentuais)
}

# Níveis absolutos críticos (estoque/uso)
EST_USO_APERTO = 3.0   # abaixo = aperto severo
EST_USO_FOLGA = 5.5    # acima = folga confortável


# =====================================================================
# Dataclasses
# =====================================================================
@dataclass
class Mudanca:
    bloco: str                       # 'soja_grao', 'milho', 'farelo_soja', ...
    safra: str                       # '2025/26'
    campo: str                       # 'producao', 'exportacao', ...
    anterior: float | None
    atual: float | None
    delta_abs: float | None
    delta_pct: float | None
    severidade: str                  # 'irrelevante' | 'relevante' | 'estrutural'
    impacto_oferta: str = "neutro"   # 'alta' | 'baixa' | 'neutro'
    impacto_demanda: str = "neutro"
    impacto_estoques: str = "neutro" # 'aperto' | 'folga' | 'neutro'
    fonte: str = ""
    comentario: str = ""

    def asdict(self) -> dict:
        return asdict(self)


@dataclass
class Diagnostico:
    mudancas: list[Mudanca] = field(default_factory=list)
    sinais: dict = field(default_factory=dict)   # por commodity
    alertas: list[str] = field(default_factory=list)
    resumo: str = ""


# =====================================================================
# Utilitários
# =====================================================================
def _safra_get(bloco: dict, nome: str) -> dict | None:
    for s in bloco.get("safras", []):
        if s.get("safra") == nome:
            return s
    return None


def _variacao(ant: float | None, atu: float | None) -> tuple[float, float]:
    if ant is None or atu is None:
        return (0.0, 0.0)
    delta = atu - ant
    pct = (delta / ant * 100) if ant else 0.0
    return delta, pct


def _severidade(campo: str, delta_pct: float, delta_abs: float = 0.0) -> str:
    # Para estoque/uso usamos delta absoluto em pp
    if campo == "estoque_uso":
        a = abs(delta_abs)
        if a >= THR["estoque_uso"]["str"]:
            return "estrutural"
        if a >= THR["estoque_uso"]["rel"]:
            return "relevante"
        return "irrelevante"
    thr = THR.get(campo, {"rel": 3.0, "str": 8.0})
    a = abs(delta_pct)
    if a >= thr["str"]:
        return "estrutural"
    if a >= thr["rel"]:
        return "relevante"
    return "irrelevante"


def _impactos(campo: str, delta: float) -> tuple[str, str, str]:
    """Retorna (oferta, demanda, estoques) dado campo + delta."""
    o = d = e = "neutro"
    if delta == 0:
        return (o, d, e)
    up = delta > 0
    if campo in ("producao", "producao_1a", "producao_2a", "area",
                 "produtividade", "importacao"):
        o = "alta" if up else "baixa"
        e = "folga" if up else "aperto"
    elif campo == "exportacao":
        d = "alta" if up else "baixa"
        e = "aperto" if up else "folga"
    elif campo == "consumo":
        d = "alta" if up else "baixa"
        e = "aperto" if up else "folga"
    elif campo == "estoques":
        e = "folga" if up else "aperto"
    return (o, d, e)


# =====================================================================
# Detecção por bloco
# =====================================================================
CAMPOS_PRINCIPAIS = {
    "soja_grao": ["area", "produtividade", "producao", "importacao",
                  "consumo", "exportacao", "estoques", "estoque_uso_pct"],
    "milho": ["area", "produtividade", "producao_1a", "producao_2a",
              "producao", "importacao", "consumo", "exportacao",
              "estoques", "estoque_uso_pct"],
    "farelo_soja": ["producao", "consumo", "exportacao", "estoques"],
    "oleo_soja": ["producao", "consumo", "exportacao", "estoques"],
}


def _diff_safra(bloco_nome: str, safra_nome: str,
                ant: dict, atu: dict) -> list[Mudanca]:
    """Compara todas as métricas relevantes de uma safra específica."""
    out = []
    for campo in CAMPOS_PRINCIPAIS[bloco_nome]:
        va, vn = ant.get(campo), atu.get(campo)
        if va is None or vn is None:
            continue
        delta, pct = _variacao(va, vn)
        if delta == 0:
            continue
        campo_sev = "estoque_uso" if campo == "estoque_uso_pct" else campo
        sev = _severidade(campo_sev, pct, delta)
        if sev == "irrelevante":
            continue
        io, id_, ie = _impactos(campo.replace("_pct", ""), delta)
        coment = ""
        # Comentário especializado
        if campo == "estoque_uso_pct":
            if vn < EST_USO_APERTO:
                coment = f"Estoque/uso em {vn:.1f}% — zona de APERTO SEVERO."
                ie = "aperto"
            elif vn > EST_USO_FOLGA and va <= EST_USO_FOLGA:
                coment = f"Cruzou para zona de FOLGA ({vn:.1f}%)."
                ie = "folga"
        out.append(Mudanca(
            bloco=bloco_nome, safra=safra_nome, campo=campo,
            anterior=va, atual=vn, delta_abs=round(delta, 3),
            delta_pct=round(pct, 2), severidade=sev,
            impacto_oferta=io, impacto_demanda=id_, impacto_estoques=ie,
            fonte=atu.get("fonte", ""), comentario=coment,
        ))
    return out


def _detectar_crush(ant: dict, atu: dict, safra_nome: str) -> list[Mudanca]:
    """
    Detecta mudança no equilíbrio do complexo soja:
      - Crush implícito = produção de farelo / produção de soja * rendimento típico
      - Mudança no spread farelo vs. óleo (% da produção)
      - Desbalanço entre produção de soja e capacidade de esmagamento
    """
    out: list[Mudanca] = []
    try:
        soja_a = _safra_get(ant["soja_grao"], safra_nome)
        soja_n = _safra_get(atu["soja_grao"], safra_nome)
        far_a = _safra_get(ant["farelo_soja"], safra_nome)
        far_n = _safra_get(atu["farelo_soja"], safra_nome)
        ol_a = _safra_get(ant["oleo_soja"], safra_nome)
        ol_n = _safra_get(atu["oleo_soja"], safra_nome)
        if not all([soja_a, soja_n, far_a, far_n, ol_a, ol_n]):
            return out

        # Crush implícito: soma de farelo+óleo produzido / grão processado
        # proxy de grão processado = consumo doméstico de soja (esmagamento ~95%)
        crush_a = (far_a["producao"] + ol_a["producao"]) / \
                  max(soja_a["consumo"], 0.001)
        crush_n = (far_n["producao"] + ol_n["producao"]) / \
                  max(soja_n["consumo"], 0.001)
        delta, pct = _variacao(crush_a, crush_n)
        if abs(pct) >= 2.0:
            out.append(Mudanca(
                bloco="complexo_soja", safra=safra_nome,
                campo="crush_ratio",
                anterior=round(crush_a, 3), atual=round(crush_n, 3),
                delta_abs=round(delta, 3), delta_pct=round(pct, 2),
                severidade="relevante" if abs(pct) < 5 else "estrutural",
                impacto_demanda="alta" if delta > 0 else "baixa",
                fonte="derivado",
                comentario="Rendimento implícito de esmagamento "
                           f"{'subiu' if delta > 0 else 'caiu'} — "
                           f"{'maior' if delta > 0 else 'menor'} demanda por grão.",
            ))

        # Spread farelo-óleo (% produção de cada sobre total processado)
        tot_a = far_a["producao"] + ol_a["producao"]
        tot_n = far_n["producao"] + ol_n["producao"]
        mix_far_a = far_a["producao"] / tot_a * 100 if tot_a else 0
        mix_far_n = far_n["producao"] / tot_n * 100 if tot_n else 0
        delta, _ = _variacao(mix_far_a, mix_far_n)
        if abs(delta) >= 0.5:
            out.append(Mudanca(
                bloco="complexo_soja", safra=safra_nome,
                campo="mix_farelo_oleo",
                anterior=round(mix_far_a, 2), atual=round(mix_far_n, 2),
                delta_abs=round(delta, 2), delta_pct=0.0,
                severidade="relevante",
                fonte="derivado",
                comentario=f"Participação do farelo no complexo "
                           f"{'subiu' if delta > 0 else 'caiu'} {abs(delta):.1f} pp.",
            ))
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return out


# =====================================================================
# Sinais de mercado (agregados por commodity)
# =====================================================================
def _sinais_commodity(bloco_nome: str, muds: list[Mudanca],
                      safra_atual: dict) -> dict:
    muds_b = [m for m in muds if m.bloco == bloco_nome]
    apertos = sum(1 for m in muds_b if m.impacto_estoques == "aperto")
    folgas = sum(1 for m in muds_b if m.impacto_estoques == "folga")
    estr = sum(1 for m in muds_b if m.severidade == "estrutural")
    eu = safra_atual.get("estoque_uso_pct") or 0

    if apertos > folgas and eu < EST_USO_APERTO + 1:
        balanco, vies = "APERTADO", "altista"
    elif folgas > apertos and eu > EST_USO_FOLGA:
        balanco, vies = "FOLGADO", "baixista"
    elif abs(apertos - folgas) <= 1:
        balanco, vies = "EQUILIBRADO", "neutro"
    else:
        balanco = "APERTADO" if apertos > folgas else "FOLGADO"
        vies = "altista" if apertos > folgas else "baixista"

    mudanca_estrutural = estr > 0
    return {
        "balanco": balanco,
        "vies": vies,
        "mudanca_estrutural": mudanca_estrutural,
        "estoque_uso": eu,
        "num_mudancas": len(muds_b),
        "num_estruturais": estr,
    }


# =====================================================================
# Geração de alertas (estilo trader)
# =====================================================================
def _alertas(muds: list[Mudanca], sinais: dict) -> list[str]:
    out: list[str] = []
    for m in muds:
        if m.severidade != "estrutural":
            continue
        bl = {"soja_grao": "Soja", "milho": "Milho",
              "farelo_soja": "Farelo de Soja", "oleo_soja": "Óleo de Soja",
              "complexo_soja": "Complexo Soja"}.get(m.bloco, m.bloco)
        if m.campo == "estoques" and m.delta_abs and m.delta_abs < 0:
            out.append(f"Redução estrutural de estoque de {bl} "
                       f"({m.anterior:.1f} → {m.atual:.1f} Mt · "
                       f"{m.delta_pct:+.1f}%) — risco de aperto à frente.")
        elif m.campo == "exportacao" and m.delta_abs and m.delta_abs > 0:
            out.append(f"Aceleração de exportação de {bl} "
                       f"({m.anterior:.1f} → {m.atual:.1f} Mt · "
                       f"{m.delta_pct:+.1f}%) acima do ritmo de safra.")
        elif m.campo == "producao" and m.delta_abs and m.delta_abs < 0:
            out.append(f"Revisão baixista de produção de {bl} "
                       f"({m.anterior:.1f} → {m.atual:.1f} Mt · "
                       f"{m.delta_pct:+.1f}%).")
        elif m.campo == "producao" and m.delta_abs and m.delta_abs > 0:
            out.append(f"Revisão altista de produção de {bl} "
                       f"({m.anterior:.1f} → {m.atual:.1f} Mt · "
                       f"{m.delta_pct:+.1f}%) — pressão baixista em prêmios.")
        elif m.campo == "estoque_uso_pct":
            out.append(f"{bl}: relação estoque/uso deslocou "
                       f"{m.anterior:.1f}% → {m.atual:.1f}% "
                       f"({m.delta_abs:+.1f} pp). " + (m.comentario or ""))
        elif m.bloco == "complexo_soja" and m.campo == "crush_ratio":
            out.append("Complexo Soja: rendimento de esmagamento mudou "
                       f"{m.delta_pct:+.1f}% — sinal de "
                       f"{'maior' if m.delta_abs > 0 else 'menor'} "
                       "demanda por farelo/óleo.")

    # Alertas sintéticos por commodity
    for key, lbl in [("soja_grao", "Soja"), ("milho", "Milho")]:
        s = sinais.get(key)
        if not s:
            continue
        if s["estoque_uso"] and s["estoque_uso"] < EST_USO_APERTO:
            out.append(f"{lbl}: estoque/uso em {s['estoque_uso']:.1f}% — "
                       "zona de aperto severo, viés altista estrutural.")
        if s["mudanca_estrutural"]:
            out.append(f"{lbl}: mudança estrutural detectada "
                       f"({s['num_estruturais']} campo(s)). "
                       f"Balanço virou para {s['balanco']} com viés {s['vies']}.")
    return out


# =====================================================================
# API principal
# =====================================================================
def detectar(anterior: dict | None, atual: dict) -> Diagnostico:
    """
    Entry point: compara dois snapshots e retorna diagnóstico completo.
    Se `anterior` for None, retorna diagnóstico vazio (sem base comparativa).
    """
    diag = Diagnostico()

    if not anterior:
        diag.resumo = ("Sem snapshot anterior — primeira execução do detector. "
                       "Nenhuma mudança pode ser avaliada.")
        return diag

    # 1) Diff por bloco/safra
    for bl in ("soja_grao", "milho", "farelo_soja", "oleo_soja"):
        if bl not in anterior or bl not in atual:
            continue
        for s_atu in atual[bl]["safras"]:
            s_ant = _safra_get(anterior[bl], s_atu["safra"])
            if not s_ant:
                continue
            diag.mudancas.extend(_diff_safra(bl, s_atu["safra"], s_ant, s_atu))

    # 2) Detecções derivadas (complexo soja, crush)
    for s in atual["soja_grao"]["safras"]:
        diag.mudancas.extend(_detectar_crush(anterior, atual, s["safra"]))

    # 3) Sinais agregados por commodity
    for key in ("soja_grao", "milho"):
        if key in atual:
            s_atu = atual[key]["safras"][-1]
            diag.sinais[key] = _sinais_commodity(key, diag.mudancas, s_atu)
    for key in ("farelo_soja", "oleo_soja"):
        if key in atual:
            s_atu = atual[key]["safras"][-1]
            muds_b = [m for m in diag.mudancas if m.bloco == key]
            diag.sinais[key] = {
                "balanco": "ESTÁVEL" if not muds_b else "EM MUDANÇA",
                "vies": "neutro",
                "mudanca_estrutural": any(
                    m.severidade == "estrutural" for m in muds_b),
                "num_mudancas": len(muds_b),
            }

    # 4) Alertas formatados
    diag.alertas = _alertas(diag.mudancas, diag.sinais)

    # 5) Resumo executivo
    n_rel = sum(1 for m in diag.mudancas if m.severidade == "relevante")
    n_str = sum(1 for m in diag.mudancas if m.severidade == "estrutural")
    if n_str == 0 and n_rel == 0:
        diag.resumo = "Sem alteração estrutural relevante."
    else:
        sj_b = diag.sinais.get("soja_grao", {}).get("balanco", "?")
        ml_b = diag.sinais.get("milho", {}).get("balanco", "?")
        diag.resumo = (f"{n_rel} mudança(s) relevante(s) e {n_str} estrutural(is) "
                       f"detectada(s). Soja: {sj_b} · Milho: {ml_b}.")
    return diag
