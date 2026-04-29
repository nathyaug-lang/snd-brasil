"""
gerar_alertas_html.py
=====================
Gera o relatório HTML de Market Change Detection.
Layout: seções 'O que mudou · Impacto · Sinais · Alertas Trader'.
"""
from __future__ import annotations
from datetime import datetime
from html import escape
from pathlib import Path

from detector_mudancas import Diagnostico, Mudanca
from gerar_html import logo_tag, fmt_n, fmt_pct


LABEL_BLOCO = {
    "soja_grao": "Soja", "milho": "Milho",
    "farelo_soja": "Farelo de Soja", "oleo_soja": "Óleo de Soja",
    "complexo_soja": "Complexo Soja",
}
LABEL_CAMPO = {
    "area": "Área plantada", "produtividade": "Produtividade",
    "producao": "Produção", "producao_1a": "Produção 1ª safra",
    "producao_2a": "Produção 2ª safra", "importacao": "Importação",
    "consumo": "Consumo interno", "exportacao": "Exportação",
    "estoques": "Estoques finais",
    "estoque_uso_pct": "Estoque/Uso",
    "crush_ratio": "Rendimento de esmagamento",
    "mix_farelo_oleo": "Mix Farelo/Óleo",
}

UNIDADE = {
    "area": "Mi ha", "produtividade": "kg/ha",
    "producao": "Mt", "producao_1a": "Mt", "producao_2a": "Mt",
    "importacao": "Mt", "consumo": "Mt", "exportacao": "Mt",
    "estoques": "Mt", "estoque_uso_pct": "%",
    "crush_ratio": "", "mix_farelo_oleo": "%",
}


