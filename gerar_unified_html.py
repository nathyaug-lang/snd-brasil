"""
gerar_unified_html.py
=====================
Gera o HTML UNIFICADO com três visões alternáveis:
  - Visão Dinâmica: daily update + change detection + destaques de alteração
  - Visão Estática: tabelas limpas, estilo relatório executivo
  - Visão Gráficos: charts SVG de evolução com projeção destacada

Toggle via botão (vanilla JS, sem dependências externas).
Charts em SVG puro — zero dependência de bibliotecas externas (offline-friendly).

Usado pelo pipeline diário (atualizar_snd.py).
"""
from __future__ import annotations
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from detector_mudancas import Diagnostico, Mudanca
from gerar_html import logo_tag, fmt_n, fmt_pct, logo_base64


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
    "crush_ratio": "Rendimento esmagamento",
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
# CSS + JS
# =====================================================================
CSS = r"""
:root{--navy:#0A2342;--green:#1E5631;--green-soft:#2E7D4F;--ink:#1B1F23;
  --muted:#5B6775;--line:#E4E7EB;--zebra:#F7F9FB;--accent:#F3F6F4;
  --warn:#B45309;--danger:#B91C1C;--up:#047857;--down:#B91C1C;
  --new:#FFFBEA;--new-br:#F59E0B;--alert-bg:#FEF3C7}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:#fff;color:var(--ink);
  font-family:"Segoe UI","Inter","Helvetica Neue",Arial,sans-serif;font-size:14px;line-height:1.55;
  -webkit-font-smoothing:antialiased}
.page{max-width:1280px;margin:0 auto;padding:40px 48px 80px}

/* ============ HEADER + TOGGLE ============ */
header.top{display:flex;align-items:center;justify-content:space-between;
  border-bottom:3px solid var(--green);padding-bottom:20px;margin-bottom:22px;
  flex-wrap:wrap;gap:18px}
.brand{display:flex;align-items:center;gap:18px}
.brand .logo{max-height:54px;width:auto;display:block}
.brand .divider{width:1px;height:56px;background:var(--line)}
.brand .tagline{font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase}
.brand .tagline strong{display:block;color:var(--navy);font-size:13px;letter-spacing:.14em;margin-bottom:2px}
.doc-meta{text-align:right;font-size:12px;color:var(--muted)}
.doc-meta .date{color:var(--navy);font-weight:600;font-size:13px}
.doc-meta .badge{display:inline-block;padding:3px 10px;border-radius:3px;font-size:10px;
  letter-spacing:.1em;margin-top:6px;font-weight:600;background:var(--green);color:#fff}

/* === TAB SWITCHER + ACTIONS BAR === */
.toolbar{display:flex;justify-content:space-between;align-items:flex-start;
  flex-wrap:wrap;gap:12px;margin-bottom:22px}
.view-switcher{display:flex;gap:0;background:var(--accent);padding:4px;
  border-radius:6px;border:1px solid var(--line);margin-bottom:0;
  width:fit-content;box-shadow:0 1px 2px rgba(10,35,66,.04)}
.actions{display:flex;gap:8px;align-items:center}
.print-btn{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;
  border:1px solid var(--navy);background:var(--navy);color:#fff;
  border-radius:6px;cursor:pointer;font-family:inherit;font-size:12px;
  font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  transition:background .15s,border-color .15s,transform .1s ease;
  box-shadow:0 1px 3px rgba(10,35,66,.15)}
.print-btn:hover{background:var(--green);border-color:var(--green)}
.print-btn:active{transform:scale(.97)}
.print-btn svg{width:14px;height:14px;flex-shrink:0}
.view-switcher button{padding:9px 20px;border:none;background:transparent;cursor:pointer;
  font-family:inherit;font-size:13px;font-weight:600;color:var(--muted);
  letter-spacing:.04em;text-transform:uppercase;border-radius:4px;transition:all .15s ease}
.view-switcher button:hover{color:var(--navy)}
.view-switcher button.active{background:var(--navy);color:#fff;
  box-shadow:0 2px 6px rgba(10,35,66,.2)}
.view-switcher .dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:8px;
  vertical-align:middle}
.view-switcher button:nth-child(1) .dot{background:var(--new-br)}
.view-switcher button:nth-child(2) .dot{background:var(--muted)}
.view-switcher button:nth-child(3) .dot{background:var(--green)}
.view-switcher button:nth-child(4) .dot{background:var(--navy)}
.view-switcher button:nth-child(5) .dot{background:#8B2D3C}
.view-switcher button:nth-child(6) .dot{background:#C7A23A}
.view-switcher button.active .dot{background:#fff}
.view-switcher{flex-wrap:wrap}

/* ============ CHARTS VIEW ============ */
.charts-view .charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:14px}
.charts-view .charts-grid.full{grid-template-columns:1fr}
.chart-card.wide{grid-column:1 / -1}

/* ============ ESTADOS VIEW ============ */
.states-view .region-block{margin-bottom:30px}
.states-view .region-head{display:flex;align-items:center;justify-content:space-between;
  background:var(--navy);color:#fff;padding:14px 20px;border-left:6px solid var(--green)}
.states-view .region-head .flag{font-size:22px;margin-right:8px}
.states-view .region-head h3{margin:0;color:#fff;border:none;padding:0;
  font-size:16px;letter-spacing:.04em;text-transform:uppercase;font-weight:700}
.states-view .region-head .src{font-size:11px;color:#C9D4E0;letter-spacing:.04em}
.states-view .sources-detail{padding:10px 18px;background:#F7F9FB;
  border:1px solid var(--line);border-top:none;border-bottom:none;
  font-size:11px;color:var(--muted);line-height:1.7}
.states-view .sources-detail strong{color:var(--navy);text-transform:uppercase;
  letter-spacing:.05em;font-size:10px;display:block;margin-bottom:4px}
.states-view .sources-detail ul{margin:0;padding-left:18px}
.states-view .sources-detail li{margin-bottom:2px}
.states-view .commodity-pair{display:grid;grid-template-columns:1fr;gap:24px;
  padding:18px;border:1px solid var(--line);border-top:none;background:#fff}
.states-view .crop-block h4{margin:0 0 10px;font-size:13px;color:var(--navy);
  text-transform:uppercase;letter-spacing:.06em;font-weight:700;
  display:flex;align-items:center;gap:8px}
.states-view .crop-block h4::before{content:"";width:10px;height:10px;border-radius:2px;
  background:var(--c)}
.states-view .crop-block.soja{--c:var(--green)}
.states-view .crop-block.milho{--c:var(--accent)}
table.states{width:100%;border-collapse:collapse;font-size:12px;background:#fff;
  border:1px solid var(--line)}
table.states thead th{background:var(--zebra);color:var(--navy);font-weight:700;
  text-align:right;padding:8px 10px;font-size:11px;letter-spacing:.03em;
  text-transform:uppercase;border-bottom:2px solid var(--line)}
table.states thead th:first-child,table.states thead th:nth-child(2){text-align:left}
table.states tbody td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line)}
table.states tbody td.uf{font-weight:800;color:var(--navy);text-align:left;
  font-family:Consolas,Monaco,monospace;letter-spacing:.5px;width:42px}
table.states tbody td.nome{text-align:left;color:var(--ink);font-weight:600}
table.states tbody tr:nth-child(even){background:var(--zebra)}
table.states tbody tr:hover{background:#EEF4EF}
table.states tbody tr.totals{background:var(--accent) !important;font-weight:700;
  border-top:2px solid var(--navy);color:var(--navy)}
table.states tbody tr.totals td{font-weight:700}
table.states th.proj{background:#E7EEE9;color:var(--green);position:relative}
table.states th.proj::after{content:"proj.";position:absolute;top:2px;right:5px;
  font-size:8px;font-style:italic;font-weight:500;letter-spacing:0;text-transform:none;
  color:var(--green-soft)}
table.states td.proj{background:#F0F5F1;font-style:italic;color:#2E7D4F}
table.states tbody tr:nth-child(even) td.proj{background:#E7EEE9}
table.states colgroup col.col-safra{border-right:1px solid var(--line)}
table.states td.delta{font-size:11px;font-weight:700;width:60px}
table.states td.delta.up{color:var(--up)}
table.states td.delta.dn{color:var(--down)}
.ranking-chart{padding:14px 18px;background:#fff;border:1px solid var(--line);
  border-top:none}
.ranking-chart h4{margin:0 0 8px;font-size:12px;color:var(--navy);text-transform:uppercase;
  letter-spacing:.06em}
.bar-row{display:grid;grid-template-columns:50px 1fr 70px;gap:10px;align-items:center;
  margin-bottom:5px;font-size:11px}
.bar-row .uf{font-weight:800;color:var(--navy);font-family:Consolas,Monaco,monospace}
.bar-row .bar-track{background:var(--zebra);height:18px;border-radius:2px;
  border:1px solid var(--line);position:relative;overflow:hidden}
.bar-row .bar-fill{height:100%;background:var(--c);position:relative;
  display:flex;align-items:center;padding:0 6px;color:#fff;font-weight:700;font-size:10px}
.bar-row .bar-fill.soja{background:var(--green)}
.bar-row .bar-fill.milho{background:var(--accent);color:var(--ink)}
.bar-row .bar-fill.us-soja{background:var(--blue,#3A6EA5)}
.bar-row .bar-fill.us-milho{background:var(--wine,#8B2D3C);color:#fff}
.bar-row .val{text-align:right;color:var(--muted);font-weight:600}
.export-note{margin-top:16px;padding:14px 18px;background:var(--accent);
  border-left:4px solid var(--green);font-size:13px}
.export-note strong{color:var(--navy)}

/* ============ EXPORTACOES UF VIEW ============ */
.exports-view .commodity-block{margin-bottom:30px;border:1px solid var(--line)}
.exports-view .commodity-head{padding:14px 20px;background:var(--navy);color:#fff;
  border-left:6px solid var(--green);display:flex;justify-content:space-between;align-items:center}
.exports-view .commodity-head h3{margin:0;color:#fff;border:none;padding:0;
  font-size:15px;text-transform:uppercase;letter-spacing:.04em}
.exports-view .commodity-head .totals-strip{font-size:11px;color:#C9D4E0;letter-spacing:.04em}
.exports-view .commodity-head .totals-strip strong{color:#fff;font-weight:700}
.exports-view .commodity-body{padding:18px 22px;background:#fff}
table.exports{width:100%;border-collapse:collapse;font-size:12px;background:#fff;
  border:1px solid var(--line)}
table.exports thead th{background:var(--zebra);color:var(--navy);font-weight:700;
  text-align:right;padding:9px 11px;font-size:11px;letter-spacing:.03em;
  text-transform:uppercase;border-bottom:2px solid var(--line)}
table.exports thead th:first-child,table.exports thead th:nth-child(2){text-align:left}
table.exports thead th.current{background:#E7EEE9;color:var(--green-soft)}
table.exports tbody td{padding:8px 11px;text-align:right;border-bottom:1px solid var(--line)}
table.exports tbody td.uf{font-weight:800;color:var(--navy);text-align:left;
  font-family:Consolas,Monaco,monospace;letter-spacing:.5px;width:42px}
table.exports tbody td.nome{text-align:left;color:var(--ink);font-weight:600}
table.exports tbody td.current{background:#F0F5F1;font-weight:700;color:var(--navy)}
table.exports tbody tr:nth-child(even){background:var(--zebra)}
table.exports tbody tr:nth-child(even) td.current{background:#E7EEE9}
table.exports tbody tr:hover{background:#EEF4EF}
table.exports tbody tr.totals{background:var(--accent) !important;font-weight:700;
  border-top:2px solid var(--navy);color:var(--navy)}
table.exports td.delta{font-size:11px;font-weight:700;width:60px}
.exports-view .yoy-bars{padding:14px 18px;border:1px solid var(--line);border-top:none;background:#fff}
.exports-view .yoy-bars h4{margin:0 0 8px;font-size:12px;color:var(--navy);
  text-transform:uppercase;letter-spacing:.06em;font-weight:700}
.bar-row.exp{grid-template-columns:50px 1fr 90px}
.bar-row.exp .bar-fill.exp-soja{background:var(--green)}
.bar-row.exp .bar-fill.exp-milho{background:var(--accent);color:var(--ink)}
.bar-row.exp .bar-fill.exp-farelo{background:var(--wine,#8B2D3C)}
.bar-row.exp .bar-fill.exp-oleo{background:var(--blue,#3A6EA5)}
.disclaimer-box{margin-top:20px;padding:14px 18px;background:#FEF3C7;
  border:1px solid var(--new-br);font-size:12px;color:#78350F}
.disclaimer-box strong{color:#92400E}

/* ============ CAPACIDADES VIEW ============ */
.cap-view .cap-summary{padding:16px 20px;background:var(--accent);
  border-left:4px solid var(--navy);margin-bottom:18px;font-size:13px}
.cap-view .cap-summary strong{color:var(--navy)}
.cap-view .legend-types{display:flex;flex-wrap:wrap;gap:14px;padding:10px 18px;
  background:var(--zebra);border:1px solid var(--line);font-size:11px;color:var(--muted);
  margin-bottom:0;border-bottom:none}
.cap-view .legend-types .lg{display:flex;align-items:center;gap:6px}
.cap-view .legend-types .lg .swatch{width:14px;height:10px;display:inline-block;border-radius:2px}
.cap-view .legend-types .lg.particular .swatch{background:#1E5631}
.cap-view .legend-types .lg.cooperativa .swatch{background:#C7A23A}
.cap-view .legend-types .lg.exportador .swatch{background:#3A6EA5}
.cap-view .legend-types .lg.outros .swatch{background:#8B2D3C}

table.cap{width:100%;border-collapse:collapse;font-size:12px;background:#fff;
  border:1px solid var(--line)}
table.cap thead th{background:var(--green);color:#fff;font-weight:700;
  text-align:right;padding:10px 12px;font-size:11px;letter-spacing:.04em;
  text-transform:uppercase;border-bottom:2px solid var(--navy)}
table.cap thead th:first-child,table.cap thead th:nth-child(2){text-align:left}
table.cap tbody td{padding:8px 12px;text-align:right;border-bottom:1px solid var(--line)}
table.cap tbody td.uf{font-weight:800;color:var(--navy);text-align:left;
  font-family:Consolas,Monaco,monospace;letter-spacing:.5px;width:42px}
table.cap tbody td.nome{text-align:left;color:var(--ink);font-weight:600}
table.cap tbody tr:nth-child(even){background:var(--zebra)}
table.cap tbody tr:hover{background:#EEF4EF}
table.cap tbody tr.totals{background:var(--accent) !important;font-weight:700;
  border-top:2px solid var(--navy);color:var(--navy)}
table.cap td.total{font-weight:800;color:var(--navy);background:#F0F5F1}
table.cap td.deficit{font-weight:700;font-size:11px}
table.cap td.deficit.high{color:var(--danger);background:#FEE2E2}
table.cap td.deficit.mid{color:var(--warn);background:#FEF3C7}
table.cap td.deficit.ok{color:var(--up);background:#D1FAE5}
table.cap td.bar-cell{padding:4px 8px;background:#fff !important}

/* Barra empilhada inline na linha (composição por tipo) */
.cap-stack-bar{display:flex;height:16px;border-radius:2px;overflow:hidden;
  border:1px solid var(--line);min-width:160px}
.cap-stack-bar .seg{height:100%;display:flex;align-items:center;justify-content:center;
  font-size:9px;font-weight:700;color:#fff;overflow:hidden;white-space:nowrap}
.cap-stack-bar .seg.particular{background:#1E5631}
.cap-stack-bar .seg.cooperativa{background:#C7A23A;color:var(--navy)}
.cap-stack-bar .seg.exportador{background:#3A6EA5}
.cap-stack-bar .seg.outros{background:#8B2D3C}

/* Mini cards de breakdown */
.cap-breakdown{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}
.cap-breakdown .cb-card{padding:12px 14px;background:#fff;border:1px solid var(--line);
  border-top:3px solid var(--c)}
.cap-breakdown .cb-card.particular{--c:#1E5631}
.cap-breakdown .cb-card.cooperativa{--c:#C7A23A}
.cap-breakdown .cb-card.exportador{--c:#3A6EA5}
.cap-breakdown .cb-card.outros{--c:#8B2D3C}
.cap-breakdown .cb-card .label{font-size:10px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.08em}
.cap-breakdown .cb-card .value{font-size:22px;color:var(--navy);font-weight:800;margin-top:4px}
.cap-breakdown .cb-card .pct{font-size:11px;color:var(--c);font-weight:700;margin-top:2px}

/* ============ COPY-AS-IMAGE BUTTON ============ */
.copy-btn{position:absolute;top:8px;right:8px;z-index:20;
  width:28px;height:28px;padding:0;border-radius:4px;
  border:1px solid var(--line);background:rgba(255,255,255,.85);
  color:var(--muted);cursor:pointer;display:inline-flex;
  align-items:center;justify-content:center;opacity:.45;
  transition:opacity .15s ease,color .15s ease,border-color .15s ease,background .15s ease;
  backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px)}
.copy-btn:hover{opacity:1;color:var(--navy);border-color:var(--navy);
  background:#fff}
.copy-btn:active{transform:scale(0.95)}
.copy-btn:disabled{cursor:wait;opacity:0.6}
.copy-btn.success{opacity:1;color:#fff;background:var(--green);border-color:var(--green)}
.copy-btn.error{opacity:1;color:#fff;background:var(--danger);border-color:var(--danger)}
.copy-btn svg{display:block;pointer-events:none}
.copy-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
  background:var(--navy);color:#fff;padding:10px 20px;border-radius:4px;
  font-size:13px;font-weight:600;letter-spacing:.03em;z-index:9999;
  box-shadow:0 4px 12px rgba(10,35,66,.25);opacity:0;
  transition:opacity .25s ease,transform .25s ease;pointer-events:none}
.copy-toast.show{opacity:1;transform:translateX(-50%) translateY(-4px)}
.copy-toast.error{background:var(--danger)}
@media print{.copy-btn,.copy-toast{display:none !important}}
.chart-card{border:1px solid var(--line);background:#fff;padding:0;
  display:flex;flex-direction:column;overflow:hidden}
.chart-card .ch-head{padding:12px 18px;background:var(--accent);
  border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:baseline}
.chart-card .ch-head h3{margin:0;font-size:13px;color:var(--navy);text-transform:uppercase;
  letter-spacing:.06em;font-weight:700;border:none;padding:0}
.chart-card .ch-head .ch-sub{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.chart-card .ch-svg{padding:14px 16px 8px;background:#fff;position:relative;overflow:hidden}
.chart-card .ch-svg::before{
  content:"";position:absolute;top:14px;right:16px;bottom:8px;left:16px;
  background-image:var(--watermark);background-position:center center;
  background-repeat:no-repeat;background-size:55% auto;
  opacity:0.07;pointer-events:none;z-index:0}
.chart-card .ch-svg svg{display:block;width:100%;height:auto;position:relative;z-index:1}
.chart-card .ch-foot{padding:8px 18px 12px;border-top:1px solid var(--line);
  font-size:11px;color:var(--muted);background:var(--zebra);
  display:flex;justify-content:space-between;align-items:baseline;
  gap:14px;flex-wrap:wrap}
.chart-card .ch-foot .ch-note{flex:1;min-width:180px}
.chart-card .ch-foot .ch-source{font-size:9px;font-style:italic;
  color:var(--muted);opacity:.6;white-space:nowrap;letter-spacing:.02em}
.chart-legend{display:flex;flex-wrap:wrap;gap:14px;padding:8px 16px 12px;
  font-size:11px;color:var(--muted);border-top:1px solid var(--line)}
.chart-legend .lg{display:flex;align-items:center;gap:6px}
.chart-legend .lg .swatch{width:14px;height:10px;display:inline-block;border-radius:2px}
.chart-legend .lg.proj .swatch{background:repeating-linear-gradient(45deg,#0A2342 0 4px,transparent 4px 8px);
  border:1px solid var(--navy)}

/* === VIEW CONTAINERS === */
.view{display:none}
.view.active{display:block;animation:fadeIn .2s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

/* ============ GENERAL TYPO ============ */
h1.title{font-size:30px;font-weight:700;color:var(--navy);margin:0 0 4px;letter-spacing:-.01em}
.subtitle{color:var(--green);font-weight:600;font-size:15px;margin-bottom:22px}
.intro{color:var(--muted);font-size:13px;margin-bottom:22px;max-width:960px}

section{margin-bottom:40px}
h2{font-size:20px;color:#fff;background:var(--navy);margin:0;padding:12px 18px;
  letter-spacing:.02em;border-left:6px solid var(--green);font-weight:600}
h2 .sub{font-weight:400;color:#C9D4E0;font-size:13px;margin-left:10px}
h3{font-size:13px;color:var(--navy);margin:22px 0 10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--line);padding-bottom:5px}

/* ============ KPI BAR ============ */
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 10px}
.kpi{padding:14px 16px;background:var(--accent);border-top:3px solid var(--green);
  border-bottom:1px solid var(--line)}
.kpi .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.kpi .value{font-size:20px;color:var(--navy);font-weight:700;margin-top:4px}
.kpi .delta{font-size:12px;color:var(--green);margin-top:2px;font-weight:600}

/* ============ TABLES ============ */
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-top:none}
table.snd{width:100%;border-collapse:collapse;font-size:13px;background:#fff}
table.snd thead th{background:var(--green);color:#fff;font-weight:600;text-align:right;
  padding:10px 12px;font-size:12px;letter-spacing:.03em;text-transform:uppercase;
  border-bottom:2px solid var(--navy)}
table.snd thead th:first-child{text-align:left}
table.snd tbody td{padding:9px 12px;text-align:right;border-bottom:1px solid var(--line)}
table.snd tbody td:first-child{text-align:left;font-weight:600;color:var(--navy)}
table.snd tbody tr:nth-child(even){background:var(--zebra)}
table.snd tbody tr:hover{background:#EEF4EF}
table.snd tbody tr.projection td{font-style:italic;color:var(--muted)}
table.snd tbody tr.projection td:first-child{color:var(--green);font-style:normal}
table.snd tbody tr.projection td:first-child::after{content:"  proj.";font-size:10px;
  color:var(--green-soft);font-weight:500;letter-spacing:.05em;text-transform:uppercase;font-style:italic}
td.hl-stock,th.hl-stock{background:#F0F5F1}
td.hl-ratio,th.hl-ratio{background:#F0F5F1;font-weight:600;color:var(--green)}
table.snd tbody tr:nth-child(even) td.hl-stock,
table.snd tbody tr:nth-child(even) td.hl-ratio{background:#E7EEE9}
/* Célula alterada (só visão dinâmica) */
.dynamic-view td.changed{background:var(--new) !important;position:relative;
  font-weight:700;color:#9A3412}
.dynamic-view td.changed::after{content:"●";color:var(--new-br);position:absolute;
  top:2px;right:4px;font-size:10px}
.unit-note{font-size:11px;color:var(--muted);margin:6px 0 0;text-align:right}

/* ============ DAILY UPDATE (visão dinâmica) ============ */
.daily-box{border:2px solid var(--new-br);background:var(--new);padding:18px 22px;
  border-radius:4px;margin-bottom:22px}
.daily-box h2{background:var(--new-br);color:#fff;border-left-color:#B45309;margin:-18px -22px 14px;
  padding:12px 22px}
.daily-box .daily-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.daily-col h3{color:var(--warn);border-bottom:1px dashed var(--new-br);margin-top:0}
.daily-col ul{margin:0;padding:0;list-style:none}
.daily-col li{padding:8px 0 8px 22px;border-bottom:1px dotted #E4C577;font-size:13px;
  position:relative}
.daily-col li:last-child{border-bottom:none}
.daily-col li::before{content:"●";color:var(--new-br);position:absolute;left:0;top:9px;font-size:11px}
.daily-col .empty{color:var(--muted);font-style:italic;padding:10px 0}
.daily-col strong{color:var(--navy)}
.daily-col .delta-up{color:var(--up);font-weight:700}
.daily-col .delta-dn{color:var(--down);font-weight:700}

/* ============ IMPACT + SIGNALS ============ */
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
.sev{padding:3px 8px;border-radius:3px;font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
.sev.relevante{background:#DBEAFE;color:#1E40AF}
.sev.estrutural{background:#FEE2E2;color:var(--danger)}

.signals{display:grid;grid-template-columns:repeat(2,1fr);gap:18px;margin-top:12px}
.signal-card{border:1px solid var(--line);background:#fff}
.signal-card .sc-head{padding:14px 18px;color:#fff;display:flex;justify-content:space-between;
  align-items:center}
.signal-card.apertado .sc-head{background:var(--danger)}
.signal-card.folgado .sc-head{background:var(--up)}
.signal-card.equilibrado .sc-head,.signal-card.sem_base .sc-head{background:var(--muted)}
.signal-card .sc-head .commodity{font-size:14px;font-weight:700;letter-spacing:.05em;text-transform:uppercase}
.signal-card .sc-head .balanco{font-size:18px;font-weight:800}
.signal-card .sc-body{padding:14px 18px;font-size:13px;line-height:1.55}
.signal-card .sc-body dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:4px 14px}
.signal-card .sc-body dt{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.signal-card .sc-body dd{margin:0;color:var(--ink)}
.signal-card .sc-body dd strong{color:var(--navy)}

.alerts-box{border:2px solid var(--new-br);background:var(--alert-bg);
  padding:16px 20px;margin-top:14px}
.alerts-box h3{color:var(--warn);border-bottom:1px solid var(--new-br);margin-top:0}
.alerts-list{margin:0;padding:0;list-style:none}
.alerts-list li{padding:10px 0 10px 28px;border-bottom:1px dotted #E4C577;font-size:13px;
  position:relative;color:var(--ink)}
.alerts-list li:last-child{border-bottom:none}
.alerts-list li::before{content:"▲";color:var(--new-br);position:absolute;left:4px;top:10px;
  font-weight:700;font-size:14px}

/* ============ NEWS FEED ============ */
.news-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:14px;
  border:1px solid var(--line);border-top:none}
.news-card{padding:10px 12px;border-left:3px solid var(--green);background:var(--zebra);font-size:12px}
.news-card a{color:var(--navy);text-decoration:none;font-weight:600}
.news-card a:hover{text-decoration:underline}
.news-card .meta{color:var(--muted);font-size:11px;margin-top:4px}

/* ============ ANALYSIS + INSIGHTS ============ */
.analysis{padding:18px 0 0}
.analysis p{margin:0 0 12px;max-width:960px}.analysis strong{color:var(--navy)}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.card{border:1px solid var(--line);border-left:4px solid var(--green);padding:14px 16px;background:#fff}
.card h4{margin:0 0 8px;font-size:12px;letter-spacing:.1em;color:var(--navy);text-transform:uppercase;font-weight:700}
.card p{margin:0;font-size:13px;line-height:1.55}
.card.navy{border-left-color:var(--navy)}
.card.warn{border-left-color:var(--warn)}.card.warn h4{color:var(--warn)}
.synth{margin-top:22px;padding:18px 22px;background:var(--accent);border-left:4px solid var(--navy)}
.synth strong{color:var(--navy)}

/* ============ STATIC VIEW TWEAKS ============ */
.static-view .static-label{display:inline-block;margin-bottom:14px;padding:4px 12px;
  background:var(--navy);color:#fff;font-size:10px;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase}

/* ============ FOOTER ============ */
footer{margin-top:50px;padding-top:16px;border-top:1px solid var(--line);
  font-size:11px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
footer .src strong{color:var(--navy)}

@media print{
  /* preserva cores em backgrounds (h2 navy, thead verde, KPIs, etc.) */
  *{-webkit-print-color-adjust:exact !important;print-color-adjust:exact !important}
  /* só margem — orientação e tamanho ficam por conta do usuário no diálogo */
  @page{margin:1.2cm 1cm}
  html,body{background:#fff}
  .page{max-width:none;padding:0}
  /* esconde UI de interação */
  .toolbar,.view-switcher,.actions,.print-btn,.copy-btn,.copy-toast{display:none !important}
  /* mostra TODAS as visões em sequência */
  .view{display:block !important;animation:none !important}
  .view + .view{page-break-before:always;padding-top:18px;margin-top:18px}
  /* page-break inteligente */
  section{page-break-inside:avoid}
  .chart-card,.crop-block,.commodity-block,.region-block{page-break-inside:avoid}
  table{page-break-inside:auto;font-size:10px}
  tr{page-break-inside:avoid}
  thead{display:table-header-group}
  h2,h3{page-break-after:avoid}
  .kpi-row{grid-template-columns:repeat(4,1fr)}
  .grid-3,.grid-2,.signals,.cap-breakdown{page-break-inside:avoid}
  /* feed de notícias polui PDF — esconde */
  .news-grid{display:none !important}
  /* charts mantêm proporção */
  .chart-card .ch-svg svg{max-width:100%;height:auto}
  footer{page-break-inside:avoid}
}
"""

