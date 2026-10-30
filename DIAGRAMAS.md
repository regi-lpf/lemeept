# Arquitetura e diagramas — LEME EPT

Este documento descreve o que existe hoje e separa as etapas planejadas. O fluxo novo é iniciado por uma pessoa; não há tarefa agendada, webhook nem sincronização automática em segundo plano.

## Fluxos implementados

### Atualizar/servir painel atual

```mermaid
flowchart LR
    XLSX["Planilha revisada\n(local; quando disponível)"] --> LEGACY["atualizar_dados.py\nnormalização/classificação"]
    LEGACY --> JSON1["painel-ept.json\ncontrato legado"]
    HTML["lemeept/index.html\nbloco Elementor"] --> FETCH["fetch via data-json-url"]
    JSON1 --> FETCH --> UI["Painel WordPress"]
```

`lemeept/index.html` é código para o widget HTML do Elementor, não uma página HTML independente. Preserve contêineres, seletores, `<p>`/`<br>`, CSS isolado e inicialização do JavaScript. Não substitua o bloco pelo HTML renderizado/copiado do navegador.

### Descoberta e revisão visual

```mermaid
flowchart TD
    START["Pessoa inicia sincronizar_revisao.py"] --> API["API WordPress do ProfEPT\nlista de dissertações"]
    API --> ID["resolver/comparar IDs\ncom painel-ept-v2.json"]
    ID --> PDF["baixar PDFs novos\npara pdf/dissertacoes/\nfora do Git"]
    PDF --> TXT["PyMuPDF: texto nativo\nlimite de páginas configurável"]
    TXT --> XLSX["gerar_planilha_revisao.py\nrevisao_ept.xlsx"]
    ID --> XLSX
    XLSX --> HUMAN["revisão/correção humana"]
    HUMAN -. "integração manual futura" .-> V2["painel-ept-v2.json"]
```

`sincronizar_revisao.py` consulta a API quando executado, mas não integra as decisões da planilha ao JSON. A chamada também não consulta eduCAPES nessa etapa. OCR e GPT não são acionados por esse comando.

### Extração comparativa da amostra

```mermaid
flowchart LR
    LEGACY["painel-ept.json\nIDs e valores legados"] --> SAMPLE["criar_amostra_comparativa.py"]
    PDFs["pdf/dissertacoes/{ID}.pdf"] --> SAMPLE
    HANDLE["Handles eduCAPES"] --> SAMPLE
    SAMPLE --> JSON["amostra_extracao_6_v2.json"]
    SAMPLE --> BOOK["comparacao_amostra_6_v2.xlsx"]
    JSON --> GPT["classificacao_assistida_6_v2.json\nrevisão contextual"]
    JSON --> PRODUCT["comparar formato do PDF\ncom tipo/coleção eduCAPES"]
    JSON --> BIB["extrair_contexto_base_epistemologica.py\ncitações e referências direcionadas"]
    BIB --> REVIEW["contexto_base_epistemologica_6_v1.xlsx\npropostas em classificacao_assistida_6_v3.json"]
```

A amostra corrente usa seis IDs únicos: EPT-0001, 0003, 0005, 0007, 0008 e 0010. A extração usa texto nativo; a consulta eduCAPES pode falhar por Handle, rede ou mudança de HTML. Valores do `dc.type`/coleção não substituem o formato específico da dissertação.

## Entidades e chaves

```mermaid
erDiagram
    DEFESA ||--|| DISSERTACAO : origina
    DEFESA ||--|| PRODUTO : origina
    DEFESA ||--|| CLASSIFICACAO : recebe
    DEFESA {
        string id PK
        string ano
        string academico
        string orientador
        string coorientador
    }
    DISSERTACAO {
        string id PK
        string defesaId FK
        string titulo
        string url
        string resumo
        array palavrasChave
    }
    PRODUTO {
        string id PK
        string defesaId FK
        string titulo
        string url
        string tipoProduto
        string colecaoEduCAPES
    }
    CLASSIFICACAO {
        string linhaPesquisa
        string macroprojeto
        string baseEpistemologica
        string nivelAplicacao
        string evidencia
        string confianca
        string metodo
    }
```

