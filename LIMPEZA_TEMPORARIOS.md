# Inventário e política de limpeza

Inventário observado neste workspace em 2026-10-30. **Nenhum arquivo é removido automaticamente.** Antes de remover um artefato local, conferir se contém fonte original, evidência não reproduzível ou revisão humana; em dúvida, preservar.

## Fontes e referências — preservar

| Caminho | Estado/função | Política |
| --- | --- | --- |
| `pdf/dissertacoes/` | Corpus local de 110 PDFs com `manifesto.json` (URLs, status, bytes, SHA-256) | Fonte de extração e QA; ignorado pelo Git. Não remover como cache. Pode ser reconstituído por `baixar_dissertacoes.py`, mas preservar até confirmar manifesto e checksums. |
| `pdf/*.pdf` | Três PDFs locais antigos da amostra | Não remover sem comparar hashes com os arquivos canônicos e confirmar que nenhuma versão difere. |
| `dados/referencia/*.json` | Vocabulários, identidades e classificações históricas versionados | Dados de referência; preservar e não sobrescrever por cópias de amostra. |
| `lemeept/painel-ept.json` e `lemeept/painel-ept-v2.json` | Bancos versionados consumido/transição | Dados do projeto, não temporários. Alterar somente por fluxo e escopo aprovados. |

## Saídas de revisão e extração

| Caminho | Situação atual | Tratamento |
| --- | --- | --- |
| `dados/revisao/amostra_extracao_6_v2.json` | Extração corrente de 6 dissertações + 6 produtos | Ignorado pelo Git; preservar como base da próxima classificação. Regenerável parcialmente pelos PDFs e scripts, mas eduCAPES pode mudar/falhar. |
| `dados/revisao/comparacao_amostra_6_v2.xlsx` | Planilha corrente de comparação, incluindo classificação assistida | Ignorada pelo Git; preservar durante a revisão. Conferir células e histórico antes de substituir. |
| `dados/revisao/classificacao_assistida_6_v2.json` | Classificação contextual da amostra; contém candidatos de base epistemológica e evidência | Ignorado pelo Git; preservar e não sobrescrever silenciosamente. |
| `dados/revisao/contexto_base_epistemologica_6_v1.json`, `classificacao_assistida_6_v3.json` | Contexto enxuto de teoria + correspondências bibliográficas; proposta de reclassificação | Ignorados pelo Git; preservar durante a calibração e comparar com v2 antes de substituir. |
| `dados/revisao/contexto_base_epistemologica_6_v1.xlsx` | Planilha visual de evidências e decisões propostas | Ignorada pelo Git; conferir decisões/histórico antes de regenerar. |
| `dados/revisao/classificacao_assistida_6_v4.json` | Análise GPT dos cinco candidatos pendentes; decisão do usuário mantém bases difíceis sem valor confirmado para revisão manual posterior | Ignorado pelo Git; preservar para revisão humana. Não regenerar sobre decisões preenchidas. |
| `dados/revisao/classificacao_produtos_5_v1.json` | Tipos dos cinco produtos confirmados pelo usuário com confiança alta; proveniência e divergência EPT-0005 preservadas | Ignorado pelo Git; preservar como rodada aprovada e referência para a próxima iteração. |
| `dados/revisao/revisao_classificacao_6_v4.xlsx` | Planilha visual atualizada com decisão manual posterior para bases e aprovação dos tipos dos produtos | Ignorada pelo Git; preservar decisões humanas. Não sobrescrever/regenerar antes de importar ou preservar essas decisões. |
| `dados/revisao/amostra_extracao_11_v1.json`, `comparacao_amostra_11.xlsx` | Amostra exploratória anterior de IDs diferentes; operacionalmente substituída como padrão, mas não equivalente à amostra atual | Manter como registro histórico local. Remover só após confirmar que as comparações não serão mais usadas; não tratar como duplicata da amostra de 6. |
| `dados/revisao/revisao_ept.xlsx` | Fila visual de lacunas/novidades gerada pela última consulta API; 455 linhas de fila, sem decisões preenchidas na inspeção | Pode ser regenerada por `sincronizar_revisao.py`, mas pode conter estado útil da API. Preservar até executar nova sincronização e conferir abas. |
| `dados/1_PegarDadosSiteIfc.xlsx`, `dados/GPT/para_gpt.json`, prompt, relatórios e `dados/cache/` | Saídas do fluxo legado e caches locais | Não remover em lote. Confirmar se não há revisão, resposta GPT ou evidência exclusiva. HTML cache é parcialmente regenerável; fonte remota pode mudar. |
| `dados/local-sample-work/` | Cópia isolada de scripts, referências, caches, relatórios v1–v4, PDFs e planilha | Amostra de QA anterior. Não apagar antes de comparar com os artefatos correntes e confirmar que seus resultados estão registrados. Não copiar suas referências sobre `dados/referencia/`. |

## Ambiente e caches descartáveis

| Caminho/padrão | Política |
| --- | --- |
| `.venv/` | Ambiente regenerável via `requirements.txt`; manter enquanto estiver em uso. |
| `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Regeneráveis. Remoção seletiva é segura após encerrar processos que os usam. |
| `*.tmp`, `*.tmp.xlsx`, `*.part` | Remover somente quando não houver execução ativa e o arquivo final correspondente estiver íntegro. |
| `painel/`, `archive/`, `backups/`, `logs/`, `teste_json/` | Se aparecerem, inspecionar conteúdo antes de remover; backups nunca são descartados sem conferir retenção. |

## Limpeza feita nesta atualização

- Documentação que ainda apresentava o fluxo de 11 itens como padrão foi corrigida para apontar à amostra corrente de 6.
- `DIAGRAMAS.md` foi substituído por diagramas alinhados aos scripts e arquivos realmente existentes; foram removidos desenhos antigos que apresentavam etapas legadas como atuais ou contradiziam regras já decididas (incluindo a consolidação MP3).
- Foi acrescentado `extrair_contexto_base_epistemologica.py` e gerado um pacote local com texto teórico e referências da amostra atual; não há chamada GPT/OCR.
- Foi gerada análise assistida v4 dos cinco casos de base epistemológica e a primeira classificação comparativa dos cinco produtos. Ambos os JSONs estão ignorados pelo Git e foram inventariados acima.
- Não houve remoção de artefatos de dados: a amostra de 11 itens não foi apagada porque cobre IDs diferentes; as planilhas/JSONs ainda guardam comparação e evidência histórica. Também foram preservados PDFs, referências, caches e dados do fluxo OCR/GPT.

## Regras para futuras limpezas

1. Consulte esta lista e inspecione o conteúdo real antes de apagar.
2. Não use remoção recursiva ampla em `dados/` ou `pdf/`.
3. Nunca apague `dados/referencia/` durante limpeza.
4. Ao regenerar uma planilha, preserve a anterior até validar abas, decisões, links e histórico.
5. Atualize este inventário quando o pipeline criar um novo diretório ou saída relevante.
6. O `.gitignore` não é política de retenção: ignorado pelo Git significa não sincronizado, não descartável.

## Arquivos ignorados pelo Git

O `.gitignore` ignora ambiente, caches, PDFs/planilhas e saídas sob `dados/`, exceto `dados/referencia/*.json`. Os PDFs e saídas de revisão precisam ser baixados ou regenerados em outro computador; o Git não os sincroniza.