JS = r"""
(function(){
  // ============ TOGGLE DE VISÕES ============
  const buttons = document.querySelectorAll('.view-switcher button');
  const views = document.querySelectorAll('.view');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.view;
      buttons.forEach(b => b.classList.toggle('active', b === btn));
      views.forEach(v => v.classList.toggle('active', v.dataset.view === target));
      try { localStorage.setItem('snd-view', target); } catch(e){}
    });
  });
  try {
    const saved = localStorage.getItem('snd-view');
    if (saved) {
      const btn = document.querySelector('.view-switcher button[data-view="'+saved+'"]');
      if (btn) btn.click();
    }
  } catch(e){}

  // ============ COPIAR COMO IMAGEM ============
  const ICON_COPY = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21,15 16,10 5,21"/></svg>';
  const ICON_OK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20,6 9,17 4,12"/></svg>';
  const ICON_ERR = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';

  let toast;
  function showToast(msg, isError){
    if(!toast){
      toast = document.createElement('div');
      toast.className = 'copy-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.toggle('error', !!isError);
    toast.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => toast.classList.remove('show'), 2200);
  }

  // Inlina estilos computados (clone <- src) — necessário p/ foreignObject
  function inlineStyles(srcRoot, dstRoot){
    const allowed = ['display','position','top','left','right','bottom','width',
      'height','min-width','min-height','max-width','max-height','padding',
      'padding-top','padding-right','padding-bottom','padding-left','margin',
      'margin-top','margin-right','margin-bottom','margin-left','border',
      'border-top','border-right','border-bottom','border-left','border-color',
      'border-width','border-style','border-radius','box-sizing','color',
      'background','background-color','background-image','background-position',
      'background-repeat','background-size','font-family','font-size',
      'font-weight','font-style','line-height','letter-spacing','text-align',
      'text-decoration','text-transform','vertical-align','white-space',
      'overflow','overflow-x','overflow-y','flex','flex-direction','flex-wrap',
      'justify-content','align-items','align-content','grid-template-columns',
      'grid-template-rows','grid-column','grid-row','gap','column-gap','row-gap',
      'opacity','transform','box-shadow','table-layout','border-collapse',
      'border-spacing','content','list-style'];
    const src = [srcRoot, ...srcRoot.querySelectorAll('*')];
    const dst = [dstRoot, ...dstRoot.querySelectorAll('*')];
    for(let i = 0; i < src.length; i++){
      const cs = window.getComputedStyle(src[i]);
      let s = '';
      for(const p of allowed){
        const v = cs.getPropertyValue(p);
        if(v) s += p + ':' + v + ';';
      }
      dst[i].setAttribute('style', s);
    }
  }

  // Carrega Image() a partir de string SVG
  function svgToImage(xml){
    return new Promise((resolve, reject) => {
      const blob = new Blob([xml], {type: 'image/svg+xml;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const img = new Image();
      img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
      img.onerror = (e) => { URL.revokeObjectURL(url); reject(e); };
      img.src = url;
    });
  }

  // Renderiza imagem em canvas com fundo branco e padding
  function imgToCanvas(img, w, h, scale, pad){
    const canvas = document.createElement('canvas');
    canvas.width = (w + pad * 2) * scale;
    canvas.height = (h + pad * 2) * scale;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, pad * scale, pad * scale, w * scale, h * scale);
    return canvas;
  }

  function canvasToBlob(canvas){
    return new Promise(res => canvas.toBlob(res, 'image/png'));
  }

  // Helper: marca-d'água como elemento SVG <image>
  function makeWatermarkImage(SVG_NS, sw, sh){
    const wmVar = getComputedStyle(document.documentElement)
                  .getPropertyValue('--watermark').trim();
    const m = wmVar.match(/url\(["']?([^"')]+)["']?\)/);
    if(!m) return null;
    const wmW = sw * 0.5;
    const wmH = wmW / 4.88;
    const wm = document.createElementNS(SVG_NS, 'image');
    wm.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', m[1]);
    wm.setAttribute('href', m[1]);
    wm.setAttribute('x', String((sw - wmW) / 2));
    wm.setAttribute('y', String((sh - wmH) / 2));
    wm.setAttribute('width', String(wmW));
    wm.setAttribute('height', String(wmH));
    wm.setAttribute('opacity', '0.07');
    wm.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    return wm;
  }

  // Chart-card -> PNG via SVG composto puro (sem foreignObject)
  // Compõe header (título + subtítulo), chart com marca-d'água, legenda e nota
  async function chartCardToBlob(card, scale){
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const innerSvg = card.querySelector('.ch-svg svg');
    if(!innerSvg) throw new Error('SVG do chart não encontrado');

    const r = innerSvg.getBoundingClientRect();
    const cw = Math.max(1, Math.round(r.width));
    const ch = Math.max(1, Math.round(r.height));

    const titleText = (card.querySelector('.ch-head h3')?.textContent || '').trim();
    const subText = (card.querySelector('.ch-head .ch-sub')?.textContent || '').trim();
    const legendItems = Array.from(card.querySelectorAll('.chart-legend .lg'));
    // Nota e fonte separadas (rodapé com 2 linhas se ambas existirem)
    const noteEl = card.querySelector('.ch-foot .ch-note');
    const sourceEl = card.querySelector('.ch-foot .ch-source');
    const footText = (noteEl ? noteEl.textContent
                              : (card.querySelector('.ch-foot')?.textContent || '')).trim();
    const sourceText = (sourceEl?.textContent || '').trim();

    const PAD = 16;
    const HEADER_H = 44;
    const LEGEND_H = legendItems.length ? 32 : 8;
    // Se há fonte, footer fica mais alto (2 linhas)
    const FOOTER_H = (footText || sourceText) ? (sourceText ? 50 : 38) : 8;
    const W = cw + PAD * 2;
    const H = HEADER_H + ch + LEGEND_H + FOOTER_H;

    const out = document.createElementNS(SVG_NS, 'svg');
    out.setAttribute('xmlns', SVG_NS);
    out.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
    out.setAttribute('width', String(W));
    out.setAttribute('height', String(H));
    out.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

    // Função utilitária para criar nós SVG
    const mk = (tag, attrs, text) => {
      const el = document.createElementNS(SVG_NS, tag);
      for(const k in attrs) el.setAttribute(k, String(attrs[k]));
      if(text != null) el.textContent = text;
      return el;
    };

    // Fundo branco
    out.appendChild(mk('rect', {x:0, y:0, width:W, height:H, fill:'#fff'}));

    // Banda do header
    out.appendChild(mk('rect', {x:0, y:0, width:W, height:HEADER_H, fill:'#F3F6F4'}));
    out.appendChild(mk('rect', {x:0, y:HEADER_H-1, width:W, height:1, fill:'#E4E7EB'}));

    // Título (uppercase navy)
    out.appendChild(mk('text', {
      x:PAD, y:HEADER_H/2 + 4,
      'font-family':'Segoe UI, Arial, sans-serif',
      'font-size':13, 'font-weight':700, fill:'#0A2342',
      'letter-spacing':'0.6'
    }, titleText.toUpperCase()));

    // Subtítulo (right-aligned, gray uppercase)
    if(subText){
      out.appendChild(mk('text', {
        x:W - PAD, y:HEADER_H/2 + 4,
        'text-anchor':'end',
        'font-family':'Segoe UI, Arial, sans-serif',
        'font-size':11, fill:'#5B6775',
        'letter-spacing':'0.4'
      }, subText.toUpperCase()));
    }

    // Chart: clona o SVG interno, insere marca-d'água, posiciona via x/y
    const chart = innerSvg.cloneNode(true);
    chart.setAttribute('xmlns', SVG_NS);
    chart.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');
    chart.removeAttribute('width');
    chart.removeAttribute('height');
    chart.setAttribute('width', String(cw));
    chart.setAttribute('height', String(ch));
    chart.setAttribute('x', String(PAD));
    chart.setAttribute('y', String(HEADER_H));
    const wm = makeWatermarkImage(SVG_NS, cw, ch);
    if(wm) chart.insertBefore(wm, chart.firstChild);
    out.appendChild(chart);

    // Legenda
    if(legendItems.length){
      const legY = HEADER_H + ch + 18;
      let lx = PAD;
      for(const lg of legendItems){
        const swatch = lg.querySelector('.swatch');
        const text = lg.textContent.trim();
        const swColor = swatch ? getComputedStyle(swatch).backgroundColor : '#999';
        out.appendChild(mk('rect', {
          x:lx, y:legY-9, width:14, height:10, rx:2, fill:swColor
        }));
        out.appendChild(mk('text', {
          x:lx+20, y:legY,
          'font-family':'Segoe UI, Arial, sans-serif',
          'font-size':11, fill:'#5B6775'
        }, text));
        // Avança x estimando largura do texto (~6.3px por char + paddings)
        lx += 20 + Math.min(text.length * 6.3 + 14, 220);
        if(lx > W - 100){ break; }   // evita overflow horizontal
      }
    }

    // Rodapé (linha 1: nota · linha 2: fonte semi-transparente)
    if(footText || sourceText){
      const footY = HEADER_H + ch + LEGEND_H;
      out.appendChild(mk('rect', {x:0, y:footY, width:W, height:FOOTER_H, fill:'#F7F9FB'}));
      out.appendChild(mk('rect', {x:0, y:footY, width:W, height:1, fill:'#E4E7EB'}));
      // Linha 1 — nota (texto principal do rodapé)
      if(footText){
        const maxChars = Math.floor((W - PAD*2) / 5.5);
        const ft = footText.length > maxChars ? footText.slice(0, maxChars - 3) + '...' : footText;
        const noteY = sourceText ? footY + 16 : footY + FOOTER_H/2 + 4;
        out.appendChild(mk('text', {
          x:PAD, y:noteY,
          'font-family':'Segoe UI, Arial, sans-serif',
          'font-size':11, fill:'#5B6775'
        }, ft));
      }
      // Linha 2 — fonte (pequena, itálica, semi-transparente)
      if(sourceText){
        const srcY = footY + FOOTER_H - 8;
        const maxSrc = Math.floor((W - PAD*2) / 4.5);
        const st = sourceText.length > maxSrc ? sourceText.slice(0, maxSrc - 3) + '...' : sourceText;
        out.appendChild(mk('text', {
          x:W - PAD, y:srcY,
          'text-anchor':'end',
          'font-family':'Segoe UI, Arial, sans-serif',
          'font-size':9, 'font-style':'italic',
          fill:'#5B6775', 'fill-opacity':'0.65',
          'letter-spacing':'0.3'
        }, st));
      }
    }

    const xml = new XMLSerializer().serializeToString(out);
    const img = await svgToImage(xml);
    const canvas = imgToCanvas(img, W, H, scale, 0);
    return canvasToBlob(canvas);
  }

  // HTML element -> PNG (via foreignObject + computed styles inline)
  // Re-injeta marca-d'água em qualquer SVG de chart aninhado.
  async function htmlElementToBlob(el, scale){
    const rect = el.getBoundingClientRect();
    const w = Math.max(el.scrollWidth, Math.round(rect.width));
    const h = Math.max(el.scrollHeight, Math.round(rect.height));

    const cloned = el.cloneNode(true);
    cloned.querySelectorAll('.copy-btn').forEach(b => b.remove());
    inlineStyles(el, cloned);

    // Re-injeta marca-d'água nos SVGs internos (charts dentro de chart-card)
    const wmVar = getComputedStyle(document.documentElement)
                  .getPropertyValue('--watermark').trim();
    const m = wmVar.match(/url\(["']?([^"')]+)["']?\)/);
    if(m){
      const srcSvgs = el.querySelectorAll('.ch-svg svg');
      const dstSvgs = cloned.querySelectorAll('.ch-svg svg');
      srcSvgs.forEach((srcSvg, i) => {
        const dstSvg = dstSvgs[i];
        if(!dstSvg) return;
        const r = srcSvg.getBoundingClientRect();
        const sw = r.width || 720;
        const sh = r.height || 320;
        // Garante dimensões explícitas no clone (foreignObject precisa)
        dstSvg.setAttribute('width', String(sw));
        dstSvg.setAttribute('height', String(sh));
        const wmW = sw * 0.5;
        const wmH = wmW / 4.88;
        const wm = document.createElementNS('http://www.w3.org/2000/svg', 'image');
        wm.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', m[1]);
        wm.setAttribute('href', m[1]);
        wm.setAttribute('x', String((sw - wmW) / 2));
        wm.setAttribute('y', String((sh - wmH) / 2));
        wm.setAttribute('width', String(wmW));
        wm.setAttribute('height', String(wmH));
        wm.setAttribute('opacity', '0.07');
        wm.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        dstSvg.insertBefore(wm, dstSvg.firstChild);
      });
    }

    // Constrói SVG com foreignObject
    const xmlClone = new XMLSerializer().serializeToString(cloned);
    const xml = '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '">' +
                '<foreignObject width="100%" height="100%">' +
                '<div xmlns="http://www.w3.org/1999/xhtml" ' +
                'style="width:' + w + 'px;background:#fff;font-family:Segoe UI,Inter,Arial,sans-serif">' +
                xmlClone + '</div></foreignObject></svg>';
    const img = await svgToImage(xml);
    const canvas = imgToCanvas(img, w, h, scale, 16);
    return canvasToBlob(canvas);
  }

  async function copyOrDownload(blob, filename){
    if(!blob) throw new Error('blob vazio');
    // 1) Tenta clipboard (Chrome/Edge/Firefox modernos)
    if(navigator.clipboard && window.ClipboardItem){
      try{
        await navigator.clipboard.write([new ClipboardItem({'image/png': blob})]);
        return 'clipboard';
      }catch(e){ /* fallback */ }
    }
    // 2) Fallback: download
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      a.remove();
    }, 100);
    return 'download';
  }

  function makeBtn(handler){
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.title = 'Copiar como imagem';
    btn.setAttribute('aria-label', 'Copiar como imagem');
    btn.innerHTML = ICON_COPY;
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      e.preventDefault();
      btn.disabled = true;
      try{
        const result = await handler();
        btn.classList.add('success');
        btn.innerHTML = ICON_OK;
        showToast(result === 'clipboard' ?
                  '✓ Imagem copiada — cole onde precisar (Ctrl+V)' :
                  '↓ Imagem baixada (clipboard indisponível)');
      }catch(err){
        console.error('Falha ao copiar:', err);
        btn.classList.add('error');
        btn.innerHTML = ICON_ERR;
        const msg = (err && err.message) ? err.message : String(err);
        showToast('Erro: ' + msg.slice(0, 90), true);
      }
      setTimeout(() => {
        btn.classList.remove('success', 'error');
        btn.innerHTML = ICON_COPY;
        btn.disabled = false;
      }, 1800);
    });
    return btn;
  }

  function ensureRelative(el){
    const pos = getComputedStyle(el).position;
    if(pos === 'static') el.style.position = 'relative';
  }

  function safeFilename(label){
    return (label || 'snd-innovagro').toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 60) || 'snd';
  }

  function attachToElement(el){
    if(el.querySelector(':scope > .copy-btn')) return;
    const isChart = el.classList.contains('chart-card');
    const handler = async () => {
      let blob;
      if(isChart){
        // SVG composto puro — sem foreignObject (mais robusto)
        blob = await chartCardToBlob(el, 2);
      } else {
        // foreignObject + computed styles — para tabelas e demais
        blob = await htmlElementToBlob(el, 2);
      }
      const t = el.querySelector('h2,h3,h4,caption');
      return copyOrDownload(blob, safeFilename(t && t.textContent) + '.png');
    };
    ensureRelative(el);
    el.appendChild(makeBtn(handler));
  }

  // Cria wrapper agrupando irmãos consecutivos (h3+legend+table)
  function wrapSiblings(elements, className){
    if(!elements.length) return null;
    const first = elements[0];
    const wrap = document.createElement('div');
    wrap.className = className;
    wrap.style.position = 'relative';
    first.parentNode.insertBefore(wrap, first);
    elements.forEach(e => wrap.appendChild(e));
    return wrap;
  }

  function setupCopyButtons(){
    // 1. Charts (Visão Gráficos) — captura chart-card COMPLETO
    //    (inclui título h3 + chart com marca-d'água + legenda + nota rodapé)
    document.querySelectorAll('.chart-card').forEach(c => attachToElement(c));

    // 2. Tabelas em Visão Dinâmica e Estática — captura a SECTION INTEIRA
    //    para incluir o <h2> do título
    document.querySelectorAll('.dynamic-view section, .static-view section')
      .forEach(s => {
        if(s.querySelector('table')) attachToElement(s);
      });

    // 3. Áreas e Produção — cada crop-block já tem <h4> dentro
    document.querySelectorAll('.states-view .crop-block')
      .forEach(c => attachToElement(c));

    // 4. Áreas e Produção: também o KPI comparativo BR×US (section dedicada)
    document.querySelectorAll('.states-view section')
      .forEach(s => { if(s.querySelector('.kpi-row,.kpi')) attachToElement(s); });

    // 5. Exportações UF — cada commodity-block já tem título dentro
    document.querySelectorAll('.exports-view .commodity-block')
      .forEach(c => attachToElement(c));

    // 6. Capacidade Estática — agrupa breakdown e tabela detalhada
    //    a) Cards de breakdown nacional
    document.querySelectorAll('.cap-view .cap-breakdown')
      .forEach(b => attachToElement(b));

    //    b) Tabela detalhada — agrupa o <h3>"Detalhamento por Estado", legend e table
    document.querySelectorAll('.cap-view table.cap').forEach(t => {
      let wrap = t.parentElement;
      if(wrap.classList.contains('cap-table-wrap')){
        attachToElement(wrap);
        return;
      }
      // Procura h3 + legend imediatamente antes da tabela
      const items = [];
      let prev = t.previousElementSibling;
      const stack = [];
      while(prev){
        stack.unshift(prev);
        if(prev.tagName === 'H3') break;
        prev = prev.previousElementSibling;
      }
      // stack agora tem [h3, ...possivelmente legend...]
      if(stack.length && stack[0].tagName === 'H3'){
        items.push(...stack);
      }
      items.push(t);
      const newWrap = wrapSiblings(items, 'cap-table-wrap');
      if(newWrap) attachToElement(newWrap);
    });
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', setupCopyButtons);
  }else{
    setupCopyButtons();
  }

  // ============ GERAR PDF ============
  function setupPrintButton(){
    const btn = document.getElementById('print-pdf-btn');
    if(!btn) return;
    btn.addEventListener('click', () => {
      // Antes de imprimir, mostra todas as views (CSS @media print já faz isso,
      // mas garantimos que o reflow tenha ocorrido)
      showToast('Abrindo diálogo de impressão — escolha "Salvar como PDF"');
      setTimeout(() => window.print(), 250);
    });
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', setupPrintButton);
  }else{
    setupPrintButton();
  }
})();
"""


