# Changelog — `lemeept` & `lemeept-extractor`

Todas as mudanças notáveis do ecossistema **LEME / ProfEPT** (portal analítico `lemeept` e pacote distribuível `lemeept-extractor`) são documentadas neste arquivo no formato *Keep a Changelog*.

---

## [0.4.1-beta] — Auditoria Anti-Overengineering (Ondas 1–3), Smoke Tests E2E, Performance e UX/Acessibilidade

### Adicionado
* **Smoke tests E2E em navegador real (`tests/test_frontend_smoke.py`):** suíte automatizada com Playwright + Chromium headless (isolada no grupo `dev`), integrada ao CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) e como *gate* bloqueante (`verify`) antes do deploy no GitHub Pages ([.github/workflows/pages.yml](.github/workflows/pages.yml)).
* **Cache incremental por SHA-256 na Etapa 2 (`OPT-02`):** campo `sha256_dissertacao` em `ContratoExtracaoDeterministicaV4` permitindo pular reextração de PDFs inalterados (com flag `--forcar` em `lemeept-extractor extract` para reprocessamento integral) e helper leve `extrair_capa_e_ficha` para ingestão local.
* **Animação FLIP de reordenação nos rankings e chip de estado vazio:** gráficos horizontais (`renderHorizontalChart`) animam transições verticais de posição (`.is-reordering`, respeitando `prefers-reduced-motion: reduce`), e os painéis de filtros exibem o indicador explícito `"Nenhum filtro ativo"` (`.leme-chip-no-filters`) quando não há recortes selecionados.

### Alterado
* **Compactação de ~46% no artefato publicado (`OPT-01`):** `public/painel-ept-v4.json` passa a ser serializado de forma minificada e sem o campo redundante `indice_busca.texto_busca_normalizado` (reconstruído em milissegundos no boot do cliente), reduzindo de `1.361,6 KB` para `737,4 KB` brutos (`309,0 KB` → `193,4 KB` gzip).
* **Simplificação de engenharia (`OE-01`, `OE-03`, `OE-05`, `OE-07`, `FR-05`):** substituição dos ~380 linhas de minificadores/lexers artesanais em `frontend_builder.py` por empacotamento direto `wpautop`-safe; `index.template.html` consolidado como fonte única de `index.html`; unificação dos classificadores de formato/tipologia em `classifiers.py`; validação estrita `ConfigDict(extra="forbid")` em `LemeConfig`; e resolução única de `__version__` (`0.4.1b0`) via `importlib.metadata`.
* **Performance de rede, LLM e UI (`OPT-03`, `OPT-04`, `OPT-06`):** `requests.Session` compartilhada com pool e retry (`obter_sessao_http`); `@lru_cache` de schemas JSON e rate-limit baseado em `time.monotonic()` em `llm_provider.py` (provedores consolidados em `gemini`, `openrouter`, `ollama` e `llama`); `Intl.Collator("pt-BR")` único, animações via `requestAnimationFrame` (zero `offsetWidth`), cache `memoBase` entre insights e gráficos, e debounce de `120 ms` na busca do modal de ranking.

