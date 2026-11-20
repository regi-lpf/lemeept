# Painel Bibliométrico LEME / ProfEPT (v4)

Repositório da pipeline de coleta, extração híbrida (determinística + LLM), curadoria epistemológica e visualização bibliométrica das defesas do Mestrado Profissional em Educação Profissional e Tecnológica (**ProfEPT — IFC Campus Blumenau**).

## Documentação do Projeto

- **[DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md):** Referência técnica completa dos módulos, contratos Pydantic v2 (`pipeline/models_v4.py`), normalizadores, provedores LLM e operação da Pipeline v4.
- **[AUDITORIA_E_REFATORACAO.md](AUDITORIA_E_REFATORACAO.md):** Auditoria técnica e registro das refatorações executadas (`AUD-01` a `AUD-25` na pipeline e `FE-01` a `FE-26` no frontend).
- **[ARQUITETURA.md](ARQUITETURA.md):** Visão resumida da arquitetura em 4 etapas e regras de governança.
- **[CONTRATO_DADOS.md](CONTRATO_DADOS.md):** Definições conceituais originais de domínio CAPES (Linhas, Macroprojetos, 9 Tipos de Produto e Públicos-Alvo).
- **[RELATORIOS.md](RELATORIOS.md):** Histórico consolidado de desenvolvimento da v4.

## Fluxo da Pipeline v4 (`pipeline/`)

```text
API WordPress ProfEPT + PDFs + eduCAPES
  ├── Etapa 1 (step1_collect.py)       -> data/stage1_manifest.json + pdf/dissertacoes/
  ├── Etapa 2 (step2_deterministic.py) -> data/stage2_payloads/EPT-*.json
  ├── Etapa 3 (step3_llm_extract.py)   -> data/records/EPT-*.json
  └── Etapa 4 (step4_compile.py)       <-> dist/revisao_epistemologica_pendente.csv
                                       -> dist/painel-ept-v4.json -> index.html (+ frontend/*) -> dist/widget-elementor.html
```

## Ambiente e Execução

O projeto utiliza Python `>=3.14` gerenciado com `uv`. Crie/sincronize o ambiente e copie `.env.dev` para `.env` caso vá executar chamadas LLM na Etapa 3:

```bash
uv sync
cp .env.dev .env
```

Execute as etapas a partir da raiz do repositório:

```bash
# Etapa 1: Coleta manifesto e baixa novos PDFs
uv run python -m pipeline.step1_collect

# Etapa 2: Extração determinística (PDFs locais + cache/scraping eduCAPES)
uv run python -m pipeline.step2_deterministic

# Etapa 3 (modo incremental padrão — não sobrescreve registros já processados)
uv run python -m pipeline.step3_llm_extract

# Etapa 3 (ressincronização determinística sem chamar LLM e preservando curadoria)
uv run python -m pipeline.step3_llm_extract --sync-deterministico

# Etapa 4: Importa revisões do CSV (se houver) e compila dist/painel-ept-v4.json
uv run python -m pipeline.step4_compile
```

Para filtrar um registro específico durante testes ou reprocessamento, utilize `--id EPT-0001` nas Etapas 2 e 3. Na Etapa 3, o reprocessamento via LLM de registros existentes requer `--sobrescrever` (e `--forcar-curados` para substituir registros já revisados por humanos).

## Curadoria Humana

1. Abra [dist/revisao_epistemologica_pendente.csv](dist/revisao_epistemologica_pendente.csv) (UTF-8-SIG, delimitador `;`).
2. Preencha `base_epistemologica_aprovada` com um termo canônico e ajuste `status_curadoria` para `APROVADO` ou `MANTER_NULO`.
3. Execute `uv run python -m pipeline.step4_compile` para persistir as decisões em `data/records/` (marcando `curado_humano: true`) e regenerar `dist/painel-ept-v4.json`.

## Visualização Local e Deploy no Elementor (`index.html` → `dist/widget-elementor.html`)

Os fontes do frontend estão separados em [index.html](index.html) (HTML5), [frontend/styles.css](frontend/styles.css) e [frontend/app.js](frontend/app.js) para teste direto via servidor HTTP local (o legado v3 permanece em [index-v3.html](index-v3.html)):

```bash
python3 -m http.server 8000
```

Acesse `http://localhost:8000/index.html` (em `localhost`, prioriza `./dist/painel-ept-v4.json` via `data-json-url-local`; em produção, usa `data-json-url`). Para gerar e validar o artefato único de produção:

```bash
python3 scripts/build_frontend.py
```

> **Atenção ao colar no Elementor / WordPress:** utilize **exclusivamente o Widget HTML (`</>`)** com o conteúdo de [dist/widget-elementor.html](dist/widget-elementor.html). **Nunca** cole no widget **Editor de Texto**, pois o TinyMCE/`wpautop` altera tags e entidades HTML e quebra os scripts do painel.

Recursos principais do widget v4:
- **Dashboard interativo compacto (*cross-filtering*) e índice facetado:** grade `3 × 3` compacta em tela cheia (`2 × 2` em *Produtos*), animações estilo BI por reconciliação de DOM e índice em memória de **10 facetas**; clique (ou acione via teclado) qualquer barra, coluna de ano, segmento de linha ou card de destaque para adicionar/remover filtros.
- **Coorientação autônoma:** mini-toggle **`Orientação` | `Coorientação (N)`** no card de Orientadores (com subtexto dedicado em `.leme-stats`, filtro por busca ou clique e contagem isolada dos orientadores principais).
- **Modais de ranking completo (`Ver todos`):** expanda os cards de *Autores mais referenciados* (`≥ 5`) e *Orientadores / Coorientação* (`Todos`, com abas internas) para pesquisar por nome, alternar cortes (`Todos`, `≥ 2`, `≥ 5`, `≥ 10`), ordenar, paginar (`30` itens/pág.), filtrar fechando o modal e exportar o ranking em `.CSV`.
- **Escopos e ordenação:** alterne entre *Todas*, *Dissertações* e *Produtos Educacionais*, ordene por ano/título/autor e alterne entre Cartões e Tabela (com botão *Ver detalhes* e fallback responsivo abaixo de `720px`).
- **Modal e metadados v4:** exibe `base_epistemologica` (consolidadas vs. *Em curadoria*), autores referenciados e bloco recolhível (`<details>`) com evidências textuais e proveniência eduCAPES.
- **Pronto para Elementor / WordPress:** [dist/widget-elementor.html](dist/widget-elementor.html) empacotado sem linhas em branco, com CSS escopado em `#leme-painel-ept`, sanitização XSS/URL, `.CSV` anti-*Formula Injection* e acessibilidade WCAG 2.1 AA.

## Testes Automatizados

```bash
uv run python -m py_compile pipeline/*.py tests/*.py scripts/build_frontend.py
uv run python -m unittest discover -s tests -v
python3 scripts/build_frontend.py --check
```
