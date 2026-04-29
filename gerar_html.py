"""
gerar_html.py
=============
Renderiza o HTML SnD a partir do snapshot JSON.
Não tem lógica de coleta - apenas template + formatação.
"""
from __future__ import annotations
import base64
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

CORES = {"navy": "#0A2342", "green": "#1E5631", "green_soft": "#2E7D4F"}

# Logo oficial em base64 (self-contained HTML)
_LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo_innovagro.jpg"


def logo_base64() -> str:
    try:
        b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    except FileNotFoundError:
        return ""


def logo_tag(altura_px: int = 54) -> str:
    src = logo_base64()
    if not src:
        return ""
    return (f'<img class="logo" src="{src}" alt="" '
            f'style="height:{altura_px}px;width:auto;display:block">')


# ===================== helpers de formatação ==========================
def fmt_n(v: Any, dec: int = 1) -> str:
    if v is None:
        return "N/A"
    try:
        s = f"{float(v):,.{dec}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "N/A"


def fmt_pct(v: Any) -> str:
    if v is None:
        return "N/A"
    return fmt_n(v, 1) + "%"


def cls_proj(s: dict) -> str:
    return ' class="projection"' if s.get("projecao") else ""


# ===================== componentes ====================================
LOGO_SVG = ""  # deprecated - usar logo_tag()

