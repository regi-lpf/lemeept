# Inventário e política de limpeza de arquivos temporários

Este catálogo evita acumular artefatos locais e, principalmente, evita apagar dados que não podem ser reproduzidos. **Nenhum arquivo é removido automaticamente.** Os caminhos locais ignorados pelo Git não serão levados para outro computador.

## Inventário observado no checkout em 2026-10-23

### Artefatos preservados da sessão de continuação

| Caminho/padrão | Estado observado | Tratamento futuro |
|---|---|---|
| `dados/local-sample-work/` | Amostra local ignorada pelo Git: cópia isolada do coletor/referências, planilha, caches, três PDFs e relatórios v1/v2/v3/v4 para oito IDs | Preservar enquanto reproduz o QA. Os PDFs são fontes; não apagar sem decisão explícita e confirmação de origem/direitos. Não copiar referências isoladas sobre `dados/referencia/`. Cinco extrações adicionais usaram os PDFs canônicos de `pdf/dissertacoes/`. |
| `pdf/` (3 PDFs baixados para compatibilidade com fluxo/testes locais) | Cópias locais dos PDFs da amostra; ignoradas pelo Git | Conferir se são cópias da amostra antes de qualquer limpeza. Manter até terminar validação/ampliação da amostra. |
| `pdf/dissertacoes/` e `manifesto.json` | Corpus local com PDFs das 110 dissertações; manifesto registra ID, URL, status, bytes e SHA-256; ignorado pelo Git | Fontes necessárias à extração reproduzível. Não remover automaticamente. Pode reconstruir com `baixar_dissertacoes.py`, mas preserve o manifesto para auditoria. |
| `dados/1_PegarDadosSiteIfc.xlsx` | Planilha local gerada pela coleta dos três registros; ignorada pelo Git | Intermediário de QA; pode conter metadados úteis. Preservar até validar os relatórios e não remover automaticamente. |
| `dados/GPT/para_gpt.json`, `PromptClassificacaoGPT.md`, relatórios/cache da etapa PDF | Artefatos locais gerados para os três PDFs; ignorados pelo Git | Inspecionar proveniência e conteúdo antes de arquivar/remover; cache regenerável, mas os relatórios servem para reproduzir o QA. |
| `.venv/` | Ambiente virtual local criado e dependências instaladas | Regenerável a partir de `requirements.txt`; manter enquanto for usado. Não apagar automaticamente. |
| `lemeept/painel-ept-v2.json` | Nova saída versionada com 110 defesas e 220 produções independentes; estado de enriquecimento pendente/parcial explícito | Dado de trabalho versionado, não temporário. Atualizar pelo gerador; não limpar como cache. |

| Caminho/padrão | Estado observado | Tratamento futuro |
|---|---|---|
| `__pycache__/` e subpastas (`lemeept/`, `lemeept/pipeline/`, `tests/`) | Cinco pastas geradas no projeto e removidas nesta sessão após confirmar que não havia processo Python ativo | Regeneráveis e ignoradas pelo Git. Limpar seletivamente quando Python estiver fechado; nada é removido automaticamente sem pedido explícito. |
| `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Não observados | Regeneráveis; limpeza segura após encerrar os processos que os usam. |
| `.venv/` | Presente (ver inventário acima) | Ambiente local; recriar na máquina nova com `requirements.txt`, não copiar. |
| `*.tmp`, `*.tmp.xlsx` | Nenhum observado fora de `.git` | Temporários de gravação. Confirmar que não há execução ativa e que o arquivo final existe antes de apagar. |
| `*.xlsx` | Planilha de amostra em `dados/local-sample-work/dados/` e cópia local de fluxo em `dados/` | Pode conter revisão humana. Antes de remover, conferir origem, abas e alterações e arquivar uma cópia se tiver conteúdo validado. |
| `*.pdf`, `pdf/` | 110 PDFs canônicos em `pdf/dissertacoes/`, três originais da amostra na raiz `pdf/` e cópias na área isolada | PDFs são fontes de pesquisa. Confirmar URL, integridade e acesso; conservar o corpus e respeitar direitos de distribuição. A pasta canônica não é cache descartável. |
| `dados/cache/` | Caches do coletor e extração preservados sob a área de amostra | Cache HTML/JSON reutilizado no QA. Regenerável em parte, mas útil para execução offline; manter até encerrar a validação da amostra. |
| `dados/GPT/` e `dados/GPT/gpt.json` | Há arquivos de preparação/relatórios locais; conferir presença de `gpt.json` antes de qualquer ação | **Não tratar como lixo automaticamente.** Respostas/sugestões revisadas podem conter trabalho humano. Fazer backup/versionamento seletivo antes de limpar. |
| `dados/1_PegarDadosSiteIfc.xlsx`, `dados/2_PdfParaJson.xlsx`, `dados/3_ArrumarPlanilha.xlsx` | A saída da etapa 1 existe localmente; as demais podem não existir | Saídas intermediárias, mas podem conter correções manuais. Verificar abas de revisão/auditoria antes de descartar. |
| `painel/`, `archive/`, `backups/`, `logs/` | Não encontrados na raiz | Diretórios ignorados para saída/execução. Examinar conteúdo antes da remoção; `backups/` nunca deve ser limpo sem conferir a política de retenção. |
| `teste_json/` | Não observado | Pode conter fixtures locais; confirmar que não é a única cópia de um caso de teste antes de apagar. |
| `dados/referencia/*.json` | Presentes e versionados: `classificacoes_historicas.json`, `identidades.json`, `vocabularios.json`; sem alterações nesta sessão | Dados de referência do projeto, não temporários. Preservar e manter no Git. |

## Regras de limpeza

1. Limpar apenas caminhos identificados neste catálogo ou confirmados por inspeção do estado local.
2. Antes de apagar, verificar se há processo do pipeline ativo e se o artefato contém revisão humana, evidência ou dado que não pode ser baixado novamente.
3. Em dúvida, mover/c copiar para backup local documentado; nunca apagar `dados/referencia/` como parte da limpeza.
4. Depois de uma execução, registrar novos diretórios/arquivos gerados nesta tabela e marcar a origem: cache de rede, intermediário, saída final ou fixture.
5. Preferir limpeza seletiva por caminho; não usar comandos recursivos amplos como `Remove-Item dados -Recurse`.
6. Se arquivos temporários crescerem de tamanho relevante, medir por pasta e data antes de decidir retenção. O repositório não define atualmente limite automático de espaço.

## Ignorados pelo Git

O `.gitignore` já ignora bytecode/caches de desenvolvimento, `*.tmp`, PDFs e planilhas; também ignora diretórios de execução (`pdf/`, `painel/`, `archive/`, `backups/`, `logs/`) e dados em `dados/`, exceto JSONs de `dados/referencia/`. Estar ignorado significa que o Git não rastreia/sincroniza o arquivo; **não significa que seja seguro apagá-lo**.

## Como atualizar este inventário

O corpus de dissertações pode ser conferido/reconstituído com `python baixar_dissertacoes.py`. O manifesto local registra checksums; a execução ignora PDFs válidos já existentes e baixa IDs ausentes.

Após executar coleta, extração ou geração do painel:

1. Liste pastas e arquivos gerados sem incluir `.git`.
2. Registre aqui caminho, propósito, se é reproduzível, retenção e condição para apagar.
3. Se o artefato for necessário para repetir QA em outra máquina, promova-o a fixture versionada minimizada ou documente como obtê-lo; não dependa de cache local ignorado.

