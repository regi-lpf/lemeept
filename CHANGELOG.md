# Changelog — `lemeept` & `lemeept-extractor`

Todas as mudanças notáveis do ecossistema **LEME / ProfEPT** (portal analítico `lemeept` e pacote distribuível `lemeept-extractor`) são documentadas neste arquivo no formato *Keep a Changelog*.

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
