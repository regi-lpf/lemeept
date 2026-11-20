# Painel Bibliométrico LEME / ProfEPT (v4)

> **Escopo deste documento:** Porta de entrada do repositório e guia rápido de operação (instalação, execução CLI das 4 etapas, curadoria humana via CSV, preview local, geração do bundle para Elementor e execução de testes).

Repositório da pipeline de coleta, extração híbrida (determinística + LLM), curadoria epistemológica e visualização bibliométrica das defesas do Mestrado Profissional em Educação Profissional e Tecnológica (**ProfEPT — IFC Campus Blumenau**).

## Mapa da Documentação (Separação de Responsabilidades)

| Documento | Responsabilidade Única |
| :--- | :--- |
| **[README.md](README.md)** | Guia rápido de setup, comandos CLI, curadoria, preview/deploy no Elementor e testes. |
| **[ARQUITETURA.md](ARQUITETURA.md)** | Visão executiva da arquitetura, fluxo Mermaid, mapa de diretórios/artefatos e regras de governança. |
| **[CONTRATO_DADOS.md](CONTRATO_DADOS.md)** | Especificação de domínio v4, taxonomia CAPES/ProfEPT (Linhas, MPs, 9 Tipos, 5 Públicos, 8 Níveis, 7 Matrizes) e regras de evidência. |
| **[DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md)** | Referência de engenharia: stack, variáveis de ambiente, schemas Pydantic v2 (`pipeline/models_v4.py`) e implementação interna dos módulos e do frontend. |
| **[AUDITORIA_E_REFATORACAO.md](AUDITORIA_E_REFATORACAO.md)** | Registro rastreável das 55 melhorias aplicadas (`AUD-01` a `AUD-25` na pipeline e `FE-01` a `FE-30` no frontend) e backlog futuro. |
| **[RELATORIOS.md](RELATORIOS.md)** | Relatório executivo de resultados do acervo compilado, orçamento empírico de tokens (viabilidade em 8 GB VRAM) e marcos históricos por etapa. |

---

## 1. Ambiente e Instalação

O projeto utiliza Python `>=3.14` gerenciado com `uv`. Sincronize o ambiente virtual (`.venv/`) e configure `.env` caso vá executar chamadas LLM na Etapa 3:

```bash
uv sync
cp .env.dev .env
```

---

## 2. Execução da Pipeline (`pipeline/`)

Execute as etapas a partir da raiz do repositório:

```bash
# Etapa 1: Coleta manifesto WordPress e baixa novos PDFs (preservando IDs estáveis)
uv run python -m pipeline.step1_collect

# Etapa 2: Extração determinística (PDFs locais via PyMuPDF + cache/scraping eduCAPES)
uv run python -m pipeline.step2_deterministic

# Etapa 3 (incremental padrão — processa apenas registros novos; não sobrescreve existentes)
uv run python -m pipeline.step3_llm_extract

# Etapa 3 (ressincronização determinística offline — atualiza dados da Etapa 2 sem chamar LLM e preserva curadoria)
uv run python -m pipeline.step3_llm_extract --sync-deterministico

# Etapa 4: Importa revisões do CSV (se houver), valida contratos Pydantic v2 e compila dist/painel-ept-v4.json
uv run python -m pipeline.step4_compile
```

* **Depuração e reprocessamento pontual:** use `--id EPT-0001` nas Etapas 2 e 3. Na Etapa 3, reprocessar um registro existente via LLM exige `--sobrescrever` (e `--forcar-curados` caso o registro já tenha `curado_humano: true`).

---

## 3. Curadoria Humana (`base_epistemologica`)

1. Abra [dist/revisao_epistemologica_pendente.csv](dist/revisao_epistemologica_pendente.csv) (`UTF-8-SIG`, delimitador `;`).
2. Preencha `base_epistemologica_aprovada` com um termo canônico (ver [CONTRATO_DADOS.md](CONTRATO_DADOS.md)) e defina `status_curadoria` como `APROVADO` ou `MANTER_NULO`.
3. Execute `uv run python -m pipeline.step4_compile` para persistir as decisões em `data/records/` (`curado_humano: true`), atualizar [dist/painel-ept-v4.json](dist/painel-ept-v4.json) e reescrever o CSV apenas com as pendências restantes.

---

## 4. Visualização Local e Deploy no Elementor (`index.html` → `dist/widget-elementor.html`)

Os fontes do frontend ficam separados em [index.html](index.html) (HTML5), [frontend/styles.css](frontend/styles.css) e [frontend/app.js](frontend/app.js):

```bash
# Preview local (prioriza ./dist/painel-ept-v4.json via data-json-url-local em localhost)
python3 -m http.server 8000
```

Acesse `http://localhost:8000/index.html`. Após editar os fontes, gere e valide o artefato autocontido de produção:

```bash
python3 scripts/build_frontend.py
```

> **Deploy no Elementor / WordPress:** em produção via GitHub Pages (publicado a partir da branch `main` por [.github/workflows/pages.yml](.github/workflows/pages.yml)), basta colar uma única vez o snippet [dist/loader-elementor.html](dist/loader-elementor.html) (ou, para colagem estática offline, o bundle completo [dist/widget-elementor.html](dist/widget-elementor.html)) **exclusivamente no Widget HTML (`</>`)** nativo do Elementor. **Nunca** utilize o widget **Editor de Texto**, pois o TinyMCE/`wpautop` injeta tags `<p>`/`<span>`, decodifica entidades HTML e quebra os scripts do painel.

---

## 5. Verificação e Testes Automatizados

```bash
uv run python -m py_compile pipeline/*.py pipeline/extractors/*.py tests/*.py scripts/build_frontend.py
uv run python -m unittest discover -s tests -v
python3 scripts/build_frontend.py --check
```
