# Documentação Técnica — Engenharia da Pipeline & Frontend v4

> **Escopo deste documento:** Especificação técnica de engenharia dos módulos em [pipeline/](pipeline), dos schemas Pydantic v2 ([pipeline/models_v4.py](pipeline/models_v4.py)), do frontend modular ([index.html](index.html) + [frontend/](frontend)) e do compilador Elementor ([scripts/build_frontend.py](scripts/build_frontend.py)).
> * Para comandos operacionais e testes: [README.md](README.md).
> * Para diagrama de fluxo, mapa de diretórios e governança: [ARQUITETURA.md](ARQUITETURA.md).
> * Para taxonomia CAPES/ProfEPT e regras de domínio: [CONTRATO_DADOS.md](CONTRATO_DADOS.md).
> * Para histórico de auditoria (`AUD-01..25` e `FE-01..30`) e métricas do acervo: [AUDITORIA_E_REFATORACAO.md](AUDITORIA_E_REFATORACAO.md) e [RELATORIOS.md](RELATORIOS.md).

---

## 1. Stack, Dependências e Configuração de Ambiente

### Ambiente Python ([pyproject.toml](pyproject.toml))

* **Runtime:** Python `>=3.14` gerenciado via `uv` (`.venv/`).
* **Dependências:**
  * `pydantic==2.14.3` — validação estrita de contratos entre todas as etapas e do envelope final.
  * `pymupdf==2.1` (`import pymupdf`) — extração nativa de texto dos PDFs página a página.
  * `requests==2.34.2` e `urllib3==2.8.0` — consumo da API REST WordPress, download de PDFs e scraping do eduCAPES.
  * `beautifulsoup4==4.15.0` — parsing HTML da página do ProfEPT e dos metadados Dublin Core (`?show=full`) do eduCAPES.
  * `google-genai>=3.3.0` (`from google import genai`) — SDK oficial para o provedor `gemini`.
  * `openai==3.50.0` — cliente OpenAI-compatível usado para `groq`, `openrouter`, `mistral` e `ollama`.
  * `python-dotenv==1.2.4` — carregamento determinístico de `.env` ancorado em `PROJECT_ROOT / ".env"`.

### Variáveis de Ambiente ([pipeline/llm_provider.py](pipeline/llm_provider.py) e [.env.dev](.env.dev))