# =====================================================================
# Helpers de renderização (compartilhados)
# =====================================================================
def _cls_proj(s: dict) -> str:
    return ' class="projection"' if s.get("projecao") else ""


def _seta(delta: float | None) -> str:
    if not delta:
        return '<span>—</span>'
    if delta > 0:
        return f'<span class="delta-up">▲ +{fmt_n(delta, 2)}</span>'
    return f'<span class="delta-dn">▼ {fmt_n(delta, 2)}</span>'


def _pill(valor: str) -> str:
    v = (valor or "neutro").lower()
    label = {"alta": "↑ Alta", "baixa": "↓ Baixa", "neutro": "— Neutro",
             "aperto": "Aperto", "folga": "Folga"}.get(v, v.capitalize())
    return f'<span class="pill {v}">{label}</span>'


def _tabela_soja(dados: dict, alterados: set, dinamico: bool) -> str:
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
            mark = " changed" if (dinamico and (s["safra"], campo) in alterados) else ""
            return f'<td class="{extra}{mark}">{fmt_n(val, dec)}</td>'
        linhas.append(
            f'<tr{_cls_proj(s)}>'
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
    return (f'<div class="table-wrap"><table class="snd"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def _tabela_milho(dados: dict, alterados: set, dinamico: bool) -> str:
    cab = ["Safra", "Área (Mi ha)", "Produtiv. (kg/ha)",
           "Prod. 1ª Safra (Mt)", "Prod. 2ª Safra (Mt)", "Prod. 3ª Safra (Mt)",
           "Prod. Total (Mt)", "Imp. (Mt)",
           "Oferta Total (Mt)", "Consumo (Mt)", "Exp. (Mt)",
           "Estoques (Mt)", "Estoque/Uso (%)"]
    ths = "".join(
        f'<th{" class=\"hl-stock\"" if "Estoques" in c else ""}'
        f'{" class=\"hl-ratio\"" if "Estoque/Uso" in c else ""}>{c}</th>'
        for c in cab)
    linhas = []
    for s in dados["milho"]["safras"]:
        def td(campo, val, dec=1, extra=""):
            mark = " changed" if (dinamico and (s["safra"], campo) in alterados) else ""
            return f'<td class="{extra}{mark}">{fmt_n(val, dec)}</td>'
        linhas.append(
            f'<tr{_cls_proj(s)}>'
            f'<td>{s["safra"]}</td>'
            f'{td("area", s.get("area"), 1)}'
            f'{td("produtividade", s.get("produtividade"), 0)}'
            f'{td("producao_1a", s.get("producao_1a"), 2)}'
            f'{td("producao_2a", s.get("producao_2a"), 2)}'
            f'{td("producao_3a", s.get("producao_3a"), 2)}'
            f'{td("producao", s.get("producao"), 1)}'
            f'{td("importacao", s.get("importacao"), 1)}'
            f'{td("oferta_total", s.get("oferta_total"), 1)}'
            f'{td("consumo", s.get("consumo"), 1)}'
            f'{td("exportacao", s.get("exportacao"), 1)}'
            f'{td("estoques", s.get("estoques"), 1, "hl-stock")}'
            f'<td class="hl-ratio">{fmt_pct(s.get("estoque_uso_pct"))}</td>'
            f'</tr>')
    return (f'<div class="table-wrap"><table class="snd"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def _tabela_sub(dados: dict, chave: str, alterados: set, dinamico: bool) -> str:
    cab = ["Safra", "Produção (Mt)", "Consumo (Mt)", "Exportação (Mt)",
           "Estoques (Mt)", "% Cons./Prod.", "% Exp./Prod."]
    ths = "".join(
        f'<th{" class=\"hl-stock\"" if "Estoques" in c else ""}'
        f'{" class=\"hl-ratio\"" if "%" in c else ""}>{c}</th>' for c in cab)
    linhas = []
    for s in dados[chave]["safras"]:
        def td(campo, val, dec=2, extra=""):
            mark = " changed" if (dinamico and (s["safra"], campo) in alterados) else ""
            return f'<td class="{extra}{mark}">{fmt_n(val, dec)}</td>'
        linhas.append(
            f'<tr{_cls_proj(s)}>'
            f'<td>{s["safra"]}</td>'
            f'{td("producao", s.get("producao"), 2)}'
            f'{td("consumo", s.get("consumo"), 2)}'
            f'{td("exportacao", s.get("exportacao"), 2)}'
            f'{td("estoques", s.get("estoques"), 2, "hl-stock")}'
            f'<td class="hl-ratio">{fmt_pct(s.get("pct_consumo"))}</td>'
            f'<td class="hl-ratio">{fmt_pct(s.get("pct_exportacao"))}</td>'
            f'</tr>')
    return (f'<div class="table-wrap"><table class="snd"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table></div>')


def _tabela_exp(dados: dict) -> str:
    rows = []
    for sj, ml, fr, ol in zip(
            dados["soja_grao"]["safras"], dados["milho"]["safras"],
            dados["farelo_soja"]["safras"], dados["oleo_soja"]["safras"]):
        rows.append(
            f'<tr{_cls_proj(sj)}><td>{sj["safra"]}</td>'
            f'<td>{fmt_n(sj["exportacao"])}</td>'
            f'<td>{fmt_pct(sj["exportacao"]/sj["producao"]*100)}</td>'
            f'<td>{fmt_n(ml["exportacao"])}</td>'
            f'<td>{fmt_pct(ml["exportacao"]/ml["producao"]*100)}</td>'
            f'<td>{fmt_n(fr["exportacao"],2)}</td>'
            f'<td>{fmt_pct(fr["exportacao"]/fr["producao"]*100)}</td>'
            f'<td>{fmt_n(ol["exportacao"],2)}</td>'
            f'<td>{fmt_pct(ol["exportacao"]/ol["producao"]*100)}</td></tr>')
    ths = ("<th>Safra</th><th>Soja (Mt)</th><th>% Exp/Prod</th>"
           "<th>Milho (Mt)</th><th>% Exp/Prod</th>"
           "<th>Farelo (Mt)</th><th>% Exp/Prod</th>"
           "<th>Óleo (Mt)</th><th>% Exp/Prod</th>")
    return (f'<div class="table-wrap"><table class="snd"><thead><tr>{ths}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


# =====================================================================
# Seções específicas da VISÃO DINÂMICA
# =====================================================================
def _unit(campo: str) -> str:
    return UNIDADE.get(campo, "")


def _sec_atualizacao_dia(diag: Diagnostico, data_ant: str) -> str:
    """Seção 'Atualização do Dia' — mudanças vs snapshot anterior (ontem)."""
    soja_m = [m for m in diag.mudancas
              if m.bloco in ("soja_grao", "farelo_soja", "oleo_soja", "complexo_soja")]
    milho_m = [m for m in diag.mudancas if m.bloco == "milho"]

    def item(m: Mudanca) -> str:
        campo = LABEL_CAMPO.get(m.campo, m.campo)
        unit = _unit(m.campo)
        delta = m.delta_abs or 0
        delta_html = (f'<span class="delta-up">▲ +{fmt_n(delta,2)}</span>'
                      if delta > 0 else
                      f'<span class="delta-dn">▼ {fmt_n(delta,2)}</span>')
        pct = (f" ({m.delta_pct:+.1f}%)" if m.delta_pct else "")
        fonte = f' <span style="color:var(--muted);font-size:10px">· {escape(m.fonte)}</span>' if m.fonte else ""
        return (f'<li><strong>{LABEL_BLOCO.get(m.bloco,m.bloco)} {m.safra}</strong> · '
                f'{campo}: {fmt_n(m.anterior,2)} → <strong>{fmt_n(m.atual,2)} {unit}</strong> '
                f'{delta_html}{pct}{fonte}</li>')

    def col(titulo: str, itens: list[Mudanca]) -> str:
        if not itens:
            return (f'<div class="daily-col"><h3>{titulo}</h3>'
                    f'<div class="empty">Sem alterações relevantes hoje.</div></div>')
        itens.sort(key=lambda x: (x.severidade != "estrutural",
                                   -(abs(x.delta_pct or 0))))
        return (f'<div class="daily-col"><h3>{titulo}</h3>'
                f'<ul>{"".join(item(m) for m in itens[:12])}</ul></div>')

    if not diag.mudancas:
        body = (f'<div class="daily-grid">'
                f'<div class="daily-col"><h3>Soja</h3>'
                f'<div class="empty">Sem alterações relevantes no SnD nesta atualização diária.</div></div>'
                f'<div class="daily-col"><h3>Milho</h3>'
                f'<div class="empty">Sem alterações relevantes no SnD nesta atualização diária.</div></div>'
                f'</div>')
    else:
        body = (f'<div class="daily-grid">{col("Soja · Complexo", soja_m)}'
                f'{col("Milho", milho_m)}</div>')

    return (f'<section class="daily-box">'
            f'<h2>Atualização do Dia '
            f'<span class="sub">vs. snapshot anterior ({escape(data_ant)})</span></h2>'
            f'{body}</section>')


def _sec_impacto_diario(diag: Diagnostico) -> str:
    rel = [m for m in diag.mudancas if m.severidade in ("relevante", "estrutural")]
    if not rel:
        return ('<section><h2>Impacto Diário no Mercado</h2>'
                '<div style="padding:18px;border:1px solid var(--line);color:var(--muted);'
                'font-style:italic">Sem impactos relevantes nesta rodada diária.</div></section>')
    # Consolida por commodity
    rows = []
    for m in rel:
        rows.append(
            f'<tr>'
            f'<td class="bloco">{LABEL_BLOCO.get(m.bloco,m.bloco)}</td>'
            f'<td>{m.safra}</td>'
            f'<td>{LABEL_CAMPO.get(m.campo,m.campo)}</td>'
            f'<td class="center">{_pill(m.impacto_oferta)}</td>'
            f'<td class="center">{_pill(m.impacto_demanda)}</td>'
            f'<td class="center">{_pill(m.impacto_estoques)}</td>'
            f'<td class="center"><span class="sev {m.severidade}">{m.severidade}</span></td>'
            f'</tr>')
    return (f'<section><h2>Impacto Diário no Mercado</h2>'
            f'<table class="impact-table">'
            f'<thead><tr><th>Commodity</th><th>Safra</th><th>Campo</th>'
            f'<th style="text-align:center">Oferta</th>'
            f'<th style="text-align:center">Demanda</th>'
            f'<th style="text-align:center">Estoques</th>'
            f'<th style="text-align:center">Severidade</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></section>')


def _sec_sinais_dia(diag: Diagnostico) -> str:
    if not diag.sinais:
        return ""
    cards = []
    for bloco in ("soja_grao", "milho"):
        s = diag.sinais.get(bloco)
        if not s:
            continue
        cls = s.get("balanco", "").lower() or "sem_base"
        eu = s.get("estoque_uso") or 0
        vies_txt = {
            "altista": "Altista — pressão de alta",
            "baixista": "Baixista — pressão baixista em prêmios",
            "neutro": "Neutro",
        }.get(s.get("vies", "neutro"), s.get("vies", ""))
        estrut = ("Sim — virada estrutural detectada hoje"
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
            f'    <dt>Mudança estrutural hoje</dt><dd>{estrut}</dd>'
            f'    <dt>Alterações detectadas</dt><dd>{s.get("num_mudancas",0)} '
            f'({s.get("num_estruturais",0)} estrutural/is)</dd>'
            f'  </dl></div>'
            f'</div>')

    alerts = ""
    if diag.alertas:
        itens = "".join(f'<li>{escape(a)}</li>' for a in diag.alertas)
        alerts = (f'<div class="alerts-box" style="margin-top:18px">'
                  f'<h3>Alertas Trader — Prioridade Alta</h3>'
                  f'<ul class="alerts-list">{itens}</ul></div>')

    return (f'<section><h2>Sinais de Mercado do Dia</h2>'
            f'<div class="signals">{"".join(cards)}</div>'
            f'{alerts}</section>')


def _sec_noticias(noticias: list[dict]) -> str:
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
    return (f'<section><h2>Feed — Conab &amp; CEPEA '
            f'<span class="sub">filtro soja/milho/safra</span></h2>'
            f'<div class="news-grid">{"".join(cards)}</div></section>')


# =====================================================================
# CHART HELPERS (SVG puro, sem dependência externa)
# =====================================================================
# Paleta de séries para os charts (cores Innovagro + complementares)
CH_COLORS = {
    "navy": "#0A2342",
    "green": "#1E5631",
    "green_soft": "#2E7D4F",
    "accent": "#C7A23A",   # mostarda
    "blue": "#3A6EA5",     # azul intermediário
    "wine": "#8B2D3C",     # vinho complementar
}

# Geometria padrão dos gráficos
CH_W = 720
CH_H = 320
CH_PAD = {"top": 28, "right": 22, "bottom": 56, "left": 56}


def _watermark_svg(w: int, h: int) -> str:
    """
    Marca d'água é renderizada via CSS pseudo-elemento (`.ch-svg::before`)
    para evitar duplicar o logo base64 em cada chart. Esta função fica como
    no-op de compatibilidade — apenas retorna string vazia.
    """
    return ""


def _label_n(v: float, dec_auto: bool = True) -> str:
    """Formato compacto para rótulos: 1 casa se < 100, 0 casas se >= 100."""
    if v is None:
        return ""
    if dec_auto:
        if abs(v) >= 100:
            return f"{v:,.0f}".replace(",", ".")
        if abs(v) >= 10:
            return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _label_pct(v: float) -> str:
    if v is None:
        return ""
    return f"{v:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def _nice_max(v: float) -> float:
    """Arredonda para escala visualmente agradável."""
    if v <= 0:
        return 1
    import math
    mag = 10 ** math.floor(math.log10(v))
    n = v / mag
    if n <= 1:
        return 1 * mag
    if n <= 2:
        return 2 * mag
    if n <= 2.5:
        return 2.5 * mag
    if n <= 5:
        return 5 * mag
    return 10 * mag


def _y_ticks(vmin: float, vmax: float, n: int = 5) -> list[float]:
    if vmax <= vmin:
        vmax = vmin + 1
    step = (vmax - vmin) / n
    # Arredonda step
    import math
    mag = 10 ** math.floor(math.log10(step)) if step > 0 else 1
    nstep = step / mag
    if nstep <= 1:
        nstep = 1
    elif nstep <= 2:
        nstep = 2
    elif nstep <= 2.5:
        nstep = 2.5
    elif nstep <= 5:
        nstep = 5
    else:
        nstep = 10
    step = nstep * mag
    ticks = []
    v = 0 if vmin >= 0 else (math.floor(vmin / step) * step)
    while v <= vmax + step / 2:
        ticks.append(round(v, 4))
        v += step
    return ticks


def _axes_svg(x_labels: list[str], proj_idx: int, vmax: float, vmin: float = 0,
              w: int = CH_W, h: int = CH_H, y_unit: str = "") -> tuple[str, callable, callable, float]:
    """
    Renderiza os eixos X (categorial) e Y (numérico). Retorna:
        svg_axes, x_pos(idx) -> px, y_pos(val) -> px, band_w
    """
    pad = CH_PAD
    inner_w = w - pad["left"] - pad["right"]
    inner_h = h - pad["top"] - pad["bottom"]
    n = len(x_labels)
    band_w = inner_w / n if n else inner_w

    def x_pos(i: float) -> float:
        return pad["left"] + band_w * (i + 0.5)

    def y_pos(v: float) -> float:
        if vmax == vmin:
            return pad["top"] + inner_h
        return pad["top"] + inner_h * (1 - (v - vmin) / (vmax - vmin))

    # Linhas de grade horizontais + ticks Y
    ticks = _y_ticks(vmin, vmax)
    grid = []
    for t in ticks:
        if t < vmin or t > vmax:
            continue
        y = y_pos(t)
        grid.append(
            f'<line x1="{pad["left"]}" y1="{y:.1f}" '
            f'x2="{pad["left"] + inner_w}" y2="{y:.1f}" '
            f'stroke="#E4E7EB" stroke-width="1"/>')
        label = f"{t:.0f}" if abs(t) >= 10 else f"{t:.1f}"
        grid.append(
            f'<text x="{pad["left"] - 8}" y="{y + 4:.1f}" '
            f'text-anchor="end" font-size="10" fill="#5B6775" '
            f'font-family="Segoe UI, Arial">{label}</text>')

    # Eixo X - rótulos + sublinha "proj" para safra projetada
    xlabels = []
    for i, lb in enumerate(x_labels):
        x = x_pos(i)
        is_proj = (i == proj_idx)
        cor = CH_COLORS["green"] if is_proj else "#1B1F23"
        peso = "700" if is_proj else "500"
        xlabels.append(
            f'<text x="{x:.1f}" y="{h - pad["bottom"] + 18}" '
            f'text-anchor="middle" font-size="11" fill="{cor}" '
            f'font-weight="{peso}" font-family="Segoe UI, Arial">{escape(lb)}</text>')
        if is_proj:
            xlabels.append(
                f'<text x="{x:.1f}" y="{h - pad["bottom"] + 31}" '
                f'text-anchor="middle" font-size="9" fill="{CH_COLORS["green_soft"]}" '
                f'font-style="italic" font-family="Segoe UI, Arial">proj.</text>')

    # Eixo Y label
    ylabel = ""
    if y_unit:
        ylabel = (f'<text x="14" y="{pad["top"] + inner_h / 2:.1f}" '
                  f'transform="rotate(-90 14 {pad["top"] + inner_h / 2:.1f})" '
                  f'text-anchor="middle" font-size="10" fill="#5B6775" '
                  f'font-family="Segoe UI, Arial" letter-spacing="1">{escape(y_unit)}</text>')

    # Linha do eixo Y de baixo
    base_y = y_pos(max(0, vmin))
    axis_x = (
        f'<line x1="{pad["left"]}" y1="{base_y:.1f}" '
        f'x2="{pad["left"] + inner_w}" y2="{base_y:.1f}" '
        f'stroke="#0A2342" stroke-width="1.5"/>')

    return ("".join(grid) + axis_x + "".join(xlabels) + ylabel,
            x_pos, y_pos, band_w)


def _legend_html(items: list[tuple[str, str]], extra_proj: bool = True) -> str:
    """items: [(label, color)]"""
    lis = []
    for lb, c in items:
        lis.append(f'<div class="lg"><span class="swatch" style="background:{c}"></span>{escape(lb)}</div>')
    if extra_proj:
        lis.append('<div class="lg proj"><span class="swatch"></span>Safra projetada</div>')
    return f'<div class="chart-legend">{"".join(lis)}</div>'


def _chart_card(titulo: str, subtitulo: str, svg: str, legend: str,
                 nota: str = "",
                 fonte: str = "Conab 7º Lev. (14/04/2026) + USDA WASDE") -> str:
    """Cria um chart-card. `fonte` aparece no rodapé pequeno e semi-transparente,
    e também é renderizada no PNG exportado pelo botão 'Copiar como imagem'."""
    foot = ""
    if nota or fonte:
        note_html = (f'<span class="ch-note">{escape(nota)}</span>'
                     if nota else '<span class="ch-note"></span>')
        source_html = (f'<span class="ch-source">Fonte: {escape(fonte)}</span>'
                       if fonte else '')
        foot = f'<div class="ch-foot">{note_html}{source_html}</div>'
    return (f'<div class="chart-card">'
            f'<div class="ch-head"><h3>{escape(titulo)}</h3>'
            f'<span class="ch-sub">{escape(subtitulo)}</span></div>'
            f'<div class="ch-svg">{svg}</div>'
            f'{legend}{foot}</div>')


# ----- Tipo: barras agrupadas (até 4 séries por safra)
def _chart_grouped_bars(safras: list[str], series: list[tuple[str, list[float], str]],
                        proj_idx: int, y_unit: str = "Mt") -> str:
    """series = [(label, valores, cor)]"""
    w, h = CH_W, CH_H
    pad = CH_PAD
    inner_w = w - pad["left"] - pad["right"]
    inner_h = h - pad["top"] - pad["bottom"]
    all_v = [v for _, vs, _ in series for v in vs]
    vmax = _nice_max(max(all_v) * 1.18) if all_v else 1   # margem extra p/ rótulo
    axes, x_pos, y_pos, band_w = _axes_svg(safras, proj_idx, vmax, 0, w, h, y_unit)

    n_series = len(series)
    bar_group_w = band_w * 0.78
    bar_w = bar_group_w / max(n_series, 1)
    bars, labels = [], []
    for i, _ in enumerate(safras):
        x_center = x_pos(i)
        x0 = x_center - bar_group_w / 2
        is_proj = (i == proj_idx)
        for si, (label, vals, color) in enumerate(series):
            v = vals[i] if i < len(vals) and vals[i] is not None else 0
            x = x0 + bar_w * si
            y = y_pos(v)
            height = max(y_pos(0) - y, 0)
            stroke = "stroke=\"#0A2342\" stroke-width=\"1\" stroke-dasharray=\"3,2\"" \
                if is_proj else f'stroke="{color}" stroke-width="0.5"'
            fill_op = "0.55" if is_proj else "1"
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 1.5:.1f}" '
                f'height="{height:.1f}" fill="{color}" fill-opacity="{fill_op}" {stroke}>'
                f'<title>{escape(label)} · {escape(safras[i])}: {fmt_n(v, 1)} {y_unit}</title>'
                f'</rect>')
            # Rótulo acima da barra
            if v > 0:
                labels.append(
                    f'<text x="{x + (bar_w - 1.5) / 2:.1f}" y="{y - 4:.1f}" '
                    f'text-anchor="middle" font-size="9" fill="{color}" '
                    f'font-weight="700" font-family="Segoe UI, Arial">'
                    f'{_label_n(v)}</text>')

    body = (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Gráfico">'
            f'{_watermark_svg(w, h)}'
            f'{axes}{"".join(bars)}{"".join(labels)}'
            f'</svg>')
    legend = _legend_html([(lb, c) for lb, _, c in series])
    return body, legend


# ----- Tipo: barras empilhadas (2-3 séries)
def _chart_stacked_bars(safras: list[str], series: list[tuple[str, list[float], str]],
                        proj_idx: int, y_unit: str = "Mt") -> str:
    w, h = CH_W, CH_H
    sums = [sum(s[1][i] or 0 for s in series) for i in range(len(safras))]
    vmax = _nice_max(max(sums) * 1.12) if sums else 1   # margem p/ rótulo
    axes, x_pos, y_pos, band_w = _axes_svg(safras, proj_idx, vmax, 0, w, h, y_unit)
    bar_w = band_w * 0.6
    bars, labels = [], []
    for i, _ in enumerate(safras):
        x_center = x_pos(i)
        x = x_center - bar_w / 2
        is_proj = (i == proj_idx)
        running = 0
        for label, vals, color in series:
            v = vals[i] if i < len(vals) and vals[i] is not None else 0
            ytop = y_pos(running + v)
            yh = y_pos(running) - ytop
            running += v
            stroke = ('stroke="#0A2342" stroke-width="1" stroke-dasharray="3,2"'
                      if is_proj else f'stroke="{color}" stroke-width="0.4"')
            fill_op = "0.6" if is_proj else "1"
            bars.append(
                f'<rect x="{x:.1f}" y="{ytop:.1f}" width="{bar_w:.1f}" '
                f'height="{max(yh,0):.1f}" fill="{color}" fill-opacity="{fill_op}" {stroke}>'
                f'<title>{escape(label)} · {escape(safras[i])}: {fmt_n(v, 1)} {y_unit}</title>'
                f'</rect>')
            # Rótulo dentro do segmento (se houver espaço suficiente)
            if yh >= 22 and v > 0:
                labels.append(
                    f'<text x="{x_center:.1f}" y="{ytop + yh / 2 + 3.5:.1f}" '
                    f'text-anchor="middle" font-size="10" fill="#fff" '
                    f'font-weight="700" font-family="Segoe UI, Arial" '
                    f'pointer-events="none">{_label_n(v)}</text>')
        # Total no topo de TODAS as barras
        if running > 0:
            cor_total = "#0A2342"
            labels.append(
                f'<text x="{x_center:.1f}" y="{y_pos(running) - 6:.1f}" '
                f'text-anchor="middle" font-size="11" fill="{cor_total}" '
                f'font-weight="800" font-family="Segoe UI, Arial">'
                f'{_label_n(running)}</text>')

    body = (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Gráfico">'
            f'{_watermark_svg(w, h)}'
            f'{axes}{"".join(bars)}{"".join(labels)}'
            f'</svg>')
    legend = _legend_html([(lb, c) for lb, _, c in series])
    return body, legend


# ----- Tipo: linhas (até 2 séries)
def _chart_lines(safras: list[str], series: list[tuple[str, list[float], str]],
                 proj_idx: int, y_unit: str = "%") -> str:
    w, h = CH_W, CH_H
    all_v = [v for _, vs, _ in series for v in vs if v is not None]
    if not all_v:
        return ('<svg viewBox="0 0 720 320"></svg>',
                _legend_html([(lb, c) for lb, _, c in series]))
    vmin = min(all_v)
    vmax = max(all_v)
    span = vmax - vmin if vmax > vmin else 1
    vmin_p = max(0, vmin - span * 0.15)
    vmax_p = _nice_max(vmax + span * 0.22)   # margem extra p/ rótulos
    axes, x_pos, y_pos, _ = _axes_svg(safras, proj_idx, vmax_p, vmin_p, w, h, y_unit)

    elements, labels = [], []
    pts_proj_any = False
    is_pct = (y_unit == "%")
    for s_idx, (label, vals, color) in enumerate(series):
        pts_hist, pts_proj = [], []
        for i, v in enumerate(vals):
            if v is None:
                continue
            x, y = x_pos(i), y_pos(v)
            if i <= proj_idx - 1:
                pts_hist.append((x, y))
            if i >= proj_idx - 1:
                pts_proj.append((x, y))
        if pts_hist:
            d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts_hist)
            elements.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
        if len(pts_proj) > 1:
            pts_proj_any = True
            d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts_proj)
            elements.append(
                f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5" '
                f'stroke-dasharray="5,4" stroke-linecap="round" stroke-linejoin="round"/>')
        # Pontos + rótulos
        for i, v in enumerate(vals):
            if v is None:
                continue
            x, y = x_pos(i), y_pos(v)
            r = 5 if i == proj_idx else 3.5
            fill = "#fff" if i == proj_idx else color
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                f'fill="{fill}" stroke="{color}" stroke-width="2">'
                f'<title>{escape(label)} · {escape(safras[i])}: {fmt_n(v, 2)} {y_unit}</title>'
                f'</circle>')
            # Rótulo: alterna acima/abaixo conforme a série (evita sobreposição)
            offset_y = -10 if s_idx == 0 else 16
            txt = _label_pct(v) if is_pct else _label_n(v)
            labels.append(
                f'<text x="{x:.1f}" y="{y + offset_y:.1f}" text-anchor="middle" '
                f'font-size="10" fill="{color}" font-weight="700" '
                f'font-family="Segoe UI, Arial" '
                f'paint-order="stroke" stroke="#fff" stroke-width="3" '
                f'stroke-linejoin="round">{txt}</text>')

    body = (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Gráfico">'
            f'{_watermark_svg(w, h)}'
            f'{axes}{"".join(elements)}{"".join(labels)}'
            f'</svg>')
    legend = _legend_html([(lb, c) for lb, _, c in series], extra_proj=False)
    if pts_proj_any:
        legend = legend.replace(
            '</div>', '</div><div class="lg proj"><span class="swatch"></span>'
                      'Projeção (linha tracejada)</div>', 1)
    return body, legend


