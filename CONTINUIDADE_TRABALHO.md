# Continuidade do trabalho — Projeto Leme EPT

Este documento transfere o contexto para outro workspace ou agente de IA. Leia primeiro `CONTRATO_DADOS.md`, `DIAGRAMAS.md` e este arquivo. O escopo atual tem duas frentes: corrigir o painel publicado em Elementor e, em seguida, redesenhar o fluxo de extração para depender menos de GPT sem perder pesquisas específicas.

## Estado atual

- Branch de trabalho: `develop`.
- O painel embutido em Elementor está em `lemeept/index.html`. O trecho é um bloco completo com `<section>`, `<style>`, marcação e `<script>`; não é uma página HTML autônoma.
- O JSON carregado pelo widget é `lemeept/painel-ept.json` (110 defesas, 220 produções representadas como `quantidadeProducoes: 2` por defesa).
- A planilha, os PDFs de entrada e os artefatos locais de execução não estão presentes no checkout. A validação empírica do novo extrator depende de uma amostra real.
- O contrato acordado está em `CONTRATO_DADOS.md`; o mapa do sistema está em `DIAGRAMAS.md`.

## Regras de produto já acordadas

1. Cada defesa tem um acadêmico, um orientador, o link e título da dissertação e o link e título do produto educacional.
2. Há sempre exatamente uma dissertação e um produto por defesa. No modelo final, devem ser produções acessíveis independentemente, cada qual ligada à defesa por `defesaId`.
3. Cada produto tem um tipo principal. “Aparece nas coleções:” do eduCAPES é evidência útil, mas a coleção do repositório pode ser mais ampla que o tipo do produto; conservar os campos separados.
4. Coorientadores, quando presentes, devem ser registrados e contados separadamente dos orientadores principais.
5. Resumo, palavras-chave, introdução e títulos do sumário alimentam pesquisas específicas. Guardar texto completo, resumo de exibição e evidência/localizador de origem.
6. Duas linhas oficiais: Práticas Educativas em EPT (MP1–MP3) e Organização e Memórias de Espaços Pedagógicos (MP4–MP6).
7. “Macroprojeto 3” e “MP3” são a mesma categoria. O código `MP3` é canônico; não criar categoria adicional.
8. Não reparar agora os resumos ausentes do JSON antigo. O pipeline novo deve tornar falhas de extração observáveis.
9. O widget é código Elementor e requer mudanças pequenas e cuidadosas; preservar seu bloco e evitar reformatar/colar HTML processado pelo editor visual.

## Implementações nesta branch

### Painel Elementor

Em `lemeept/index.html`:

- Orientadores contam defesas únicas (alunos), não `quantidadeProducoes`.
- Tipos de produto contam uma vez por defesa/produto.
- Macroprojetos são apresentados e agregados pelo código canônico. A defesa EPT-0108 tem código `MP3` mas o rótulo legado “Macroprojeto 3”; agora se junta ao MP3.
- A base atual soma 42 produções MP3 (21 defesas), antes divididas em dois rótulos. Total geral permanece 220 produções em 110 defesas.
- Os textos auxiliares dos gráficos explicam as unidades de contagem.

### Fluxo e contrato

- `CONTRATO_DADOS.md` documenta entidades, campos, contagens e conferência inicial de fontes.
- `DIAGRAMAS.md` foi ampliado com o fluxo e o modelo proposto.
- Etapa 1 (`1_PegarDadosSiteIfc.py`) mantém coleção e metadados eduCAPES separados e reconhece variações do rótulo de coorientador.
- Etapa 2 (`2_PdfParaJson.py`) tenta extrair o coorientador do PDF e transporta campos eduCAPES.
- Etapa 3 (`3_ArrumarPlanilha.py`) prioriza o coorientador confirmado no PDF, registra divergências e carrega metadados até a planilha final.
- A atualização e geração do próximo JSON carregam coorientador, metadados eduCAPES, coleção e resumo completo/curto.
- Os testes focados de `tests/test_pipeline.py` passam. Os testes de `tests/test_fluxo.py` não puderam importar a etapa 1 no runtime usado por falta de `beautifulsoup4`.

## Próximos passos recomendados

1. Publicar e conferir o bloco atualizado no WordPress/Elementor. Validar no painel: 220 produções, 110 trabalhos/defesas, orientadores sem duplicação por dissertação+produto, tipos somando produtos uma vez e MP3 consolidado em 42 produções.
2. Obter um pequeno conjunto representativo de PDFs e registros eduCAPES para desenvolvimento e QA do extrator. Não existe amostra local neste checkout.
3. Implementar extração determinística incremental: metadados do eduCAPES; campos estáveis do PDF (ficha catalográfica, resumo, palavras-chave, sumário e introdução); coorientador com variações de rótulo; evidências com URL/página/campo.
4. Reduzir GPT para pesquisas específicas e classificação ambígua, preservando evidências, confiança e revisão manual. Evitar depender do GPT para copiar campos estruturados previsíveis.
5. Só após estabilizar o fluxo, migrar a saída para 220 registros de produção independentes, ligados às 110 defesas por `defesaId`; adaptar o widget em uma etapa própria e sem reformatar o bloco Elementor.
6. Depois da migração, atualizar interface: Linha de Pesquisa antes de Macroprojeto; nomenclatura “trabalhos analisados”; campos e contagens sem duplicação; manter HTML do Elementor intacto fora das alterações necessárias.

## Verificações feitas

- JavaScript embutido em `lemeept/index.html` passou por compilação sintática com Node.
- Conferência aritmética do JSON: 110 registros de defesa, 220 produções, seis códigos de macroprojeto e 42 produções com código MP3.
- `git diff --check` passou.
- O teste `python -m unittest discover -s tests -p test_pipeline.py -v` passou (8 testes).
- Os testes de integração de `test_fluxo.py` exigem dependências de `requirements.txt`; no runtime disponível faltou `beautifulsoup4`.

## Cuidados para a próxima pessoa/agente

- Antes de alterar, confira `git status` e leia as instruções locais do repositório.
- Não tratar cada defesa como se tivesse duas vezes o mesmo orientador ou o mesmo tipo de produto.
- Não agrupar macroprojeto pelo rótulo bruto quando existe `codigoMacroprojeto`.
- Não inferir o tipo específico somente da coleção eduCAPES.
- Não colar no Elementor texto copiado de uma página renderizada: ele pode conter `<br />` e `<p>` injetados. Use o bloco-fonte do arquivo do repositório e preserve sua estrutura.
- Não alterar nem reparar o JSON legado como parte da próxima etapa do extrator, salvo solicitação expressa; primeiro estabilizar a geração nova.