| Variável | Padrão por Provedor | Descrição |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `"groq"` | Seleciona o backend: `gemini`, `groq`, `openrouter`, `mistral` ou `ollama`. |
| `LLM_MODEL` | `gemini`: `gemini-2.5-flash`<br>`groq`: `llama-3.3-70b-versatile`<br>`openrouter`: `meta-llama/llama-3.3-70b-instruct:free`<br>`mistral`: `mistral-small-latest`<br>`ollama`: `qwen2.5:7b-instruct` | Identificador do modelo enviado na chamada da API. |
| `LLM_DELAY` | `gemini`: `4.2` · `groq`: `5.0` · `openrouter`: `4.5` · `mistral`: `2.0` · `ollama`: `0.0` | Pausa em segundos aplicada após cada requisição bem-sucedida. |
| `LLM_BASE_URL` | `groq`: `https://api.groq.com/openai/v1`<br>`openrouter`: `https://openrouter.ai/api/v1`<br>`mistral`: `https://api.mistral.ai/v1`<br>`ollama`: `http://localhost:11434/v1` | Endpoint base para clientes OpenAI-compatíveis. |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` / `MISTRAL_API_KEY` / `LLM_API_KEY` | `"ollama"` (para `ollama` local) | Chaves de autenticação lidas pelo nome em `env_key` (com fallback para `LLM_API_KEY`). |
| `LLM_THINKING_BUDGET` | `None` (opcional, int) | Configura `types.ThinkingConfig(thinking_budget=...)` no `gemini` (`0` desativa *thinking*). |
| `LLM_NUM_CTX` | `None` (opcional, int) | Enviado via `extra_body={"options": {"num_ctx": ...}}` no `ollama` (ex.: `8192`). |
| `LLM_THINK` | `None` (opcional, bool) | Enviado via `extra_body={"think": ...}` no `ollama` (ex.: `false` para GPUs de 8 GB VRAM). |

---

## 2. Schemas Técnicos Pydantic v2 ([pipeline/models_v4.py](pipeline/models_v4.py))

Todos os modelos utilizam timestamps padrão em **ISO-8601 UTC** (`datetime.now(timezone.utc).isoformat()`). Os tipos `Literal` (`LinhaPesquisaCode`, `MacroprojetoCode`, `TipoProdutoSlug`, `PublicoAlvoSlug`, `ConfiancaEpistemologica`, `FonteTipoProduto`) implementam a taxonomia definida em [CONTRATO_DADOS.md](CONTRATO_DADOS.md).

1. **Contrato 1 — Manifesto de Pré-Extração (`Stage1ManifestV4`, salvo em `data/stage1_manifest.json`):**
   * `Stage1ManifestV4`: `schema_version="4.0"`, `gerado_em`, `total_registros`, `registros: List[PreExtracaoItemV4]`.
   * `PreExtracaoItemV4`: `id` (`^EPT-[0-9]{4}$`), `coletado_em`, `fonte_profept: FonteProfeptV4` (`titulo_bruto`, `autor_bruto`, `orientador_bruto`, `ano`, `campus="IFC Blumenau"`, `url_dissertacao`, `titulo_produto_bruto`, `handle_educapes`), `arquivos: ArquivosDefesaV4` (`pdf_dissertacao_path`, `sha256_dissertacao`, `pdf_produto_path`, `status_download: "OK" | "ERRO_HTTP" | "CORROMPIDO"`).
2. **Contrato 2 — Payload Determinístico (`ContratoExtracaoDeterministicaV4`, salvo em `data/stage2_payloads/EPT-XXXX.json`):**
   * `MetadadosResolvidos`: `ano`, `autor`, `orientador`, `coorientadores: List[str]`, `instituicao="Instituto Federal Catarinense (IFC)"`, `campus="IFC Blumenau"`, `linha_pesquisa` *(aceita `"LP_INDEFINIDA"`)*, `macroprojeto` *(aceita `"MP_INDEFINIDO"`)*.
   * `DissertacaoDeterministica`: `titulo`, `link`, `palavras_chave`, `autores_referenciados`.
   * `EvidenciasEduCAPES`: `handle_url`, `titulo_produto`, `titulo_produto_bruto`, `data_publicacao`, `autores_colaboradores: List[AutorColaboradorV4]`, `identificadores: List[IdentificadorProdutoV4]`, `colecao_educapes`, `dc_type_educapes`, `palavras_chave_educapes`, `tipo_produto_regex`, `fonte_tipo_regex: Optional[FonteTipoProduto]`, `formato_produto_regex`, `fonte_formato_regex: Optional[FonteTipoProduto]`. (`AutorColaboradorV4` e `IdentificadorProdutoV4` impõem `ConfigDict(extra="forbid")`).
   * `RecortesTextuais`: `capa`, `ficha_catalografica`, `sumario`, `resumo`, `introducao`, `descricao_produto_na_dissertacao`, `trechos_epistemologicos: List[TrechoEpistemologico]` (`secao`, `pagina`, `texto`, `citacoes_detectadas`), `referencias_filtradas`.
3. **Contrato Intermediário da LLM (`RespostaInterpretativaLLM`):**
   * `macroprojeto: MacroprojetoCode`, `produto_titulo`, `produto_tipo: TipoProdutoSlug`, `produto_formato: Optional[str]`, `produto_publico_alvo: List[PublicoAlvoSlug]`, `produto_nivel_aplicacao`, `base_epistemologica: BaseEpistemologicaLLM` (`valor`, `candidato`, `confianca`, `justificativa` `<= 2` frases, `evidencias: List[EvidenciaCurtaLLM]` com `trecho_curto` `<= 180` chars).
4. **Contrato 3 — Registro Final e Envelope Publicado (`ContratoDefesaV4` e `PainelEptV4Output`):**
   * `ContratoDefesaV4`: `schema_version="4.0"`, `id`, `ano`, `autor`, `orientador`, `coorientadores`, `instituicao`, `campus`, `linha_pesquisa: LinhaPesquisaCode`, `macroprojeto: MacroprojetoCode`, `dissertacao: DissertacaoFinalV4` (com `base_epistemologica: BaseEpistemologicaV4` incluindo `revisao_pendente: bool` e `curado_humano: bool = False`), `produto: ProdutoFinalV4` (`titulo`, `tipo`, `formato`, `link`, `publico_alvo`, `nivel_aplicacao`, `palavras_chave`, `data_publicacao`, `autores_colaboradores`, `identificadores`, `proveniencia: ProvenienciaProdutoV4`), `indice_busca: IndiceBuscaV4`.
   * `PainelEptV4Output`: `schema_version="4.0"`, `gerado_em`, `total_defesas`, `total_producoes`, `defesas: List[ContratoDefesaV4]`.

---

## 3. Especificação Técnica por Módulo

### 3.1. Etapa 1 — Coleta e Pré-Extração ([pipeline/step1_collect.py](pipeline/step1_collect.py))

* **Fonte e TLS:** Consulta `https://profept.ifc.edu.br/wp-json/wp/v2/pages?slug=dissertacoes` com `SSL_VERIFY = False` e supressão de `InsecureRequestWarning` (contornando cadeia SSL intermediária incompleta no domínio institucional).
* **Parser sequencial independente de DOM (`extrair_defesas_do_html`):** Percorre tags em fluxo contínuo ignorando listas `<ul>`/`<li>` mal aninhadas, delimita cada defesa por `Acadêmico/Discente/Autor:`, resolve o ano via cabeçalhos `DEFESAS 20XX` com fallback regex na URL do PDF (`/uploads/sites/54/YYYY/`) e preserva `titulo_produto_bruto` e `handle_educapes`. Reutiliza `formatar_nome_proprio`, `limpar_prefixo_orientador` e `normalizar_chave_busca` de `pipeline/normalizers.py`.
* **Estabilidade multi-referência de IDs (`carregar_mapeamento_ids_existentes`):** Consulta em ordem de prioridade `[data/stage1_manifest.json, dist/painel-ept-v4.json, painel-ept-v3.json]`, preservando o primeiro ID mapeado por URL ou autor normalizado e numerando novas defesas em ordem cronológica (`reversed(fontes)`).
* **Download e integridade:** Reaproveita PDFs locais válidos (`st_size > 1024` e assinatura `b"%PDF-"`), valida assinatura mágica via streaming e calcula `SHA-256`.
* **CLI:** `--saida`, `--pdfs-dir`, `--ref-ids`.