# ----- Tipo: barras 100% (mix exportação vs interno)
def _chart_pct_stack(safras: list[str], series: list[tuple[str, list[float], str]],
                     proj_idx: int) -> str:
    w, h = CH_W, CH_H
    axes, x_pos, y_pos, band_w = _axes_svg(safras, proj_idx, 100, 0, w, h, "%")
    bar_w = band_w * 0.6
    bars, labels = [], []
    for i, _ in enumerate(safras):
        total = sum(s[1][i] or 0 for s in series)
        if total <= 0:
            continue
        x = x_pos(i) - bar_w / 2
        is_proj = (i == proj_idx)
        running_pct = 0
        for label, vals, color in series:
            v = vals[i] or 0
            pct = v / total * 100
            ytop = y_pos(running_pct + pct)
            yh = y_pos(running_pct) - ytop
            stroke = ('stroke="#0A2342" stroke-width="1" stroke-dasharray="3,2"'
                      if is_proj else 'stroke="#fff" stroke-width="0.5"')
            fill_op = "0.6" if is_proj else "1"
            bars.append(
                f'<rect x="{x:.1f}" y="{ytop:.1f}" width="{bar_w:.1f}" '
                f'height="{max(yh,0):.1f}" fill="{color}" fill-opacity="{fill_op}" {stroke}>'
                f'<title>{escape(label)} · {escape(safras[i])}: '
                f'{pct:.1f}% ({fmt_n(v, 1)} Mt)</title></rect>')
            # Rótulo dentro do segmento (se grande o bastante)
            if yh >= 18 and pct >= 8:
                labels.append(
                    f'<text x="{x_pos(i):.1f}" y="{ytop + yh / 2 + 3.5:.1f}" '
                    f'text-anchor="middle" font-size="11" fill="#fff" '
                    f'font-weight="800" font-family="Segoe UI, Arial" '
                    f'pointer-events="none">{pct:.0f}%</text>')
            running_pct += pct

    body = (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Gráfico">'
            f'{_watermark_svg(w, h)}'
            f'{axes}{"".join(bars)}{"".join(labels)}'
            f'</svg>')
    legend = _legend_html([(lb, c) for lb, _, c in series])
    return body, legend


