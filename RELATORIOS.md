Prompt: fechamos a etapa x. gere um prompt que inclua breve relatório dessa etapa para contexto, incluindo os fixes e decisões técnicas e chame a próxima etapa.

### Contexto da Etapa 1 Concluída & Fixes Aplicados (Pipeline v4)

A **Etapa 1 (Coleta e Pré-Extração)** está finalizada, validada e rodando em `pipeline/step1_collect.py` com modelos tipados em `pipeline/models_v4.py`. O artefato de saída `data/stage1_manifest.json` contém **111 defesas catalogadas** (preservando os 110 IDs legados `EPT-0001` a `EPT-0110` e incorporando a defesa inédita `EPT-0111`), com todos os PDFs baixados localmente em `pdf/dissertacoes/EPT-XXXX.pdf` e validados por assinatura mágica (`%PDF-`) e hash `SHA-256`.#### Fixes Técnicos Incorporados na Etapa 1 (para manter no restante da pipeline):1. **SSL Institucional (`profept.ifc.edu.br` / `.edu.br`):** O servidor apresenta cadeia intermediária incompleta, causando `SSLCertVerificationError`. Requisições HTTP aos domínios institucionais utilizam `verify=False` com `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)`.2. **Parser Sequencial Independente de Estrutura (`<ul>` quebradas):** O HTML da API do WordPress contém listas mal fechadas (`<p>` aberto dentro de `<li>`) que mesclam defesas adjacentes no DOM. O parser percorre os `<li>` sequencialmente usando `Acadêmico/Discente/Autor:` como delimitador de registro em vez de depender do fechamento de `<ul>`.3. **Flexibilidade de Rótulos e Pontuação:** Regex tolerante a variações manuais do WordPress (`Dissertação:`, `Dissertação :`, `Dissertação intitulada`, sem dois-pontos, `Artigo:`, `Orientador:` / `Orientadora:`).4. **Preservação do Rótulo Bruto do Produto:** O campo `titulo_produto_bruto` no manifesto já captura prefixos declarados antes do link na página do ProfEPT (ex.: `"Texto – "`, `"Podcast – "`, `"Portal – "`, `"Curso – "`, `"Livro Digital – "`, `"Sequência Didática: "`), servindo como evidência prioritária para o classificador determinístico na Etapa 2.5. **Fallback de Ano:** Captura o ano pelos cabeçalhos `DEFESAS YYYY` no DOM, com fallback automático via regex no caminho da URL (`/uploads/sites/54/YYYY/`).

---### Próximo Passo: Etapa 2 (`pipeline/step2_deterministic.py`)
Partindo de `data/stage1_manifest.json` e dos PDFs em `pdf/dissertacoes/`, implementar a extração determinística e o scraping do eduCAPES para gerar os payloads individuais em `data/stage2_payloads/EPT-XXXX.json` conforme o `ContratoExtracaoDeterministicaV4`.

### Contexto da Etapa 2 Concluída & Fixes Aplicados (Pipeline v4)

A **Etapa 2 (Extração Determinística)** está finalizada, validada e rodando em `pipeline/step2_deterministic.py` com modelos tipados em `pipeline/models_v4.py`. Os 111 payloads estruturados (`ContratoExtracaoDeterministicaV4`) foram gerados em `data/stage2_payloads/EPT-0001.json` a `EPT-0111.json`, contendo os metadados determinísticos resolvidos, evidências do eduCAPES e recortes cirúrgicos de texto para consumo na etapa final.

#### Fixes e Decisões Técnicas Incorporadas na Etapa 2 (para manter na Etapa 3):
1. **Varredura Taxonômica Integral & Vínculo Rígido (`MP1–3 → LP1` | `MP4–6 → LP2`):** A busca determinística por `Macroprojeto` e `Linha de Pesquisa` varre o texto integral do PDF (incluindo introdução e fichas técnicas de produto ao final dos arquivos), normalizando espaços colados, numeração romana/arábica, plurais/inversões e prevenindo falsos positivos de formato de vídeo (`MP4`). Registros sem menção explícita no PDF permanecem marcados como `MP_INDEFINIDO` / `LP_INDEFINIDA` para inferência semântica na Etapa 3.
2. **Hierarquia de Fontes & Classificação de Produto:** A detecção via regex prioriza o rótulo bruto da fonte ProfEPT (`titulo_produto_bruto`) e a sentença exata onde *"produto educacional"* ocorre no resumo/corpo da dissertação, evitando falsos positivos com termos do contexto da pesquisa (ex.: *"Cursos Técnicos Integrados"* disparando `curso_oficina`). Metadados do eduCAPES (`dc.type`, coleção, `<meta>` Dublin Core e tabela `?show=full`, com cache local em `data/cache_educapes/`) são preservados como evidência complementar.
3. **Isolamento Cirúrgico de Recortes Textuais:** Cada payload isola exclusivamente capa, ficha catalográfica, sumário, resumo, introdução, descrição do produto na dissertação, trechos com marcadores epistemológicos (preservando `[PÁG. X]`) e apenas as entradas bibliográficas correspondentes às citações detectadas nesses trechos — mantendo o contexto enxuto (~3k–5k tokens) para execução local sem enviar PDFs inteiros.
4. **Governança de Campos Interpretativos:** Campos interpretativos (especialmente `base_epistemologica`) exigem evidência localizável (seção, página, trecho e referência correspondente) e trava de confiança (`confianca == "alta"` para preencher `valor`; `media`, `baixa` ou `abstencao` mantêm `valor: null` e `revisao_pendente: true`).

