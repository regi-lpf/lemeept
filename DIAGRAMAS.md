# Diagramas do PAINEL EPT / LEME

Este documento complementa o guia de continuidade com uma visão visual do sistema.

O fluxo legado permanece organizado principalmente em scripts e funções. A nova pipeline usa `Registro` como dataclass e `GeradorPainel` para serialização; o diagrama representa responsabilidades e dependências, não todos os detalhes internos.

## Mapa para orientar as próximas mudanças

O projeto tem dois trechos distintos que não devem ser confundidos:

1. **Extração e preparação:** fontes ProfEPT/IFC e eduCAPES passam pela coleta, PDFs/OCR, classificação assistida e revisão humana até chegar à planilha final. É aqui que está o principal fluxo a revisar.
2. **Atualização do painel:** `lemeept/atualizar_dados.py` lê a planilha final revisada, normaliza/classifica os registros e grava `lemeept/painel-ept.json`. O `lemeept/index.html` é o bloco de código para o widget HTML do Elementor e busca o JSON por `data-json-url`.

### Fluxo de dados atual

```mermaid
flowchart LR
    subgraph coleta["1. Extração e preparação — fluxo a revisar"]
        SITE["Site ProfEPT / IFC"] --> COLETA["Coleta de trabalhos e metadados"]
        EDU["eduCAPES"] --> COLETA
        REFS["Referências e cache"] <--> COLETA
        COLETA --> PDFs["PDFs e planilha bruta"]
        PDFs --> OCR["OCR e extração de evidências"]
        OCR --> GPT["Classificação assistida / GPT"]
        GPT --> REV["Validação e revisão humana"]
        REV --> XLSX["dados/dados_finais_painel_ept.xlsx"]
    end

    subgraph painel["2. Preparação dos dados publicados"]
        XLSX --> UPD["lemeept/atualizar_dados.py"]
        UPD --> MAP["Mapeamento de colunas e normalização"]
        MAP --> CLASS["Preservar classificação revisada ou classificar"]
        CLASS --> BUILD["Contrato Registro + validação de IDs"]
        BUILD --> JSON["lemeept/painel-ept.json"]
    end

    subgraph wordpress["3. Exibição — Elementor / WordPress"]
        WIDGET["Widget HTML do Elementor\nlemeept/index.html"] --> FETCH["fetch via data-json-url"]
        JSON --> FETCH
        FETCH --> UI["Filtros, busca, gráficos, tabela/cards"]
        UI --> WP["Página publicada no WordPress"]
    end
```

### Fronteira cuidadosa do Elementor

`lemeept/index.html` contém código para ser inserido em um **widget HTML do Elementor**. Embora esteja salvo como `.html`, não é uma página independente: CSS, elementos e JavaScript dependem do escopo/estrutura do widget e da integração WordPress. Alterações visuais devem preservar o contêiner `#leme-painel-ept`, os IDs/classes usados pelo JavaScript, o carregamento JSON por `data-json-url` e o isolamento dos estilos. Antes de trocar o bloco publicado, conferir o diff e validar no editor e na página publicada.

| Tipo de mudança | Ponto inicial recomendado | Cuidado principal |
| --- | --- | --- |
| Mudar de onde vêm os dados ou como são coletados | Scripts de coleta/OCR e `dados/referencia/` | Não alterar junto o contrato do painel sem necessidade; preservar IDs e trilha de revisão. |
| Mudar colunas, limpeza ou classificação antes do painel | `lemeept/atualizar_dados.py` e `lemeept/pipeline/` | Manter os nomes/tipos de campos esperados no JSON. |
| Mudar filtros, gráficos, layout ou exibição | `lemeept/index.html` | Tratar como código de widget Elementor; preservar seletores, escopo CSS e inicialização JS. |
| Mudar campos disponíveis no painel | Pipeline e `index.html` em conjunto | Conferir o contrato de `Registro`, regenerar JSON e verificar renderização. |

## Requisitos do próximo desenho

Estes itens descrevem o **estado desejado** e não afirmam que já estejam implementados.