# =====================================================================
# VISÃO GRÁFICOS
# =====================================================================
def _view_graficos(dados: dict) -> str:
    safras_sj = [s["safra"] for s in dados["soja_grao"]["safras"]]
    safras_ml = [s["safra"] for s in dados["milho"]["safras"]]
    proj_sj = next((i for i, s in enumerate(dados["soja_grao"]["safras"])
                    if s.get("projecao")), len(safras_sj) - 1)
    proj_ml = next((i for i, s in enumerate(dados["milho"]["safras"])
                    if s.get("projecao")), len(safras_ml) - 1)

    # === 1. Soja: Produção × Exportação × Consumo
    sj = dados["soja_grao"]["safras"]
    body1, leg1 = _chart_grouped_bars(
        safras_sj,
        [("Produção", [s["producao"] for s in sj], CH_COLORS["green"]),
         ("Exportação", [s["exportacao"] for s in sj], CH_COLORS["navy"]),
         ("Consumo Interno", [s["consumo"] for s in sj], CH_COLORS["accent"])],
        proj_sj, y_unit="Mt")
    card1 = _chart_card(
        "Soja — Produção × Exportação × Consumo",
        f"{safras_sj[0]} → {safras_sj[-1]}",
        body1, leg1,
        "Produção e exportação seguem em alta. Consumo interno cresce de forma estrutural via crush.",
        fonte="Conab 7º Lev. 2025/26 + USDA WASDE abr/2026")

    # === 2. Milho: Produção × Exportação × Consumo (espelha card 1 da soja)
    ml = dados["milho"]["safras"]
    body2, leg2 = _chart_grouped_bars(
        safras_ml,
        [("Produção", [s["producao"] for s in ml], CH_COLORS["green"]),
         ("Exportação", [s["exportacao"] for s in ml], CH_COLORS["navy"]),
         ("Consumo Interno", [s["consumo"] for s in ml], CH_COLORS["accent"])],
        proj_ml, y_unit="Mt")
    card2 = _chart_card(
        "Milho — Produção × Exportação × Consumo",
        f"{safras_ml[0]} → {safras_ml[-1]}",
        body2, leg2,
        "Consumo interno cresce com etanol de milho e ração. Exportação acelerou a partir de 2021/22 com a safrinha consolidada.",
        fonte="Conab 7º Lev. 2025/26 + USDA WASDE abr/2026")

    # === 2b. Milho: 1ª + 2ª + 3ª safra empilhadas
    body2b, leg2b = _chart_stacked_bars(
        safras_ml,
        [("1ª Safra (verão)",
          [s.get("producao_1a") or 0 for s in ml], CH_COLORS["green_soft"]),
         ("2ª Safra (safrinha)",
          [s.get("producao_2a") or 0 for s in ml], CH_COLORS["navy"]),
         ("3ª Safra (Norte/NE)",
          [s.get("producao_3a") or 0 for s in ml], CH_COLORS["accent"])],
        proj_ml, y_unit="Mt")
    card2b = _chart_card(
        "Milho — Produção por Safra (1ª × 2ª × 3ª)",
        "verão (Sul/SE) + safrinha (CO) + 3ª safra (N/NE)",
        body2b, leg2b,
        "Safrinha ~78%, 1ª safra ~20%, 3ª safra ~2%. Exp/cons não se separam por safra — milho é fungível.",
        fonte="Conab 7º Lev. 2025/26 (14/04/2026)")

    # === 3a. Estoques Finais Soja
    body3a, leg3a = _chart_lines(
        safras_sj,
        [("Soja", [s["estoques"] for s in sj], CH_COLORS["green"])],
        proj_sj, y_unit="Mt")
    card3a = _chart_card(
        "Estoques Finais — Soja",
        "Evolução por safra · Mt",
        body3a, leg3a,
        "Soja recompõe estoque após anos de aperto (2021/22 a 2023/24).",
        fonte="Conab + USDA · cálculo Innovagro")

    # === 3b. Estoques Finais Milho
    body3b, leg3b = _chart_lines(
        safras_ml,
        [("Milho", [s["estoques"] for s in dados["milho"]["safras"]], CH_COLORS["navy"])],
        proj_ml, y_unit="Mt")
    card3b = _chart_card(
        "Estoques Finais — Milho",
        "Evolução por safra · Mt",
        body3b, leg3b,
        "Milho oscila com volume da safrinha — janela de chuvas fev–mai é crítica.",
        fonte="Conab + USDA · cálculo Innovagro")

    # === 4a. Estoque/Uso Soja
    body4a, leg4a = _chart_lines(
        safras_sj,
        [("Soja", [s.get("estoque_uso_pct") or 0 for s in sj], CH_COLORS["green"])],
        proj_sj, y_unit="%")
    card4a = _chart_card(
        "Estoque/Uso — Soja",
        "Indicador de aperto vs. folga · %",
        body4a, leg4a,
        "Abaixo de 4% = aperto severo · 4-5% = equilíbrio · Acima de 5% = folga estrutural.",
        fonte="Conab + USDA · cálculo Innovagro (estoques ÷ uso)")

    # === 4b. Estoque/Uso Milho
    body4b, leg4b = _chart_lines(
        safras_ml,
        [("Milho", [s.get("estoque_uso_pct") or 0 for s in dados["milho"]["safras"]],
          CH_COLORS["navy"])],
        proj_ml, y_unit="%")
    card4b = _chart_card(
        "Estoque/Uso — Milho",
        "Indicador de aperto vs. folga · %",
        body4b, leg4b,
        "Abaixo de 4% = aperto severo · 4-5% = equilíbrio · Acima de 5% = folga estrutural.",
        fonte="Conab + USDA · cálculo Innovagro (estoques ÷ uso)")

    # === 5. Complexo Soja: Produção Farelo × Óleo
    fr = dados["farelo_soja"]["safras"]
    ol = dados["oleo_soja"]["safras"]
    proj_fr = next((i for i, s in enumerate(fr) if s.get("projecao")), len(fr) - 1)
    body5, leg5 = _chart_grouped_bars(
        [s["safra"] for s in fr],
        [("Farelo", [s["producao"] for s in fr], CH_COLORS["wine"]),
         ("Óleo", [s["producao"] for s in ol], CH_COLORS["accent"])],
        proj_fr, y_unit="Mt")
    card5 = _chart_card(
        "Complexo Soja — Produção Farelo × Óleo",
        "Esmagamento total · Mt",
        body5, leg5,
        "Crush em expansão sustentado por biodiesel (B14 → B15) e demanda pecuária.",
        fonte="ABIOVE + Conab + USDA WASDE")

    # === 6. Soja: Mix Exportação vs Mercado Interno (100%)
    body6, leg6 = _chart_pct_stack(
        safras_sj,
        [("Exportação", [s["exportacao"] for s in sj], CH_COLORS["navy"]),
         ("Mercado Interno", [s["consumo"] for s in sj], CH_COLORS["green"])],
        proj_sj)
    card6 = _chart_card(
        "Soja — Mix Exportação vs. Mercado Interno",
        "Participação % por safra",
        body6, leg6,
        "Brasil mantém mix export-driven (~65%). Crescimento doméstico via biodiesel B15.",
        fonte="Conab + Secex/ComexStat (exportação)")

    # === 7. Milho: Mix Exportação vs Mercado Interno (100%) — espelha card 6
    body7, leg7 = _chart_pct_stack(
        safras_ml,
        [("Exportação", [s["exportacao"] for s in ml], CH_COLORS["navy"]),
         ("Mercado Interno", [s["consumo"] for s in ml], CH_COLORS["green"])],
        proj_ml)
    card7 = _chart_card(
        "Milho — Mix Exportação vs. Mercado Interno",
        "Participação % por safra",
        body7, leg7,
        "Inverso da soja: mercado interno predomina (~65-70%) — etanol de milho, ração avícola/suína, indústria.",
        fonte="Conab + Secex/ComexStat (exportação)")

    return f"""
<div class="view charts-view" data-view="graficos">
  <p class="intro">Visão <strong>Gráficos</strong> — evolução histórica e projeção da safra
  corrente. Barras tracejadas e pontos brancos no contorno marcam a
  <strong style="color:var(--green)">safra projetada</strong>. Marca d'água Innovagro
  no fundo de cada chart.</p>

  <div class="charts-grid">
    {card1}{card2}{card2b}{card5}{card3a}{card3b}{card4a}{card4b}{card6}{card7}
  </div>

  <div class="synth"><strong>Como ler:</strong> linhas tracejadas e barras com hachura
  representam projeção (Conab + USDA). Ponto branco com contorno = safra atual em curso.
  Rótulos diretos em cada barra/ponto. Pairar o cursor mostra o valor exato + safra.
  <br><br>
  <strong>Nota sobre milho:</strong> exportação e consumo não são separáveis por
  verão × safrinha — Secex/ComexStat reportam apenas total (NCM 10059010), e o
  consumo doméstico (etanol, ração) trata milho como commodity fungível.
  A separação de produção por safra está no chart "Milho — Produção por Safra".</div>
</div>"""