### 3.2. Catálogos Externos, Extratores Modulares e Etapa 2 ([pipeline/resources/](pipeline/resources), [pipeline/catalogs.py](pipeline/catalogs.py), [pipeline/extractors/](pipeline/extractors) e [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py))

* **Catálogos declarativos ([pipeline/resources/](pipeline/resources) + [pipeline/catalogs.py](pipeline/catalogs.py)):** Tabelas taxonômicas (`taxonomia.json`), filtros/aliases de pessoas (`pessoas.json`) e stopwords/aliases bibliográficos sem duplicação literal (`referencias.json`) são carregados via `json.loads` com `@lru_cache` e expostos como coleções imutáveis (`frozenset`, `tuple`, `dict`) em `catalogs.py`.
* **Classificadores ([pipeline/extractors/classifiers.py](pipeline/extractors/classifiers.py)):** `detectar_macroprojeto_e_linha` (varredura em texto limpo/condensado com filtro de contexto para `.mp4` e vínculo via `MP_PARA_LP` de `catalogs.py`), `classificar_produto_com_fonte` / `classificar_produto_regex` (distinguindo `"dissertacao_ficha"` de `"educapes_dc_type"`) e `classificar_formato_produto_com_fonte` + `extrair_contexto_produto` (extração ancorada do formato específico priorizando o resumo e a descrição da dissertação/título sobre `dc_type_educapes`).
* **Metadados preliminares ([pipeline/extractors/metadata.py](pipeline/extractors/metadata.py)):** `extrair_coorientador` (rótulos com dois-pontos em `paginas[:5]` + ficha ABNT, continuação de linha, limpeza de titulações via `normalizar_nome_orientador` e deduplicação contra `orientador` principal) e `extrair_palavras_chave_resumo` (suporte a separadores `;`, `.` ou `,`).
* **Isolamento de seções ([pipeline/extractors/pdf_sections.py](pipeline/extractors/pdf_sections.py)):** `ler_paginas_pdf` (PyMuPDF + `normalizar_espacos`) e `isolar_secoes_pdf` → `(RecortesTextuais, texto_refs)` decomposto em auxiliares por região (`_extrair_pre_textuais`, `_localizar_introducao`, `_coletar_secoes_referencias`, `_extrair_descricao_produto`, `_extrair_trechos_epistemologicos`, `_filtrar_referencias_citadas`), ignorando sumários/continuações sem pontilhado (`_eh_pagina_sumario`) e delimitando fronteiras pós-textuais com verificação de densidade bibliográfica (`_pagina_tem_indicio_bib`).
* **Scraping eduCAPES ([pipeline/extractors/educapes.py](pipeline/extractors/educapes.py)):** Separa I/O/cache (`coletar_evidencias_educapes` em `data/cache_educapes/`) do parsing HTML Dublin Core (`_extrair_metadados_html_educapes`), deduplicando `<meta>` e `<table>` e preenchendo `tipo_produto_regex` e `formato_produto_regex`.
* **Orquestrador Etapa 2 ([pipeline/step2_deterministic.py](pipeline/step2_deterministic.py)):** Mantém apenas a orquestração do manifesto (`executar_etapa2`), CLI (`--manifesto`, `--saida-dir`, `--cache-dir`, `--id`) e re-exports públicos de compatibilidade (`__all__`).

