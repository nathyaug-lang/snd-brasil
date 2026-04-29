# SnD Brasil — Soja e Milho

Site público do relatório Supply and Demand (SnD) Brasil — Soja e Milho.

Roda como app Flask no Render. O botão **Atualizar** dispara o pipeline server-side que coleta dados de Conab, CEPEA, IBGE SIDRA, ComexStat e USDA, regenera o HTML e recarrega a página com a versão nova.

## Arquitetura

| Componente | Função |
|---|---|
| `app.py` | Flask app — serve o HTML em `/`, executa pipeline em `POST /atualizar`, status em `/healthz`. |
| `atualizar_snd.py` | Pipeline principal — coleta fontes, faz diff, regrava snapshot, gera HTMLs. |
| `gerar_unified_html.py`, `gerar_html.py`, `gerar_alertas_html.py` | Geradores de HTML (visões dinâmica, estática, gráficos, alertas). |
| `detector_mudancas.py` | Diff estrutural entre snapshots. |
| `dados/snd_dados.json` | Snapshot vivo (entrada e saída do pipeline). |
| `output/SnD_Brasil_Unified.html` | HTML servido publicamente. |
| `Procfile`, `render.yaml`, `runtime.txt`, `requirements.txt` | Deploy Render. |

## Endpoints

- `GET /` — serve `output/SnD_Brasil_Unified.html`.
- `POST /atualizar` — executa pipeline (~30-90s). Retorna JSON com `mudancas`, `noticias`, `alertas`, `last_run`. Lock em memória previne execuções concorrentes.
- `GET /healthz` — status do app.

## Rodar localmente

```bash
pip install -r requirements.txt
python app.py            # http://localhost:8000
# ou
gunicorn app:app --timeout 180
```

## Atualização de dados

Cada clique no botão **Atualizar** roda o pipeline completo (`atualizar_snd.executar()`) e re-aplica os patches públicos no HTML (botão + handler). Não há agendamento automático.

## Persistência

Render free tier tem filesystem efêmero — snapshots e HTMLs vivem entre requisições mas são resetados a cada deploy. Para persistência real, usar disk add-on do Render ou commitar os snapshots de volta ao repo via Action.