# =====================================================================
# VISÃO ESTADOS — Áreas e Produção (BR + EUA · Soja + Milho)
# =====================================================================
def _states_table(estados: list[dict], safras: list[str],
                  proj_set: set | None = None) -> str:
    """Tabela de estados com N safras. Marca safras projetadas. Última coluna = Δ%."""
    proj_set = proj_set or set()
    s_first, s_last = safras[0], safras[-1]
    head_safras = "".join(
        f'<th colspan="3"{" class=\"proj\"" if s in proj_set else ""}>'
        f'{escape(s)}</th>' for s in safras)
    head_metric = "".join(
        ('<th class="proj">Área</th><th class="proj">Prod.</th>'
         '<th class="proj">Produção</th>' if s in proj_set
         else '<th>Área</th><th>Prod.</th><th>Produção</th>')
        for s in safras)

    body_rows = []
    tot = {s: {"area": 0.0, "producao": 0.0} for s in safras}
    for e in estados:
        cells = []
        for s in safras:
            d = e["dados"].get(s, {}) or {}
            cls = ' class="proj"' if s in proj_set else ""
            cells.append(f'<td{cls}>{fmt_n(d.get("area"), 2)}</td>')
            cells.append(f'<td{cls}>{fmt_n(d.get("produtividade"), 0)}</td>')
            cells.append(
                f'<td{cls}><strong>{fmt_n(d.get("producao"), 2)}</strong></td>')
            tot[s]["area"] += d.get("area") or 0
            tot[s]["producao"] += d.get("producao") or 0
        # Variação % de produção entre primeira e última safra
        p_first = (e["dados"].get(s_first) or {}).get("producao") or 0
        p_last = (e["dados"].get(s_last) or {}).get("producao") or 0
        delta = ((p_last / p_first - 1) * 100) if p_first else 0
        cls_d = "up" if delta >= 0 else "dn"
        seta = "▲" if delta >= 0 else "▼"
        body_rows.append(
            f'<tr><td class="uf">{escape(e["uf"])}</td>'
            f'<td class="nome">{escape(e["nome"])}</td>'
            f'{"".join(cells)}'
            f'<td class="delta {cls_d}">{seta} {abs(delta):.1f}%</td></tr>')

    # Linha total (top-N)
    tot_cells = []
    for s in safras:
        cls = ' class="proj"' if s in proj_set else ""
        tot_cells.append(f'<td{cls}>{fmt_n(tot[s]["area"], 2)}</td>')
        tot_cells.append(f'<td{cls}>—</td>')
        tot_cells.append(
            f'<td{cls}><strong>{fmt_n(tot[s]["producao"], 1)}</strong></td>')
    delta_tot = ((tot[s_last]["producao"] / tot[s_first]["producao"] - 1) * 100) \
        if tot[s_first]["producao"] else 0
    cls_dt = "up" if delta_tot >= 0 else "dn"
    seta_t = "▲" if delta_tot >= 0 else "▼"
    body_rows.append(
        f'<tr class="totals"><td class="uf">Σ</td>'
        f'<td class="nome">Top {len(estados)}</td>'
        f'{"".join(tot_cells)}'
        f'<td class="delta {cls_dt}">{seta_t} {abs(delta_tot):.1f}%</td></tr>')

    return (f'<table class="states">'
            f'<thead><tr><th rowspan="2">UF</th><th rowspan="2">Estado</th>'
            f'{head_safras}<th rowspan="2">Δ {safras[0]}→{safras[-1]}</th></tr>'
            f'<tr>{head_metric}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>')


def _ranking_bars(estados: list[dict], safra: str, cls: str = "soja") -> str:
    """Barras horizontais ranqueadas pela produção da safra mais recente."""
    rows = []
    sorted_e = sorted(estados,
                      key=lambda e: e["dados"].get(safra, {}).get("producao") or 0,
                      reverse=True)
    vmax = max((e["dados"].get(safra, {}).get("producao") or 0)
               for e in sorted_e) or 1
    for e in sorted_e:
        v = e["dados"].get(safra, {}).get("producao") or 0
        pct_w = (v / vmax * 100) if vmax else 0
        rows.append(
            f'<div class="bar-row">'
            f'<span class="uf">{escape(e["uf"])}</span>'
            f'<div class="bar-track">'
            f'<div class="bar-fill {cls}" style="width:{pct_w:.1f}%">'
            f'{escape(e["uf"])}</div></div>'
            f'<span class="val">{fmt_n(v, 1)} Mt</span>'
            f'</div>')
    return (f'<div class="ranking-chart">'
            f'<h4>Ranking por Produção · {escape(safra)}</h4>'
            f'{"".join(rows)}</div>')


def _commodity_block(estados: list[dict], safras: list[str],
                     classe: str, titulo: str,
                     proj_set: set | None = None) -> str:
    """Bloco de uma commodity (soja ou milho) — tabela + ranking."""
    return (f'<div class="crop-block {classe}">'
            f'<h4>{escape(titulo)}</h4>'
            f'{_states_table(estados, safras, proj_set)}'
            f'{_ranking_bars(estados, safras[-1], classe)}'
            f'</div>')