### Corrigido e Endurecido (Segurança, Dados e WCAG 2.2 AA)
* **Escrita atômica e segurança (`FR-01..04`, `BUG-03`, `BUG-07`):** gravação atômica via arquivo temporário + `os.replace` em todos os estágios e downloads de PDF; detecção de `;`/`,`, validação de cabeçalho, rejeição de `"---"` e proteção contra *CSV Formula Injection* / *path traversal* na curadoria; escape de `</script>` e fallback seguro no `loader-elementor.html`; prevenção de colisão intra-lote em `resolver_id_estavel` e códigos de saída não-zero em falhas de lote.
* **Precisão bibliométrica (`BUG-01..02`, `BUG-04..06`, `BUG-08..10`, `EC-01..02`, `EC-04`, `EC-07`, `EC-12`):** janelas centradas nos matches epistemológicos e inclusão de `Aprendizagem Significativa` e `Teoria Crítica`; normalização de chaves em `catalogs.aplicar_overlay`; suporte a composições canônicas (`phc`, barras e `" e "` internos); parser ABNT para prenomes hifenizados (`Jean-Paul`), prenomes curtos ALL-CAPS (`ANA`, `RUI`), sobrenomes `DELLA FONTE`/`CÂMARA`, citações múltiplas com `;` e `LUKÁCS`; `--limite` incremental na Etapa 3, `json.dumps` no prompt OpenRouter e sem retry em erros 4xx; guarda anti-`MP3` (áudio), `Profa. Dra.`, `"Referências bibliográficas"`, deduplicação eduCAPES, handles crus/`&show=full`, `"Ma Li"`, `"Mestre"`/`"Mestra"` e `D'Avila`/`Silva-Santos`.
* **Acessibilidade e frontend (`FR-08`, `BUG-11..16`, `EC-08`):** alvos táteis elevados para `>= 24×24px` (WCAG 2.2 AA), `tabindex="-1"` em `#leme-controles`, `Escape` progressivo em `#leme-ranking-busca` (limpa busca antes de fechar o modal), fallback de foco em `fecharModal()`, denominador/rótulos corretos para `formato_produto` no modal de ranking, período sem repetição em acervo de ano único e revogação assíncrona de `Blob URL` no export CSV.

---

## [0.4.0-beta] — Pre-release: Universalização da Pipeline, Empacotamento PyPA (`lemeept-extractor`) e Auditoria Integral

### Resumo da Pipeline Universalizada (`lemeept-extractor`)

A partir da versão **`0.4.0-beta`**, o motor bibliométrico originalmente construído para o ProfEPT do IFC Campus Blumenau passa a ser distribuído como o pacote Python universal e instalável **`lemeept-extractor`** (`pip` / `uvx`, Python `>=3.12`), completamente desacoplado da instância de origem:

1. **Entrada agnóstica (`ingest`):** além do coletor institucional específico do IFC ([collectors/ifc_blumenau.py](collectors/ifc_blumenau.py), mantido fora do pacote), qualquer instituição da Rede ProfEPT ou outro programa de pós-graduação pode iniciar a pipeline a partir de um **CSV simples** (`--csv`, baixando links HTTP ou validando PDFs locais com `%PDF-` + `SHA-256`) ou diretamente de um **diretório local de PDFs** (`--pdfs-dir`, com extração preliminar automática de capa e ficha catalográfica), preservando identificadores estáveis (`EPT-XXXX`).
2. **Modo Somente Dissertações (`--somente-dissertacoes` / `sem_produto=true`):** programas ou acervos sem produto educacional vinculado executam as Etapas 1 a 4 sem buscar/inferir produto (`produto: null`), com contrato LLM reduzido (`RespostaInterpretativaDissertacaoLLM`), cálculo consistente (`total_producoes = total_defesas + defesas_com_produto`) e renderização defensiva no frontend BI.
3. **Configuração declarativa por instituição (`lemeept.toml`):** catálogos genéricos base (`taxonomia.json`, `pessoas.json`, `referencias.json`) livres de docentes e topônimos locais, extensíveis por `[catalogos]` / `overlay_json`, `[instituicao]`, `[llm]` (`skill_path`) e `[frontend]` via `--config` ou variável `LEMEEPT_CONFIG`.
4. **Extração híbrida e curadoria (`extract` → `llm` → `compile`):** extração determinística modular via `pymupdf`, parsers ABNT e eduCAPES; cliente LLM agnóstico (`gemini`, `groq`, `mistral`, `openrouter`, `ollama` local em 8 GB VRAM) com JSON reduzido, trava de confiança epistemológica e `--sync-deterministico`; e curadoria bidirecional em CSV (`UTF-8-SIG`, `;`) protegida contra sobrescrita.
5. **Gerador universal de painel BI (`build-frontend`):** motor stdlib-only com templates parametrizáveis (`index.template.html` e `loader-elementor.template.html`) que gera site estático completo (`--emit-site`), valida e compacta o widget autocontido `wpautop`-safe para Elementor (`--check --emit-loader`).

