# SnD Brasil — Soja e Milho

Relatório público de **Supply and Demand** (oferta e demanda) de soja e milho brasileiros, com coleta automática de fontes oficiais e regeneração sob demanda.

🌐 **Live:** https://snd-brasil.onrender.com
📦 **Backup estático (GitHub Pages):** https://nathyaug-lang.github.io/snd-brasil/

---

## O que esse site faz

Apresenta o balanço de oferta e demanda de **soja** e **milho** no Brasil em seis visões:

- **Visão Dinâmica** — destaca células que mudaram desde a última atualização (●)
- **Visão Estática** — tabela completa do balanço atual
- **Visão Gráficos** — produção × exportação × consumo, séries históricas + projeção
- **Áreas e Produção** — estados produtores (Centro-Oeste, Sul, Nordeste, etc.)
- **Fluxo de Exportação por UF** — origem e destino dos embarques
- **Capacidade Estática** — armazenagem e infraestrutura logística

Cada visão tem um botão de copiar imagem (PNG) e a página inteira pode ser salva como PDF.

## Como atualizar

Clique no botão verde **Atualizar** no topo da página. Isso dispara o pipeline server-side (~30-90s) que:

1. Consulta Conab (RSS), CEPEA (RSS), IBGE SIDRA, ComexStat e USDA PSD
2. Compara com o snapshot anterior, registra o que mudou
3. Regrava o HTML público
4. Recarrega a página com os dados novos

## Fontes consumidas

| Fonte | Tipo | Uso |
|---|---|---|
| Conab | RSS | Notícias e boletins de safra |
| CEPEA/ESALQ | RSS | Sinais de preço e mercado |
| IBGE SIDRA | API REST (JSON) | Validação LSPA — tabela 6588 |
| ComexStat (MDIC) | API POST (JSON) | Volumes exportados por NCM |
| USDA PSD | API REST (chave) | Referência global (opcional) |

## Stack

- **Backend:** Python 3.12 + Flask + gunicorn
- **Frontend:** HTML/CSS/JS estático autocontido (CSS e JS inline)
- **Hospedagem:** [Render](https://render.com) (free tier) via Blueprint (`render.yaml`)
- **Versionamento:** GitHub — auto-deploy a cada push em `main`

## Rodar localmente

```bash
pip install -r requirements.txt
python app.py        # http://localhost:8000
```

Ou só rodar o pipeline (sem servir HTTP):

```bash
python atualizar_snd.py             # atualização completa
python atualizar_snd.py --apenas-feeds   # só notícias (mais rápido)
python atualizar_snd.py --dry-run        # simula sem gravar
```

## Endpoints

| Rota | Método | Descrição |
|---|---|---|
| `/` | GET | Serve `output/SnD_Brasil_Unified.html` |
| `/atualizar` | POST | Executa pipeline + reaplica patches públicos. Retorna JSON. |
| `/healthz` | GET | Status: `{ok, html_exists, running, last_run, last_error}` |

## Aviso

Os dados são compilados de fontes públicas e o relatório **não constitui recomendação de investimento**. Casas privadas (StoneX, AgRural, Safras & Mercado) podem divergir 3-8 Mt em projeções de safra — metodologias próprias.

---

Para contexto interno e instruções pra desenvolvedores, ver [CONTEXTO.md](CONTEXTO.md).