### 3.3. Normalizadores e Referências ABNT ([pipeline/normalizers.py](pipeline/normalizers.py) e [pipeline/references.py](pipeline/references.py))

* **Normalização geral ([pipeline/normalizers.py](pipeline/normalizers.py)):**
  * *Texto e Unicode:* `remover_acentos` (NFKD), `limpar_texto`, `normalizar_espacos`, `normalizar_chave_busca` e `normalizar_texto_busca`.
  * *Pessoas e Docentes:* `formatar_nome_proprio`, `limpar_nome_pessoa` (remove filiações, pontuação e titulações via `TITULACOES_PESSOA_RE`, inclusive sem espaço ou com dois-pontos após ponto), `normalizar_nome_orientador` (`ALIASES_DOCENTES`) e `limpar_prefixo_orientador`.
  * *Conteúdo e Taxonomia:* `limpar_palavras_chave`, `limpar_resumo_publico`, `normalizar_base_epistemologica`, `normalizar_nivel_aplicacao` e `normalizar_formato_produto`.
* **Domínio de Referências Bibliográficas ([pipeline/references.py](pipeline/references.py)):**
  * *Extração ABNT (`extrair_autores_referencias`):* reconstrói entradas multilinhas (`_reconstruir_entradas_referencias`) exigindo evidência estrutural da obra (`INDICIO_ENTRADA_REF_RE`), extrai nomes completos em ordem natural com coautores (`;`, `&`, `,` e `e SOBRENOME,`), descarta entidades/substantivos comuns (`STOPWORDS_ENTIDADE_REF` e `STOPWORDS_TOKEN_NAO_PESSOA`), preserva agnomes e sobrenomes compostos e deduplica intradocumento.
  * *Normalização e reconciliação (`normalizar_autor_referencia` e `reconciliar_autores_referenciados`):* normaliza espaçamento entre iniciais e aliases (`ALIASES_AUTORES_REFERENCIA`), convergindo em 4 passos determinísticos (aliases explícitos, equivalência sem acentos/preposições, expansão inequívoca de nomes do meio e resolução inequívoca de iniciais preservando homônimos ambíguos).

