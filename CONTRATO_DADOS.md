# Contrato de dados do painel LEME / ProfEPT

**Status:** proposta inicial baseada nas regras já definidas para o projeto.  
**Objetivo:** separar a defesa acadêmica das duas produções que ela gera, mantendo dados pesquisáveis e rastreáveis.

## Regras já definidas

- Cada defesa tem um acadêmico, um orientador, uma dissertação e um produto educacional.
- Quando a dissertação informa coorientador(a), esse vínculo também é registrado e contado em métrica própria, separada dos orientadores.
- Cada defesa gera exatamente duas produções para o painel: dissertação e produto educacional.
- As duas produções têm título e link e são acessíveis/listáveis individualmente.
- Metadados obtidos nos links enriquecem a pesquisa: eduCAPES fornece dados do produto; o PDF fornece conteúdo selecionado da dissertação.
- Cada produto educacional tem um único tipo principal; usar “Aparece nas coleções:” do eduCAPES quando disponível e compatível com o vocabulário do projeto.
- Resumo, palavras-chave e introdução alimentam a pesquisa por termos específicos, incluindo base epistemológica, nível de aplicação, tipo de produto, linha e macroprojeto.
- “Macroprojeto 3” e “MP3” são rótulos da mesma categoria. O código canônico é `MP3`; “Macroprojeto 3” é um alias a normalizar.

## Unidades e contagens

| Indicador | Unidade | Regra |
| --- | --- | --- |
| Defesas analisadas | Defesa | Contar cada `defesa.id` uma vez. |
| Produções | Produção | Contar cada `producao.id` uma vez. Com 110 defesas completas, o total esperado é 220. |
| Alunos orientados por orientador | Vínculo aluno–orientador | Contar uma vez cada par único (`academico.id`, `orientador.id`). Produto e dissertação não criam novos vínculos. |
| Coorientadores | Pessoa no papel de coorientador | Contar pessoas únicas por `coorientador.chave`, em indicador próprio separado do total de orientadores. Não somar essa pessoa ao indicador de orientadores principais. |
| Produtos por tipo | Produto educacional | Contar cada produção do tipo `produto_educacional` uma vez, agrupada por tipo canônico. A dissertação não entra nessa métrica. |
| Linha de pesquisa e macroprojeto | Produção associada à defesa | Os gráficos de produção atribuem as duas produções da defesa à classificação dela. Exibir também contagem de defesas quando o rótulo do indicador disser “defesas”. |

Quando um indicador não explicitar a unidade, a interface deve identificar se está mostrando defesas ou produções. Nomes, links ou metadados repetidos não podem criar novas entidades nem aumentar as contagens.

## Estrutura lógica

```text
Defesa (1)
├── Acadêmico (1)
├── Orientador (1)
├── Coorientador (0..1, se informado na dissertação)
├── Classificação da defesa
└── Produções (exatamente 2)
    ├── Dissertação (1)
    └── Produto educacional (1)
```

Linha de pesquisa, macroprojeto, base epistemológica e nível de aplicação são classificações da defesa/dissertação, com evidências apontando para a dissertação. As produções herdam linha e macroprojeto para pesquisa e agregações, sem manter cópias editáveis que possam divergir. O tipo de produto pertence somente à produção de produto educacional.

### Vocabulário de linhas e macroprojetos

O vocabulário em `dados/referencia/vocabularios.json` e as regras em `lemeept/pipeline/classifier.py` confirmam duas linhas e sua relação com os seis macroprojetos:

| Código interno proposto | Nome canônico | Macroprojetos |
| --- | --- | --- |
| `LP1` | Práticas Educativas em Educação Profissional e Tecnológica (EPT) | MP1, MP2 e MP3 |
| `LP2` | Organização e Memórias de Espaços Pedagógicos na Educação Profissional e Tecnológica (EPT) | MP4, MP5 e MP6 |

Os códigos `LP1` e `LP2` são identificadores técnicos estáveis deste contrato; os nomes e a relação com os MPs vêm do vocabulário do projeto. Para os macroprojetos, usar os nomes extensos já presentes nesse vocabulário:

