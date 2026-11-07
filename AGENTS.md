# Orientações para o Agent — Projeto LEME EPT

## Ordem de leitura

Ao iniciar uma tarefa neste repositório, leia nesta ordem:

1. `CONTRATO_DADOS.md` — regras e proveniência dos dados.
2. `DIAGRAMAS.md` — fluxos implementados e planejados.

Se um documento divergir do código ou de uma decisão explícita mais recente do usuário, confira o estado real e atualize a documentação; não perpetue a divergência.

## Regras de trabalho

- A API do site ProfEPT é a fonte de descoberta de defesas. A coleta é iniciada manualmente; não existe monitoramento automático contínuo.
- A primeira etapa do fluxo de revisão extrai texto nativo do PDF, consulta o Handle eduCAPES e gera JSON/planilha. Nela, não se executa LLM/OCR. Os scripts de extração preenchem a maioria dos campos. 
- A LLM/OCR entra somente na segunda fase da extração híbrida, sendo necessária para os campos de maior irregularidade (ou com necessidade de maior interpretação). 
- Classificações precisam de valor, confiança, evidência localizável e método. Em campos interpretativos, aceite automaticamente apenas candidato de confiança alta; encaminhe média/baixa ou ausência de evidência para revisão.
- Base epistemológica exige evidência conceitual no texto. Use referências bibliográficas para corroborar autores/obras citados no referencial teórico; a mera presença de uma obra na bibliografia não comprova a base.
- Resumo e palavras-chave são esperados conforme a estrutura acadêmica. Se a extração não os localizar, sinalize falha/lacuna de extração e encaminhe ao PDF; não conclua que estão ausentes da dissertação sem inspeção.
- Para tipo do produto, consulte `GUIA_CLASSIFICACAO_PRODUTOS.md`;
- `index.html` é um bloco para Elementor. Faça diffs mínimos e preserve sua estrutura, especialmente `<p>`, `<br>`, IDs, seletores e carregamento do JSON.
- Não publique/push sem confirmar que a mudança concreta está revisada e que quaisquer dados pessoais ou protegidos já estão cobertos pela autorização do usuário.

## Fontes da verdade

- Contrato e regras: `CONTRATO_DADOS.md`.
- Modelo e fluxo: `DIAGRAMAS.md`.
