# Inventário e política de limpeza de arquivos temporários

Este catálogo evita acumular artefatos locais e, principalmente, evita apagar dados que não podem ser reproduzidos. **Nenhum arquivo é removido automaticamente.** Os caminhos locais ignorados pelo Git não serão levados para outro computador.

## Inventário observado no checkout em 2026-10-23

| Caminho/padrão | Estado observado | Tratamento futuro |
|---|---|---|
| `__pycache__/` e subpastas (`lemeept/`, `lemeept/pipeline/`, `tests/`) | Presentes; arquivos `.pyc` gerados por execução de Python; ignorados pelo Git | Regeneráveis. Pode apagar as pastas `__pycache__` quando Python estiver fechado; não é necessário copiá-las entre máquinas. |
| `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Não observados | Regeneráveis; limpeza segura após encerrar os processos que os usam. |
| `.venv/` | Não observado no checkout | Ambiente local; recriar na máquina nova com `requirements.txt`, não copiar. |
| `*.tmp`, `*.tmp.xlsx` | Nenhum observado fora de `.git` | Temporários de gravação. Confirmar que não há execução ativa e que o arquivo final existe antes de apagar. |
| `*.xlsx` | Nenhum encontrado no checkout atual | Pode conter revisão humana. Antes de remover, conferir origem, abas e alterações e arquivar uma cópia se tiver conteúdo validado. Recriar apenas se a fonte de entrada estiver disponível. |
| `*.pdf`, `pdf/` | Nenhum PDF/pasta de PDFs encontrado no checkout atual | Downloads podem ser regeneráveis, mas PDFs também são fontes do projeto. Confirmar URL, integridade e acesso; conservar amostras necessárias à reprodução e respeitar direitos de distribuição. |
| `dados/cache/` | Não encontrado | Cache HTML/JSON de rede, em princípio regenerável. Apagar só sem execução ativa; em modo offline, o pipeline pode depender dele. |
| `dados/GPT/` e `dados/GPT/gpt.json` | Não encontrados nesta varredura | **Não tratar como lixo automaticamente.** Respostas/sugestões revisadas podem conter trabalho humano. Fazer backup/versionamento seletivo antes de limpar. |
| `dados/1_PegarDadosSiteIfc.xlsx`, `dados/2_PdfParaJson.xlsx`, `dados/3_ArrumarPlanilha.xlsx` | Não encontrados nesta varredura | Saídas intermediárias, mas podem conter correções manuais. Verificar abas de revisão/auditoria antes de descartar. |
| `painel/`, `archive/`, `backups/`, `logs/` | Não encontrados na raiz | Diretórios ignorados para saída/execução. Examinar conteúdo antes da remoção; `backups/` nunca deve ser limpo sem conferir a política de retenção. |
| `teste_json/` | Não observado | Pode conter fixtures locais; confirmar que não é a única cópia de um caso de teste antes de apagar. |
| `dados/referencia/*.json` | Presentes e versionados: `classificacoes_historicas.json`, `identidades.json`, `vocabularios.json` | Dados de referência do projeto, não temporários. Preservar e manter no Git. |

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

Após executar coleta, extração ou geração do painel:

1. Liste pastas e arquivos gerados sem incluir `.git`.
2. Registre aqui caminho, propósito, se é reproduzível, retenção e condição para apagar.
3. Se o artefato for necessário para repetir QA em outra máquina, promova-o a fixture versionada minimizada ou documente como obtê-lo; não dependa de cache local ignorado.