CSS = r"""
:root{--navy:#0A2342;--green:#1E5631;--green-soft:#2E7D4F;--ink:#1B1F23;
  --muted:#5B6775;--line:#E4E7EB;--zebra:#F7F9FB;--accent:#F3F6F4;--warn:#B45309;
  --new:#FFFBEA;--new-br:#F59E0B}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:#fff;color:var(--ink);
  font-family:"Segoe UI","Inter","Helvetica Neue",Arial,sans-serif;font-size:14px;line-height:1.55}
.page{max-width:1280px;margin:0 auto;padding:40px 48px 80px}
header.top{display:flex;align-items:center;justify-content:space-between;
  border-bottom:3px solid var(--green);padding-bottom:20px;margin-bottom:28px}
.brand{display:flex;align-items:center;gap:18px}.brand .logo{max-height:54px;width:auto}
.brand .divider{width:1px;height:56px;background:var(--line)}
.brand .tagline{font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase}
.brand .tagline strong{display:block;color:var(--navy);font-size:13px;letter-spacing:.14em;margin-bottom:2px}
.doc-meta{text-align:right;font-size:12px;color:var(--muted)}
.doc-meta .date{color:var(--navy);font-weight:600;font-size:13px}
.doc-meta .live{display:inline-block;padding:3px 10px;background:var(--green);color:#fff;
  border-radius:3px;font-size:10px;letter-spacing:.1em;margin-top:6px;font-weight:600}
h1.title{font-size:30px;font-weight:700;color:var(--navy);margin:0 0 4px;letter-spacing:-.01em}
.subtitle{color:var(--green);font-weight:600;font-size:15px;margin-bottom:24px}
.section-intro{color:var(--muted);font-size:13px;margin-bottom:24px;max-width:960px}
section{margin-bottom:44px}
h2{font-size:20px;color:#fff;background:var(--navy);margin:0;padding:12px 18px;
  letter-spacing:.02em;border-left:6px solid var(--green);font-weight:600}
h2 .sub{font-weight:400;color:#C9D4E0;font-size:13px;margin-left:10px}
h3{font-size:14px;color:var(--navy);margin:24px 0 10px;font-weight:600;
  text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--line);padding-bottom:6px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-top:none}
table{width:100%;border-collapse:collapse;font-size:13px;background:#fff}
thead th{background:var(--green);color:#fff;font-weight:600;text-align:right;
  padding:10px 12px;font-size:12px;letter-spacing:.03em;text-transform:uppercase;
  border-bottom:2px solid var(--navy)}
thead th:first-child{text-align:left}
tbody td{padding:9px 12px;text-align:right;border-bottom:1px solid var(--line)}
tbody td:first-child{text-align:left;font-weight:600;color:var(--navy)}
tbody tr:nth-child(even){background:var(--zebra)}
tbody tr:hover{background:#EEF4EF}
tbody tr.projection td{font-style:italic;color:var(--muted)}
tbody tr.projection td:first-child{color:var(--green);font-style:normal}
tbody tr.projection td:first-child::after{content:"  proj.";font-size:10px;
  color:var(--green-soft);font-weight:500;letter-spacing:.05em;text-transform:uppercase;font-style:italic}
td.hl-stock,th.hl-stock{background:#F0F5F1}
td.hl-ratio,th.hl-ratio{background:#F0F5F1;font-weight:600;color:var(--green)}
tbody tr:nth-child(even) td.hl-stock,tbody tr:nth-child(even) td.hl-ratio{background:#E7EEE9}
td.changed{background:var(--new) !important;position:relative;font-weight:700;color:#9A3412}
td.changed::after{content:"●";color:var(--new-br);position:absolute;top:2px;right:4px;font-size:10px}
.unit-note{font-size:11px;color:var(--muted);margin:6px 0 0;text-align:right}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 10px}
.kpi{padding:14px 16px;background:var(--accent);border-top:3px solid var(--green);
  border-bottom:1px solid var(--line)}
.kpi .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.kpi .value{font-size:20px;color:var(--navy);font-weight:700;margin-top:4px}
.kpi .delta{font-size:12px;color:var(--green);margin-top:2px;font-weight:600}
.updates-box{border:2px solid var(--new-br);background:var(--new);padding:16px 20px;
  border-radius:4px;margin-bottom:24px}
.updates-box h2{background:var(--new-br);color:#fff;border-left-color:#B45309;margin-bottom:12px}
.updates-box .none{color:var(--muted);font-style:italic;padding:12px 0}
.updates-list{margin:14px 0 0;padding:0;list-style:none}
.updates-list li{padding:6px 0;border-bottom:1px dotted #E4C577;font-size:13px}
.updates-list li:last-child{border-bottom:none}
.updates-list strong{color:var(--navy)}
.updates-list .delta-up{color:var(--green);font-weight:700}
.updates-list .delta-dn{color:var(--warn);font-weight:700}
.news-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.news-card{padding:10px 12px;border-left:3px solid var(--green);background:var(--zebra);font-size:12px}
.news-card a{color:var(--navy);text-decoration:none;font-weight:600}
.news-card a:hover{text-decoration:underline}
.news-card .meta{color:var(--muted);font-size:11px;margin-top:4px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.card{border:1px solid var(--line);border-left:4px solid var(--green);padding:14px 16px;background:#fff}
.card h4{margin:0 0 8px;font-size:12px;letter-spacing:.1em;color:var(--navy);text-transform:uppercase;font-weight:700}
.card p{margin:0;font-size:13px;line-height:1.55}
.card.navy{border-left-color:var(--navy)}
.card.warn{border-left-color:var(--warn)}.card.warn h4{color:var(--warn)}
.analysis p{margin:0 0 12px;max-width:960px}.analysis strong{color:var(--navy)}
.synth-box{margin-top:22px;padding:16px 20px;background:var(--accent);border-left:4px solid var(--navy)}
footer{margin-top:50px;padding-top:16px;border-top:1px solid var(--line);
  font-size:11px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
footer .src strong{color:var(--navy)}
"""