# =====================================================================
# CSS (herda visual do SnD principal + estilos de alerta)
# =====================================================================
CSS = r"""
:root{--navy:#0A2342;--green:#1E5631;--green-soft:#2E7D4F;--ink:#1B1F23;
  --muted:#5B6775;--line:#E4E7EB;--zebra:#F7F9FB;--accent:#F3F6F4;
  --warn:#B45309;--danger:#B91C1C;--up:#047857;--down:#B91C1C;
  --alert-bg:#FEF3C7;--alert-br:#F59E0B}
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
.doc-meta .badge{display:inline-block;padding:3px 10px;border-radius:3px;font-size:10px;
  letter-spacing:.1em;margin-top:6px;font-weight:600}
.badge.detector{background:var(--alert-br);color:#fff}
.badge.live{background:var(--green);color:#fff;margin-left:6px}

h1.title{font-size:30px;font-weight:700;color:var(--navy);margin:0 0 4px;letter-spacing:-.01em}
.subtitle{color:var(--green);font-weight:600;font-size:15px;margin-bottom:22px}

.summary-bar{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:18px 0}
.summary{padding:14px 16px;background:var(--accent);border-top:3px solid var(--navy);
  border-bottom:1px solid var(--line)}
.summary .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.summary .value{font-size:22px;color:var(--navy);font-weight:700;margin-top:4px}
.summary.apertado{border-top-color:var(--danger)}
.summary.folgado{border-top-color:var(--up)}
.summary.equilibrado{border-top-color:var(--muted)}
.summary.apertado .value{color:var(--danger)}
.summary.folgado .value{color:var(--up)}
.summary .hint{font-size:11px;color:var(--muted);margin-top:2px}

section{margin-bottom:36px}
h2{font-size:20px;color:#fff;background:var(--navy);margin:0;padding:12px 18px;
  letter-spacing:.02em;border-left:6px solid var(--green);font-weight:600}
h2 .sub{font-weight:400;color:#C9D4E0;font-size:13px;margin-left:10px}
h3{font-size:13px;color:var(--navy);margin:22px 0 10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--line);padding-bottom:5px}

.empty-note{padding:22px;background:var(--zebra);color:var(--muted);
  font-style:italic;text-align:center;border:1px dashed var(--line)}

/* === O QUE MUDOU === */
.changes-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:14px}
.changes-col{border:1px solid var(--line);padding:0}
.changes-col .col-head{background:var(--green);color:#fff;padding:10px 14px;
  font-weight:700;letter-spacing:.04em;text-transform:uppercase;font-size:13px;
  display:flex;justify-content:space-between;align-items:center}
.changes-col .col-head .count{background:#fff;color:var(--green);padding:2px 8px;
  border-radius:20px;font-size:11px;font-weight:700}
.change-item{padding:12px 14px;border-bottom:1px solid var(--line);font-size:13px;display:flex;
  justify-content:space-between;align-items:flex-start;gap:14px}
.change-item:last-child{border-bottom:none}
.change-item .head{font-weight:700;color:var(--navy);font-size:13px}
.change-item .field{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.change-item .values{margin-top:3px;font-size:13px}
.change-item .values .old{color:var(--muted)}
.change-item .values .new{color:var(--navy);font-weight:700}
.change-item .sev{padding:3px 8px;border-radius:3px;font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;flex-shrink:0}
.sev.relevante{background:#DBEAFE;color:#1E40AF}
.sev.estrutural{background:#FEE2E2;color:var(--danger)}
.change-item .delta{margin-left:6px}
.up{color:var(--up);font-weight:700}.down{color:var(--down);font-weight:700}
.change-item .fonte{color:var(--muted);font-size:10px;margin-top:3px}
.change-item .coment{color:var(--navy);font-style:italic;font-size:11px;margin-top:4px}

/* === IMPACTO === */
.impact-table{width:100%;border-collapse:collapse;margin-top:10px;border:1px solid var(--line)}
.impact-table thead th{background:var(--green);color:#fff;font-weight:600;padding:9px 12px;
  font-size:11px;letter-spacing:.04em;text-transform:uppercase;text-align:left}
.impact-table tbody td{padding:8px 12px;border-bottom:1px solid var(--line);font-size:12px}
.impact-table tbody tr:nth-child(even){background:var(--zebra)}
.impact-table td.bloco{font-weight:700;color:var(--navy)}
.impact-table td.center{text-align:center}
.pill{display:inline-block;padding:2px 9px;border-radius:3px;font-size:10px;
  font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.pill.alta{background:#D1FAE5;color:var(--up)}
.pill.baixa{background:#FEE2E2;color:var(--down)}
.pill.neutro{background:var(--line);color:var(--muted)}
.pill.aperto{background:#FECACA;color:var(--danger)}
.pill.folga{background:#BBF7D0;color:var(--up)}

/* === SINAIS === */
.signals{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin-top:12px}
.signal-card{border:1px solid var(--line);padding:0;background:#fff}
.signal-card .sc-head{padding:14px 18px;color:#fff;display:flex;justify-content:space-between;
  align-items:center}
.signal-card.apertado .sc-head{background:var(--danger)}
.signal-card.folgado .sc-head{background:var(--up)}
.signal-card.equilibrado .sc-head{background:var(--muted)}
.signal-card.sem_base .sc-head{background:var(--muted)}
.signal-card .sc-head .commodity{font-size:14px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.signal-card .sc-head .balanco{font-size:18px;font-weight:800}
.signal-card .sc-body{padding:14px 18px;font-size:13px;line-height:1.55}
.signal-card .sc-body dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:4px 14px}
.signal-card .sc-body dt{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.signal-card .sc-body dd{margin:0;color:var(--ink)}
.signal-card .sc-body dd strong{color:var(--navy)}

/* === ALERTAS === */
.alerts-box{border:2px solid var(--alert-br);background:var(--alert-bg);
  padding:16px 20px;margin-top:14px}
.alerts-box h3{color:var(--warn);border-bottom:1px solid var(--alert-br);margin-top:0}
.alerts-list{margin:0;padding:0;list-style:none}
.alerts-list li{padding:10px 0 10px 28px;border-bottom:1px dotted #E4C577;
  font-size:13px;position:relative;color:var(--ink)}
.alerts-list li:last-child{border-bottom:none}
.alerts-list li::before{content:"▲";color:var(--alert-br);position:absolute;left:4px;top:10px;
  font-weight:700;font-size:14px}

.synth{margin-top:22px;padding:18px 22px;background:var(--accent);border-left:4px solid var(--navy)}
.synth strong{color:var(--navy)}

footer{margin-top:46px;padding-top:14px;border-top:1px solid var(--line);
  font-size:11px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
footer .src strong{color:var(--navy)}
"""


