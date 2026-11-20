# Auditoria Técnica e Registro de Refatorações — Pipeline & Frontend v4

> **Escopo deste documento:** Registro rastreável de todas as auditorias e correções aplicadas na pipeline (`AUD-01` a `AUD-25`) e no frontend (`FE-01` a `FE-26`), além do backlog futuro. Para a especificação técnica atual dos módulos, consulte [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md); para resultados empíricos do acervo, consulte [RELATORIOS.md](RELATORIOS.md).

---

## 1. Auditoria e Refatoração da Pipeline (`AUD-01` a `AUD-25`)

### Comparativo de Qualidade do Acervo (Snapshot da Auditoria)

| Métrica do Acervo (`dist/painel-ept-v4.json`) | Pré-Refatoração (Snapshot Inicial) | Pós-Refatoração da Pipeline |
| :--- | :--- | :--- |
| Validação do envelope raiz (`PainelEptV4Output`) | Ausente (validava apenas itens isolados) | **100% validado** (`PainelEptV4Output` + `ContratoDefesaV4`) |
| `dissertacao.autores_referenciados` preenchidos | 77 / 111 (10 dessincronizados entre Etapas 2 e 3) | **108 / 111** *(apenas 3 PDFs sem camada de texto legível: `EPT-0059`, `EPT-0072`, `EPT-0073` — posteriormente 112/112 no compilado atual)* |
| `dissertacao.resumo` limpos (sem `[PÁG. X]`) | 105 / 111 preenchidos (**102** com `[PÁG. X]\n` residual) | **107 / 111** preenchidos (**0** com `[PÁG. X]` residual) |
| `dissertacao.palavras_chave` preenchidas | 87 / 111 | **107 / 111** (100% dos resumos extraídos) |
| Valores distintos em `base_epistemologica.valor` | 44 (incluindo *typos*, `snake_case` e termos livres) | **100% vocabulário canônico** (termos livres rebaixados para revisão pendente) |
| Valores distintos em `produto.nivel_aplicacao` | 21 (Title Case + `snake_case` + genéricos) | **7–8 rótulos canônicos padronizados** |
| `base_epistemologica.valor` em `indice_busca` | Não indexada | **100% indexada e pesquisável** |
| Prevenção de falso positivo `.mp4` em `MP4` | `EPT-0100` classificado como `MP4/LP2` por `"mp4 – um padrao..."` | Filtro contextual anti-extensão `.mp4` em `step2`; divergências sinalizadas no `--sync-deterministico` |
| Suíte de testes automatizados (`unittest`) | 0 testes | **Suíte unitária offline completa** em [tests/test_pipeline_v4.py](tests/test_pipeline_v4.py) |

### Quadro Consolidado dos Achados da Pipeline (`AUD-01` a `AUD-25`)

* **Total:** **25 itens** (**4 Críticos**, **6 Altos**, **9 Médios**, **6 Baixos** — todos **Resolvidos**).