### 3.4. Cliente Modular de LLM ([pipeline/llm_provider.py](pipeline/llm_provider.py))

* Ancora `.env` em `PROJECT_ROOT / ".env"`, resolve credenciais pelo nome da variável em `env_key` (sem vazar segredos em exceções), remove `additionalProperties` e expande `$defs`/`$ref` para compatibilidade entre Gemini OpenAPI Schema (`_limpar_schema_gemini`) e endpoints OpenAI-compatíveis (`_resolver_refs_schema`, usando `strict: True` em `groq`/`mistral`/`ollama` e `json_object` no `openrouter`), com retry exponencial que relança imediatamente na última tentativa em caso de `RateLimitError`.

### 3.5. Etapa 3 — Inferência, Hidratação e Sync ([pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) + [pipeline/SKILL.md](pipeline/SKILL.md))

* `montar_prompt_enxuto` envia apenas os recortes necessários (incluindo `linha_pesquisa_pre_detectada`, `tipo_sugerido_regex` e `formato_sugerido_regex`, sem trafegar `autores_referenciados`).
* `montar_registro_final` impõe `MP → LP`, aplica `normalizar_base_epistemologica` + trava de confiança (`confianca == "alta"`), limpa o resumo público, normaliza `nivel_aplicacao` e `produto.formato` (`normalizar_formato_produto`), preserva `rotulo_original_declarado`, diferencia as 3 fontes de tipologia e constrói `indice_busca` (incluindo `base_epistemologica.valor`, `produto.formato`, `autores_referenciados` e `coorientadores`).
* `executar_etapa3` opera com `sobrescrever=False` por padrão e protege registros com `curado_humano=True` (exigindo `--forcar-curados`).
* `ressincronizar_registros_deterministico` (`--sync-deterministico`) propaga atualizações determinísticas da Etapa 2 e normalizadores para `data/records/` sem chamadas LLM e sem alterar decisões de curadoria humana.

### 3.6. Etapa 4 — Curadoria e Compilação ([pipeline/step4_compile.py](pipeline/step4_compile.py))

* `aplicar_curadoria_csv` importa decisões `APROVADO` e `MANTER_NULO` do CSV (inferindo `APROVADO` se `base_epistemologica_aprovada` estiver preenchida), normaliza termos via `normalizar_base_epistemologica`, marca `curado_humano = True` e recalcula `indice_busca`.
* `compilar_pipeline_v4` executa `reconciliar_autores_referenciados` sobre todo o conjunto de registros (atualizando `indice_busca` e `data/records/` de forma idempotente quando há unificações entre defesas), valida todos os registros com `PainelEptV4Output`, grava `dist/painel-ept-v4.json` e atualiza (ou remove se vazio) `dist/revisao_epistemologica_pendente.csv`.
* **CLI:** `--records-dir`, `--dist-dir`.

### 3.7. Frontend e Build Elementor ([index.html](index.html) + [frontend/](frontend) → [dist/widget-elementor.html](dist/widget-elementor.html))