# ===================== renderização de tabelas ========================
def tabela_soja(dados: dict, alterados: set) -> str:
    cab = ["Safra", "Área (Mi ha)", "Produtividade (kg/ha)", "Produção (Mt)",
           "Importação (Mt)", "Oferta Total (Mt)", "Consumo (Mt)",
           "Exportação (Mt)", "Estoques Finais (Mt)", "Estoque/Uso (%)"]
    ths = "".join(
        f'<th{" class=\"hl-stock\"" if "Estoques" in c else ""}'
        f'{" class=\"hl-ratio\"" if "Estoque/Uso" in c else ""}>{c}</th>'
        for c in cab)
    linhas = []
    for s in dados["soja_grao"]["safras"]:
        def td(campo, val, dec=1, extra=""):
            mark = " changed" if (s["safra"], campo) in alterados else ""
            return f'<td class="{extra}{mark}">{fmt_n(val, dec)}</td>'
        linhas.append(
            f'<tr{cls_proj(s)}>'
            f'<td>{s["safra"]}</td>'
            f'{td("area", s.get("area"), 1)}'
            f'{td("produtividade", s.get("produtividade"), 0)}'
            f'{td("producao", s.get("producao"), 1)}'
            f'{td("importacao", s.get("importacao"), 2)}'
            f'{td("oferta_total", s.get("oferta_total"), 1)}'
            f'{td("consumo", s.get("consumo"), 1)}'
            f'{td("exportacao", s.get("exportacao"), 1)}'
            f'{td("estoques", s.get("estoques"), 1, "hl-stock")}'
            f'<td class="hl-ratio">{fmt_pct(s.get("estoque_uso_pct"))}</td>'
            f'</tr>')
    return (f'<div class="table-wrap"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def tabela_milho(dados: dict, alterados: set) -> str:
    cab = ["Safra", "Área (Mi ha)", "Produtiv. (kg/ha)", "Prod. 1ª Safra (Mt)",
           "Prod. 2ª Safra (Mt)", "Produção Total (Mt)", "Importação (Mt)",
           "Oferta Total (Mt)", "Consumo (Mt)", "Exportação (Mt)",
           "Estoques (Mt)", "Estoque/Uso (%)"]
    ths = "".join(
        f'<th{" class=\"hl-stock\"" if "Estoques" in c else ""}'
        f'{" class=\"hl-ratio\"" if "Estoque/Uso" in c else ""}>{c}</th>'
        for c in cab)
    linhas = []
    for s in dados["milho"]["safras"]:
        def td(campo, val, dec=1, extra=""):
            mark = " changed" if (s["safra"], campo) in alterados else ""
            return f'<td class="{extra}{mark}">{fmt_n(val, dec)}</td>'
        linhas.append(
            f'<tr{cls_proj(s)}>'
            f'<td>{s["safra"]}</td>'
            f'{td("area", s.get("area"), 1)}'
            f'{td("produtividade", s.get("produtividade"), 0)}'
            f'{td("producao_1a", s.get("producao_1a"), 1)}'
            f'{td("producao_2a", s.get("producao_2a"), 1)}'
            f'{td("producao", s.get("producao"), 1)}'
            f'{td("importacao", s.get("importacao"), 1)}'
            f'{td("oferta_total", s.get("oferta_total"), 1)}'
            f'{td("consumo", s.get("consumo"), 1)}'
            f'{td("exportacao", s.get("exportacao"), 1)}'
            f'{td("estoques", s.get("estoques"), 1, "hl-stock")}'
            f'<td class="hl-ratio">{fmt_pct(s.get("estoque_uso_pct"))}</td>'
            f'</tr>')
    return (f'<div class="table-wrap"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def tabela_sub(dados: dict, chave: str, alterados: set) -> str:
    cab = ["Safra", "Produção (Mt)", "Consumo Interno (Mt)", "Exportação (Mt)",
           "Estoques Finais (Mt)", "% Cons./Prod.", "% Exp./Prod."]
    ths = "".join(
        f'<th{" class=\"hl-stock\"" if "Estoques" in c else ""}'
        f'{" class=\"hl-ratio\"" if "%" in c else ""}>{c}</th>' for c in cab)
    linhas = []
    for s in dados[chave]["safras"]:
        def td(campo, val, dec=2, extra=""):
            mark = " changed" if (s["safra"], campo) in alterados else ""
            return f'<td class="{extra}{mark}">{fmt_n(val, dec)}</td>'
        linhas.append(
            f'<tr{cls_proj(s)}>'
            f'<td>{s["safra"]}</td>'
            f'{td("producao", s.get("producao"), 2)}'
            f'{td("consumo", s.get("consumo"), 2)}'
            f'{td("exportacao", s.get("exportacao"), 2)}'
            f'{td("estoques", s.get("estoques"), 2, "hl-stock")}'
            f'<td class="hl-ratio">{fmt_pct(s.get("pct_consumo"))}</td>'
            f'<td class="hl-ratio">{fmt_pct(s.get("pct_exportacao"))}</td>'
            f'</tr>')
    return (f'<div class="table-wrap"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def tabela_exportacoes(dados: dict) -> str:
    rows = []
    for sj, ml, fr, ol in zip(
            dados["soja_grao"]["safras"], dados["milho"]["safras"],
            dados["farelo_soja"]["safras"], dados["oleo_soja"]["safras"]):
        rows.append(
            f'<tr{cls_proj(sj)}><td>{sj["safra"]}</td>'
            f'<td>{fmt_n(sj["exportacao"])}</td>'
            f'<td>{fmt_pct(sj["exportacao"]/sj["producao"]*100)}</td>'
            f'<td>{fmt_n(ml["exportacao"])}</td>'
            f'<td>{fmt_pct(ml["exportacao"]/ml["producao"]*100)}</td>'
            f'<td>{fmt_n(fr["exportacao"],2)}</td>'
            f'<td>{fmt_pct(fr["exportacao"]/fr["producao"]*100)}</td>'
            f'<td>{fmt_n(ol["exportacao"],2)}</td>'
            f'<td>{fmt_pct(ol["exportacao"]/ol["producao"]*100)}</td></tr>')
    ths = ("<th>Safra</th><th>Soja (Mt)</th><th>% Exp/Prod Soja</th>"
           "<th>Milho (Mt)</th><th>% Exp/Prod Milho</th>"
           "<th>Farelo (Mt)</th><th>% Exp/Prod Farelo</th>"
           "<th>Óleo (Mt)</th><th>% Exp/Prod Óleo</th>")
    return (f'<div class="table-wrap"><table><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


# ===================== seções dinâmicas ===============================
def seta(delta: float) -> str:
    if delta > 0:
        return '<span class="delta-up">▲ +{:.1f}</span>'.format(delta)
    if delta < 0:
        return '<span class="delta-dn">▼ {:.1f}</span>'.format(delta)
    return '<span>—</span>'


LABEL_BLOCO = {"soja_grao": "Soja", "milho": "Milho",
               "farelo_soja": "Farelo Soja", "oleo_soja": "Óleo Soja"}
LABEL_CAMPO = {"area": "área", "produtividade": "produtividade",
               "producao": "produção", "producao_1a": "produção 1ª safra",
               "producao_2a": "produção 2ª safra", "exportacao": "exportação",
               "consumo": "consumo interno", "importacao": "importação",
               "estoques": "estoques finais"}


def sec_atualizacoes(muds: list[dict]) -> str:
    if not muds:
        return ('<section class="updates-box"><h2>Atualizações Recentes '
                '<span class="sub">última execução do coletor</span></h2>'
                '<div class="none">Nenhum dado oficial foi modificado nesta '
                'rodada — valores mantidos do snapshot anterior.</div>'
                '</section>')
    itens = []
    for m in muds[:20]:
        bloco = LABEL_BLOCO.get(m["bloco"], m["bloco"])
        campo = LABEL_CAMPO.get(m["campo"], m["campo"])
        try:
            delta = float(m["novo"]) - float(m["anterior"])
        except (TypeError, ValueError):
            delta = 0
        itens.append(
            f'<li><strong>{escape(bloco)} {escape(m["safra"])}</strong> · '
            f'{escape(campo)}: {fmt_n(m["anterior"], 2)} → '
            f'<strong>{fmt_n(m["novo"], 2)}</strong> {seta(delta)} '
            f'<span style="color:#5B6775;font-size:11px">'
            f'[{escape(m.get("fonte","?"))} · '
            f'{escape(str(m.get("periodo","")))}]</span></li>')
    return ('<section class="updates-box"><h2>Atualizações Recentes '
            f'<span class="sub">{len(muds)} campo(s) alterado(s)</span></h2>'
            f'<ul class="updates-list">{"".join(itens)}</ul></section>')


def sec_noticias(noticias: list[dict]) -> str:
    if not noticias:
        return ""
    cards = []
    for n in noticias[:10]:
        link = escape(n.get("link", "#"))
        titulo = escape(n.get("titulo", "")[:160])
        data = escape(n.get("data", "")[:30])
        fonte = escape(n.get("fonte", ""))
        cards.append(
            f'<div class="news-card"><a href="{link}" target="_blank" '
            f'rel="noopener">{titulo}</a>'
            f'<div class="meta">{fonte} · {data}</div></div>')
    return (f'<section><h2>Sinais de Mercado '
            f'<span class="sub">Feed Conab &amp; CEPEA · filtro soja/milho</span></h2>'
            f'<div style="padding:14px;border:1px solid var(--line);'
            f'border-top:none"><div class="news-grid">{"".join(cards)}</div></div>'
            f'</section>')


def sec_analise(dados: dict, muds: list[dict]) -> str:
    sj = dados["soja_grao"]["safras"]
    ml = dados["milho"]["safras"]
    cur_sj, cur_ml = sj[-1], ml[-1]
    ant_sj, ant_ml = sj[-2], ml[-2]
    dl = lambda n, a: round((n - a) / a * 100, 1) if a else 0

    delta_prod_sj = dl(cur_sj["producao"], ant_sj["producao"])
    delta_exp_sj = dl(cur_sj["exportacao"], ant_sj["exportacao"])
    delta_est_sj = dl(cur_sj["estoques"], ant_sj["estoques"])
    delta_prod_ml = dl(cur_ml["producao"], ant_ml["producao"])
    delta_exp_ml = dl(cur_ml["exportacao"], ant_ml["exportacao"])

    aperto_sj = "apertado" if (cur_sj.get("estoque_uso_pct") or 0) < 4 else \
                "confortável" if (cur_sj.get("estoque_uso_pct") or 0) >= 5 else "neutro"
    aperto_ml = "apertado" if (cur_ml.get("estoque_uso_pct") or 0) < 4 else \
                "confortável" if (cur_ml.get("estoque_uso_pct") or 0) >= 5 else "neutro"

    n_muds = len(muds)
    resumo_muds = f"{n_muds} campos atualizados nesta rodada." if n_muds else \
                  "Nenhuma alteração de dado oficial na rodada atual."

    return f"""
<section>
  <h2>Análise Automática de Mercado <span class="sub">gerada a partir do snapshot atual</span></h2>
  <div class="analysis" style="padding:18px 0 0">
    <h3>Mudanças na Oferta</h3>
    <p>Soja {cur_sj['safra']}: produção em <strong>{fmt_n(cur_sj['producao'])} Mt</strong>
    ({delta_prod_sj:+.1f}% vs. safra anterior). Milho {cur_ml['safra']}:
    <strong>{fmt_n(cur_ml['producao'])} Mt</strong> ({delta_prod_ml:+.1f}% vs. safra anterior).
    {resumo_muds}</p>

    <h3>Ritmo de Exportação</h3>
    <p>Soja: {fmt_n(cur_sj['exportacao'])} Mt ({delta_exp_sj:+.1f}% a/a),
    equivale a <strong>{fmt_pct(cur_sj['exportacao']/cur_sj['producao']*100)}</strong>
    da produção. Milho: {fmt_n(cur_ml['exportacao'])} Mt ({delta_exp_ml:+.1f}% a/a),
    ou <strong>{fmt_pct(cur_ml['exportacao']/cur_ml['producao']*100)}</strong> da produção.</p>

    <h3>Impacto nos Estoques</h3>
    <p>Estoques finais de soja em <strong>{fmt_n(cur_sj['estoques'])} Mt</strong>
    (estoque/uso {fmt_pct(cur_sj.get('estoque_uso_pct'))} — cenário <strong>{aperto_sj}</strong>,
    variação de {delta_est_sj:+.1f}% vs. safra anterior). Milho: {fmt_n(cur_ml['estoques'])} Mt
    com estoque/uso {fmt_pct(cur_ml.get('estoque_uso_pct'))} (<strong>{aperto_ml}</strong>).</p>

    <h3>Complexo Esmagamento (Crush)</h3>
    <p>Farelo {dados['farelo_soja']['safras'][-1]['safra']}: produção
    {fmt_n(dados['farelo_soja']['safras'][-1]['producao'])} Mt, exportação
    {fmt_pct(dados['farelo_soja']['safras'][-1].get('pct_exportacao'))} da produção.
    Óleo: produção {fmt_n(dados['oleo_soja']['safras'][-1]['producao'])} Mt,
    exportação apenas {fmt_pct(dados['oleo_soja']['safras'][-1].get('pct_exportacao'))}
    — biodiesel segue como dreno doméstico estrutural.</p>
  </div>
</section>"""


def sec_insights(dados: dict) -> str:
    cur_sj = dados["soja_grao"]["safras"][-1]
    cur_ml = dados["milho"]["safras"][-1]
    eu_sj = cur_sj.get("estoque_uso_pct") or 0
    eu_ml = cur_ml.get("estoque_uso_pct") or 0
    bal_sj = ("APERTADO — viés de alta" if eu_sj < 4
              else "FOLGADO — viés baixista" if eu_sj >= 5
              else "EQUILIBRADO")
    bal_ml = ("APERTADO — viés de alta" if eu_ml < 4
              else "FOLGADO — viés baixista" if eu_ml >= 5
              else "EQUILIBRADO")
    return f"""
<section>
  <h2>Insights — Leitura de Trader</h2>
  <div class="grid-3">
    <div class="card navy"><h4>Balanço Soja</h4>
      <p>Estoque/uso {fmt_pct(eu_sj)} — <strong>{bal_sj}</strong>.
      Qualquer quebra no Centro-Oeste recoloca prêmios rapidamente.</p></div>
    <div class="card navy"><h4>Balanço Milho</h4>
      <p>Estoque/uso {fmt_pct(eu_ml)} — <strong>{bal_ml}</strong>.
      Safrinha continua sendo a variável-chave (fev–mai).</p></div>
    <div class="card warn"><h4>Riscos de Curto Prazo</h4>
      <p>(i) climático safrinha; (ii) câmbio apreciado pressiona rentabilidade;
      (iii) China-EUA no radar tarifário; (iv) logística Arco Norte no pico.</p></div>
    <div class="card"><h4>Preço — Soja</h4>
      <p>Oferta ampla pressiona base. Foco em spreads interno × FOB;
      crush margin positivo sustenta premium do complexo.</p></div>
    <div class="card"><h4>Preço — Milho</h4>
      <p>Etanol de milho é piso estrutural. Exportação competitiva vs. EUA
      depende de câmbio e diferencial logístico.</p></div>
    <div class="card"><h4>Estratégia Comercial</h4>
      <p>Vendido de hedge com opção de recompra em eventos climáticos.
      Spread farelo–óleo favorece processador.</p></div>
  </div>
  <div class="synth-box"><strong style="color:var(--navy)">Síntese:</strong>
  Balanço soja {bal_sj.split(' — ')[0].lower()} e milho
  {bal_ml.split(' — ')[0].lower()}. Monitorar feed de notícias Conab/CEPEA
  para sinais antecipados sobre safrinha e fluxo de exportação.</div>
</section>"""


# ===================== render principal ===============================
def gerar(dados: dict, saida: Path) -> None:
    saida.parent.mkdir(exist_ok=True, parents=True)

    muds_recentes = dados.get("atualizacoes_recentes", [])
    alterados = {(m["safra"], m["campo"]) for m in muds_recentes}
    noticias = dados.get("noticias_feed", [])

    meta = dados["meta"]
    try:
        dt = datetime.fromisoformat(meta["atualizado_em"].replace("Z", "+00:00"))
        data_str = dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, KeyError):
        data_str = meta.get("atualizado_em", "N/A")

    cur_sj = dados["soja_grao"]["safras"][-1]
    cur_ml = dados["milho"]["safras"][-1]

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<title>SnD Brasil — Soja e Milho · Dinâmico</title>
<style>{CSS}</style></head><body><div class="page">

<header class="top">
  <div class="brand">{logo_tag(54)}
    <div class="divider"></div>
    <div class="tagline"><strong>Research &amp; Market Intelligence</strong>
      Modelo Dinâmico · Atualização Automática</div>
  </div>
  <div class="doc-meta">
    <div class="date">Atualizado em {data_str}</div>
    <div>Pipeline: Conab · CEPEA · ComexStat · IBGE · USDA</div>
    <div class="live">● LIVE MODEL</div>
  </div>
</header>

<h1 class="title">Supply and Demand Brasil — Soja e Milho</h1>
<div class="subtitle">Modelo Vivo · Safras 2020/21 a {cur_sj['safra']} (projeção)</div>

<p class="section-intro">
  Relatório automatizado com pipeline de coleta via RSS (Conab, CEPEA) e APIs
  (ComexStat, IBGE SIDRA, USDA PSD). Células destacadas em amarelo ●
  foram modificadas na última execução do coletor.
  Fontes priorizadas: <strong>Conab</strong> (Brasil) · <strong>USDA</strong> (global)
  · <strong>IBGE</strong> (validação cruzada).
</p>

<div class="kpi-row">
  <div class="kpi"><div class="label">Soja {cur_sj['safra']} · Produção</div>
    <div class="value">{fmt_n(cur_sj['producao'])} Mt</div>
    <div class="delta">Est/Uso {fmt_pct(cur_sj.get('estoque_uso_pct'))}</div></div>
  <div class="kpi"><div class="label">Milho {cur_ml['safra']} · Produção</div>
    <div class="value">{fmt_n(cur_ml['producao'])} Mt</div>
    <div class="delta">Est/Uso {fmt_pct(cur_ml.get('estoque_uso_pct'))}</div></div>
  <div class="kpi"><div class="label">Exp. Soja {cur_sj['safra']}</div>
    <div class="value">{fmt_n(cur_sj['exportacao'])} Mt</div>
    <div class="delta">{fmt_pct(cur_sj['exportacao']/cur_sj['producao']*100)} prod.</div></div>
  <div class="kpi"><div class="label">Exp. Milho {cur_ml['safra']}</div>
    <div class="value">{fmt_n(cur_ml['exportacao'])} Mt</div>
    <div class="delta">{fmt_pct(cur_ml['exportacao']/cur_ml['producao']*100)} prod.</div></div>
</div>

{sec_atualizacoes(muds_recentes)}

<section><h2>1. Soja — Grão <span class="sub">Balanço nacional</span></h2>
{tabela_soja(dados, alterados)}
<div class="unit-note">Fonte: Conab / USDA / IBGE · atualizado via API.</div></section>

<section><h2>2. Complexo Soja <span class="sub">Farelo e Óleo</span></h2>
<h3>2.1 Farelo de Soja</h3>{tabela_sub(dados, "farelo_soja", alterados)}
<h3>2.2 Óleo de Soja</h3>{tabela_sub(dados, "oleo_soja", alterados)}</section>

<section><h2>3. Milho <span class="sub">1ª e 2ª safra</span></h2>
{tabela_milho(dados, alterados)}
<div class="unit-note">2ª safra (safrinha) responde por ~80% do total nacional.</div></section>

<section><h2>4. Exportações Consolidadas</h2>{tabela_exportacoes(dados)}</section>

{sec_noticias(noticias)}

{sec_analise(dados, muds_recentes)}

{sec_insights(dados)}

<footer>
  <div class="src"><strong>Fontes:</strong> Conab · USDA/WASDE ·
    IBGE SIDRA (API) · ComexStat (API) · CEPEA ·
    pipeline automatizado Innovagro.</div>
  <div>© 2026 Innovagro Brasil · Modelo dinâmico · Não é recomendação de investimento.</div>
</footer>
</div></body></html>"""
    saida.write_text(html, encoding="utf-8")