| ID | Sev. | Status | Arquivo(s) | Problema Identificado e Solução Aplicada |
| :--- | :--- | :--- | :--- | :--- |
| `AUD-01` | Crítico | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py) | `OPENAI_COMPAT_PRESETS` guardava o valor do segredo em `"env_key"` e chamava `os.getenv(valor)`. Corrigido para guardar o nome da variável (`"GROQ_API_KEY"`, etc.), com fallback `LLM_API_KEY` e sem expor segredos em `EnvironmentError`. |
| `AUD-02` | Crítico | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py) | Substituído `load_dotenv("../.env")` por `PROJECT_ROOT / ".env"` ancorado via `Path(__file__).resolve().parent.parent`. |
| `AUD-03` | Crítico | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | Alterado default para `sobrescrever=False` e criado `curado_humano: bool = False` em `BaseEpistemologicaV4`, protegendo curadorias humanas contra `--sobrescrever` sem `--forcar-curados`. |
| `AUD-04` | Crítico | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py), [.env.dev](.env.dev) | Implementado preset `mistral` (`MISTRAL_API_KEY`) e removido provedor obsoleto `gonka` de `.env.dev`. |
| `AUD-05` | Alto | **Resolvido** | [pipeline/normalizers.py](pipeline/normalizers.py), [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `normalizar_base_epistemologica` padroniza as 7 matrizes canônicas (+ composições por `" e "`) e move termos não canônicos sem curadoria para `candidato` com `revisao_pendente=True`. |
| `AUD-06` | Alto | **Resolvido** | [pipeline/normalizers.py](pipeline/normalizers.py), [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `normalizar_nivel_aplicacao` converte variantes `snake_case`/livres nos 8 rótulos canônicos de nível de aplicação. |
| `AUD-07` | Alto | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | Criado `ressincronizar_registros_deterministico` (`--sync-deterministico`) para atualizar registros offline com dados da Etapa 2 preservando curadoria e alertando divergências (`EPT-0100`, `EPT-0108`). |
| `AUD-08` | Alto | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py), [pipeline/SKILL.md](pipeline/SKILL.md) | `REGRAS_TIPO_PRODUTO` harmonizada (`podcast`, `ava`, `moodle`, `site`, `blog`, `folder`, `portfólio` → `material_didatico_instrucional`; `software_aplicativo` restrito a software real) + `REGRAS_DC_TYPE_EDUCAPES` para tags não ambíguas. |
| `AUD-09` | Alto | **Resolvido** | [pipeline/SKILL.md](pipeline/SKILL.md) | Prompt reescrito para espelhar `montar_prompt_enxuto` (`linha_pesquisa_pre_detectada`) e `RespostaInterpretativaLLM` (`trecho_curto`, vocabulário canônico). |
| `AUD-10` | Alto | **Resolvido** | [pipeline/step1_collect.py](pipeline/step1_collect.py) | `carregar_mapeamento_ids_existentes` consulta em prioridade `[data/stage1_manifest.json, dist/painel-ept-v4.json, painel-ept-v3.json]` com numeração cronológica. |
| `AUD-11` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | `isolar_secoes_pdf([])` corrigido para retornar tupla `(RecortesTextuais(), "")`. |
| `AUD-12` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | Branch sem `handle_url` de `coletar_evidencias_educapes` unificada com `extrair_sentenca_produto` e `classificar_produto_com_fonte`. |
| `AUD-13` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | Remoção de controle invisível (`\u200b`, `\x01`), `_eh_pagina_sumario`, `_PADRAO_REFS` tolerante a numeração/Title Case e filtro anti-`.mp4` em `detectar_macroprojeto_e_linha`. |
| `AUD-14` | Médio | **Resolvido** | [pipeline/normalizers.py](pipeline/normalizers.py), [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | `limpar_resumo_publico` remove `[PÁG. X]` e cabeçalho `RESUMO`; captura de resumo multi-página e regex `Palavras[\s\-–]+chaves?` com `;`/`.`/`,` ampliaram cobertura para 100% dos resumos legíveis. |
| `AUD-15` | Médio | **Resolvido** | `models_v4.py`, `step2`, `step3` | `classificar_produto_com_fonte` retorna `(tipo, fonte)` diferenciando `"dissertacao_ficha"` de `"educapes_dc_type"`; `titulo_produto_bruto` preservado em `rotulo_original_declarado`. |
| `AUD-16` | Médio | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `construir_indice_busca` passou a indexar `dissertacao.base_epistemologica.valor`. |
| `AUD-17` | Médio | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py), [pipeline/SKILL.md](pipeline/SKILL.md) | `montar_prompt_enxuto` inclui `linha_pesquisa_pre_detectada` e `montar_registro_final` emite warning em caso de divergência. |
| `AUD-18` | Médio | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py), [.env.dev](.env.dev) | Suporte a `LLM_THINKING_BUDGET` (Gemini), `LLM_NUM_CTX`/`LLM_THINK` (Ollama) e default `qwen2.5:7b-instruct`. |
| `AUD-19` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | `extrair_autores_referencias` suporta acentuação maiúscula (`À–Ý`), remove `AGNOMES`, amplia `IGNORAR_ENTRADAS_REF` e preserva sobrenomes compostos. |
| `AUD-20` | Baixo | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | Helpers `_adicionar_unico`, `_adicionar_colaborador_unico` e `_adicionar_identificador_unico` deduplicam `<meta>` e `<table>` do eduCAPES. |
| `AUD-21` | Baixo | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py) | `RateLimitError` verifica `tentativa == max_retries` e relança antes do `time.sleep`. |
| `AUD-22` | Baixo | **Resolvido** | `step1`, `step2`, `llm_provider`, [pyproject.toml](pyproject.toml) | Limpeza de imports/variáveis mortas (`ssl`, `urlparse`, `bloco_busca_mp`), indentação e remoção de `google>=3.0.0`. |
| `AUD-23` | Baixo | **Resolvido** | `step1`–`step4`, [pipeline/models_v4.py](pipeline/models_v4.py) | CLI `argparse` nos 4 módulos, `PainelEptV4Output`, timestamps UTC e padronização de `campus="IFC Blumenau"`. |
| `AUD-24` | Baixo | **Resolvido** | Documentação (`*.md`) | Sincronização de contratos, comandos e limpeza de formatação Markdown. |
| `AUD-25` | Baixo | **Resolvido** | [tests/test_pipeline_v4.py](tests/test_pipeline_v4.py) | Suíte de testes unitários offline cobrindo normalizadores, provedores e Etapas 1–4. |

