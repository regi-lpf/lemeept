# Manutenção da pipeline do painel

Este guia descreve somente o caminho entre a planilha final revisada e a página publicada. O fluxo de coleta, OCR e classificação manual está em [README_LEGADO.md](README_LEGADO.md).

## Visão operacional

```text
Site ProfEPT/IFC -> etapa legada de coleta/OCR/GPT -> planilha revisada
                                               dados/dados_finais_painel_ept.xlsx
                                                          |
                                                          v
                                lemeept/atualizar_dados.py
                                  | ler e mapear colunas
                                  | normalizar campos
                                  | preservar ou classificar Linha/Macro
                                  | montar contrato + searchText
                                  | validar IDs e salvar atomicamente
                                                          v
                                         lemeept/painel-ept.json
                                                          |
                                            fetch(data-json-url)
                                                          v
                                         lemeept/index-elementor-json.html
```

O atualizador **não coleta o site, não lê PDFs/OCR e não gera HTML**. Ele transforma uma tabela final existente em JSON. O HTML é mantido manualmente como shell estático e busca o JSON no navegador. O conjunto publicado atual foi migrado uma única vez do bloco de dados do HTML do Elementor; esse HTML não é mais fonte de atualizações.

## Atualização normal

Pré-requisito: a planilha `dados/dados_finais_painel_ept.xlsx` deve existir e ter passado pela revisão humana.

```bash
python -m lemeept.atualizar_dados \
  --entrada dados/dados_finais_painel_ept.xlsx \
  --saida lemeept/painel-ept.json \
  --estrito
```

O comando lê XLSX, CSV ou JSON. A opção `--estrito` aborta se encontrar um item JSON que não seja objeto; sem ela, esses itens são ignorados e contabilizados no aviso. O builder grava primeiro um arquivo temporário e só substitui o destino depois de validar que não há IDs duplicados.

Sem argumentos, a fonte padrão é `dados/dados_finais_painel_ept.xlsx`. Se ela não existir, o script encerra com erro; não há fallback para amostra antiga. Assim não é possível publicar dados desatualizados sem perceber.

`--reclassificar` força as heurísticas oficiais a rodarem mesmo quando a planilha já traz um código MP válido. Use somente quando quiser revisar a classificação em lote; a classificação automática pode marcar casos para revisão manual.

## Como os campos chegam ao JSON

1. `ler_registros` abre a fonte tabular ou JSON.
2. `extrair_campos` usa `MAPEAMENTO_COLUNAS` para reconhecer nomes de coluna antigos e aliases, por exemplo `Título da Dissertação` -> `titulo`.
3. `normalizar_registro` limpa espaços e valores vazios, extrai o ano, separa/deduplica tags, gera a chave do orientador e limita o resumo.
4. `processar_registros` preserva códigos oficiais MP1–MP6 já revisados; quando não há código reconhecido, aplica `classifier.py`. `--reclassificar` ignora essa preservação.
5. `montar_search_text` pré-calcula o campo pesquisável normalizado.
6. `Registro` define o contrato publicado; `GeradorPainel` serializa JSON compacto, valida IDs únicos e substitui o arquivo de destino atomicamente.
7. `index-elementor-json.html` executa `fetch` para a URL declarada no atributo `data-json-url`. Não recebe nem armazena os dados dentro do HTML.

## Unidade de contagem

Cada registro corresponde a um trabalho de um pesquisador, não a uma apresentação. A propriedade `quantidadeProducoes` vale:

- `1` pela dissertação, quando há título;
- mais `1` pelo produto educacional, quando há título de produto válido ou link de produto;
- portanto, uma dissertação com produto representa `2` produções.

Apresentações não são uma unidade de contagem e não são inferidas pelo número de links. KPIs de produções e gráficos somam `quantidadeProducoes`; contagem de trabalhos, busca, paginação e cards continuam usando um registro por dissertação. O campo `produtos com link` conta somente produtos com URL.

## Onde fazer manutenção

| Mudança | Arquivo / ponto de alteração |
| --- | --- |
| Nome novo de coluna na planilha | `MAPEAMENTO_COLUNAS` em `lemeept/atualizar_dados.py` |
| Regra de texto, ano, tags ou busca | funções em `lemeept/pipeline/normalizer.py` |
| Regra oficial MP1–MP6 ou desempate | `lemeept/pipeline/classifier.py` e teste correspondente |
| Campo publicado ou regra de produção | `Registro` em `lemeept/pipeline/data_model.py` e `tests/test_pipeline.py` |
| Campos exibidos, filtros ou gráficos | `lemeept/index-elementor-json.html` |
| Nova extensão/fonte de arquivo | `ler_registros` em `lemeept/atualizar_dados.py` |

A cada mudança de contrato, atualize os testes e regenere o JSON. Não edite o JSON gerado à mão: corrija a planilha fonte ou a transformação responsável e rode novamente o comando.

## Testar antes de publicar

```bash
python -m unittest discover -s tests -p test_pipeline.py -v
python -m py_compile lemeept/atualizar_dados.py lemeept/pipeline/*.py
python -m lemeept.atualizar_dados --entrada dados/dados_finais_painel_ept.xlsx --saida /tmp/painel-ept.json --estrito
python -m http.server 8000 --directory lemeept
```

Abra `http://localhost:8000/index-elementor-json.html`, confira o console e a aba Network: o shell e `painel-ept.json` devem responder com status 200. Verifique totais, busca, filtros, gráficos e links. O servidor local testa o `fetch`, mas não comprova permissões, CORS, cache ou CSP do WordPress publicado.

## Publicar

Publique `lemeept/index-elementor-json.html` uma vez no widget HTML do Elementor. Hospede o JSON em URL HTTPS com GET anônimo; prefira o mesmo domínio do WordPress. Configure essa URL no atributo `data-json-url`. Para domínio diferente, configure CORS no servidor do JSON. Depois de atualizar dados, substitua somente o JSON e invalide o cache/CDN se necessário.

O Elementor ou plugins de segurança podem restringir JavaScript inline, CSP e arquivos `.json` na biblioteca de mídia. Nesse caso, mantenha o shell no widget HTML e hospede o JSON em um caminho público/CDN aprovado. Faça a validação final na página publicada, fora do editor.