### Adicionado
* Novo pacote PEP 621 `lemeept-extractor` (`0.4.0b0`, `hatchling`, `src-layout` em `src/lemeept_extractor/`) com CLI unificada (`ingest`, `extract`, `llm`, `compile`, `build-frontend`).
* Módulo `lemeept_extractor.stages.ingest` e utilitários compartilhados em `lemeept_extractor.io_utils`.
* Sistema declarativo de configuração `lemeept_extractor.config` (`lemeept.toml`, overlays JSON de catálogos e `usar_config` isolado).
* Templates parametrizáveis de frontend (`src/lemeept_extractor/templates/frontend/`) compartilhando `styles.css` e `app.js` no wheel via `force-include` sem duplicação no Git.
* Pipeline de CI automatizada ([.github/workflows/ci.yml](.github/workflows/ci.yml)) em matriz Python `3.12`/`3.14` com lint (`ruff`), compilação, 36 testes unitários, validação do frontend/JSON v4, auditoria do `.whl` e *smoke test* da CLI em venv isolado.
* Artefatos de distribuição e citação acadêmica: [LICENSE](LICENSE) (MIT), [CITATION.cff](CITATION.cff) (pronto para GitHub/Zenodo DOI) e [CHANGELOG.md](CHANGELOG.md).

### Alterado
* Reorganização arquitetural completa: código do pacote universal em `src/lemeept_extractor/` (`stages/`, `extractors/`, `resources/`, `templates/`), coletor específico do IFC Blumenau isolado em `collectors/ifc_blumenau.py`, documentação técnica consolidada em `docs/` e separação estrita entre artefatos web (`public/`) e artefatos de build Python (`dist/` ignorado no Git).
* `requires-python` ampliado para `>=3.12` (mantendo compatibilidade total até `3.14`).
* `frontend/app.js` atualizado com guarda defensiva para `produto: null` (`tem_produto`, `contarProducoesLista`) e remoção genérica de siglas institucionais em `formatarInstituicaoCampus`.
* Suíte expandida para **36 testes unitários offline** em [tests/test_lemeept.py](tests/test_lemeept.py).

### Corrigido
* Corrigido erro crítico em `_chamar_gemini` (`llm_provider.py`) onde `config` não era instanciado com `types.GenerateContentConfig` nem conectado a `LLM_THINKING_BUDGET`, além de fallback seguro para `LLM_PROVIDER`.
* Eliminado bug de geração de arquivo PDF órfão em `ingerir_de_diretorio_pdfs(..., copiar_pdfs=True)` ao reutilizar IDs existentes.
* Corrigido escape de atributos HTML com aspas (`quote=True`) na renderização dos templates de frontend e isolamento da variável `LEMEEPT_CONFIG` em `cli.py` via `try/finally`.

### Notas de Migração (Instância IFC Blumenau / Elementor)
* Os artefatos web publicados passaram de `dist/` para `public/` ([public/painel-ept-v4.json](public/painel-ept-v4.json), [public/widget-elementor.html](public/widget-elementor.html), [public/loader-elementor.html](public/loader-elementor.html)).
* Após publicar esta versão na branch `main`, **atualize uma única vez o snippet no Widget HTML (`</>`) do Elementor** com o conteúdo de [public/loader-elementor.html](public/loader-elementor.html) (nova URL `/public/widget-elementor.html`).
* O coletor específico do IFC Blumenau saiu da CLI universal e passa a ser acionado explicitamente por `uv run python collectors/ifc_blumenau.py`.
