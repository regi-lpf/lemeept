# LEME / ProfEPT — Portal Analítico (`lemeept`) & Extrator Universal (`lemeept-extractor`)

> **Escopo deste documento:** Porta de entrada do repositório: arquitetura em duas camadas, guia rápido para adoção em outras instituições/programas, guia operacional da instância IFC Blumenau, build do painel Elementor, testes e empacotamento.

Este repositório abriga dois componentes desacoplados e complementares:

1. **`lemeept` (Instância Bússola LEME / ProfEPT — IFC Blumenau):** o portal web publicado no GitHub Pages e incorporado no WordPress/Elementor ([index.html](index.html), [frontend/](frontend), [public/](public), [collectors/ifc_blumenau.py](collectors/ifc_blumenau.py), [config/ifc_blumenau_catalogos.json](config/ifc_blumenau_catalogos.json) e [lemeept.toml](lemeept.toml)).
2. **`lemeept-extractor` ([src/lemeept_extractor/](src/lemeept_extractor)):** pacote Python distribuível (`pip` / `uvx`, CLI `lemeept-extractor`) que implementa a pipeline bibliométrica agnóstica em 4 etapas + gerador parametrizável do frontend BI, utilizável por qualquer Instituição Associada da Rede ProfEPT ou outro programa de pós-graduação.

---

## Mapa da Documentação

| Documento | Responsabilidade Única |
| :--- | :--- |
| **[README.md](README.md)** | Visão geral do projeto, guias rápidos (outra instituição e instância IFC), Elementor, testes e build. |
| **[CHANGELOG.md](CHANGELOG.md)** | Histórico de versões e resumo executivo da pre-release `v0.4.0-beta` (pipeline universalizada). |
| **[docs/ARQUITETURA.md](docs/ARQUITETURA.md)** | Diagrama de fluxo Mermaid, estrutura modular, mapa de diretórios e regras de governança. |
| **[docs/CONTRATO_DADOS.md](docs/CONTRATO_DADOS.md)** | Taxonomia CAPES/ProfEPT (Linhas, MPs, 9 Tipos, 5 Públicos, 8 Níveis, 7 Matrizes) e regras de evidência. |
| **[docs/DOCUMENTACAO_TECNICA.md](docs/DOCUMENTACAO_TECNICA.md)** | Referência de engenharia: stack, variáveis `.env`, schemas Pydantic v2 (`models.py`), módulos e CI/CD. |
| **[docs/AUDITORIA_E_REFATORACAO.md](docs/AUDITORIA_E_REFATORACAO.md)** | Registro rastreável das auditorias (`AUD-01..33`, `FE-01..32`, `CI-01`) e backlog futuro. |
| **[docs/RELATORIOS.md](docs/RELATORIOS.md)** | Fotografia empírica do acervo compilado (`112` defesas / `224` produções), tokens e marcos por etapa. |

---

## 1. Visão Geral da Pipeline Universal (`lemeept-extractor`)

| Etapa / Subcomando | Função | Entrada Principal | Saída |
| :--- | :--- | :--- | :--- |
| **`ingest`** (`Stage 1`) | Ingestão via CSV ou pasta local de PDFs (preservando IDs `EPT-XXXX`, `%PDF-` e `SHA-256`) | `--csv` ou `--pdfs-dir` | `data/stage1_manifest.json` |
| **`extract`** (`Stage 2`) | Extração determinística (`pymupdf`), recortes textuais, referências ABNT, coorientação e eduCAPES | `data/stage1_manifest.json` + PDFs | `data/stage2_payloads/EPT-XXXX.json` |
| **`llm`** (`Stage 3`) | Inferência semântica enxuta (Gemini, Groq, Mistral, OpenRouter ou Ollama) + `--sync-deterministico` | `data/stage2_payloads/` + `.env` | `data/records/EPT-XXXX.json` |
| **`compile`** (`Stage 4`) | Curadoria humana via CSV, reconciliação global de autores e validação Pydantic v2 | `data/records/` + CSV de revisão | `public/painel-ept-v4.json` |
| **`build-frontend`** | Renderiza templates `[frontend]` e compila bundle autocontido `wpautop`-safe para Elementor | `lemeept.toml` + templates/fontes | `index.html`, `frontend/`, `public/widget-elementor.html`, `public/loader-elementor.html` |

* **Modo somente dissertações (`--somente-dissertacoes` / `sem_produto=true`):** para programas sem produto educacional vinculado, desativa busca/inferência de produto e calcula `total_producoes = total_defesas + defesas_com_produto`.
* **Configuração por instituição (`lemeept.toml`):** centraliza `[instituicao]`, `[catalogos]` (overlays externos de docentes/referências), `[llm]` (`skill_path` opcional) e `[frontend]` (títulos, eyebrow e URLs de produção/local).

---