---

## 2. Auditoria e Refatoração do Frontend (`FE-01` a `FE-26`)

> **Arquitetura e Regra de Deploy no Elementor:** O código-fonte foi modularizado em [index.html](index.html) + [frontend/styles.css](frontend/styles.css) + [frontend/app.js](frontend/app.js) e compilado via [scripts/build_frontend.py](scripts/build_frontend.py) em [dist/widget-elementor.html](dist/widget-elementor.html). **No Elementor, cole o bundle exclusivamente no Widget HTML (`</>`)** — nunca no **Editor de Texto** (TinyMCE/`wpautop` injeta `<p>`/`<span>` e corrompe scripts).

### Resumo Comparativo do Frontend (Antes vs. Depois)

| Aspecto do Frontend | Pré-Refatoração (`index-new.html` / `index.html` v3) | Pós-Refatoração ([index.html](index.html) + `frontend/` → [dist/widget-elementor.html](dist/widget-elementor.html)) |
| :--- | :--- | :--- |
| Estrutura e Empacotamento | Monólito de 4.732 linhas (209 KB) / `index.html` v3 + `index-new.html` | Fontes modulares (`index.html` 204L + `frontend/*`) + bundle validado `dist/widget-elementor.html` (`142 KB` / `30,9 KB` gzip, `0` linhas em branco, `FE-26`) |
| Sanitização HTML, URLs e CSV | `escapeHtml` *no-op* (`<`→`<`) com DOM-XSS e quebra em `EPT-0020`/`EPT-0029`; links/CSV sem proteção | `HTML_ESCAPE_MAP` com escapes Unicode; `sanitizarUrl` (`http:`/`https:` + `rel="noopener noreferrer"`); `csvEscape` anti-*Formula Injection* |
| Orientadores, Coorientação e Campus | `30` entradas com `:`/`.`, coorientação sem métrica/filtro próprio, `"IFC – IFC Blumenau"` | Orientadores consolidados + **`coorientador` como 10ª faceta autônoma** (`FE-25`: toggle no card, subtexto em `.leme-stats`, aba/CSV no modal); `"IFC – Campus Blumenau"` |
| Cobertura do Contrato v4 e Busca | Busca sem rótulos `I18N`/`publico_alvo`; omitia `gerado_em`, `evidencias`, `proveniencia`, `data_publicacao` | Busca enriquecida com `I18N`/`publico_alvo`/`instituicao`/coorientadores; `gerado_em` no topo; `<details>` recolhido no modal |
| Dashboard BI e Rankings (`FE-22..24`) | Apenas barras de autores filtravam (por substring); cards altos; só Top 12/Top 10 visíveis | Grade compacta `3 × 3` (`2 × 2` em `produtos`), animações BI via reconciliação DOM, índice de **10 facetas**, *cross-filtering* nos 9 gráficos + 3 insights e modal `"Ver todos"` com busca, cortes, paginação (`30`/pág.) e CSV |
| Ordenação, Responsividade e WCAG AA | Sem ordenação (2026 no fim); armadilha Tabela em `<= 720px`; contrastes `< 3.5:1` e `backdrop-filter` | Ordenação `ano_desc` padrão + seletor; Tabela com `"Ver detalhes"` e fallback `matchMedia`; contraste `>= 4.5:1`; sem `backdrop-filter` |