# =====================================================================
# helpers de renderização
# =====================================================================
def _seta(delta: float | None) -> str:
    if not delta:
        return '<span>—</span>'
    if delta > 0:
        return f'<span class="up">▲ +{fmt_n(delta, 2)}</span>'
    return f'<span class="down">▼ {fmt_n(delta, 2)}</span>'


def _unit(campo: str) -> str:
    return UNIDADE.get(campo, "")


def _pill(valor: str) -> str:
    v = (valor or "neutro").lower()
    label = {"alta": "↑ Alta", "baixa": "↓ Baixa", "neutro": "— Neutro",
             "aperto": "Aperto", "folga": "Folga"}.get(v, v.capitalize())
    return f'<span class="pill {v}">{label}</span>'


def _sec_o_que_mudou(muds: list[Mudanca]) -> str:
    if not muds:
        return ('<section><h2>1. O que mudou no SnD</h2>'
                '<div class="empty-note">Sem alteração estrutural relevante.</div></section>')

    def _render_item(m: Mudanca) -> str:
        campo = LABEL_CAMPO.get(m.campo, m.campo)
        unit = _unit(m.campo)
        delta_ref = m.delta_abs if m.campo == "estoque_uso_pct" else m.delta_abs
        delta_txt = _seta(delta_ref)
        pct_txt = (f' <span class="delta">({m.delta_pct:+.1f}%)</span>'
                   if m.campo != "estoque_uso_pct" and m.delta_pct else '')
        sev_cls = m.severidade if m.severidade in ("relevante", "estrutural") else "relevante"
        coment = (f'<div class="coment">{escape(m.comentario)}</div>'
                  if m.comentario else '')
        fonte = (f'<div class="fonte">Fonte: {escape(m.fonte)}</div>'
                 if m.fonte else '')
        return (
            f'<div class="change-item">'
            f'  <div style="flex:1">'
            f'    <div class="head">{escape(LABEL_BLOCO.get(m.bloco,m.bloco))} · {escape(m.safra)}</div>'
            f'    <div class="field">{escape(campo)}</div>'
            f'    <div class="values">'
            f'      <span class="old">{fmt_n(m.anterior,2)} {unit}</span>'
            f'      &nbsp;→&nbsp;'
            f'      <span class="new">{fmt_n(m.atual,2)} {unit}</span>'
            f'      &nbsp;{delta_txt}{pct_txt}'
            f'    </div>'
            f'    {coment}{fonte}'
            f'  </div>'
            f'  <span class="sev {sev_cls}">{escape(m.severidade)}</span>'
            f'</div>'
        )

    soja_blocos = ("soja_grao", "farelo_soja", "oleo_soja", "complexo_soja")
    soja = [m for m in muds if m.bloco in soja_blocos]
    milho = [m for m in muds if m.bloco == "milho"]

    def col(titulo: str, itens: list[Mudanca]) -> str:
        if not itens:
            return (f'<div class="changes-col">'
                    f'<div class="col-head">{titulo}<span class="count">0</span></div>'
                    f'<div class="change-item" style="color:var(--muted);'
                    f'font-style:italic;justify-content:center">Sem alterações relevantes.</div>'
                    f'</div>')
        itens.sort(key=lambda x: (x.severidade != "estrutural",
                                  -(abs(x.delta_pct or 0))))
        return (f'<div class="changes-col">'
                f'<div class="col-head">{titulo}<span class="count">{len(itens)}</span></div>'
                + "".join(_render_item(m) for m in itens) +
                f'</div>')

    return (f'<section><h2>1. O que mudou no SnD '
            f'<span class="sub">{len(muds)} alteração(ões) detectada(s)</span></h2>'
            f'<div class="changes-grid">'
            f'{col("Soja · Complexo Soja", soja)}'
            f'{col("Milho", milho)}'
            f'</div></section>')