| Código | Nome canônico |
| --- | --- |
| MP1 | Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT |
| MP2 | Inclusão e diversidade em espaços formais e não formais de ensino na EPT |
| MP3 | Práticas Educativas no Currículo Integrado |
| MP4 | História e memórias no contexto da EPT |
| MP5 | Organização do currículo integrado na EPT |
| MP6 | Organização de espaços pedagógicos na EPT |

“Macroprojeto 3” é alias/rótulo divergente para MP3, não uma categoria adicional. A defesa que aparece com esse rótulo deve ser conferida e normalizada para `MP3` na migração.

A linha de pesquisa deriva da relação oficial com o macroprojeto: MP1–MP3 implicam LP1; MP4–MP6 implicam LP2. Isso evita classificar linha e macroprojeto independentemente e produzir combinações contraditórias. Se o macroprojeto estiver pendente, a linha também fica pendente até revisão/evidência suficiente.

## Campos de classificação e evidências

Os campos abaixo ampliam a especificidade da pesquisa. Em geral, a evidência está no resumo e na introdução da dissertação. Nem todos são metadados catalogados pela fonte; por isso, o contrato deve guardar tanto o valor atribuído quanto como ele foi obtido.

| Campo | Evidência prioritária | Regra quando não estiver explícito |
| --- | --- | --- |
| Base epistemológica | Resumo e introdução da dissertação | Classificar pelas evidências textuais e registrar como classificação, não como transcrição da fonte. |
| Nível de aplicação | Resumo e introdução; contexto educacional descrito no trabalho | Inferir pelo contexto descrito, anexando trecho/página e sinalizando revisão quando ambíguo. |
| Tipo de produto | “Aparece nas coleções:” e demais metadados do eduCAPES; ficha técnica/descrição do próprio produto quando disponível | Atribuir um único tipo principal. Guardar a coleção do repositório separadamente: ela pode ser mais ampla que o tipo educacional específico. Normalizar o tipo para vocabulário controlado, preservando rótulo e origem. Se a evidência não permitir decidir, deixar pendente de revisão em vez de criar múltiplos tipos. |
| Linha de pesquisa | Resumo e introdução confrontados com as descrições oficiais das linhas | Atribuir por regra de classificação com evidência e confiança; encaminhar empates ou evidência fraca para revisão. |
| Macroprojeto | Resumo e introdução confrontados com os critérios oficiais dos macroprojetos | Como o macroprojeto pode não aparecer no PDF ou não ter posição fixa, não exigir extração literal. Classificar por critérios versionados, guardar evidência e marcar inferência/revisão. |

O resumo, suas palavras-chave e a introdução são a base de pesquisa por termos específicos. O sumário e a ficha catalográfica podem acrescentar pistas e localizar seções. Se essas partes não resolverem uma classificação, uma pesquisa textual focada pode procurar termos e trechos adicionais no PDF. A ausência de uma menção literal a linha ou macroprojeto não equivale a falha de extração.

Para decidir os campos técnicos sem exigir análise estatística especializada, adotar valores simples e auditáveis: confiança `alta`, `media` ou `baixa`; marcar baixa confiança para revisão humana; registrar método e evidência por classificação. A extração deve distinguir `encontrado`, `nao_encontrado`, `falha_extracao` e `nao_tentado`. O campo ausente na fonte não deve ser tratado como erro do extrator.

### Proveniência por classificação

Cada valor classificatório deve ter informação de proveniência separada do rótulo, por exemplo:

```json
{
  "valor": "MP3",
  "rotulo": "MP3 – Práticas Educativas no Currículo Integrado",
  "metodo": "classificacao_por_regras",
  "evidencias": [
    {
      "producaoId": "EPT-0001-DIS",
      "secao": "introducao",
      "pagina": 8,
      "trecho": "Trecho curto que sustenta a classificação."
    }
  ],
  "confianca": "media",
  "revisao": "necessaria"
}
```

Valores válidos de `metodo` devem distinguir pelo menos metadado explícito, extração de texto, classificação por regra e revisão humana. Quando a fonte não disser explicitamente o valor, usar um método de classificação/inferência e nunca registrar a fonte como se tivesse fornecido aquele rótulo. Uma revisão humana pode confirmar ou substituir a sugestão sem apagar a evidência e o valor anterior da trilha de auditoria.