`painel-ept-v2.json` mantém `defesas` e `producoes` em listas independentes; cada produção tem ID e `defesaId`. O JSON legado `painel-ept.json` continua separado durante a transição. Não migre o widget até validar o consumidor e a publicação no WordPress.

## Sequência de revisão de uma defesa

```mermaid
sequenceDiagram
    actor Operador
    participant API as API ProfEPT
    participant PDF as PDF local
    participant EX as Extração determinística
    participant EDU as eduCAPES
    participant XLS as Planilha de revisão
    participant GPT as Classificação assistida opcional

    Operador->>API: executa sincronizar_revisao.py
    API-->>Operador: defesas e links atuais
    Operador->>PDF: baixar PDF ausente
    PDF->>EX: texto nativo e campos localizados
    EX->>XLS: evidência, estado e lacunas
    Operador->>EDU: consulta Handle do produto (etapa comparativa)
    EDU-->>XLS: metadados/coleção e estado de consulta
    Operador->>GPT: envia somente segmentos selecionados, se necessário
    GPT-->>XLS: candidatos, confiança e evidência
    Operador->>XLS: confirma/corrige campos e registra decisão
```

## Decisões técnicas estáveis

- Contagens: 110 defesas e 220 produções esperadas; cada produto conta uma vez; orientadores são contados por vínculo aluno–orientador único; coorientadores são separados.
- Macroprojeto é canônico pelo código MP1–MP6. `Macroprojeto 3` é alias de MP3, não uma categoria adicional.
- Linha de pesquisa deriva da relação oficial do macroprojeto: MP1–MP3 → LP1; MP4–MP6 → LP2.
- Base epistemológica é interpretativa. O texto da dissertação sustenta a classificação; autores e obras da bibliografia podem corroborar uma hipótese quando correspondem a citações/argumentos do referencial teórico.
- Classificação assistida de confiança alta pode ser usada como valor de trabalho; média/baixa, abstenção ou evidência contraditória seguem para conferência humana.
- Toda evidência preserva seção, página e trecho curto; registro da fonte não significa que ela declare literalmente o rótulo atribuído.

## Arquivos por responsabilidade

| Responsabilidade | Arquivos |
| --- | --- |
| Coleta e compatibilidade do fluxo antigo | `1_PegarDadosSiteIfc.py`, `2_PdfParaJson.py`, `3_ArrumarPlanilha.py`, `4_GerarPainelHtml.py` |
| Download local de PDFs | `baixar_dissertacoes.py`; corpus e manifesto em `pdf/dissertacoes/` (ignorados pelo Git) |
| Amostra de extração/eduCAPES | `criar_amostra_comparativa.py` |
| Evidência textual/bibliográfica de base epistemológica | `extrair_contexto_base_epistemologica.py` |
| Sincronização manual com API e planilha de lacunas | `sincronizar_revisao.py`, `gerar_planilha_revisao.py`, `GUIA_REVISAO.md` |
| JSON de transição | `lemeept/gerar_painel_v2.py`, `lemeept/pipeline/production_builder.py`, `lemeept/painel-ept-v2.json` |
| Painel legado e contrato legado | `lemeept/atualizar_dados.py`, `lemeept/pipeline/`, `lemeept/painel-ept.json`, `lemeept/index.html` |
| Vocabulários e identidades | `dados/referencia/` — preservar; não tratar como temporário |

## Pendências em ordem

1. Conferir os contextos bibliográficos gerados; calibrar citações que o regex não localiza e revisar a proposta alta de EPT-0007.
2. Refinar classificação do produto combinando formato declarado na dissertação com campos eduCAPES, sem equiparar coleção ampla a tipo.
3. Integrar decisões humanas da planilha ao JSON v2 de forma auditável.
4. Repetir o fluxo para uma defesa nova antes de automatizar publicação ou alterar o widget Elementor.