### Quadro Consolidado dos Achados do Frontend (`FE-01` a `FE-26`)

| ID | Sev. | Status | Resumo da Solução Aplicada |
| :--- | :--- | :--- | :--- |
| `FE-01` | Crítico | **Resolvido** | Reescrita de `escapeHtml` com `HTML_ESCAPE_MAP` Unicode (`\u0026amp;`..`\u0026#39;`), eliminando DOM-XSS e corrupção por editores HTML. |
| `FE-02` | Crítico | **Resolvido** | `sanitizarUrl` restringe links a `http:`/`https:` com `rel="noopener noreferrer"` em cards, tabela e modal. |
| `FE-03` | Alto | **Resolvido** | `limparNomePessoa` e `consolidarOrientadores` removem pontuação residual (`:`/`.`) e unificam KPI, gráfico e filtro por chave normalizada. |
| `FE-04` | Alto | **Resolvido** | `texto_busca_normalizado` enriquecido no boot com rótulos `I18N`, `publico_alvo`, `instituicao`, `campus` e `coorientadores` (`extrasBusca`). |
| `FE-05` | Alto | **Resolvido** | Exibição de `gerado_em`, 3 estados para `base_epistemologica`, nota de pendências no gráfico e `<details>` recolhido com `base_evidencias` e metadados eduCAPES. |
| `FE-06` | Alto | **Resolvido** | Ordenação padrão `ano_desc` + seletor `#leme-ordenar` (`ano_desc`, `ano_asc`, `titulo_asc`, `autor_asc`). |
| `FE-07` | Alto | **Resolvido** | `csvEscape` anti-*Formula Injection* (`=`, `+`, `-`, `@`, `\t`, `\r`), desabilitação com 0 resultados e inclusão de `autores_referenciados`/`coorientadores`/`data_publicacao`. |
| `FE-08` | Alto | **Resolvido** | Filtro de `"Autores mais referenciados"` migrado para estado dedicado + `<button type="button">` acessível por teclado (unificado em `FE-22`). |
| `FE-09` | Alto | **Resolvido** | Paleta ajustada (`#3b47e5`, `#1f7a49`, `#d62849`, `#b91c3a`, `#526075`) cumprindo contraste `>= 4.5:1` (WCAG 2.1 AA). |
| `FE-10` | Médio | **Resolvido** | `formatarInstituicaoCampus` remove redundância `"IFC – IFC Blumenau"` e textos de campus hardcoded. |
| `FE-11` | Médio | **Resolvido** | `matchMedia("(max-width: 720px)")` garante fallback automático da Tabela para Cartões em telas pequenas. |
| `FE-12` | Médio | **Resolvido** | Botão `"Ver detalhes"` na Tabela, colunas próprias no escopo `dissertacoes`, `title` nos códigos e título do modal adaptado em `produtos`. |
| `FE-13` | Médio | **Resolvido** | *Focus trap* (`manterFocoNoModal`) e restauração de foco no modal, bloqueio de scroll no `body`, `role="group"` e `aria-live="polite"` enxuto. |
| `FE-14` | Médio | **Resolvido** | Blindagem Elementor/WordPress (`data-leme-init`, `overflow: clip`, `z-index: 100000`, CSS 100% escopado em `#leme-painel-ept`, `mqMobile.addListener`). |
| `FE-15` | Médio | **Resolvido** | `data-json-url` (produção) + `data-json-url-local` (local) e estado degradado de erro com botão `"Tentar novamente"`. |
| `FE-16` | Médio | **Resolvido** | Fallbacks `valorPublico` em campos vazios e filtro `Ano` ordenado em ordem decrescente (`2026..2020`). |
| `FE-17` | Médio | **Resolvido** | Consolidação final do frontend v4 em [index.html](index.html) (e posterior remoção dos artefatos legados v3 da raiz). |
| `FE-18` | Baixo | **Resolvido** | Remoção de classes CSS mortas, variáveis duplicadas, IDs não lidos e retenção desnecessária de `item.raw`. |
| `FE-19` | Baixo | **Resolvido** | Padronização em `LF` com quebra final em EOF e `font-weight` padrão (`700`/`800`). |
| `FE-20` | Baixo | **Resolvido** | Lookup O(1) por `Map(id)`, *fast-path* em `highlightText`, recorte `trechoResumoCard`, cache de referências DOM e ordenação sem recalcular gráficos. |
| `FE-21` | Baixo | **Resolvido** | Validação defensiva do envelope JSON em `iniciarPainel` e remoção de `backdrop-filter`. |
| `FE-22` | Melhoria | **Resolvido** | Dashboard 100% interativo (`data-filter-campo` / `data-filter-valor` + `alternarFiltroInterativo`) nos **9 gráficos** e **3 cards categóricos de destaque**. |
| `FE-23` | Melhoria | **Resolvido** | Dashboard compacto `3 × 3` fullscreen em `>= 1080px` (`2 × 2` em `produtos`), animações estilo BI via reconciliação de DOM (`dataset.barKey`) e índice facetado em memória (`indiceFacetas`). |
| `FE-24` | Melhoria | **Resolvido** | Modais expansíveis unificados (`abrirModalRanking` / `RANKING_CONFIGS`) acionados via `"Ver todos"` com busca, pills adaptáveis (`Todos`, `≥ 2`, `≥ 5`, `≥ 10`), ordenação, paginação (`rankingPorPagina = 30` via `data-ranking-pagina`), filtro por clique e exportação `.CSV`. |
| `FE-25` | Melhoria | **Resolvido** | Coorientação autônoma (`coorientador` como 10ª faceta em `indiceFacetas` isolada de `orientador`): toggle `Orientação \| Coorientação (N)` no card, subtexto `#leme-stat-coorientadores` em `.leme-stats`, chip dedicado, alternador interno e CSV próprio no modal. |
| `FE-26` | Melhoria | **Resolvido** | Modularização em [index.html](index.html) + [frontend/styles.css](frontend/styles.css) + [frontend/app.js](frontend/app.js) e build via [scripts/build_frontend.py](scripts/build_frontend.py) (`--check`) gerando [dist/widget-elementor.html](dist/widget-elementor.html) (`0` linhas em branco, `wpautop`-safe). |

---

## 3. Backlog Futuro (Fora do Escopo Atual)

* **Otimização do Artefato JSON (`Opção C` — Etapa 4):** Minificar `dist/painel-ept-v4.json` e omitir `indice_busca.texto_busca_normalizado` do arquivo publicado (~34,8% do JSON compacto, reduzindo de `~1.171 KB` / `~241 KB` gzip para `~643 KB` / `~159 KB` gzip), reconstruindo o índice textual em ~3 ms no boot do frontend — além de eventual *split* entre catálogo leve e detalhes sob demanda caso o acervo supere ~400–500 defesas.