## Campos propostos

### Defesa

| Campo | Obrigatório | Observação |
| --- | --- | --- |
| `id` | Sim | Identificador estável; preservar os IDs históricos sempre que houver correspondência confiável. |
| `ano` | Sim | Ano da defesa, em formato `YYYY`; usar estado de revisão se não puder ser identificado. |
| `academico.nome` | Sim | Nome exibido do acadêmico. |
| `academico.chave` | Sim | Forma normalizada para deduplicação; não substitui o nome original. |
| `orientador.nome` | Sim | Nome exibido do orientador. |
| `orientador.chave` | Sim | Forma normalizada para contagem de vínculos. |
| `coorientador` | Condicional | Objeto `{nome, chave}` quando informado no PDF; caso contrário `null`. Não inferir. |
| `linhaPesquisa` | Sim | Código/valor canônico controlado, mais rótulo de exibição. |
| `macroprojeto.codigo` | Sim | Código canônico, por exemplo `MP3`. |
| `macroprojeto.nome` | Sim | Nome de exibição canônico. |
| `baseEpistemologica` | Classificação | Valor canônico ou pendente, com proveniência/confiança; evidência normalmente no resumo/introdução. |
| `nivelAplicacao` | Classificação | Valor canônico ou pendente, com proveniência/confiança; evidência no contexto descrito pela dissertação. |

### Produção

Toda defesa deve ter exatamente estes dois objetos. Os IDs são estáveis e derivados do ID da defesa, por exemplo `EPT-0001-DIS` e `EPT-0001-PRO`.

| Campo | Obrigatório | Observação |
| --- | --- | --- |
| `id` | Sim | ID único e estável da produção. |
| `defesaId` | Sim | Chave estrangeira para a defesa que a originou. |
| `tipo` | Sim | `dissertacao` ou `produto_educacional`. |
| `titulo` | Sim | Título publicado na fonte principal da produção. |
| `url` | Sim | Link de acesso fornecido pela defesa. |
| `metadados` | Sim | Objeto; propriedades enriquecidas podem estar pendentes/indisponíveis. |
| `buscaTexto` | Sim | Texto normalizado derivado de título, metadados e conteúdo selecionado para pesquisa. |
| `fontes` | Sim | URLs e localizadores da evidência usada, como página do PDF ou campo do eduCAPES. |
| `proveniencia` | Sim | Origem por campo enriquecido: URL, campo de metadado, seção/página, método e data da coleta. |
| `estadoEnriquecimento` | Sim | `completo`, `parcial`, `pendente` ou `revisao`; detalhar ausência/falha por campo, sem confundir os dois casos. |

#### Metadados da dissertação

- `resumo`: resumo da dissertação;
- `fichaCatalografica`: texto/campos bibliográficos úteis;
- `sumario`: títulos e hierarquia de seções, incluindo a introdução;
- `introducao`: texto extraído da seção de introdução;
- `palavrasChave`: lista, em geral extraída do resumo, quando disponível.

`buscaTexto` da dissertação será formado por título, resumo, palavras-chave do resumo, introdução, títulos do sumário e classificações. O texto da introdução e os títulos do sumário ficam disponíveis para busca específica; o PDF inteiro permanece acessível pelo link e não é copiado para o JSON. Cada trecho extraído registra páginas do PDF quando a paginação puder ser determinada.

#### Metadados do produto educacional

- `autoresColaboradores`: pessoas e seus papéis quando a fonte informar;
- `identificadores`: esquema, valor e URL, incluindo identificadores de outros hospedeiros;
- `dataPublicacao`: data ISO `YYYY-MM-DD` ou precisão menor se a fonte só fornecer ano/mês;
- `colecaoEduCAPES`: rótulo original de “Aparece nas coleções:”, separado do tipo educacional;
- `tipoProduto`: exatamente um tipo principal canônico; usar “Aparece nas coleções:” como evidência quando for específico, e complementar com metadados/ficha do produto; preservar rótulo de origem e campo consultado;
- `palavrasChave`: lista de termos fornecidos pelo eduCAPES.