### Extração unificada e pesquisa direcionada

```mermaid
flowchart LR
    SRC["Fontes: ProfEPT / IFC, eduCAPES e PDFs"] --> FETCH["Coleta unificada com cache e deduplicação"]
    FETCH --> EVID["Metadados + texto/OCR + referências de origem"]
    EVID --> INDEX["Índice pesquisável dos registros e evidências"]
    INDEX --> QUERY["Consultas específicas por tema, período, campus, autor, orientador ou classificação"]
    QUERY --> RULES["Regras determinísticas e vocabulários"]
    RULES --> REVIEW["Revisão humana para lacunas e casos ambíguos"]
    EVID -. "GPT opcional, limitado a tarefas focadas" .-> REVIEW
    QUERY --> OUT["Conjunto de resultados rastreável"]
    REVIEW --> OUT
    OUT --> XLSX["Fonte revisada / exportação para o painel"]
```

Objetivos de projeto: reduzir etapas duplicadas e dependência de GPT; manter buscas específicas reproduzíveis; guardar de onde veio cada evidência; e enviar à revisão humana apenas o que regras e dados disponíveis não resolverem com segurança. A escolha do mecanismo de índice e o formato exato das consultas ainda são decisões de implementação.

### Produção como unidade independente

O total de **220** deve representar produções acessíveis individualmente, e não defesas multiplicadas pela presença de um produto. O modelo alvo separa a entidade que agrupa uma defesa/trabalho da entidade que representa cada produção:

```mermaid
erDiagram
    TRABALHO ||--o{ PRODUCAO : agrupa
    TRABALHO {
        string idTrabalho
        string autor
        string orientador
        string tituloDissertacao
        string linkDissertacao
    }
    PRODUCAO {
        string idProducao
        string tipoProducao
        string titulo
        string link
    }
```

Uma dissertação e seu produto educacional podem ser duas produções ligadas ao mesmo trabalho, cada uma com identidade, tipo, título e acesso próprios. O total do painel conta entidades `PRODUCAO`; métricas de pessoas e relacionamentos devem usar identidades normalizadas/deduplicadas no nível de `TRABALHO` ou do vínculo, não somas das produções. Por consequência, número de alunos orientados não pode crescer porque o mesmo aluno tem dissertação e produto, e totais por tipo de produto não podem contar o mesmo produto mais de uma vez.

### Linhas e macroprojetos

- Dar destaque visual às **linhas de pesquisa** no painel e oferecer leitura/consulta própria, além de mantê-las como filtro/classificação dos registros.
- Tratar **“Macroprojeto 3”** e **“MP3”** como categorias distintas a partir da divisão informada. Não fundir por semelhança textual nem reclassificar registros históricos automaticamente. A regra de vigência, os rótulos oficiais e como atribuir registros anteriores devem ser definidos antes da migração.
- Ao alterar agregações, documentar a unidade de cada indicador (produção, trabalho/aluno, orientador único, produto único) para evitar que um gráfico some entidades diferentes.

## 1. Visão geral do fluxo