## 2. Uso em Outra Instituição ou Programa (Pacote Universal)

Requer Python `>=3.12`. Em um diretório próprio da instituição:

```bash
# 1. Instalar o pacote universal (do repositório local, GitHub Release ou wheel)
pip install lemeept-extractor
# ou com uv: uv pip install lemeept-extractor

# 2. (Opcional) Configurar lemeept.toml e .env (chaves LLM para a Etapa 3)
cat > lemeept.toml <<'EOF'
[instituicao]
nome = "Instituto Federal Exemplo (IFE)"
campus = "Campus Central"
sigla = "IFE"
somente_dissertacoes = false

[frontend]
titulo = "Painel Bibliométrico – IFE"
eyebrow = "PROFEPT IFE"
titulo_graficos = "Panorama da Produção"
json_url = "https://exemplo.github.io/painel/public/painel-ept-v4.json"
EOF

# 3. Executar as 4 etapas + geração completa do site/widget
lemeept-extractor ingest --csv acervos.csv
# (ou a partir de PDFs locais sem produto educacional:)
# lemeept-extractor ingest --pdfs-dir ./meus_pdfs --somente-dissertacoes

lemeept-extractor extract
lemeept-extractor llm
lemeept-extractor compile
lemeept-extractor build-frontend --emit-site
```

Com `--emit-site`, o pacote emite `index.html`, `frontend/{styles.css,app.js}`, `public/widget-elementor.html` e `public/loader-elementor.html` já parametrizados para a sua instituição, prontos para GitHub Pages e Elementor.

---

## 3. Operação Local da Instância de Referência (LEME / IFC Blumenau)

```bash
# Ambiente de desenvolvimento
uv sync
cp .env.dev .env

# Etapa 1A (específica do IFC Blumenau, fora do pacote universal)
uv run python collectors/ifc_blumenau.py

# Etapas 2, 3 e 4 via CLI universal (lê ./lemeept.toml automaticamente)
uv run lemeept-extractor extract
uv run lemeept-extractor llm                  # ou --sync-deterministico offline
uv run lemeept-extractor compile
```

* **Depuração pontual:** use `--id EPT-0001` em `extract` e `llm`. Na Etapa 3, sobrescrever registro existente exige `--sobrescrever` (e `--forcar-curados` quando `curado_humano: true`).
* **Curadoria humana (`base_epistemologica`):** edite [public/revisao_epistemologica_pendente.csv](public/revisao_epistemologica_pendente.csv) (`UTF-8-SIG`, `;`), preencha `base_epistemologica_aprovada` e `status_curadoria` (`APROVADO` ou `MANTER_NULO`) e rode `uv run lemeept-extractor compile`.

---

## 4. Preview Local e Deploy no Elementor (`public/`)

```bash
# Preview HTTP local (prioriza ./public/painel-ept-v4.json via data-json-url-local)
python3 -m http.server 8000
```

Após editar [index.html](index.html), [frontend/styles.css](frontend/styles.css) ou [frontend/app.js](frontend/app.js), recompile e valide os artefatos publicados:

```bash
python3 scripts/build_frontend.py --emit-loader
python3 scripts/build_frontend.py --check --emit-loader
```

> **Deploy no Elementor / WordPress:** em produção via GitHub Pages (publicado a partir da branch `main` por [.github/workflows/pages.yml](.github/workflows/pages.yml) em `_site/public/`), cole uma única vez o snippet [public/loader-elementor.html](public/loader-elementor.html) (ou, offline, [public/widget-elementor.html](public/widget-elementor.html)) **exclusivamente no Widget HTML (`</>`)** do Elementor — **nunca** no widget **Editor de Texto** (TinyMCE/`wpautop` corrompe tags e scripts).

---

## 5. Verificação, CI/CD e Empacotamento (`uv build`)

```bash
ruff check --select F,E9,E402,B src/ collectors/ scripts/ tests/
PYTHONPATH=src uv run --no-sync python -m compileall -q src collectors scripts tests
PYTHONPATH=src uv run --no-sync python -m unittest discover -s tests -v
python3 scripts/build_frontend.py --check --emit-loader
uv build
```

O workflow [.github/workflows/ci.yml](.github/workflows/ci.yml) executa essa verificação em matriz Python `3.12`/`3.14`, valida [public/painel-ept-v4.json](public/painel-ept-v4.json) contra `PainelEptV4Output`, audita a inclusão/exclusão do `.whl` em `dist/` e testa a CLI `lemeept-extractor` em ambiente virtual isolado.

---

## 6. Citação Científica e Licença

Licenciado sob **MIT** ([LICENSE](LICENSE)). Se utilizar o portal `lemeept` ou o pacote `lemeept-extractor` em pesquisas ou relatórios institucionais, cite conforme [CITATION.cff](CITATION.cff) (compatível com GitHub Citation e arquivamento com DOI no Zenodo).