def _sec_impacto(muds: list[Mudanca]) -> str:
    rel = [m for m in muds if m.severidade in ("relevante", "estrutural")]
    if not rel:
        return ('<section><h2>2. Impacto no Balanço</h2>'
                '<div class="empty-note">Nenhum impacto relevante a reportar.</div></section>')
    linhas = []
    for m in rel:
        linhas.append(
            f'<tr>'
            f'<td class="bloco">{escape(LABEL_BLOCO.get(m.bloco,m.bloco))}</td>'
            f'<td>{escape(m.safra)}</td>'
            f'<td>{escape(LABEL_CAMPO.get(m.campo,m.campo))}</td>'
            f'<td class="center">{_pill(m.impacto_oferta)}</td>'
            f'<td class="center">{_pill(m.impacto_demanda)}</td>'
            f'<td class="center">{_pill(m.impacto_estoques)}</td>'
            f'<td class="center"><span class="sev {m.severidade}">{m.severidade}</span></td>'
            f'</tr>')
    return (f'<section><h2>2. Impacto no Balanço</h2>'
            f'<table class="impact-table">'
            f'<thead><tr><th>Commodity</th><th>Safra</th><th>Campo</th>'
            f'<th style="text-align:center">Oferta</th>'
            f'<th style="text-align:center">Demanda</th>'
            f'<th style="text-align:center">Estoques</th>'
            f'<th style="text-align:center">Severidade</th></tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></section>')


def _sec_sinais(diag: Diagnostico) -> str:
    if not diag.sinais:
        return ('<section><h2>3. Sinais de Mercado</h2>'
                '<div class="empty-note">Sem base comparativa.</div></section>')
    cards = []
    for bloco in ("soja_grao", "milho"):
        s = diag.sinais.get(bloco)
        if not s:
            continue
        cls = s["balanco"].lower() if s.get("balanco") in \
              ("APERTADO", "FOLGADO", "EQUILIBRADO") else "equilibrado"
        eu = s.get("estoque_uso") or 0
        vies_txt = {
            "altista": "Altista — preços sob pressão de alta",
            "baixista": "Baixista — pressão em prêmios",
            "neutro": "Neutro — sem viés claro",
        }.get(s.get("vies", "neutro"), s.get("vies", ""))
        estrut = ("Sim — virada estrutural detectada"
                  if s.get("mudanca_estrutural") else "Não")
        cards.append(
            f'<div class="signal-card {cls}">'
            f'  <div class="sc-head">'
            f'    <span class="commodity">{LABEL_BLOCO[bloco]}</span>'
            f'    <span class="balanco">{s["balanco"]}</span>'
            f'  </div>'
            f'  <div class="sc-body"><dl>'
            f'    <dt>Viés</dt><dd><strong>{escape(vies_txt)}</strong></dd>'
            f'    <dt>Estoque/Uso</dt><dd>{fmt_n(eu,1)}%</dd>'
            f'    <dt>Mudança estrutural</dt><dd>{estrut}</dd>'
            f'    <dt>Nº de mudanças</dt><dd>{s.get("num_mudancas",0)} '
            f'({s.get("num_estruturais",0)} estrutural/is)</dd>'
            f'  </dl></div>'
            f'</div>')
    return (f'<section><h2>3. Sinais de Mercado</h2>'
            f'<div class="signals">{"".join(cards)}</div></section>')


