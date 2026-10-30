# PAINEL EPT / LEME

Este README documenta a atualização do painel estático. Para o fluxo de coleta e revisão em desenvolvimento, veja [GUIA_REVISAO.md](GUIA_REVISAO.md); para o contrato de dados e arquitetura, veja [CONTRATO_DADOS.md](CONTRATO_DADOS.md), [DIAGRAMAS.md](DIAGRAMAS.md) e [AGENTS.md](AGENTS.md). [GUIA_PIPELINE.md](GUIA_PIPELINE.md) descreve a transformação legada da planilha revisada para o painel.

Para consultar a API ProfEPT sob demanda e abrir a fila visual de lacunas/casos novos, veja [GUIA_REVISAO.md](GUIA_REVISAO.md) (`sincronizar_revisao.py`).

A explicação completa para a continuidade do projeto está em [GUIA.md](GUIA.md).
Os diagramas de arquitetura, dados e execução estão em [DIAGRAMAS.md](DIAGRAMAS.md).

## Instalação

É necessário ter Python 3.11+ e Tesseract OCR com o idioma português.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Uso

Execute o primeiro script. Ele faz a coleta e chama o OCR automaticamente:

```bash
python 1_PegarDadosSiteIfc.py
```

Ao final, envie estes arquivos ao GPT:

```text
dados/dados_finais_painel_ept.xlsx
				-> lemeept/atualizar_dados.py
				-> lemeept/pipeline/{normalizer,classifier,builder}.py
				-> lemeept/painel-ept.json
				-> lemeept/index.html faz fetch do JSON
```

Salve a resposta como `dados/GPT/gpt.json` e conclua:

```bash
python 3_ArrumarPlanilha.py
python 4_GerarPainelHtml.py
```

O resultado final fica em `painel/painel_leme_ept.html`.

## Opções úteis

```bash
# usar os dados e PDFs já armazenados localmente
python 1_PegarDadosSiteIfc.py --offline

# pular somente a consulta complementar ao eduCAPES
python 1_PegarDadosSiteIfc.py --sem-educapes

# normalmente o fallback é automático; esta opção força o modo compatível
python 1_PegarDadosSiteIfc.py --inseguro-tls

# testar coleta + OCR com poucos registros
python 1_PegarDadosSiteIfc.py --limite 2
```

Abra `http://localhost:8000/index.html`. Não use `file://`, porque o navegador bloqueia o carregamento local do JSON.

## Publicar no Elementor

Publique `lemeept/index.html` no widget HTML. Hospede `lemeept/painel-ept.json` em uma URL HTTPS que aceite GET anônimo, de preferência no mesmo domínio, e configure essa URL no atributo `data-json-url` do shell. Para outro domínio, o servidor do JSON precisa permitir CORS. Em atualizações seguintes, troque somente o JSON e invalide o cache/CDN se necessário.

## Verificações

```bash
python -m py_compile util.py 1_PegarDadosSiteIfc.py 2_PdfParaJson.py 3_ArrumarPlanilha.py 4_GerarPainelHtml.py
python -m unittest discover -s tests -v
```

O fluxo OCR/GPT legado permanece disponível nos scripts numerados da raiz para fallback; não é executado pelo sincronizador novo. Veja [DIAGRAMAS.md](DIAGRAMAS.md) para a separação entre os dois fluxos.