def _view_estados(dados: dict) -> str:
    br = dados.get("estados_brasil", {})
    us = dados.get("estados_eua", {})
    if not br and not us:
        return ('<div class="view states-view" data-view="estados">'
                '<div class="empty-note">Dados por estado ainda não carregados.</div></div>')

    safras_br = br.get("safras", [])
    safras_us = us.get("safras", [])
    proj_br = set(br.get("safras_projetadas", []))
    proj_us = set(us.get("safras_projetadas", []))
    src_br = br.get("fonte_principal") or br.get("fonte", "Conab / IBGE")
    src_us = us.get("fonte_principal") or us.get("fonte", "USDA NASS")
    fontes_br = br.get("fontes_detalhadas", [])
    fontes_us = us.get("fontes_detalhadas", [])

    def _fontes_html(fontes: list[str]) -> str:
        if not fontes:
            return ""
        items = "".join(f'<li>{escape(f)}</li>' for f in fontes)
        return (f'<div class="sources-detail"><strong>Fontes</strong>'
                f'<ul>{items}</ul></div>')

    # Bloco BRASIL — agora vertical (soja em cima, milho embaixo)
    bloco_br = ""
    if br:
        bloco_br = (
            f'<div class="region-block">'
            f'<div class="region-head">'
            f'<div><span class="flag">🇧🇷</span><h3 style="display:inline">Brasil — Estados</h3></div>'
            f'<div class="src">Fonte: {escape(src_br)}</div>'
            f'</div>'
            f'{_fontes_html(fontes_br)}'
            f'<div class="commodity-pair">'
            f'{_commodity_block(br.get("soja", []), safras_br, "soja", "Soja — Top 10 estados", proj_br)}'
            f'{_commodity_block(br.get("milho", []), safras_br, "milho", "Milho — Top 10 estados", proj_br)}'
            f'</div></div>')

    # Bloco EUA — também vertical
    bloco_us = ""
    if us:
        bloco_us = (
            f'<div class="region-block">'
            f'<div class="region-head">'
            f'<div><span class="flag">🇺🇸</span><h3 style="display:inline">Estados Unidos — Estados</h3></div>'
            f'<div class="src">Fonte: {escape(src_us)}</div>'
            f'</div>'
            f'{_fontes_html(fontes_us)}'
            f'<div class="commodity-pair">'
            f'{_commodity_block(us.get("soja", []), safras_us, "us-soja", "Soybean — Top 10 states", proj_us)}'
            f'{_commodity_block(us.get("milho", []), safras_us, "us-milho", "Corn — Top 10 states", proj_us)}'
            f'</div></div>')

    # Resumo BR vs US
    def _total_safra(estados: list[dict], safra: str) -> float:
        return sum((e["dados"].get(safra, {}).get("producao") or 0) for e in estados)

    sj_br = _total_safra(br.get("soja", []), safras_br[-1]) if safras_br else 0
    sj_us = _total_safra(us.get("soja", []), safras_us[-1]) if safras_us else 0
    ml_br = _total_safra(br.get("milho", []), safras_br[-1]) if safras_br else 0
    ml_us = _total_safra(us.get("milho", []), safras_us[-1]) if safras_us else 0

    comp = f"""
<section style="margin-top:8px">
  <h2>Comparativo Brasil × Estados Unidos
    <span class="sub">Top 10 estados · soma de produção</span></h2>
  <div class="kpi-row" style="grid-template-columns:repeat(4,1fr);margin:18px 0">
    <div class="kpi"><div class="label">Soja BR (Top 10)</div>
      <div class="value">{fmt_n(sj_br, 1)} Mt</div>
      <div class="delta">safra {escape(safras_br[-1] if safras_br else '—')}</div></div>
    <div class="kpi"><div class="label">Soja EUA (Top 10)</div>
      <div class="value">{fmt_n(sj_us, 1)} Mt</div>
      <div class="delta">safra {escape(safras_us[-1] if safras_us else '—')}</div></div>
    <div class="kpi"><div class="label">Milho BR (Top 10)</div>
      <div class="value">{fmt_n(ml_br, 1)} Mt</div>
      <div class="delta">safra {escape(safras_br[-1] if safras_br else '—')}</div></div>
    <div class="kpi"><div class="label">Milho EUA (Top 10)</div>
      <div class="value">{fmt_n(ml_us, 1)} Mt</div>
      <div class="delta">safra {escape(safras_us[-1] if safras_us else '—')}</div></div>
  </div>
</section>"""

    # Nota apontando para a 5ª aba dedicada
    export_note = """
<section><h2>Exportação por Estado <span class="sub">disponível em aba dedicada</span></h2>
<div class="export-note">
  <strong>📊 A análise de exportação por UF está em aba própria.</strong>
  Acesse <strong>"Fluxo de Exportação por UF"</strong> no toggle superior para ver:
  volumes YTD por estado de origem, FOB em US$, variação a/a e ranking
  para soja, milho, farelo e óleo.
  <br><br>
  <strong>Fonte:</strong> ComexStat (MDIC) por NCM e UF de origem da carga.
</div>
</section>"""

    return f"""
<div class="view states-view" data-view="estados">
  <p class="intro">Visão <strong>Áreas e Produção</strong> — área plantada, produtividade
  e produção por estado para Brasil e Estados Unidos, comparando 3 safras consecutivas.
  Tabela inclui variação a/a (Δ) e ranking visual por produção da safra mais recente.</p>

  {comp}
  {bloco_br}
  {bloco_us}
  {export_note}

  <div class="synth"><strong>Notas:</strong> dados convertidos para sistema métrico
  (Mt e kg/ha). Rendimentos do milho EUA são especialmente altos por usarem cultivares
  de alta tecnologia e clima temperado mais estável. Brasil compensa via 2ª safra
  (safrinha) e expansão de área no Centro-Oeste.</div>
</div>"""