def _sec_alertas(diag: Diagnostico) -> str:
    if not diag.alertas:
        return ('<section><h2>4. Alertas Trader</h2>'
                '<div class="empty-note">Nenhum alerta disparado — sem alteração estrutural relevante.</div></section>')
    itens = "".join(f'<li>{escape(a)}</li>' for a in diag.alertas)
    return ('<section><h2>4. Alertas Trader '
            f'<span class="sub">{len(diag.alertas)} alerta(s) ativo(s)</span></h2>'
            f'<div class="alerts-box">'
            f'<h3>Alertas Prioritários</h3>'
            f'<ul class="alerts-list">{itens}</ul></div></section>')


# =====================================================================
# Render principal
# =====================================================================
def gerar(diag: Diagnostico, meta_atual: dict, meta_anterior: dict | None,
          saida: Path) -> None:
    saida.parent.mkdir(exist_ok=True, parents=True)

    total = len(diag.mudancas)
    rel = sum(1 for m in diag.mudancas if m.severidade == "relevante")
    estr = sum(1 for m in diag.mudancas if m.severidade == "estrutural")

    sj = diag.sinais.get("soja_grao", {})
    ml = diag.sinais.get("milho", {})

    def _dt(meta: dict | None) -> str:
        if not meta:
            return "—"
        try:
            d = datetime.fromisoformat(
                meta["atualizado_em"].replace("Z", "+00:00"))
            return d.strftime("%d/%m/%Y %H:%M")
        except (KeyError, ValueError):
            return meta.get("atualizado_em", "—")

    data_atual = _dt(meta_atual)
    data_ant = _dt(meta_anterior)

    def _summary(label: str, value: str, cls: str = "", hint: str = "") -> str:
        return (f'<div class="summary {cls}"><div class="label">{label}</div>'
                f'<div class="value">{value}</div>'
                f'<div class="hint">{hint}</div></div>')

    summary_bar = "".join([
        _summary("Total mudanças", str(total),
                 hint="vs. snapshot anterior"),
        _summary("Relevantes", str(rel), hint="± 2-5% a/a"),
        _summary("Estruturais", str(estr),
                 cls="apertado" if estr > 0 else "",
                 hint="&gt; threshold estrutural"),
        _summary("Soja", sj.get("balanco", "—"),
                 cls=sj.get("balanco", "").lower() or "sem_base",
                 hint=f"est/uso {fmt_n(sj.get('estoque_uso',0),1)}%"),
        _summary("Milho", ml.get("balanco", "—"),
                 cls=ml.get("balanco", "").lower() or "sem_base",
                 hint=f"est/uso {fmt_n(ml.get('estoque_uso',0),1)}%"),
    ])

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<title>Market Change Detection — Soja e Milho Brasil</title>
<style>{CSS}</style></head><body><div class="page">

<header class="top">
  <div class="brand">{logo_tag(54)}
    <div class="divider"></div>
    <div class="tagline"><strong>Research &amp; Market Intelligence</strong>
      Market Change Detection · Soja &amp; Milho Brasil</div>
  </div>
  <div class="doc-meta">
    <div class="date">Gerado em {data_atual}</div>
    <div>Snapshot anterior: {data_ant}</div>
    <div><span class="badge detector">● DETECTOR ATIVO</span>
         <span class="badge live">LIVE</span></div>
  </div>
</header>

<h1 class="title">Market Change Detection — Soja e Milho</h1>
<div class="subtitle">Análise comparativa entre snapshots do SnD · Sinais, Impactos e Alertas</div>

<div class="summary-bar">{summary_bar}</div>

{_sec_o_que_mudou(diag.mudancas)}
{_sec_impacto(diag.mudancas)}
{_sec_sinais(diag)}
{_sec_alertas(diag)}

<div class="synth"><strong>Síntese executiva:</strong> {escape(diag.resumo)}</div>

<footer>
  <div class="src"><strong>Fontes:</strong> Conab · USDA/WASDE · IBGE SIDRA ·
    ComexStat · CEPEA · Detector Innovagro.</div>
  <div>© 2026 Innovagro Brasil · Market Change Detection ·
    Não constitui recomendação de investimento.</div>
</footer>
</div></body></html>"""
    saida.write_text(html, encoding="utf-8")
