# CONTEXTO — SnD Brasil — Soja e Milho (versão pública)

> Documento de contexto pra sessões futuras de Claude. Captura tudo que outro Claude precisa saber pra continuar o projeto sem reler todo o histórico de chat.

---

## 1. Identidade do projeto

- **Nome:** SnD Brasil — Soja e Milho
- **Tipo:** Site público com relatório diário de Supply and Demand (SnD) de soja e milho brasileiros
- **Origem:** Cópia desbrandada do projeto interno SnD_Sistema da Innovagro Brasil
- **URL pública (Render):** https://snd-brasil.onrender.com
- **URL backup (GitHub Pages, estática):** https://nathyaug-lang.github.io/snd-brasil/
- **Repositório:** https://github.com/nathyaug-lang/snd-brasil (público)
- **Owner GitHub:** `nathyaug-lang` (Nathália — Innovagro Brasil)
- **Pasta local:** `C:/Users/Nathália/Desktop/Backup/SnD_Site/`

## 2. Origem e relação com o projeto interno

- O projeto **interno e privado** vive em `C:/Users/Nathália/innovagro/INNOVAGRO - Geral/17 - CODE/00 - NATHALIA/SnD_Sistema/` — esse é o canônico que a Innovagro usa internamente, com logo e branding.
- Em 2026-04-29 foi feita uma cópia pública em `C:/Users/Nathália/Desktop/Backup/SnD_Sistema_Publico/` (cópia bruta de tudo, sem alterações), e depois uma versão de site enxuta em `C:/Users/Nathália/Desktop/Backup/SnD_Site/` (apenas o necessário pra rodar no Render).
- **Nunca mexer no projeto interno em `innovagro/`** sem pedido explícito da usuária. Mudanças de produto vão pro `SnD_Site/`. Mudanças de pipeline (lógica de coleta) podem voltar pro original via merge manual depois.

## 3. Arquitetura

```
┌───────────────────────┐          ┌────────────────────────┐
│   Navegador público   │          │   Render (free tier)   │
│                       │          │                        │
│  GET /                ├─────────▶│  gunicorn → app.py     │
│                       │  serve   │    └─ output/...html   │
│  POST /atualizar      ├─────────▶│  app.py → pipeline     │
│  ↑ botão Atualizar    │          │    ├─ atualizar_snd.py │
│                       │          │    ├─ regenera HTML    │
│                       │◀─────────┤    └─ aplica patches   │
│  reload + cache-bust  │  ok      │                        │
└───────────────────────┘          └────────────────────────┘
                                              │
                                              ▼  externo (read-only)
                                   ┌────────────────────────┐
                                   │ Conab RSS · CEPEA RSS  │
                                   │ IBGE SIDRA · ComexStat │
                                   │ USDA PSD (opcional)    │
                                   └────────────────────────┘
```

**Decisão chave:** GitHub Pages só serve estático. Como a usuária quis que o botão Atualizar **rode o pipeline de fato** ao clicar, migramos pra Render (Flask + gunicorn). Pages segue ativo como backup estático mas não recebe atualizações automáticas.

## 4. Estrutura do repositório

```
SnD_Site/
├── app.py                      # Flask: rotas / e POST /atualizar
├── atualizar_snd.py            # Pipeline (executar() é o entry point)
├── gerar_unified_html.py       # Gera o HTML unificado (visões dinâmica/estática/gráficos/etc)
├── gerar_html.py               # Helpers compartilhados (logo_tag, fmt_n, fmt_pct, logo_base64)
├── gerar_alertas_html.py       # Gera HTML de alertas
├── detector_mudancas.py        # Diff entre snapshots
├── dados/
│   ├── snd_dados.json          # Snapshot vivo (in/out do pipeline)
│   ├── snd_dados_anterior.json # Snapshot da execução anterior
│   └── snd_dados_ontem.json    # Snapshot diário (preserva 'ontem')
├── output/
│   ├── SnD_Brasil_Unified.html             # ← Servido em GET / (com botão Atualizar)
│   ├── SnD_Brasil_Soja_Milho_Dinamico.html # Gerado pelo pipeline (não servido)
│   └── Market_Change_Detection.html        # Gerado pelo pipeline (não servido)
├── logs/                       # Vazio em deploy (gerado em runtime, gitignored)
├── index.html                  # Versão estática usada SOMENTE pelo GitHub Pages backup
├── README.md                   # README público
├── CONTEXTO.md                 # Este arquivo
├── Procfile                    # web: gunicorn app:app --timeout 180 --workers 1
├── render.yaml                 # Blueprint do Render (free, Oregon)
├── requirements.txt            # flask 3.0.3, gunicorn 23.0.0, requests 2.32.3
├── runtime.txt                 # python-3.12.7
└── .gitignore                  # __pycache__, *.log, etc.
```

**Importante:** `index.html` na raiz é uma cópia ESTÁTICA com botão Atualizar simplificado (apenas reload com cache-bust, sem POST). Existe só pra GitHub Pages servir um fallback funcional. O Flask **não** usa esse arquivo. O HTML servido pelo Flask é `output/SnD_Brasil_Unified.html`.