* **Modularização, Empacotamento e Deploy GitHub Pages (`FE-26`, `FE-29`):** O desenvolvimento é dividido entre [index.html](index.html) (~237 linhas de preview HTML5 + `<section id="leme-painel-ept">` com `#leme-graficos-filtros`, switch de formato e card dedicado de formatos), [frontend/styles.css](frontend/styles.css) (CSS consolidado e 100% escopado em `#leme-painel-ept`) e [frontend/app.js](frontend/app.js) (`92` funções em Vanilla JS). O script [scripts/build_frontend.py](scripts/build_frontend.py) (`--check`) extrai o `<section>` por profundidade de tags, minifica CSS preservando combinadores descendentes (`#leme-painel-ept :focus-visible`), compacta HTML/JS removendo comentários e todas as linhas em branco (`0` `\n\n` e `0` CRLF, prevenindo injeção de `<p>`/`<br>` pelo `wpautop`), executa validação léxica/estrutural e gera [dist/widget-elementor.html](dist/widget-elementor.html) (~158,2 KB bruto / ~33,5 KB gzip). Em produção, o workflow [.github/workflows/pages.yml](.github/workflows/pages.yml) (branch `main`) valida `--check` e publica apenas os artefatos públicos no GitHub Pages, enquanto [dist/loader-elementor.html](dist/loader-elementor.html) busca o widget publicado e reexecuta o `<script>` nativamente.
  * **Regra de Deploy no Elementor:** colar `dist/loader-elementor.html` (ou `dist/widget-elementor.html` estático) **exclusivamente no Widget HTML (`</>`)** nativo do Elementor — **nunca** no widget **Editor de Texto** (TinyMCE/`wpautop` corrompe tags e entidades).