```mermaid
flowchart TD
    SITE["Site oficial ProfEPT/IFC"]
    EDU["eduCAPES"]
    E1["1_PegarDadosSiteIfc.py<br/>Coleta e PDFs"]
    REF["dados/referencia/<br/>identidades, classificações e vocabulários"]
    XLS1["dados/1_PegarDadosSiteIfc.xlsx"]
    PDF["pdf/*.pdf"]
    E2["2_PdfParaJson.py<br/>OCR e preparação do GPT"]
    CACHE["dados/cache/<br/>eduCAPES e OCR"]
    PROMPT["PromptClassificacaoGPT.md"]
    JSONIN["para_gpt.json"]
    GPT["GPT<br/>etapa manual"]
    JSONOUT["gpt.json"]
    E3["3_ArrumarPlanilha.py<br/>Validação e padronização"]
    XLS2["dados_finais_painel_ept.xlsx"]
    REL["Relatórios de OCR e validação"]
    PIPE["lemeept/atualizar_dados.py<br/>normalizar, classificar e serializar"]
    JSONP["lemeept/painel-ept.json<br/>contrato legado do widget"]
    JSONV2["lemeept/painel-ept-v2.json<br/>defesas + producoes"]
    HTML["lemeept/index.html<br/>bloco do widget HTML do Elementor"]
    WP["Elementor / WordPress<br/>publicação manual"]

    SITE --> E1
    EDU --> E1
    REF --> E1
    E1 --> XLS1
    E1 --> PDF
    E1 --> E2
    XLS1 --> E2
    PDF --> E2
    REF --> E2
    CACHE <--> E1
    CACHE <--> E2
    E2 --> PROMPT
    E2 --> JSONIN
    E2 --> REL
    PROMPT --> GPT
    JSONIN --> GPT
    GPT --> JSONOUT
    JSONOUT --> E3
    XLS1 --> E3
    REF --> E3
    E3 --> XLS2
    E3 --> REL
    XLS2 --> PIPE
    PIPE --> JSONP
    PIPE -.-> JSONV2
    HTML -->|inserido/publicado no widget| WP
    JSONP -->|fetch HTTPS via data-json-url| HTML
```

O contrato legado `painel-ept.json` continua alimentando o widget Elementor. `painel-ept-v2.json` é uma saída de transição com arrays independentes `defesas` e `producoes`; cada produção tem ID próprio e `defesaId`. O widget não consome o v2 até uma migração deliberada e validada no WordPress.

## 2. Diagrama de classes conceitual

```mermaid
classDiagram
    class ColetorProfEPT {
        +URL paginaOficial
        +URL apiOficial
        +obterPagina()
        +extrairTrabalhos()
        +resolverIdentidades()
        +salvarPlanilha()
    }

    class ClienteEduCAPES {
        +consultar(handle)
        +extrairMetadadosDC()
        +listarBitstreams()
        +resolverInstituicaoCampus()
    }

    class ClienteHTTP {
        +criarSessao()
        +requisicaoSegura()
        +fallbackTLSdoIFC()
    }

    class GerenciadorIdentidades {
        +carregarReferencias()
        +encontrarPorURL()
        +encontrarPorAutorTituloAno()
        +criarProximoID()
        +validarHash()
    }

    class GerenciadorPDF {
        +baixarPDF()
        +validarAssinaturaPDF()
        +calcularSHA256()
        +nomearPorID()
    }

    class ProcessadorOCR {
        +abrirPDF()
        +renderizarPaginas()
        +reconhecerTexto()
        +usarCache()
        +extrairCampos()
    }

    class PreparadorGPT {
        +aplicarVocabularios()
        +montarContextoGlobal()
        +gerarJSONEntrada()
        +gerarPrompt()
    }

    class ValidadorGPT {
        +validarJSON()
        +validarIDs()
        +validarCategorias()
        +aplicarSugestoesSeguras()
        +encaminharRevisaoManual()
    }

    class GeradorPlanilha {
        +gerarAbaPrincipal()
        +gerarAlteracoes()
        +gerarValidacoes()
        +gerarRevisaoManual()
        +gerarAuditoriaGPT()
    }

    class GeradorPainel {
        +validarIDs()
        +montarContratoJSON()
        +salvarJSONAtomico()
    }

    class RepositorioReferencias {
        +identidadesJson
        +classificacoesHistoricasJson
        +vocabulariosJson
    }

    class RepositorioCache {
        +cacheEduCAPES
        +cacheOCR
    }

    ColetorProfEPT --> ClienteHTTP : usa
    ColetorProfEPT --> ClienteEduCAPES : consulta
    ColetorProfEPT --> GerenciadorIdentidades : resolve IDs
    ColetorProfEPT --> GerenciadorPDF : baixa e valida
    ClienteEduCAPES --> ClienteHTTP : usa
    GerenciadorIdentidades --> RepositorioReferencias : lê e atualiza
    ClienteEduCAPES --> RepositorioCache : reutiliza HTML
    ProcessadorOCR --> GerenciadorPDF : lê PDFs validados
    ProcessadorOCR --> RepositorioCache : reutiliza OCR
    PreparadorGPT --> ProcessadorOCR : recebe evidências
    PreparadorGPT --> RepositorioReferencias : usa classificações
    ValidadorGPT --> RepositorioReferencias : valida vocabulários
    ValidadorGPT --> GeradorPlanilha : entrega dados aprovados
    GeradorPlanilha --> GeradorPainel : fornece planilha final
```