## 5. Diferenças do público vs. projeto interno

Comparado ao `innovagro/.../SnD_Sistema/`:
1. **`assets/logo_innovagro.jpg` deletado** — sem o arquivo, `gerar_html.logo_base64()` retorna string vazia.
2. **`gerar_html.logo_tag()` modificado** — retorna `""` em vez do fallback de texto "INNOVAGRO BRASIL". Linha modificada:
   ```python
   def logo_tag(altura_px: int = 54) -> str:
       src = logo_base64()
       if not src:
           return ""
       return (f'<img class="logo" src="{src}" alt="" '
               f'style="height:{altura_px}px;width:auto;display:block">')
   ```
3. **Watermark dos charts vira `--watermark:none`** automaticamente — `gerar_unified_html.py:2580` já fazia esse fallback quando `logo_base64()` retorna vazio.
4. **Botão "Atualizar" verde** injetado em runtime por `app.aplicar_patches_publico()` ao lado do "Gerar PDF".
5. **`app.py`** novo — não existe no projeto interno (que roda só pelo CLI do `atualizar_snd.py`).
6. **Texto "Innovagro" no footer/tagline foi mantido** — usuária pediu apenas pra remover o logo visual.

## 6. Fluxo de dados completo

### 6.1 Render servindo a página inicial (GET /)
1. Usuário visita https://snd-brasil.onrender.com
2. Flask lê `output/SnD_Brasil_Unified.html` do disco e devolve.
3. Esse HTML já tem:
   - Sem logo (gerado por `gerar_html.logo_tag()` modificado)
   - Sem watermark (`--watermark:none`)
   - Botão Atualizar verde (injetado pela última execução)
   - JS handler do botão fazendo `fetch('/atualizar', {method:'POST'})`

### 6.2 Usuário clica em Atualizar (POST /atualizar)
1. Botão fica disabled, label muda pra "Atualizando...", toast aparece.
2. Frontend POST em `/atualizar`.
3. Flask pega `_lock` (threading.Lock, blocking=False). Se já travado → `409 already_running`.
4. Importa tardio `from atualizar_snd import executar`.
5. `executar(apenas_feeds=False, dry_run=False, usda_key=None)` roda:
   - Lê `dados/snd_dados.json`
   - Coleta Conab RSS, CEPEA RSS, IBGE SIDRA, ComexStat (USDA opcional, sem chave por padrão)
   - Diff contra snapshot
   - Atualiza derivadas
   - Promove snapshot atual pra "anterior", grava novo
   - Chama `gerar_html.gerar()`, `gerar_alertas_html.gerar()`, `gerar_unified_html.gerar_unified()`
   - Resultado: `output/SnD_Brasil_Unified.html` regravado (limpo, sem botão Atualizar)
6. `aplicar_patches_publico(OUTPUT_HTML)` injeta o botão verde, CSS e handler de volta.
7. Retorna JSON `{status:"ok", mudancas, noticias, alertas, last_run}`.
8. Frontend mostra toast "Atualizado!" e recarrega com `?_t=<timestamp>` pra furar cache.
9. GET / serve o novo HTML.

### 6.3 Erro durante atualização
- Frontend espera JSON. Em qualquer erro 5xx ou rede, mostra toast vermelho com mensagem.
- `_lock.release()` no finally — nunca trava o serviço.

## 7. A função `aplicar_patches_publico` (em `app.py`)

É **idempotente** — se o HTML já tem `id="update-btn"`, não faz nada. Senão:
1. Insere o `<button class="print-btn update-btn" ...>` antes do `<button id="print-pdf-btn">`.
2. Adiciona regras CSS `.update-btn{...}` depois de `.print-btn:active`.
3. Injeta o handler JS antes do fechamento `})();</script>`.

Os 3 marcadores (`btn_marker`, `css_marker`, `close_marker`) são strings hardcoded que precisam casar exatamente com o que `gerar_unified_html.py` produz. **Se o gerador mudar esses trechos, o patch falha silenciosamente** (o `if marker in src` previne crash mas não avisa).

## 8. Render — config e limitações

### 8.1 Plano free (atual)
- **750 horas/mês** de execução (suficiente pra um serviço sempre-ligado)
- **Sleep após 15 min idle** — primeira request acorda em 30-60s (cold start)
- **512 MB RAM, 0.1 CPU**
- **Filesystem efêmero** — disk persiste entre requests, é resetado em deploys e em alguns restarts
- **Sem disco persistente** — pra ter, precisa migrar pra plano pago ($1/mo por 1GB)

### 8.2 Implicações
- Snapshots em `dados/*.json` são resetados a cada deploy → diff "última atualização" reseta
- HTMLs em `output/` também são resetados em deploys → primeiro request após deploy serve o HTML commitado, não o último gerado em runtime
- Cold start torna a primeira visita lenta — aceitável pra ferramenta interna, ruim se houver tráfego frequente

### 8.3 Auto-deploy
`render.yaml` tem `autoDeploy: true`. Cada `git push` em `main` dispara redeploy do Render automaticamente (~3 min).

