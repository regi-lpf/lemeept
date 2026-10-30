# Sincronização manual e planilha de revisão

## Iniciar uma revisão

Quando uma defesa nova for anunciada, execute na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -B sincronizar_revisao.py
```

O comando consulta a API WordPress oficial do ProfEPT (`/wp-json/wp/v2/pages?slug=dissertacoes`), compara os IDs com `lemeept/painel-ept-v2.json` e gera `dados/revisao/revisao_ept.xlsx`.

Para reduzir tempo e uso de recursos, a execução padrão processa no máximo cinco defesas ainda não presentes na base e lê até 20 páginas por PDF. Ajustes:

```powershell
.\.venv\Scripts\python.exe -B sincronizar_revisao.py --limite-novos 1
.\.venv\Scripts\python.exe -B sincronizar_revisao.py --limite-novos 0 --max-paginas 20
```

O extrator tenta texto nativo. Quando não encontra resumo/palavras-chave, a planilha sinaliza o caso para OCR/manual; este comando não dispara OCR nem GPT. PDFs baixados ficam em `pdf/dissertacoes/`, ignorado pelo Git, e entram no `manifesto.json` local. `baixar_dissertacoes.py` continua disponível para baixar o conjunto já conhecido.

## Revisar

- **Leia primeiro** resume o conteúdo do arquivo.
- **Fila de revisão** contém lacunas, campos sem evidência, classificações sinalizadas e novas defesas. Filtre `Status`; registre a decisão em `Decisão / correção` e mantenha o valor extraído e a evidência como referência.
- **Banco atual** permite filtrar e localizar os campos e links já estruturados.
- **Novas defesas** mostra separadamente o que veio da API na última execução, com o resultado do PDF.

As células destacadas em salmão indicam ausência; amarelo indica conferência ou consulta pendente. Links de fonte são clicáveis.

Resumo e palavras-chave não são classificados como ausentes da dissertação: quando não aparecem no banco, a fila informa se a extração está pendente ou se o extrator não os localizou, para conferir no PDF. A base epistemológica aparece como classificação herdada a reanalisar com OCR/GPT segmentado e evidências de página/trecho. “Classificação geral” não é um campo do contrato e foi removida da fila; o aviso antigo vinha do sinal genérico `revisaoManual`, compartilhado por classificações herdadas.

Também é possível regenerar a planilha sem consultar a API:

```powershell
.\.venv\Scripts\python.exe -B gerar_planilha_revisao.py
```

Para reconstruir a amostra comparativa corrente (seis dissertações e seis produtos) a partir dos PDFs locais e dos Handles eduCAPES:

```powershell
.\.venv\Scripts\python.exe -B criar_amostra_comparativa.py
```

Por padrão, usa EPT-0001, 0003, 0005, 0007, 0008 e 0010. Grava `dados/revisao/amostra_extracao_6_v2.json` e `dados/revisao/comparacao_amostra_6_v2.xlsx`, sem editar o JSON legado. A amostra usa texto nativo de até 80 páginas; não roda OCR nem GPT. A classificação contextual resultante fica separada em `dados/revisao/classificacao_assistida_6_v2.json` e alimenta a aba correspondente da planilha. A amostra de 11 itens continua apenas como artefato histórico de comparação; não é a saída padrão.

Trechos curtos do referencial teórico e referências bibliográficas correspondentes às citações podem ser preparados sem enviar o PDF inteiro nem usar presença de autor na bibliografia, isoladamente, como prova da base. Candidatos de alta confiança podem preencher o valor no JSON de trabalho; os demais continuam na fila visual.

```powershell
.\.venv\Scripts\python.exe -B extrair_contexto_base_epistemologica.py
```

O comando gera `dados/revisao/contexto_base_epistemologica_6_v1.json/.xlsx` e `dados/revisao/classificacao_assistida_6_v3.json`. A planilha contém as abas **Base epistemológica** e **Decisão proposta**. O script usa texto nativo local, não chama GPT/OCR/rede e não altera os JSONs principais. Na calibração atual, somente EPT-0007 recebeu proposta de alta confiança com evidência direta e corroboração bibliográfica; os outros cinco permanecem para revisão humana.

A rodada assistida posterior está em `dados/revisao/classificacao_assistida_6_v4.json`. Ela analisa os cinco casos ainda pendentes com o contexto segmentado, mantém o valor confirmado nulo quando a evidência não estabelece uma base dominante e registra candidatos/páginas para decisão. Não confundir esta avaliação com execução de uma API GPT no script: o script local continua apenas preparando contexto.

Para revisar visualmente, abra `dados/revisao/revisao_classificacao_6_v4.xlsx`. A aba **Base epistemológica** mantém sem valor confirmado os casos não resolvidos, para revisão manual posterior. A aba **Tipo de produto** compara o formato proposto com `dc.type` e coleção; os cinco tipos foram confirmados pelo usuário com confiança alta. O conflito de metadados do EPT-0005 permanece visível como proveniência. Os JSONs de proposta não são atualizados automaticamente por edições na planilha.

O contrato e a regra aplicada ao tipo dos produtos estão em `CONTRATO_DADOS.md` e `GUIA_CLASSIFICACAO_PRODUTOS.md`. A primeira decisão comparativa dos cinco produtos está em `dados/revisao/classificacao_produtos_5_v1.json`; formatos explícitos no PDF foram preservados. EPT-0005 permanece sinalizado por conflito entre “Infográfico” no PDF e metadados eduCAPES (“Vídeos”/“livro digital”); EPT-0008 está sem metadados eduCAPES completos.

## Limites desta primeira versão

A planilha preserva correções visuais e oferece rastreio para facilitar a revisão. As correções digitadas ainda não são importadas automaticamente para o JSON v2. Uma defesa nova aparece em **Novas defesas** e na fila, mas só entra no banco final após a etapa de integração aprovada. A base atual continua sendo a versão v2 existente; a consulta à API não modifica JSONs publicados nem arquivos em `dados/referencia/`.

O catálogo usado para comparar IDs deriva das identidades versionadas e é resolvido em memória. Entradas ambíguas ou sem autor, título, ano e URL do PDF podem ficar sem ID estável e precisam de conferência antes de integrar.

## EduCAPES

Sim, scraping é possível e já está no coletor legado: `1_PegarDadosSiteIfc.py::consultar_educapes` visita o Handle do produto com `?mode=full`, lê campos Dublin Core e links de bitstream, e guarda o HTML em cache por Handle. Não precisa varrer a busca geral do portal quando o site ProfEPT já fornece o Handle.

O ponto frágil é depender da estrutura HTML. Para reforçar sem API, mantenha a coleta por Handle, selecione pares rótulo/valor em vez de posição na página, normalize variações de nomes `dc.*`, registre por campo se veio dado ou houve falha e preserve cache/status HTTP. Fixtures HTML minimizadas ajudam a detectar mudanças dos seletores. A CAPES informa que eduCAPES usa DSpace e Dublin Core. OAI-PMH pode ser investigado depois como alternativa, mas não é pré-requisito para o scraping atual.