## 3. Modelo conceitual dos dados

```mermaid
classDiagram
    class Trabalho {
        +string id
        +string ano
        +string titulo
        +string autor
        +string orientador
        +string coorientador
        +string produtoEducacional
        +string instituicao
        +string campus
        +string programa
        +string urlPDF
        +string urlProduto
    }

    class Identidade {
        +string idPermanente
        +string urlPDFCanonica
        +string nomePDF
        +string sha256
        +list aliasesTitulos
        +list aliasesAutores
        +boolean vinculoConfirmado
    }

    class DocumentoPDF {
        +string caminho
        +string sha256
        +string status
        +int totalPaginas
    }

    class MetadadosEduCAPES {
        +string handle
        +map camposDublinCore
        +list bitstreams
        +string campusExplicito
        +string origemConsulta
    }

    class ConteudoOCR {
        +string resumo
        +list palavrasChave
        +string objetivos
        +string metodologia
        +string descricaoProduto
        +string publicoAlvo
        +list errosPaginas
    }

    class Classificacao {
        +string linhaPesquisa
        +string macroprojeto
        +string baseEpistemologica
        +string nivelAplicacao
        +string tipoProduto
        +string areaTematica
        +string publicoAlvo
        +string confianca
        +boolean revisaoManual
    }

    class Vocabulario {
        +map valoresCanonicos
        +map aliases
        +map relacaoLinhaMacro
        +list orientadoresCanonicos
    }

    Trabalho "1" --> "1" Identidade : possui
    Trabalho "1" --> "1" DocumentoPDF : referencia
    Trabalho "1" --> "0..1" MetadadosEduCAPES : complementado por
    DocumentoPDF "1" --> "0..1" ConteudoOCR : produz
    Trabalho "1" --> "1" Classificacao : recebe
    Vocabulario "1" --> "0..*" Classificacao : restringe
```

## 4. Diagrama de sequência da execução normal

```mermaid
sequenceDiagram
    actor Pessoa as Responsável pelo projeto
    participant E1 as Python 1
    participant IFC as ProfEPT/IFC
    participant EDU as eduCAPES
    participant REF as Referências
    participant E2 as Python 2 / OCR
    participant GPT as GPT
    participant E3 as Python 3
    participant PIPE as Pipeline do painel
    participant WP as Elementor

    Pessoa->>E1: python 1_PegarDadosSiteIfc.py
    E1->>IFC: Consulta API com TLS
    alt Certificado válido
        IFC-->>E1: Página oficial
    else Certificado do IFC rejeitado
        E1->>IFC: Repete somente para o IFC sem validar certificado
        IFC-->>E1: Página oficial
    end
    E1->>REF: Carrega identidades permanentes
    loop Para cada trabalho
        E1->>EDU: Consulta metadados e campus explícito
        EDU-->>E1: Dublin Core e bitstreams
        E1->>IFC: Baixa PDF ausente
        IFC-->>E1: PDF
        E1->>REF: Confere ID e SHA-256
    end
    E1->>E2: Inicia OCR automaticamente
    loop Para cada PDF validado
        E2->>E2: Renderiza páginas e executa Tesseract
        E2->>E2: Extrai evidências e atualiza cache
    end
    E2-->>Pessoa: PromptClassificacaoGPT.md + para_gpt.json
    Pessoa->>GPT: Envia os dois arquivos
    GPT-->>Pessoa: JSON único de resposta
    Pessoa->>E3: Salva gpt.json e executa Python 3
    E3->>E3: Valida IDs, categorias e confiança
    E3-->>Pessoa: Planilha final + relatório
    Pessoa->>Pessoa: Faz revisão humana
    Pessoa->>PIPE: python -m lemeept.atualizar_dados
    PIPE->>PIPE: Normaliza e classifica registros
    PIPE->>PIPE: Valida IDs e grava JSON compacto
    PIPE-->>Pessoa: lemeept/painel-ept.json
    Pessoa->>WP: Atualiza somente o JSON hospedado
    WP->>WP: HTML estático faz fetch do JSON por HTTPS
```