## 9. Histórico de decisões

| Data | Decisão | Por quê |
|---|---|---|
| 2026-04-29 | Criar cópia pública em `Backup/SnD_Sistema_Publico/` | Usuária queria isolar o projeto público do interno |
| 2026-04-29 | Remover apenas o logo visual, manter texto "Innovagro" | Usuária pediu literal: "retire a logo da empresa" |
| 2026-04-29 | Publicar primeiro no GitHub Pages | Mais rápido pra ter algo público no ar |
| 2026-04-29 | Migrar pra Render | Usuária pediu botão Atualizar que rode o pipeline de fato — Pages é estático |
| 2026-04-29 | Manter `index.html` raiz pro Pages como backup | Não havia razão pra quebrar a URL Pages durante transição |
| 2026-04-29 | `logo_tag` retornar `""` em vez do fallback de texto | Preserva o gerador funcional sem precisar patch em runtime pra retirar o texto INNOVAGRO BRASIL |
| 2026-04-29 | Patch do botão Atualizar em runtime (não no gerador) | Menos invasivo no `gerar_unified_html.py` (124KB), mais fácil de manter |
| 2026-04-29 | Single worker no gunicorn | `_lock` em memória só funciona num worker — múltiplos workers permitiriam corrida |

## 10. Comandos úteis

### 10.1 Rodar localmente
```bash
cd C:/Users/Nathália/Desktop/Backup/SnD_Site
pip install -r requirements.txt
python app.py                      # http://localhost:8000
# ou via gunicorn (igual produção):
gunicorn app:app --timeout 180 --workers 1
```

### 10.2 Rodar só o pipeline (sem Flask)
```bash
python atualizar_snd.py            # atualização completa
python atualizar_snd.py --apenas-feeds   # só notícias
python atualizar_snd.py --dry-run        # simula
```

### 10.3 Deploy
```bash
git add <arquivos>
git commit -m "..."
git push                            # Render redeployar automaticamente
```

### 10.4 Forçar regeneração local + patch (sem rodar Flask)
```bash
python atualizar_snd.py
python -c "import app; app.aplicar_patches_publico(app.OUTPUT_HTML)"
```

### 10.5 Smoke test do site
```bash
curl -sI https://snd-brasil.onrender.com/
curl -s https://snd-brasil.onrender.com/healthz
```

## 11. Problemas conhecidos / armadilhas

1. **APIs externas retornam 4xx às vezes:** Conab RSS, CEPEA RSS, ComexStat são instáveis. O pipeline tem fallback (mantém valor anterior, loga WARNING). Isso é esperado, não é bug.
2. **CEPEA bloqueia alguns user-agents** com 403. Quando acontecer com frequência, pode precisar trocar `UA` em `atualizar_snd.py:57`.
3. **ComexStat tem rate limit** (429). Espaçar requests ou rodar `--apenas-feeds` se for atualização rápida.
4. **IBGE LSPA (tabela 6588)** retorna `"..."` quando o mês ainda não foi divulgado — script trata.
5. **Cold start no Render:** se reportar "site lento", quase sempre é só o primeiro request após sleep — segundo request já é rápido.
6. **Pipeline trava o request por até 90s** durante atualização. Se passar de 180s (timeout do gunicorn), gunicorn mata o worker. Se isso virar problema recorrente, mover pra background thread + endpoint de status polling.
7. **Patches do botão dependem de markers hardcoded** em `aplicar_patches_publico`. Se algum dia o `gerar_unified_html.py` mudar `.print-btn:active{transform:scale(.97)}` ou o ID `print-pdf-btn`, o patch silenciosamente não aplica.

## 12. Quando precisar ajudar a usuária

- **"Site não atualiza" / botão sem efeito:** abrir DevTools → Network → ver resposta de POST `/atualizar`. `/healthz` mostra `last_error`.
- **"Não tô vendo os dados de hoje":** Render free dorme após 15 min. Snapshot do disco pode ter resetado. Pedir pra clicar Atualizar.
- **"Quero adicionar gráfico/coluna nova":** mexe em `gerar_unified_html.py` (no `SnD_Site/`). Considerar se a mudança também deve voltar pro projeto interno em `innovagro/`.
- **"Quero domínio próprio":** Render dashboard → Service → Settings → Custom Domain. Configurar CNAME no provedor de DNS.
- **"Quero email/notificação quando atualizar":** adicionar lógica em `/atualizar` antes do return — SMTP, webhook Discord/Slack, etc.
- **"Quero histórico de atualizações":** atualmente `logs/atualizacoes.log` é gerado mas reseta no deploy. Pra persistir, commitar de volta ao repo via Action ou usar serviço externo (Sentry, Logtail).

## 13. Memórias relevantes (Claude memory system)

A usuária tem auto memory ativo em `C:/Users/Nathália/.claude/projects/C--Users-Nath-lia-Desktop-Backup/memory/`:
- `user_role.md` — Nathália da Innovagro, PT-BR
- `project_snd_publico.md` — resumo deste projeto

Conferir essas memórias no início de sessão pra não perguntar coisa que ela já contou.
