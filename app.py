"""
SnD Brasil - Soja e Milho - Servidor Flask para Render.

Rotas:
  GET  /            -> serve output/SnD_Brasil_Unified.html (versao publica)
  POST /atualizar   -> executa pipeline completo (atualizar_snd.py) e regrava o HTML
  GET  /healthz     -> status (uptime, ultima atualizacao, ultimo erro)
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, send_file

BASE = Path(__file__).resolve().parent
OUTPUT_HTML = BASE / "output" / "SnD_Brasil_Unified.html"

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

_lock = threading.Lock()
_state: dict = {"last_run": None, "last_error": None, "running": False}


# --------------------------------------------------------------------------
# Patches publicos aplicados sobre o HTML recem-gerado pelo pipeline.
# - injeta o botao "Atualizar" verde
# - troca o handler para POST /atualizar (em vez de reload simples)
# Logo + watermark ja sao tratados pelo gerador (logo_tag retorna "" quando
# o arquivo do logo nao existe na pasta assets/).
# --------------------------------------------------------------------------
_UPDATE_BTN_HTML = (
    '<button class="print-btn update-btn" type="button" id="update-btn" '
    'title="Buscar dados mais recentes (roda o pipeline)">'
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="23 4 23 10 17 10"/>'
    '<polyline points="1 20 1 14 7 14"/>'
    '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/>'
    '<path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/>'
    '</svg>Atualizar</button>\n    '
)

_UPDATE_BTN_CSS = (
    "\n.update-btn{background:var(--green);border-color:var(--green)}"
    "\n.update-btn:hover{background:var(--green-soft);border-color:var(--green-soft)}"
    "\n.update-btn:disabled{opacity:.6;cursor:wait}"
)

_UPDATE_HANDLER_JS = """
  // ============ ATUALIZAR (POST /atualizar) ============
  function setupUpdateButton(){
    const btn = document.getElementById('update-btn');
    if(!btn) return;
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      const original = btn.innerHTML;
      btn.innerHTML = btn.innerHTML.replace('Atualizar', 'Atualizando...');
      showToast('Atualizando dados — pode levar até 2 minutos...');
      try {
        const r = await fetch('/atualizar', {method:'POST'});
        const data = await r.json().catch(() => ({status:'error', message:'resposta invalida'}));
        if (r.ok && data.status === 'ok') {
          showToast('Atualizado! Recarregando...');
          setTimeout(() => {
            const url = new URL(window.location.href);
            url.searchParams.set('_t', Date.now().toString());
            window.location.href = url.toString();
          }, 600);
        } else if (r.status === 409) {
          showToast('Já existe uma atualização em andamento. Aguarde.', true);
          btn.disabled = false;
          btn.innerHTML = original;
        } else {
          showToast('Falha: ' + (data.message || data.status || 'erro desconhecido'), true);
          btn.disabled = false;
          btn.innerHTML = original;
        }
      } catch(err) {
        showToast('Erro de rede: ' + err.message, true);
        btn.disabled = false;
        btn.innerHTML = original;
      }
    });
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', setupUpdateButton);
  }else{
    setupUpdateButton();
  }

"""


def aplicar_patches_publico(html_path: Path) -> None:
    """Aplica idempotentemente os patches publicos no HTML."""
    if not html_path.exists():
        app.logger.warning("aplicar_patches_publico: arquivo nao existe %s", html_path)
        return
    src = html_path.read_text(encoding="utf-8")
    if 'id="update-btn"' in src:
        return  # ja patchado

    btn_marker = '<button class="print-btn" type="button" id="print-pdf-btn"'
    if btn_marker in src:
        src = src.replace(btn_marker, _UPDATE_BTN_HTML + btn_marker, 1)

    css_marker = ".print-btn:active{transform:scale(.97)}"
    if css_marker in src:
        src = src.replace(css_marker, css_marker + _UPDATE_BTN_CSS, 1)

    close_marker = "})();\n</script>"
    if close_marker in src:
        src = src.replace(close_marker, _UPDATE_HANDLER_JS + close_marker, 1)

    html_path.write_text(src, encoding="utf-8")
    app.logger.info("Patches publicos aplicados em %s", html_path.name)


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------
@app.route("/")
def index():
    if not OUTPUT_HTML.exists():
        return (
            "<h1>SnD Brasil</h1><p>HTML ainda nao foi gerado. "
            'Faca POST em <code>/atualizar</code> ou aguarde o primeiro deploy.</p>',
            503,
        )
    return send_file(str(OUTPUT_HTML))


@app.route("/atualizar", methods=["POST"])
def atualizar():
    if not _lock.acquire(blocking=False):
        return jsonify({
            "status": "already_running",
            "message": "Atualizacao ja em andamento",
        }), 409

    _state["running"] = True
    try:
        from atualizar_snd import executar  # import tardio para evitar custo no boot
        resultado = executar(apenas_feeds=False, dry_run=False, usda_key=None)
        aplicar_patches_publico(OUTPUT_HTML)
        diag = resultado.get("diagnostico")
        _state["last_run"] = datetime.now().isoformat(timespec="seconds")
        _state["last_error"] = None
        return jsonify({
            "status": "ok",
            "mudancas": len(resultado["mudancas"]),
            "noticias": resultado["noticias"],
            "alertas": (len(diag.alertas) if diag else 0),
            "last_run": _state["last_run"],
        })
    except Exception as e:  # noqa: BLE001 - queremos capturar e devolver via JSON
        app.logger.exception("Falha em /atualizar")
        _state["last_error"] = str(e)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        _state["running"] = False
        _lock.release()


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "html_exists": OUTPUT_HTML.exists(), **_state})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