## 5. Decisão da instituição e do campus

```mermaid
flowchart TD
    A["Registro do trabalho"] --> B["Consultar eduCAPES"]
    B --> C{"dc.contributor informa<br/>campus explicitamente?"}
    C -- Sim --> D["Usar o campus informado<br/>pelo eduCAPES"]
    C -- Não --> E["Usar Blumenau como contexto<br/>do ProfEPT/IFC"]
    D --> F["Registrar Fonte do Campus:<br/>eduCAPES: dc.contributor"]
    E --> G["Registrar Fonte do Campus:<br/>eduCAPES sem campus explícito"]
    F --> H["Salvar na planilha da etapa 1"]
    G --> H

    I["Campus citado apenas no<br/>título ou resumo"] --> J["Não usar automaticamente"]
    J --> K["Pode ser somente o local pesquisado"]
```

## 6. Decisão de conexão TLS e download

```mermaid
flowchart TD
    A["Iniciar consulta HTTPS"] --> B["Validar certificado normalmente"]
    B --> C{"Conexão funcionou?"}
    C -- Sim --> D["Continuar download seguro"]
    C -- Não --> E{"Erro é de certificado e o host<br/>é profept.ifc.edu.br?"}
    E -- Não --> F["Interromper e mostrar o erro real"]
    E -- Sim --> G["Mostrar aviso"]
    G --> H["Repetir sem validar certificado<br/>somente para o domínio do IFC"]
    H --> I{"Segunda tentativa funcionou?"}
    I -- Sim --> J["Continuar coleta e download"]
    I -- Não --> F
```

## 7. Ciclo de vida dos arquivos

```mermaid
flowchart LR
    subgraph Git["Arquivos versionados no Git"]
        COD["Scripts Python"]
        REQ["requirements.txt"]
        DOC["Documentação"]
        TEST["Testes"]
        RJSON["JSONs de referência"]
    end

    subgraph Local["Arquivos locais gerados"]
        PDFs["pdf/"]
        PLAN["Planilhas"]
        GPTF["Arquivos de troca com GPT"]
        CACHES["Caches"]
        REPORTS["Relatórios"]
        SHELL["lemeept/index-elementor-json.html<br/>shell estático do Elementor"]
        DATA["lemeept/painel-ept.json<br/>dados de publicação"]
    end

    COD --> Local
    REQ --> COD
    RJSON --> Local
    TEST --> COD
    COD --> DATA
    SHELL --> WP["Elementor / WordPress"]
    DATA --> WP
    Local -.->|ignorado por .gitignore| Git
```

## 8. Dependências técnicas

```mermaid
flowchart TD
    PY["Python 3.11+"] --> REQ["requirements.txt"]
    REQ --> BS["BeautifulSoup<br/>interpretação de HTML"]
    REQ --> REQUESTS["requests<br/>HTTP"]
    REQ --> PANDAS["pandas<br/>tabelas"]
    REQ --> OPENPYXL["openpyxl<br/>Excel"]
    REQ --> PYMUPDF["PyMuPDF<br/>leitura e imagem do PDF"]
    REQ --> PILLOW["Pillow<br/>imagens"]
    REQ --> PYTESS["pytesseract<br/>integração Python"]
    TESS["Tesseract instalado no sistema"] --> PYTESS
    LANG["Idioma português do Tesseract"] --> TESS
```

O `requirements.txt` instala as bibliotecas Python. O Tesseract e seu pacote de idioma são dependências externas e precisam ser instalados no sistema operacional.