* **Resolução de Dados e Domínio (`FE-03..05`, `FE-10`, `FE-15..16`, `FE-30`):** Prioriza `data-json-url-local` (`./dist/painel-ept-v4.json`) em `localhost`/`127.0.0.1`/`file:` com fallback para `data-json-url` (GitHub Pages em produção); traduz todos os slugs via `I18N`; enriquece `texto_busca_normalizado` com rótulos traduzidos, `formato_produto`, instituição/campus e coorientadores (`extrasBusca`); formata instituição/campus sem siglas duplicadas; exibe `base_epistemologica` em 3 estados explícitos (com selo `"Validado por curadoria"`, `"Em curadoria"` sem vazar `candidato`, ou `"Não declarada explicitamente"`); expõe `formato_produto` em badge/coluna de tabela (`produtos`), no modal de detalhes e na exportação `.CSV` (`produtos` e `todas`); e agrupa evidências/proveniência em `<details>` recolhido no modal.
* **Dashboard BI, Índice de 11 Facetas, Seleção Múltipla, Formato de Produto e Coorientação Autônoma (`FE-22..25`, `FE-27..28`, `FE-30`):**
  * Grade compacta **`3 × 3`** em desktop `>= 1080px` para `todas` (`3 × 2` em `dissertacoes`, **`2 + 3`** em `produtos` via `.is-scope-produtos` de 6 trilhas com 2 superiores `.is-produtos-half` `span 3` e 3 inferiores `span 2` terminando em `Formato do produto` à direita; 2 colunas em `721–1079px` com reset `grid-column: auto`; 1 coluna em `<= 720px`), com animações estilo BI via reconciliação de DOM por `dataset.barKey` (`scaleX`, `height`, `width`) e truncamento com reticências (`FE-27`: `grid-template-columns: minmax(0, 1fr)` em `.leme-bars`/`.leme-composition-legend` e `min-width: 0; overflow: hidden; text-overflow: ellipsis` em rótulos de barras, composição, anos, abas e cards de destaque, preservando o texto integral em `title`).
  * Índice facetado em memória (`indiceFacetas` / `construirIndiceFacetas`) cobrindo **11 facetas** (`ano`, `linha_pesquisa`, `macroprojeto`, `orientador`, `coorientador`, `base_epistemologica`, `autor_referenciado`, `tipo_produto`, `formato_produto`, `publico_alvo`, `nivel_aplicacao`) com estado unificado `filtrosSelecionados` (`Map<campo, Set<valor>>`) e seleção múltipla (`FE-28`): lógica **OU** intra-faceta (`obterUniaoIndicesFaceta`) e **E** entre facetas (`intersecarSets`); facetamento disjuntivo por gráfico (`obterListaGraficoFaceta`) mantendo itens irmãos visíveis com atenuação WCAG AA (`.is-filtered`); promoção de selecionados fora do Top N / `"Outras"`; barra compacta `#leme-graficos-filtros` (`:empty` oculto) espelhada em `#leme-filtros-ativos` com remoção unitária (`data-clear-filter-campo` + `data-clear-filter-valor`), incluindo chip próprio `"Formato do produto: ..."`; sincronização dos 8 `<select>` via `MULTI_SELECT_SENTINEL` (`"N selecionados"`, prefixo `✓` e contagem exata sem dupla contagem em `publico_alvo`); e mini-switch **`Tipo (CAPES)` | `Formato`** exclusivo no escopo `todas` (`renderCardTipoProduto`, oculto em `produtos` onde `Formato do produto` tem card próprio).
  * **Coorientação autônoma (`FE-25`):** contabilizada separadamente de `orientador` principal, acessível via mini-toggle **`Orientação` | `Coorientação (N)`** no card, subtexto `#leme-stat-coorientadores` em `.leme-stats`, busca textual, chip próprio `"Coorientador: ..."` (mantendo os 8 `<select>` em `.leme-filters`) e aba própria + CSV no modal.
  * **Modais expansíveis de ranking (`FE-24`, `FE-28`, `FE-30` — `abrirModalRanking` / `RANKING_CONFIGS`):** botão `"Ver todos"` nos cards de *Autores mais referenciados* (corte inicial adaptável `≥ 5`), *Orientadores / Coorientadores* (corte inicial `Todos` com alternador interno) e *Formatos de produto* (`RANKING_CONFIGS.formato_produto`, corte inicial `Todos`, CSV `ranking-formatos-produto-leme-ept.csv`, acionável tanto pela aba `Formato` do switch em `todas` via `#leme-expand-tipo-formato` — oculto em `Tipo (CAPES)` — quanto pelo card dedicado em `produtos` via `#leme-expand-formato`, exibindo Top 10 no card), com pesquisa por nome (+ resgate em `Todos`), pills `Todos / ≥ 2 / ≥ 5 / ≥ 10`, ordenação (`Frequência` / `A–Z`), paginação isolada (`rankingPorPagina = 30` via `data-ranking-pagina`), seleção múltipla contínua sobre base disjuntiva sem fechamento automático (`data-modal-ranking-row` + sincronização *in-place* em `sincronizarEstadoModalRanking` preservando o scroll, com contador e botão `Limpar` inline) e exportação `.CSV` do ranking (`baixarCsvRanking`).
* **Segurança, Acessibilidade (WCAG 2.1 AA) e Performance (`FE-01..02`, `FE-06..09`, `FE-11..14`, `FE-18..21`):** `escapeHtml` com escapes Unicode (`\u0026amp;`..`\u0026#39;`), `sanitizarUrl` (`http:`/`https:` + `rel="noopener noreferrer"`), `csvEscape` anti-*Formula Injection* (`=`, `+`, `-`, `@`, `\t`, `\r`), contraste `>= 4.5:1`, *focus trap* e restauração de foco no modal, fallback automático da Tabela para Cartões em `<= 720px` via `matchMedia`, *fast-path* em `highlightText` e remoção de `backdrop-filter`.
* **Plano Futuro (Otimização de Payload JSON — `Opção C`):** Caso o acervo cresça significativamente, minificar `dist/painel-ept-v4.json` e omitir `indice_busca.texto_busca_normalizado` do arquivo publicado (~34,8% do payload, reduzindo de `~1.171 KB` / `~241 KB` gzip para `~643 KB` / `~159 KB` gzip), reconstruindo o índice textual no boot do frontend em ~3 ms (e avaliar *split* catálogo/detalhes acima de ~400–500 defesas).
