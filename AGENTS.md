# Orientações para o Codex — Projeto LEME EPT

## Ordem de leitura

Ao iniciar uma tarefa neste repositório, leia nesta ordem:

1. `CONTRATO_DADOS.md` — regras e proveniência dos dados.
2. `DIAGRAMAS.md` — fluxos implementados e planejados.
3. `CONTINUIDADE_TRABALHO.md` — estado atual, decisões recentes e próxima etapa.
4. `LIMPEZA_TEMPORARIOS.md` — inventário e política de retenção.
5. O guia operacional específico da tarefa (`GUIA_REVISAO.md`, `GUIA_CLASSIFICACAO_PRODUTOS.md` ou `GUIA_PIPELINE.md`).

Se um documento divergir do código ou de uma decisão explícita mais recente do usuário, confira o estado real e atualize a documentação; não perpetue a divergência.

## Regras de trabalho

- A API do site ProfEPT é a fonte de descoberta de defesas. A coleta é iniciada manualmente; não existe monitoramento automático contínuo.
- O fluxo novo de revisão extrai texto nativo do PDF, consulta o Handle eduCAPES quando possível e gera JSON/planilha. Ele não executa GPT/OCR nem integra decisões da planilha automaticamente ao banco final.
- Use OCR somente como fallback quando o texto nativo não cobrir o campo. O fluxo legado OCR/GPT deve continuar disponível durante a transição.
- Classificações precisam de valor, confiança, evidência localizável e método. Em campos interpretativos, aceite automaticamente apenas candidato de confiança alta; encaminhe média/baixa ou ausência de evidência para revisão.
- Base epistemológica exige evidência conceitual no texto. Use referências bibliográficas para corroborar autores/obras citados no referencial teórico; a mera presença de uma obra na bibliografia não comprova a base.
- Resumo e palavras-chave são esperados conforme a estrutura acadêmica. Se a extração não os localizar, sinalize falha/lacuna de extração e encaminhe ao PDF; não conclua que estão ausentes da dissertação sem inspeção.
- eduCAPES `dc.type` e coleção são evidência complementar. Não substituem automaticamente o formato específico declarado na dissertação/ficha do produto.
- Para tipo do produto, consulte `GUIA_CLASSIFICACAO_PRODUTOS.md`; preserve fonte e rótulo original e registre conflitos sem forçar normalização.
- Mantenha os 220 registros de produção independentes vinculados a 110 defesas no JSON v2; não altere o JSON legado consumido pelo painel como efeito colateral.
- `lemeept/index.html` é um bloco para Elementor. Faça diffs mínimos e preserve sua estrutura, especialmente `<p>`, `<br>`, IDs, seletores e carregamento do JSON.
- Consulte `LIMPEZA_TEMPORARIOS.md` antes de remover qualquer arquivo. Não apague PDFs, referências, planilhas de revisão ou artefatos com evidência/revisão humana automaticamente.
- Não publique/push sem confirmar que a mudança concreta está revisada e que quaisquer dados pessoais ou protegidos já estão cobertos pela autorização do usuário.

## Fontes da verdade

- Contrato e regras: `CONTRATO_DADOS.md`.
- Modelo e fluxo: `DIAGRAMAS.md`.
- Procedimento e estado do trabalho: `CONTINUIDADE_TRABALHO.md`.
- Inventário/limpeza: `LIMPEZA_TEMPORARIOS.md`.
- Execução da planilha visual: `GUIA_REVISAO.md`.