# =====================================================================
# VISÃO EXPORTAÇÕES POR UF (5ª aba) — ComexStat
# =====================================================================
def _exports_table(estados: list[dict], periodos: dict,
                   commodity_label: str) -> str:
    """Tabela YTD: UF, nome, vol_2024, vol_2025, vol_2026, FOB, %total, Δ a/a."""
    p_ant = periodos.get("periodo_anterior", "YTD ano-1")
    p_atu = periodos.get("periodo_atual", "YTD ano corrente")
    p_2a = periodos.get("periodo_2anos", "YTD ano-2")
    body = []
    tot_a = sum(e.get("ytd_2024") or 0 for e in estados)
    tot_b = sum(e.get("ytd_2025") or 0 for e in estados)
    tot_c = sum(e.get("ytd_2026") or 0 for e in estados)
    tot_fob = sum(e.get("fob_2026") or 0 for e in estados)
    for e in estados:
        v_a = e.get("ytd_2024") or 0
        v_b = e.get("ytd_2025") or 0
        v_c = e.get("ytd_2026") or 0
        delta_yoy = ((v_c / v_b - 1) * 100) if v_b else 0
        cls_d = "up" if delta_yoy >= 0 else "dn"
        seta = "▲" if delta_yoy >= 0 else "▼"
        body.append(
            f'<tr>'
            f'<td class="uf">{escape(e["uf"])}</td>'
            f'<td class="nome">{escape(e["nome"])}</td>'
            f'<td>{fmt_n(v_a, 0)}</td>'
            f'<td>{fmt_n(v_b, 0)}</td>'
            f'<td class="current">{fmt_n(v_c, 0)}</td>'
            f'<td class="current">{fmt_n(e.get("fob_2026"), 0)}</td>'
            f'<td>{fmt_n(e.get("pct_total"), 1)}%</td>'
            f'<td class="delta {cls_d}">{seta} {abs(delta_yoy):.1f}%</td>'
            f'</tr>')
    delta_tot = ((tot_c / tot_b - 1) * 100) if tot_b else 0
    cls_dt = "up" if delta_tot >= 0 else "dn"
    seta_t = "▲" if delta_tot >= 0 else "▼"
    body.append(
        f'<tr class="totals">'
        f'<td class="uf">Σ</td><td class="nome">Top {len(estados)}</td>'
        f'<td>{fmt_n(tot_a, 0)}</td>'
        f'<td>{fmt_n(tot_b, 0)}</td>'
        f'<td class="current">{fmt_n(tot_c, 0)}</td>'
        f'<td class="current">{fmt_n(tot_fob, 0)}</td>'
        f'<td>—</td>'
        f'<td class="delta {cls_dt}">{seta_t} {abs(delta_tot):.1f}%</td>'
        f'</tr>')
    return (f'<table class="exports">'
            f'<thead><tr>'
            f'<th>UF</th><th>Estado</th>'
            f'<th>{escape(p_2a)}<br>(kt)</th>'
            f'<th>{escape(p_ant)}<br>(kt)</th>'
            f'<th class="current">{escape(p_atu)}<br>(kt)</th>'
            f'<th class="current">FOB 2026<br>(US$ Mi)</th>'
            f'<th>% Total</th>'
            f'<th>Δ a/a</th>'
            f'</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def _exports_yoy_bars(estados: list[dict], cls_bar: str) -> str:
    """Ranking horizontal pelo volume YTD do ano corrente."""
    rows = []
    sorted_e = sorted(estados, key=lambda e: e.get("ytd_2026") or 0, reverse=True)
    vmax = max((e.get("ytd_2026") or 0) for e in sorted_e) or 1
    for e in sorted_e:
        v = e.get("ytd_2026") or 0
        v_b = e.get("ytd_2025") or 0
        delta = ((v / v_b - 1) * 100) if v_b else 0
        seta = "▲" if delta >= 0 else "▼"
        cls_d = "up" if delta >= 0 else "dn"
        pct_w = v / vmax * 100 if vmax else 0
        rows.append(
            f'<div class="bar-row exp">'
            f'<span class="uf">{escape(e["uf"])}</span>'
            f'<div class="bar-track">'
            f'<div class="bar-fill {cls_bar}" style="width:{pct_w:.1f}%">'
            f'{fmt_n(v, 0)} kt</div></div>'
            f'<span class="val {cls_d}" style="font-weight:700">'
            f'{seta} {abs(delta):.1f}%</span>'
            f'</div>')
    return (f'<div class="yoy-bars">'
            f'<h4>Ranking YTD 2026 + variação a/a vs. YTD 2025</h4>'
            f'{"".join(rows)}</div>')


def _commodity_exp_block(estados: list[dict], periodos: dict,
                         titulo: str, cls_bar: str) -> str:
    if not estados:
        return ""
    tot_atu = sum(e.get("ytd_2026") or 0 for e in estados)
    tot_ant = sum(e.get("ytd_2025") or 0 for e in estados)
    delta = ((tot_atu / tot_ant - 1) * 100) if tot_ant else 0
    seta = "▲" if delta >= 0 else "▼"
    return (f'<div class="commodity-block">'
            f'<div class="commodity-head">'
            f'<h3>{escape(titulo)}</h3>'
            f'<div class="totals-strip">'
            f'YTD 2026: <strong>{fmt_n(tot_atu, 0)} kt</strong> · '
            f'a/a {seta} {abs(delta):.1f}%</div>'
            f'</div>'
            f'<div class="commodity-body">'
            f'{_exports_table(estados, periodos, titulo)}'
            f'</div>'
            f'{_exports_yoy_bars(estados, cls_bar)}'
            f'</div>')


def _view_exportacoes_uf(dados: dict) -> str:
    bloco = dados.get("exportacoes_uf")
    if not bloco:
        return ('<div class="view exports-view" data-view="exportacoes">'
                '<div class="empty-note">Dados de exportação por UF não carregados.</div></div>')

    fontes = bloco.get("fontes_detalhadas", [])
    fontes_html = ""
    if fontes:
        items = "".join(f'<li>{escape(f)}</li>' for f in fontes)
        fontes_html = (f'<div class="sources-detail" style="border:1px solid var(--line);'
                       f'border-top:none;margin-bottom:18px">'
                       f'<strong>Fontes</strong><ul>{items}</ul></div>')

    periodos = {
        "periodo_atual": bloco.get("periodo_atual", "YTD"),
        "periodo_anterior": bloco.get("periodo_anterior", "YTD ano-1"),
        "periodo_2anos": bloco.get("periodo_2anos", "YTD ano-2"),
    }

    # KPI strip resumo total YTD
    def _tot(key):
        return sum(e.get("ytd_2026") or 0 for e in bloco.get(key, []))

    kpi = f"""
<div class="kpi-row" style="grid-template-columns:repeat(4,1fr);margin:18px 0">
  <div class="kpi"><div class="label">Soja · YTD 2026</div>
    <div class="value">{fmt_n(_tot('soja'), 0)} kt</div>
    <div class="delta">{escape(periodos['periodo_atual'])}</div></div>
  <div class="kpi"><div class="label">Milho · YTD 2026</div>
    <div class="value">{fmt_n(_tot('milho'), 0)} kt</div>
    <div class="delta">{escape(periodos['periodo_atual'])}</div></div>
  <div class="kpi"><div class="label">Farelo · YTD 2026</div>
    <div class="value">{fmt_n(_tot('farelo_soja'), 0)} kt</div>
    <div class="delta">{escape(periodos['periodo_atual'])}</div></div>
  <div class="kpi"><div class="label">Óleo · YTD 2026</div>
    <div class="value">{fmt_n(_tot('oleo_soja'), 0)} kt</div>
    <div class="delta">{escape(periodos['periodo_atual'])}</div></div>
</div>"""

    blocks = (
        _commodity_exp_block(bloco.get("soja", []), periodos,
                             "Soja em grão", "exp-soja") +
        _commodity_exp_block(bloco.get("milho", []), periodos,
                             "Milho em grão", "exp-milho") +
        _commodity_exp_block(bloco.get("farelo_soja", []), periodos,
                             "Farelo de Soja", "exp-farelo") +
        _commodity_exp_block(bloco.get("oleo_soja", []), periodos,
                             "Óleo de Soja", "exp-oleo")
    )

    return f"""
<div class="view exports-view" data-view="exportacoes">
  <p class="intro">Visão <strong>Fluxo de Exportação por UF</strong> — volume embarcado
  acumulado YTD (Year-to-Date) por estado de origem da carga, com FOB em US$ milhões e
  variação a/a vs. mesmo período do ano anterior. Quatro commodities do complexo:
  soja em grão, milho, farelo e óleo.</p>

  {kpi}

  {fontes_html}

  {blocks}

  <div class="disclaimer-box">
    <strong>⚠ Observação metodológica:</strong> os dados são consolidados pela
    <strong>UF de origem da carga</strong> declarada na DUE (Declaração Única de
    Exportação) — pode diferir da UF do porto de embarque. Por exemplo: soja
    produzida no PR frequentemente embarca por SC ou SP. Esta visão prioriza a
    origem produtiva, não o ponto logístico.<br><br>
    <strong>Atualização:</strong> ComexStat publica dados consolidados mensalmente
    (D+30 do mês de referência). YTD acumulado é recalculado a cada novo mês
    publicado. Configure o coletor para refresh diário durante a janela útil.
  </div>

  <div class="synth"><strong>Leitura geral:</strong>
  Mato Grosso domina exportação de soja e milho com folga (~31% e ~38%).
  Paraná é #1 em farelo (capacidade de esmagamento) e óleo (mesmo motivo).
  Milho mostra <strong>aceleração estrutural a/a</strong> (acima de +40%)
  consolidando o ciclo da safrinha 2025/26.</div>
</div>"""


# =====================================================================
# VISÃO CAPACIDADE ESTÁTICA (6ª aba) — Conab/SICARM
# =====================================================================
def _stack_bar_inline(seg_values: dict, total: float) -> str:
    """Barra empilhada inline mostrando composição por tipo."""
    if total <= 0:
        return ""
    segs = []
    for tipo in ("particular", "cooperativa", "exportador", "outros"):
        v = seg_values.get(tipo) or 0
        if v <= 0:
            continue
        pct = v / total * 100
        label = f"{pct:.0f}%" if pct >= 8 else ""
        segs.append(
            f'<div class="seg {tipo}" style="width:{pct:.1f}%" '
            f'title="{tipo.capitalize()}: {v:.1f} Mt ({pct:.1f}%)">{label}</div>')
    return f'<div class="cap-stack-bar">{"".join(segs)}</div>'


def _view_capacidades(dados: dict) -> str:
    cap = dados.get("capacidade_estatica")
    if not cap:
        return ('<div class="view cap-view" data-view="capacidades">'
                '<div class="empty-note">Dados de capacidade estática não carregados.</div></div>')

    tot = cap.get("totais_nacional", {})
    total_nac = tot.get("total") or 0
    fontes = cap.get("fontes_detalhadas", [])
    data_ref = cap.get("data_referencia", "—")

    # Cross-reference com produção (estados_brasil) para calcular déficit
    estados_br = dados.get("estados_brasil", {})
    safras_br = estados_br.get("safras", [])
    safra_atual = safras_br[-1] if safras_br else None

    # Map UF -> produção total (soja + milho) na safra atual
    prod_uf = {}
    if safra_atual:
        for crop in ("soja", "milho"):
            for e in estados_br.get(crop, []):
                v = (e["dados"].get(safra_atual) or {}).get("producao") or 0
                prod_uf[e["uf"]] = prod_uf.get(e["uf"], 0) + v

    # Cards de breakdown nacional
    def _card(tipo: str, label: str) -> str:
        v = tot.get(tipo) or 0
        pct = (v / total_nac * 100) if total_nac else 0
        return (f'<div class="cb-card {tipo}">'
                f'<div class="label">{escape(label)}</div>'
                f'<div class="value">{fmt_n(v, 1)} Mt</div>'
                f'<div class="pct">{pct:.1f}% do total</div>'
                f'</div>')

    breakdown = (
        f'<div class="cap-breakdown">'
        f'{_card("particular", "Particular")}'
        f'{_card("cooperativa", "Cooperativa")}'
        f'{_card("exportador", "Exportador")}'
        f'{_card("outros", "Outros (Conab + 3ª parte)")}'
        f'</div>')

    # Tabela detalhada por UF
    body = []
    soma = {"total": 0, "particular": 0, "cooperativa": 0,
            "exportador": 0, "outros": 0}
    for u in cap.get("por_uf", []):
        for k in soma:
            soma[k] += u.get(k) or 0
        prod = prod_uf.get(u["uf"], 0)
        # Razão produção / capacidade — > 1 indica déficit estrutural
        razao = (prod / u["total"]) if u["total"] else 0
        if razao >= 1.5:
            cls_def, lbl_def = "high", "Déficit severo"
        elif razao >= 1.0:
            cls_def, lbl_def = "mid", "Déficit"
        else:
            cls_def, lbl_def = "ok", "Adequada"

        body.append(
            f'<tr>'
            f'<td class="uf">{escape(u["uf"])}</td>'
            f'<td class="nome">{escape(u["nome"])}</td>'
            f'<td class="total">{fmt_n(u["total"], 2)}</td>'
            f'<td>{fmt_n(u.get("particular"), 2)}</td>'
            f'<td>{fmt_n(u.get("cooperativa"), 2)}</td>'
            f'<td>{fmt_n(u.get("exportador"), 2)}</td>'
            f'<td>{fmt_n(u.get("outros"), 2)}</td>'
            f'<td class="bar-cell">{_stack_bar_inline(u, u["total"])}</td>'
            f'<td>{fmt_n(prod, 1)}</td>'
            f'<td class="deficit {cls_def}" title="{lbl_def}">'
            f'{razao*100:.0f}%</td>'
            f'</tr>')

    # Linha total
    soma_prod = sum(prod_uf.values())
    razao_tot = (soma_prod / soma["total"]) if soma["total"] else 0
    cls_dt = "high" if razao_tot >= 1.5 else "mid" if razao_tot >= 1 else "ok"
    body.append(
        f'<tr class="totals">'
        f'<td class="uf">Σ</td><td class="nome">Top {len(cap.get("por_uf", []))}</td>'
        f'<td class="total">{fmt_n(soma["total"], 1)}</td>'
        f'<td>{fmt_n(soma["particular"], 1)}</td>'
        f'<td>{fmt_n(soma["cooperativa"], 1)}</td>'
        f'<td>{fmt_n(soma["exportador"], 1)}</td>'
        f'<td>{fmt_n(soma["outros"], 1)}</td>'
        f'<td class="bar-cell">{_stack_bar_inline(soma, soma["total"])}</td>'
        f'<td>{fmt_n(soma_prod, 1)}</td>'
        f'<td class="deficit {cls_dt}">{razao_tot*100:.0f}%</td>'
        f'</tr>')

    tabela = (f'<table class="cap">'
              f'<thead><tr>'
              f'<th>UF</th><th>Estado</th><th>Total (Mt)</th>'
              f'<th>Particular</th><th>Cooperativa</th>'
              f'<th>Exportador</th><th>Outros</th>'
              f'<th>Composição</th>'
              f'<th>Prod. {escape(safra_atual or "")} (Mt)</th>'
              f'<th>Prod./Cap.</th>'
              f'</tr></thead>'
              f'<tbody>{"".join(body)}</tbody></table>')

    legend = ('<div class="legend-types">'
              '<div class="lg particular"><span class="swatch"></span>Particular</div>'
              '<div class="lg cooperativa"><span class="swatch"></span>Cooperativa</div>'
              '<div class="lg exportador"><span class="swatch"></span>Exportador</div>'
              '<div class="lg outros"><span class="swatch"></span>Outros (Conab/3ª parte)</div>'
              '</div>')

    fontes_html = ""
    if fontes:
        items = "".join(f"<li>{escape(f)}</li>" for f in fontes)
        fontes_html = (f'<div class="sources-detail" style="border:1px solid var(--line);'
                       f'margin:0 0 18px">'
                       f'<strong>Fontes</strong><ul>{items}</ul></div>')

    return f"""
<div class="view cap-view" data-view="capacidades">
  <p class="intro">Visão <strong>Capacidade Estática</strong> — armazenagem de grãos
  por UF, segregada por <strong>tipo de proprietário</strong>: Particular (produtores
  e empresas privadas), Cooperativa (rede cooperativista), Exportador (trading companies)
  e Outros (Conab + indústrias). Coluna <strong>Prod./Cap.</strong> compara produção
  (soja+milho da última safra) com a capacidade — valores acima de 100% indicam
  déficit estrutural de armazenagem.</p>

  <div class="cap-summary">
    <strong>Brasil — total nacional:</strong> {fmt_n(total_nac, 1)} Mt de capacidade
    instalada (referência {escape(data_ref)}). Brasil produz mais grãos do que armazena —
    o <strong>déficit estrutural</strong> obriga escoamento rápido pós-colheita,
    pressionando logística e prêmios FOB.
  </div>

  {breakdown}

  {fontes_html}

  <h3 style="margin-top:24px">Detalhamento por Estado</h3>
  {legend}
  {tabela}

  <div class="synth"><strong>Leitura:</strong>
  Mato Grosso é o estado com maior capacidade absoluta (~53 Mt), mas também o maior
  déficit relativo (produção ~96 Mt — razão ~180%). Sul (RS+PR+SC) tem perfil
  cooperativista forte (~40-50% da capacidade). Trading companies (Bunge, Cargill, ADM)
  concentram capacidade em portos e corredores logísticos do Centro-Oeste e Norte.
  </div>
</div>"""


# =====================================================================
# VIEWS (Dinâmica / Estática)
# =====================================================================
def _view_dinamica(dados: dict, diag: Diagnostico, data_ant: str) -> str:
    alterados = {(m.safra, m.campo) for m in diag.mudancas}
    cur_sj = dados["soja_grao"]["safras"][-1]
    cur_ml = dados["milho"]["safras"][-1]

    kpi = f"""
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
</div>"""

    resumo_synth = escape(diag.resumo or "")
    return f"""
<div class="view dynamic-view active" data-view="dinamica">
  <p class="intro">Modo <strong>atualização diária automática</strong>.
  Células com <span style="background:var(--new);padding:2px 6px;font-weight:700;color:#9A3412">● destaque amarelo</span>
  foram modificadas nesta rodada. As seções abaixo detalham o que mudou desde ontem e o impacto no balanço.</p>

  {kpi}
  {_sec_atualizacao_dia(diag, data_ant)}
  {_sec_impacto_diario(diag)}
  {_sec_sinais_dia(diag)}

  <section><h2>Soja — Grão</h2>{_tabela_soja(dados, alterados, True)}
    <div class="unit-note">Fonte: Conab · USDA · IBGE — células destacadas foram alteradas hoje.</div></section>

  <section><h2>Complexo Soja</h2>
    <h3>Farelo de Soja</h3>{_tabela_sub(dados, "farelo_soja", alterados, True)}
    <h3>Óleo de Soja</h3>{_tabela_sub(dados, "oleo_soja", alterados, True)}</section>

  <section><h2>Milho</h2>{_tabela_milho(dados, alterados, True)}
    <div class="unit-note">3 safras: 1ª (verão · ~20%) + 2ª (safrinha · ~78%) + 3ª (Norte/Nordeste · ~2%) — Conab 7º Lev. 14/04/2026.</div></section>

  <section><h2>Exportações Consolidadas</h2>{_tabela_exp(dados)}</section>

  {_sec_noticias(dados.get("noticias_feed", []))}

  <div class="synth"><strong>Síntese do dia:</strong> {resumo_synth}</div>
</div>"""


def _view_estatica(dados: dict) -> str:
    """Visão limpa — tabelas sem marcação de mudança, formato relatório executivo."""
    cur_sj = dados["soja_grao"]["safras"][-1]
    cur_ml = dados["milho"]["safras"][-1]

    kpi = f"""
<div class="kpi-row">
  <div class="kpi"><div class="label">Soja {cur_sj['safra']}</div>
    <div class="value">{fmt_n(cur_sj['producao'])} Mt</div>
    <div class="delta">Produção projetada</div></div>
  <div class="kpi"><div class="label">Milho {cur_ml['safra']}</div>
    <div class="value">{fmt_n(cur_ml['producao'])} Mt</div>
    <div class="delta">Produção projetada</div></div>
  <div class="kpi"><div class="label">Exportação Soja</div>
    <div class="value">{fmt_n(cur_sj['exportacao'])} Mt</div>
    <div class="delta">{fmt_pct(cur_sj['exportacao']/cur_sj['producao']*100)} da produção</div></div>
  <div class="kpi"><div class="label">Exportação Milho</div>
    <div class="value">{fmt_n(cur_ml['exportacao'])} Mt</div>
    <div class="delta">{fmt_pct(cur_ml['exportacao']/cur_ml['producao']*100)} da produção</div></div>
</div>"""

    return f"""
<div class="view static-view" data-view="estatica">
  <div class="static-label">Relatório Executivo · Visão Consolidada</div>
  <p class="intro">Visão estática — dados tabulares limpos sem destaque de alterações.
  Ideal para impressão, arquivo e apresentações.</p>

  {kpi}

  <section><h2>1. Soja — Grão</h2>{_tabela_soja(dados, set(), False)}
    <div class="unit-note">Fonte: Conab 10º Lev. 2025/26 · USDA/WASDE · IBGE/LSPA.</div></section>

  <section><h2>2. Complexo Soja</h2>
    <h3>2.1 Farelo de Soja</h3>{_tabela_sub(dados, "farelo_soja", set(), False)}
    <h3>2.2 Óleo de Soja</h3>{_tabela_sub(dados, "oleo_soja", set(), False)}</section>

  <section><h2>3. Milho</h2>{_tabela_milho(dados, set(), False)}
    <div class="unit-note">1ª safra (verão · Sul/SE) + 2ª safra (safrinha · Centro-Oeste) + 3ª safra (Norte/Nordeste) — Conab.</div></section>

  <section><h2>4. Exportações Consolidadas</h2>{_tabela_exp(dados)}</section>

  <section><h2>5. Análise de Mercado</h2>
    <div class="analysis">
      <h3>Evolução da produção</h3>
      <p>Produção brasileira de soja cresceu <strong>~27%</strong> entre 2020/21 e a safra corrente.
      Milho acumula expansão de <strong>~56%</strong> no mesmo intervalo, puxado pela 2ª safra
      (safrinha), hoje responsável por ~80% do total.</p>

      <h3>Tendência de consumo</h3>
      <p>Consumo interno de soja cresce <strong>~4% a.a.</strong>, impulsionado por esmagamento
      (mandatos B12 → B14 → B15 no biodiesel). Milho doméstico cresce fortemente com
      etanol de milho em MT/GO.</p>

      <h3>Dinâmica de exportações</h3>
      <p>Brasil líder global em soja (&gt;55% do comércio mundial). Em milho, disputa topo com EUA.
      Concentração chinesa em soja (~72% dos embarques) é risco geopolítico estrutural.</p>

      <h3>Estoques e balanço</h3>
      <p>Soja com estoque/uso em <strong>{fmt_pct(cur_sj.get('estoque_uso_pct'))}</strong>;
      milho em <strong>{fmt_pct(cur_ml.get('estoque_uso_pct'))}</strong>. Ambos permanecem
      estruturalmente apertados frente à média global (&gt;25%).</p>
    </div>
  </section>

</div>"""


# =====================================================================
# RENDER PRINCIPAL
# =====================================================================
def gerar_unified(dados: dict, diag: Diagnostico, meta_atual: dict,
                   meta_anterior: dict | None, saida: Path) -> None:
    saida.parent.mkdir(exist_ok=True, parents=True)

    def _dt(meta: dict | None, fallback: str = "—") -> str:
        if not meta:
            return fallback
        try:
            d = datetime.fromisoformat(
                meta["atualizado_em"].replace("Z", "+00:00"))
            return d.strftime("%d/%m/%Y %H:%M")
        except (KeyError, ValueError):
            return meta.get("atualizado_em", fallback)

    data_atual = _dt(meta_atual)
    data_ant = _dt(meta_anterior, "primeira execução")

    n_muds = len(diag.mudancas)
    badge_diario = ("✓ SEM ALTERAÇÕES RELEVANTES" if n_muds == 0
                    else f"● {n_muds} MUDANÇA(S) HOJE")

    # Marca d'água: logo embutido UMA vez via variável CSS
    wm_url = logo_base64()
    wm_css = (f':root{{--watermark:url("{wm_url}")}}' if wm_url
              else ':root{--watermark:none}')

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<title>SnD Brasil — Soja e Milho · Daily Refresh</title>
<style>{wm_css}{CSS}</style></head><body><div class="page">

<header class="top">
  <div class="brand">{logo_tag(54)}
    <div class="divider"></div>
    <div class="tagline"><strong>Research &amp; Market Intelligence</strong>
      Daily Refresh · SnD Soja &amp; Milho Brasil</div>
  </div>
  <div class="doc-meta">
    <div class="date">Atualizado em {data_atual}</div>
    <div>Snapshot anterior: {data_ant}</div>
    <div><span class="badge">{badge_diario}</span></div>
  </div>
</header>

<h1 class="title">Supply and Demand Brasil — Soja e Milho</h1>
<div class="subtitle">Atualização Diária Automática</div>

<div class="toolbar">
  <div class="view-switcher" role="tablist">
    <button data-view="dinamica" class="active" role="tab">
      <span class="dot"></span>Visão Dinâmica
    </button>
    <button data-view="estatica" role="tab">
      <span class="dot"></span>Visão Estática
    </button>
    <button data-view="graficos" role="tab">
      <span class="dot"></span>Visão Gráficos
    </button>
    <button data-view="estados" role="tab">
      <span class="dot"></span>Áreas e Produção
    </button>
    <button data-view="exportacoes" role="tab">
      <span class="dot"></span>Fluxo de Exportação por UF
    </button>
    <button data-view="capacidades" role="tab">
      <span class="dot"></span>Capacidade Estática
    </button>
  </div>
  <div class="actions">
    <button class="print-btn" type="button" id="print-pdf-btn" title="Gerar PDF com todas as visões">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 9V2h12v7"/>
        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
        <rect x="6" y="14" width="12" height="8"/>
      </svg>
      Gerar PDF
    </button>
  </div>
</div>

{_view_dinamica(dados, diag, data_ant)}
{_view_estatica(dados)}
{_view_graficos(dados)}
{_view_estados(dados)}
{_view_exportacoes_uf(dados)}
{_view_capacidades(dados)}

<footer>
  <div class="src"><strong>Fontes:</strong> Conab 7º Levantamento Safra 2025/26 (14/04/2026) ·
    USDA/WASDE · IBGE SIDRA · ComexStat · CEPEA · pipeline automatizado Innovagro.
    <em>Casas privadas (StoneX, AgRural, Safras &amp; Mercado) podem divergir 3-8 Mt — metodologias próprias.</em></div>
  <div>© 2026 Innovagro Brasil · Daily Refresh · Não constitui recomendação de investimento.</div>
</footer>
</div>
<script>{JS}</script>
</body></html>"""

    saida.write_text(html, encoding="utf-8")