“Aparece nas coleções:” não é necessariamente o tipo pedagógico específico. Na amostra conferida, dois produtos diferentes (uma Cartilha e um E-book) aparecem ambos na coleção ampla “Livros digitais”. Portanto guardar essa coleção sem convertê-la automaticamente em tipo. Usar os demais metadados e a ficha/descrição do produto para atribuir exatamente um tipo principal. Se ainda houver ambiguidade, manter o tipo pendente de revisão.

### Coorientador

O campo é opcional porque nem toda defesa informa coorientador. No PDF, procurar logo abaixo do(a) orientador(a), aceitando os rótulos `co-orientador`, `co-orientadora`, `coorientador` e `coorientadora`, sem diferenciar maiúsculas/minúsculas. Registrar nome original e chave normalizada. A contagem própria do painel usa pessoas únicas por chave.

## Esqueleto JSON

```json
{
  "schemaVersion": "2.0",
  "geradoEm": "2026-10-14T12:00:00Z",
  "defesas": [
    {
      "id": "EPT-0001",
      "ano": "2026",
      "academico": {"nome": "Nome do acadêmico", "chave": "nome do academico"},
      "orientador": {"nome": "Nome do orientador", "chave": "nome do orientador"},
      "coorientador": {"nome": "Nome do coorientador", "chave": "nome do coorientador"},
      "classificacoes": {
        "baseEpistemologica": {"valor": "Educação Crítica / Emancipatória", "confianca": "media", "revisao": "necessaria"},
        "nivelAplicacao": {"valor": "Ensino Médio Integrado", "confianca": "alta", "revisao": "nao_necessaria"}
      },
      "linhaPesquisa": {"codigo": "LP1", "nome": "Práticas Educativas em Educação Profissional e Tecnológica (EPT)"},
      "macroprojeto": {"codigo": "MP3", "nome": "MP3 – Práticas Educativas no Currículo Integrado"},
      "producoes": [
        {
          "id": "EPT-0001-DIS",
          "defesaId": "EPT-0001",
          "tipo": "dissertacao",
          "titulo": "Título da dissertação",
          "url": "https://exemplo.org/dissertacao.pdf",
          "metadados": {
            "resumo": "Resumo extraído do PDF.",
            "fichaCatalografica": {},
            "sumario": [],
            "introducao": "Texto extraído da introdução.",
            "palavrasChave": []
          },
          "buscaTexto": "texto normalizado usado para pesquisa específica",
          "fontes": [{"url": "https://exemplo.org/dissertacao.pdf", "paginas": [1, 2, 5]}],
          "estadoEnriquecimento": "parcial"
        },
        {
          "id": "EPT-0001-PRO",
          "defesaId": "EPT-0001",
          "tipo": "produto_educacional",
          "titulo": "Título do produto educacional",
          "url": "https://educapes.capes.gov.br/handle/capes/123",
          "metadados": {
            "autoresColaboradores": [],
            "identificadores": [],
            "dataPublicacao": null,
            "colecaoEduCAPES": "Livros digitais",
            "tipoProduto": {"codigo": "ebook", "nome": "E-book", "rotuloOrigem": "eBook", "campoOrigem": "ficha/descrição do produto"},
            "palavrasChave": []
          },
          "buscaTexto": "texto normalizado usado para pesquisa específica",
          "fontes": [{"url": "https://educapes.capes.gov.br/handle/capes/123", "campos": ["dc.title", "dc.contributor"]}],
          "estadoEnriquecimento": "parcial"
        }
      ]
    }
  ]
}
```

`LP1` e `LP2` são códigos internos estáveis das linhas; o JSON legado tem os nomes, mas não os códigos.

## Normalização e ausência de dados

