# Painel ProfEPT / LEME

Este README documenta a atualização do painel estático. Para o fluxo de coleta e revisão em desenvolvimento, veja [GUIA_REVISAO.md](GUIA_REVISAO.md); para o contrato de dados e arquitetura, veja [CONTRATO_DADOS.md](CONTRATO_DADOS.md), [DIAGRAMAS.md](DIAGRAMAS.md) e [AGENTS.md](AGENTS.md). [GUIA_PIPELINE.md](GUIA_PIPELINE.md) descreve a transformação legada da planilha revisada para o painel.

Para consultar a API ProfEPT sob demanda e abrir a fila visual de lacunas/casos novos, veja [GUIA_REVISAO.md](GUIA_REVISAO.md) (`sincronizar_revisao.py`).

## Como os arquivos se relacionam

```text
dados/dados_finais_painel_ept.xlsx
				-> lemeept/atualizar_dados.py
				-> lemeept/pipeline/{normalizer,classifier,builder}.py
				-> lemeept/painel-ept.json
				-> lemeept/index.html faz fetch do JSON
```

O XLSX é a fonte revisada. O atualizador gera somente JSON; o HTML é shell estático e não é regenerado. Um registro do JSON representa um trabalho de um pesquisador. Os agregados contam 1 pela dissertação e mais 1 pelo produto quando houver título ou link. Apresentações não são incluídas.

O JSON atual foi importado uma vez dos 110 registros que estavam embutidos no HTML do Elementor. Essa migração já terminou: as próximas versões devem vir da planilha final revisada, não do HTML nem do JSON gerado.

## Atualizar dados

Depois que a planilha final foi revisada:

```bash
python -m lemeept.atualizar_dados \
	--entrada dados/dados_finais_painel_ept.xlsx \
	--saida lemeept/painel-ept.json \
	--estrito
```

`--estrito` interrompe em linhas malformadas. Sem `--entrada`, o script usa `dados/dados_finais_painel_ept.xlsx`; se a planilha não existir, a execução falha em vez de publicar uma fonte antiga por engano.

## Testar localmente

Sirva shell e dados pela mesma origem para simular o `fetch`:

```bash
python -m http.server 8000 --directory lemeept
```

Abra `http://localhost:8000/index.html`. Não use `file://`, porque o navegador bloqueia o carregamento local do JSON.

## Publicar no Elementor

Publique `lemeept/index.html` no widget HTML. Hospede `lemeept/painel-ept.json` em uma URL HTTPS que aceite GET anônimo, de preferência no mesmo domínio, e configure essa URL no atributo `data-json-url` do shell. Para outro domínio, o servidor do JSON precisa permitir CORS. Em atualizações seguintes, troque somente o JSON e invalide o cache/CDN se necessário.

## Verificações

```bash
python -m unittest discover -s tests -p test_pipeline.py -v
python -m py_compile lemeept/atualizar_dados.py lemeept/pipeline/*.py
```

O fluxo OCR/GPT legado permanece disponível nos scripts numerados da raiz para fallback; não é executado pelo sincronizador novo. Veja [DIAGRAMAS.md](DIAGRAMAS.md) para a separação entre os dois fluxos.