---

### Próximo Passo: Etapa 3 (`SKILL.md` + `pipeline/step3_llm_extract.py` + Compilação v4)
Partindo dos payloads individuais em `data/stage2_payloads/EPT-XXXX.json`:
1. Redigir o arquivo de instruções operacionais `SKILL.md` com as regras de negócio, critérios de classificação de `tipo` de produto, `publico_alvo`, `nivel_aplicacao`, resolução de `MP`/`LP` remanescentes e regras estritas de abstenção/evidência para `base_epistemologica`.
2. Implementar `pipeline/step3_llm_extract.py` utilizando inferência local estruturada (*JSON Schema / Structured Outputs* via Ollama) e trava determinística pós-LLM, persistindo os registros finais validados (`ContratoDefesaV4`) em `data/records/EPT-XXXX.json`.
3. Implementar `pipeline/step4_compile.py` para normalizar palavras-chave/índices de busca (`indice_busca`), compilar o artefato final `dist/painel-ept-v4.json` e gerar o relatório de registros com `revisao_pendente: true`.

### Contexto da Etapa 3 & 4 Concluídas (Pipeline v4 — LEME / ProfEPT)

As **Etapas 3 (Inferência Semântica Estruturada)** e **4 (Compilação e Curadoria)** foram concluídas e validadas, encerrando a camada de extração e geração de dados do projeto:

1. **Contratos Tipados (`pipeline/models_v4.py`):**
   - Implementados e validados os três contratos estritos em Pydantic v2 (`Stage1ManifestV4`, `ContratoExtracaoDeterministicaV4` e `ContratoDefesaV4`), garantindo cardinalidade fixa (1 Defesa = 1 Dissertação + 1 Produto Educacional) e campos pré-indexados para o frontend (`indice_busca`).

2. **Camada Modular de Inferência (`pipeline/llm_provider.py` + `pipeline/step3_llm_extract.py`):**
   - Implementado o adaptador agnóstico `LLMClient` com suporte a *Structured Outputs* (JSON Schema) via SDK oficial `google-genai` (`gemini-2.5-flash`) e endpoints OpenAI-compatíveis (`groq`, `openrouter`, `mistral` e `ollama` local).
   - **Fixes de Schema & Serialização:** Removida a restrição `extra="forbid"` (`additionalProperties`) incompatível com o OpenAPI Schema do Gemini e adicionada sanitização automática de `$defs`/`$ref`, além da serialização explícita via `.model_dump()` para submodelos (`autores_colaboradores` e `identificadores`).
   - **Governança Pós-LLM:** Imposto vínculo taxonômico rígido determinístico (`MP1–3 → LP1` e `MP4–6 → LP2`), preservação dos metadados da Etapa 2 e priorização das classificações determinísticas de produto sobre metadados genéricos do eduCAPES.

3. **Decisão sobre Base Epistemológica & Compilação (`pipeline/step4_compile.py`):**
   - Aplicado vocabulário canônico calibrado no `pipeline/SKILL.md` e trava de evidência localizável (`secao`, `pagina`, `trecho`).
   - **Decisão Operacional:** A extração automatizada da Etapa 3 foi encerrada e qualquer preenchimento ou ajuste remanescente de `base_epistemologica` será conduzido exclusivamente de forma manual via curadoria.
   - O compilador (`pipeline/step4_compile.py`) está operacional, consolidando os registros individuais de `data/records/EPT-XXXX.json` no artefato único `dist/painel-ept-v4.json` e exportando o relatório `dist/revisao_epistemologica_pendente.csv` para revisão humana.

---

### Próximo Passo: Integração e Atualização do Frontend (Painel Bibliométrico v4)

Com o artefato `dist/painel-ept-v4.json` gerado e validado pelo contrato `ContratoDefesaV4`, a próxima etapa consiste na adaptação da interface do painel (widget HTML/CSS/JS para Elementor) mantendo a identidade visual existente e consumindo o novo schema v4:

1. **Adaptação ao Contrato v4 (`ContratoDefesaV4`):**
   - Atualizar o mapeamento de propriedades no script Vanilla JS para ler a nova estrutura (`dissertacao.base_epistemologica`, `produto.tipo`, `produto.publico_alvo`, `produto.proveniencia` e `indice_busca.texto_busca_normalizado`).
   - Utilizar `indice_busca.texto_busca_normalizado` para busca textual instantânea (sem acentos/pontuação) e `indice_busca.termos_unificados` para a contagem limpa de palavras-chave frequentes.

2. **Camada de Apresentação (`I18N` / Rótulos Legíveis):**
   - Implementar o dicionário de tradução no frontend para converter os slugs canônicos (`LP1`..`LP2`, `MP1`..`MP6`, os 9 tipos de produto da CAPES e os 5 grupos de `publico_alvo`) em rótulos completos e amigáveis nos filtros, gráficos e cards, mantendo os slugs como valores internos de filtragem.

3. **Separação de Escopo (Todas / Dissertações / Produtos) e Métricas:**
   - Garantir que o alternador de escopo separe visualmente e metricamente as **Dissertações** (destacando resumo, orientador, base epistemológica aprovada e link do PDF) dos **Produtos Educacionais** (destacando tipo CAPES, nível de aplicação, público-alvo e link do eduCAPES).
   - Tratar graciosamente registros em que `base_epistemologica.valor` seja `null` (`revisao_pendente: true`), exibindo indicador discreto ou omitindo-os das contagens consolidadas de matrizes epistemológicas sem quebrar os gráficos.