- Normalizar `Macroprojeto 3` para código `MP3`; conservar o rótulo original somente em `fontes`/auditoria, nunca como segunda categoria.
- Campos enriquecidos não encontrados ficam `null`, `[]` ou `{}` conforme o tipo; não usar o texto literal `"Resumo não disponível."` como dado.
- Os resumos ausentes no JSON antigo são uma falha geral da extração anterior. Não fazem parte desta etapa de correção da base antiga; o novo fluxo deve extrair o resumo do PDF e registrar falhas por campo para que não se repitam silenciosamente.
- O estado de enriquecimento registra extração incompleta ou falha. A interface decide a mensagem de apresentação.
- Guardar metadados de origem suficientes para localizar o valor (URL, campo da fonte, página do PDF e data de coleta); não atribuir valor sem evidência.
- O texto de busca deriva dos campos de conteúdo selecionados, sem substituir nem corromper o valor exibido do resumo.
- Para pesquisa da dissertação, incluir resumo, palavras-chave nele, introdução, títulos do sumário e classificações no `buscaTexto`; para o produto, incluir título, metadados eduCAPES, tipo e palavras-chave.
- O JSON antigo com resumos ausentes não será reparado nesta etapa. A extração do resumo será tratada no fluxo novo; a mensagem de ausência é uma apresentação da interface, não um valor armazenado.

## Validações de aceitação

1. Cada `defesa.id` é único.
2. Cada defesa tem exatamente uma produção `dissertacao` e uma `produto_educacional`, com IDs únicos e `defesaId` correspondente.
3. Cada produção tem título e URL não vazios.
4. O total de produções é igual a duas vezes o total de defesas completas; para a base atual de 110 defesas, a referência é 220 produções.
5. A contagem de alunos por orientador deduplica pelo par acadêmico–orientador, nunca pelas produções.
6. A contagem de coorientadores é separada e deduplica por `coorientador.chave`.
7. A contagem por tipo de produto inclui somente a produção educacional e conta cada ID uma vez, com um tipo principal por produto.
8. Defesas classificadas como “Macroprojeto 3” são normalizadas para MP3; a defesa identificada como rótulo divergente deve ser conferida pela fonte antes da migração.
9. Resumo e demais evidências extraídas têm fonte/localizador, e falha de extração é distinguível de conteúdo ausente na fonte.

## Validações práticas pendentes

1. Conferir o vocabulário de tipos já existente contra valores de “Aparece nas coleções:” e fichas de produto; manter a coleção ampla e o tipo educacional em campos separados.
2. Experimentar a extração em um pequeno conjunto de PDFs/eduCAPES para conferir rótulos de coorientador, paginação das evidências e tamanho do JSON.
3. Na geração do JSON novo, normalizar rótulos de macroprojeto a partir do código canônico. No JSON atual, `EPT-0108` já tem `codigoMacroprojeto: MP3`; o problema observado é o rótulo textual “Macroprojeto 3”, que cria uma fatia separada em agregações feitas pelo rótulo.

### Conferência inicial de fontes reais

Uma amostra de itens eduCAPES confirmou que “Aparece nas coleções” deve ser preservado como campo próprio, sem tratá-lo sempre como o tipo educacional específico:

| Defesa / item | Evidência do eduCAPES | Implicação para o contrato |
| --- | --- | --- |
| EPT-0001 / [capes/1171935](https://educapes.capes.gov.br/handle/capes/1171935) | Coleção “Livros digitais”; o produto associado tem ficha técnica que o descreve como Cartilha. | Guardar coleção e tipo educacional separadamente. |
| EPT-0002 / [capes/1171701](https://educapes.capes.gov.br/handle/capes/1171701) | Também aparece em “Livros digitais”; o registro informa “livro digital”, e a classificação atual é E-book. | A coleção é uma categoria ampla; usar metadados e descrição do produto para o tipo único específico. |
| EPT-0108 / [capes/1180962](https://educapes.capes.gov.br/handle/capes/1180962) | Registro sem arquivos associados, com `dc.identifier` apontando para site externo; seu código local de macroprojeto já é MP3. | Preservar identificadores externos; não inferir hospedagem/arquivo a partir do handle nem duplicar MP3 pelo rótulo. |

Esta é uma amostra de validação, não uma auditoria dos 110 itens. Arquivos XLSX/PDF/cache de execução não estão presentes no checkout; a validação integral deverá ocorrer quando o novo coletor produzir os artefatos locais.


