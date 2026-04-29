# SnD Brasil — Soja e Milho

Site público do relatório Supply and Demand (SnD) Brasil — Soja e Milho.

Versão estática hospedada no GitHub Pages. Cada visita carrega a versão mais recente publicada; o botão **Atualizar** no topo da página força um recarregamento sem cache.

## Estrutura

- `index.html` — página única, autocontida (CSS e JS inline). Inclui as visões: Dinâmica, Estática, Gráficos, Áreas e Produção, Fluxo de Exportação por UF e Capacidade Estática.

## Como atualizar o conteúdo

O HTML é gerado por um pipeline interno (não publicado). Para publicar uma nova versão:

1. Gerar novo `SnD_Brasil_Unified.html` pelo pipeline.
2. Copiar para este repositório como `index.html`.
3. `git add index.html && git commit -m "atualiza relatório DD/MM" && git push`.
4. GitHub Pages re-publica em ~1 minuto.
