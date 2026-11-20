# Auditoria Técnica, Discrepâncias e Backlog de Refatoração — Pipeline & Frontend v4

> **Status Atual:** **Pipeline (`AUD-01` a `AUD-25`) e Frontend (`FE-01` a `FE-24`) Concluídos.** As fases da pipeline foram implementadas e validadas nos registros do acervo; o frontend consolidado em [index.html](index.html) teve todas as 24 melhorias aplicadas e aprovadas em checagem estática.

---

## 1. Resumo da Execução da Refatoração (Antes vs. Depois)

| Métrica do Acervo Compilado (`dist/painel-ept-v4.json`) | Pré-Refatoração (Snapshot Inicial) | Pós-Refatoração (Compilado Atual) |
| :--- | :--- | :--- |
| Defesas compiladas (`PainelEptV4Output`) | 111 (sem validação do envelope raiz) | **111** (222 produções; validado por `PainelEptV4Output`) |
| `dissertacao.autores_referenciados` preenchidos | 77 / 111 (87 na Etapa 2; 10 dessincronizados) | **108 / 111** *(restam apenas 3 PDFs sem camada de texto legível: `EPT-0059`, `EPT-0072`, `EPT-0073`)* |
| `dissertacao.resumo` preenchidos | 105 / 111 (**102** iniciavam com `[PÁG. X]\n`) | **107 / 111** (**0** com `[PÁG. X]` residual) |
| `dissertacao.palavras_chave` preenchidas | 87 / 111 | **107 / 111** (100% dos resumos extraídos) |
| Valores distintos em `base_epistemologica.valor` | 44 (incluindo *typos*, `snake_case` e termos livres) | **4** termos canônicos aprovados (60 registros) + 51 pendentes (`None`) |
| Valores distintos em `produto.nivel_aplicacao` | 21 (Title Case + `snake_case` + genéricos) | **7** rótulos canônicos padronizados |
| `base_epistemologica.valor` indexada em `indice_busca` | Não | **Sim** (100% pesquisável) |
| Correção bônus de falso positivo `.mp4` | `EPT-0100` classificado como `MP4/LP2` por `"mp4 – um padrao..."` | `step2` detecta `LP1`; `EPT-0100` e `EPT-0108` sinalizados via warning na ressincronização para eventual `--id ... --sobrescrever` |
| Suíte de testes automatizados | 0 testes | **19 testes unitários** passando (`unittest`, 0 falhas) |

---

## 2. Quadro Resumo dos Achados (`AUD-01` a `AUD-25`)

* **Total de achados:** **25 itens** — **4 Críticos**, **6 Altos**, **9 Médios** e **6 Baixos** (todos **Resolvidos**).

| ID | Severidade | Status | Arquivo(s) / Linhas | Resumo |
| :--- | :--- | :--- | :--- | :--- |
| `AUD-01` | Crítico | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py) | `OPENAI_COMPAT_PRESETS` agora guarda nomes das variáveis em `env_key` e resolve sem expor segredos no `EnvironmentError`. |
| `AUD-02` | Crítico | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py) | `load_dotenv` ancorado em `PROJECT_ROOT / ".env"` (`Path(__file__).resolve().parent.parent`). |
| `AUD-03` | Crítico | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | Default alterado para `sobrescrever=False`; adicionado `curado_humano: bool` com trava contra sobrescrita sem `--forcar-curados`. |
| `AUD-04` | Crítico | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py), [.env.dev](.env.dev) | Preset `mistral` (`MISTRAL_API_KEY`) implementado; `.env.dev` atualizado removendo `gonka`. |
| `AUD-05` | Alto | **Resolvido** | [pipeline/normalizers.py](pipeline/normalizers.py), [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `normalizar_base_epistemologica` padroniza as 7 matrizes (+ composições) e rebaixa valores não canônicos para revisão pendente. |
| `AUD-06` | Alto | **Resolvido** | [pipeline/normalizers.py](pipeline/normalizers.py), [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `normalizar_nivel_aplicacao` reduz variantes e `snake_case` a rótulos canônicos. |
| `AUD-07` | Alto | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | Criado `ressincronizar_registros_deterministico` (`--sync-deterministico`); 111/111 registros sincronizados offline sem rechamar LLM. |
| `AUD-08` | Alto | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py), [pipeline/SKILL.md](pipeline/SKILL.md) | `REGRAS_TIPO_PRODUTO` e `REGRAS_DC_TYPE_EDUCAPES` harmonizados com `SKILL.md` e `CONTRATO_DADOS.md`. |
| `AUD-09` | Alto | **Resolvido** | [pipeline/SKILL.md](pipeline/SKILL.md) | `SKILL.md` reescrito para espelhar exatamente `montar_prompt_enxuto` e `RespostaInterpretativaLLM`. |
| `AUD-10` | Alto | **Resolvido** | [pipeline/step1_collect.py](pipeline/step1_collect.py) | `carregar_mapeamento_ids_existentes` aceita múltiplos arquivos em ordem de prioridade (`stage1_manifest.json` -> `painel-ept-v4.json` -> `painel-ept-v3.json`). |
| `AUD-11` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | `isolar_secoes_pdf([])` corrigido para retornar `(RecortesTextuais(), "")`. |
| `AUD-12` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | Branch `if not handle_url:` unificada usando `extrair_sentenca_produto` e `classificar_produto_com_fonte`. |
| `AUD-13` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | Limpeza de controle invisível, `_eh_pagina_sumario` e `_PADRAO_REFS` aumentaram cobertura de `autores_referenciados` para 108/111. |
| `AUD-14` | Médio | **Resolvido** | [pipeline/normalizers.py](pipeline/normalizers.py), [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | `limpar_resumo_publico` eliminou 100% dos `[PÁG. X]` no JSON público; resumo multi-página e `Palavras-chave(s)` elevaram cobertura para 107/111. |
| `AUD-15` | Médio | **Resolvido** | [pipeline/models_v4.py](pipeline/models_v4.py), [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py), [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `classificar_produto_com_fonte` distingue `"dissertacao_ficha"` de `"educapes_dc_type"`; `titulo_produto_bruto` preservado separadamente. |
| `AUD-16` | Médio | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py) | `construir_indice_busca` agora indexa `dissertacao.base_epistemologica.valor`. |
| `AUD-17` | Médio | **Resolvido** | [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py), [pipeline/SKILL.md](pipeline/SKILL.md) | `montar_prompt_enxuto` envia `linha_pesquisa_pre_detectada` e `montar_registro_final` valida divergências. |
| `AUD-18` | Médio | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py), [.env.dev](.env.dev) | Adicionado suporte a `LLM_THINKING_BUDGET` (Gemini), `LLM_NUM_CTX`/`LLM_THINK` (Ollama) e default `qwen2.5:7b-instruct`. |
| `AUD-19` | Médio | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | `extrair_autores_referencias` suporta acentos (`À–Ý`), remove `AGNOMES`, amplia `IGNORAR_ENTRADAS_REF` e preserva sobrenomes compostos. |
| `AUD-20` | Baixo | **Resolvido** | [pipeline/step2_deterministic.py](pipeline/step2_deterministic.py) | Helpers `_adicionar_unico`, `_adicionar_colaborador_unico` e `_adicionar_identificador_unico` deduplicam `<meta>` e `<table>`. |
| `AUD-21` | Baixo | **Resolvido** | [pipeline/llm_provider.py](pipeline/llm_provider.py) | `RateLimitError` agora relança imediatamente na última tentativa antes do `time.sleep`. |
| `AUD-22` | Baixo | **Resolvido** | `step1`, `step2`, `llm_provider`, [pyproject.toml](pyproject.toml) | Removidos imports/variáveis mortas (`ssl`, `urlparse`, `bloco_busca_mp`), corrigida indentação e removida dependência `google>=3.0.0`. |
| `AUD-23` | Baixo | **Resolvido** | `step1`–`step4`, [pipeline/models_v4.py](pipeline/models_v4.py) | Adicionada CLI `argparse` nos 4 módulos, `PainelEptV4Output`, timestamps unificados em UTC e `campus="IFC Blumenau"`. |
| `AUD-24` | Baixo | **Resolvido** | [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md), [README.md](README.md), [ARQUITETURA.md](ARQUITETURA.md), [RELATORIOS.md](RELATORIOS.md) | Documentação sincronizada e cerca de código órfã removida de `RELATORIOS.md`. |
| `AUD-25` | Baixo | **Resolvido** | [tests/test_pipeline_v4.py](tests/test_pipeline_v4.py) | Criada suíte com 19 testes unitários offline via `unittest` (100% aprovados). |

---

## 3. Detalhamento Técnico dos Achados e Soluções Aplicadas

### Críticos (`AUD-01` a `AUD-04`)

* **`AUD-01` — Lookup e segurança de API keys em [pipeline/llm_provider.py](pipeline/llm_provider.py):** `OPENAI_COMPAT_PRESETS` antes armazenava `os.getenv("GROQ_API_KEY")` (o valor do segredo) em `"env_key"` e invocava `os.getenv(preset["env_key"])`. Corrigido para armazenar os nomes das variáveis (`"GROQ_API_KEY"`, `"OPENROUTER_API_KEY"`, `"MISTRAL_API_KEY"`), resolver via `os.getenv(preset["env_key"]) or os.getenv("LLM_API_KEY")` e nunca interpolar valores secretos em exceções.
* **`AUD-02` — Caminho relativo de `.env` em [pipeline/llm_provider.py](pipeline/llm_provider.py):** Substituído `load_dotenv(dotenv_path="../.env")` por `PROJECT_ROOT / ".env"` ancorado via `Path(__file__).resolve().parent.parent`, permitindo execução confiável a partir da raiz do projeto.
* **`AUD-03` — Proteção contra sobrescrita de curadoria em [pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py):** `__main__` passou a usar `sobrescrever=False` por padrão; `BaseEpistemologicaV4` ganhou `curado_humano: bool = False` (ativado pela Etapa 4), impedindo reprocessamentos com `--sobrescrever` de apagar revisões humanas sem `--forcar-curados`.
* **`AUD-04` — Provedores suportados ([pipeline/llm_provider.py](pipeline/llm_provider.py), [.env.dev](.env.dev)):** Removido `gonka` de `.env.dev`.

### Alta Prioridade (`AUD-05` a `AUD-10`)

* **`AUD-05` — Normalização de `base_epistemologica.valor` ([pipeline/normalizers.py](pipeline/normalizers.py)):** Criada `normalizar_base_epistemologica` com aliases e suporte a composições válidas das 7 matrizes canônicas. Em `montar_registro_final` e na ressincronização, valores não canônicos sem curadoria humana são automaticamente movidos para `candidato` com `revisao_pendente = True`.
* **`AUD-06` — Normalização de `produto.nivel_aplicacao` ([pipeline/normalizers.py](pipeline/normalizers.py)):** Criada `normalizar_nivel_aplicacao`, reduzindo as 21 variações originais para 7 rótulos canônicos no acervo atual.
* **`AUD-07` — Ressincronização determinística Etapa 2 -> Etapa 3 ([pipeline/step3_llm_extract.py](pipeline/step3_llm_extract.py)):** Implementado `ressincronizar_registros_deterministico` (`--sync-deterministico`), atualizando os 111 registros sem chamadas LLM e preservando integralmente campos curados. Durante a ressincronização, `EPT-0100` (agora `LP1` na Etapa 2 após ajuste de falso positivo `.mp4`) e `EPT-0108` (`LP2` determinística vs. `MP3/LP1` anterior) foram sinalizados via log para eventual reprocessamento pontual (`--id ... --sobrescrever`).
* **`AUD-08` — Alinhamento taxonômico de produtos ([pipeline/step2_deterministic.py](pipeline/step2_deterministic.py), [pipeline/SKILL.md](pipeline/SKILL.md)):** `podcast`, `ava`, `moodle`, `website`, `site educativo`, `blog`, `material de apoio`, `folder educativo` e `portfólio formativo` unificados em `material_didatico_instrucional`; `software_aplicativo` restringido para evitar falsos positivos em sequências didáticas que apenas citam apps; adicionada `REGRAS_DC_TYPE_EDUCAPES` apenas para tags não ambíguas do eduCAPES.
* **`AUD-09` — Alinhamento de `pipeline/SKILL.md` ([pipeline/SKILL.md](pipeline/SKILL.md)):** Prompt reescrito para refletir o payload enxuto real (`montar_prompt_enxuto`), o schema `RespostaInterpretativaLLM` (`trecho_curto`, ausência de `revisao_pendente`) e os rótulos canônicos de `produto_nivel_aplicacao` e `base_epistemologica`.
* **`AUD-10` — Estabilidade de IDs na Etapa 1 ([pipeline/step1_collect.py](pipeline/step1_collect.py)):** `carregar_mapeamento_ids_existentes` agora consulta por prioridade `[data/stage1_manifest.json, dist/painel-ept-v4.json, painel-ept-v3.json]`.

### Média Prioridade (`AUD-11` a `AUD-19`)

* **`AUD-11`:** `isolar_secoes_pdf([])` corrigido para retornar `(RecortesTextuais(), "")`.
* **`AUD-12`:** Branch sem `handle_url` de `coletar_evidencias_educapes` unificada com `extrair_sentenca_produto` e `classificar_produto_com_fonte`.
* **`AUD-13`:** Adicionada remoção de caracteres invisíveis (`\u200b`, `\x01`, etc.), detecção de sumário (`_eh_pagina_sumario`) e `_PADRAO_REFS` tolerante a numeração e variações de cabeçalho (elevando `autores_referenciados` para `108/111`; `EPT-0059`, `EPT-0072` e `EPT-0073` não possuem texto legível na camada PDF). Além disso, corrigiu-se um falso positivo adicional na detecção de `MP4` em `detectar_macroprojeto_e_linha` que antes capturava `"mp4 – um padrao de audio e video"` em `EPT-0100`.
* **`AUD-14`:** `limpar_resumo_publico` remove `[PÁG. X]` e `RESUMO` na gravação de `dissertacao.resumo`; captura de `RESUMO` multi-página + regex flexível `Palavras[\s\-–]+chaves?` elevaram `palavras_chave` para `107/111`.
* **`AUD-15`:** `classificar_produto_com_fonte` retorna `(tipo, fonte)` alcançando `"educapes_dc_type"`; `EvidenciasEduCAPES` e `proveniencia.rotulo_original_declarado` preservam `titulo_produto_bruto`.
* **`AUD-16`:** `construir_indice_busca` passou a incluir `dissertacao.base_epistemologica.valor`.
* **`AUD-17`:** `montar_prompt_enxuto` inclui `linha_pesquisa_pre_detectada`, com alerta em `montar_registro_final` e na ressincronização quando houver divergência.
* **`AUD-18`:** `LLMClient` ganhou suporte a `LLM_THINKING_BUDGET` (Gemini), `LLM_NUM_CTX`/`LLM_THINK` (Ollama) e default `qwen2.5:7b-instruct`.
* **`AUD-19`:** `extrair_autores_referencias` ampliado para acentuação maiúscula completa (`À–Ý`), filtragem de `AGNOMES` e stopwords institucionais, preservando sobrenomes compostos reais.

### Baixa Prioridade (`AUD-20` a `AUD-25`)

* **`AUD-20`:** Deduplicação unificada entre `<meta>` e `<table>` em `coletar_evidencias_educapes`.
* **`AUD-21`:** `RateLimitError` em `llm_provider.py` verifica `tentativa == max_retries` antes do backoff.
* **`AUD-22`:** Limpeza de imports mortos (`ssl`, `urlparse`), variável `bloco_busca_mp`, indentação em `llm_provider.py` e remoção de `google>=3.0.0` do [pyproject.toml](pyproject.toml).
* **`AUD-23`:** Adicionada interface CLI `argparse` em `step1`–`step4`, criado `PainelEptV4Output` em [pipeline/models_v4.py](pipeline/models_v4.py), unificados timestamps em UTC e padronizado `campus="Blumenau"`.
* **`AUD-24`:** Atualizados [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md), [README.md](README.md), [ARQUITETURA.md](ARQUITETURA.md) e removida cerca ```` ``` ```` órfã em [RELATORIOS.md](RELATORIOS.md).
* **`AUD-25`:** Criada suíte de testes unitários em [tests/test_pipeline_v4.py](tests/test_pipeline_v4.py) (19 casos cobrindo todos os módulos da pipeline v4).

---

## 4. Auditoria e Refatoração do Frontend (`FE-01` a `FE-24`)

> **Consolidação:** O widget v4 em andamento (`index-new.html`) foi consolidado e refatorado diretamente em [index.html](index.html), preservando o widget legado v3 sem alterações em [index-v3.html](index-v3.html).

### Resumo Comparativo (Antes vs. Depois)

| Aspecto do Frontend | Pré-Refatoração (`index-new.html` / `index.html` v3) | Pós-Refatoração ([index.html](index.html) v4) |
| :--- | :--- | :--- |
| Estrutura de arquivos e URL JSON | `index.html` (v3) + `index-new.html` (`./dist/painel-ept-v4.json` relativo) | Consolidado em `index.html` (`data-json-url` produção + `data-json-url-local` em `localhost`); legado em `index-v3.html` |
| Sanitização HTML (`escapeHtml`) e URLs | *No-op* (`<`→`<`, `"`→`"`) com DOM-XSS ativo e quebra em `EPT-0020`/`EPT-0029`; links sem checagem | `HTML_ESCAPE_MAP` com escapes Unicode; `sanitizarUrl` (`http:`/`https:` + `rel="noopener noreferrer"`); `csvEscape` anti-fórmula |
| Orientadores e Instituição/Campus | `30` entradas com `:`/`.`, `": Juliene Marques Bogo"` no gráfico, `"IFC – IFC Blumenau"` | **21** orientadores canônicos consolidados (`orientadorChave`); `"Instituto Federal Catarinense (IFC) – Campus Blumenau"` |
| Busca e Cobertura do Contrato v4 | Busca sem rótulos `I18N`/`publico_alvo`; omitia `gerado_em`, `evidencias`, `proveniencia`, `data_publicacao` | Busca enriquecida com `I18N`/`publico_alvo`/`instituicao`; `gerado_em` no topo; `<details>` recolhido no modal |
| Interatividade do Dashboard e Layout BI | Apenas barras de `"Autores mais referenciados"` filtravam (por substring via `#leme-busca`); cards altos | Grade compacta `3 × 3` (`2 × 2` em `produtos`), animações BI via reconciliação DOM + índice facetado (`FE-23`) e *cross-filtering* nos **9 gráficos** + **3 cards categóricos** (`FE-22`) |
| Exploração de Rankings Longos (`FE-24`) | Apenas Top 12 autores e Top 10 orientadores visíveis no card; sem busca, corte nem exportação do ranking | Botão `"Ver todos"` abre modal unificado (autores em `≥ 5` e orientadores em `Todos`) com busca por nome, cortes adaptáveis, ordenação, paginação (`30`/pág.), clique para filtrar e CSV do ranking |
| Ordenação, Responsividade e WCAG AA | Sem ordenação (2026 no fim); armadilha Tabela em `<= 720px`; contrastes `< 3.5:1` e `backdrop-filter` | Ordenação `ano_desc` padrão + seletor; Tabela com `"Ver detalhes"` e fallback `matchMedia`; contraste `>= 4.5:1`; sem `backdrop-filter` |

### Quadro Resumo dos Achados do Frontend (`FE-01` a `FE-24`)

| ID | Severidade | Status | Resumo |
| :--- | :--- | :--- | :--- |
| `FE-01` | Crítico | **Resolvido** | Reescrita de `escapeHtml` com `HTML_ESCAPE_MAP` Unicode (`\u0026amp;`..`\u0026#39;`), corrigindo DOM-XSS e quebras de DOM em resumos/títulos. |
| `FE-02` | Crítico | **Resolvido** | Adicionada `sanitizarUrl` (`http:`/`https:` apenas) e `rel="noopener noreferrer"` em todos os links de card, tabela e modal. |
| `FE-03` | Alto | **Resolvido** | `limparNomePessoa` e `consolidarOrientadores` eliminaram pontuação residual (`:`/`.`) e unificaram KPI, gráfico e filtro em 21 chaves. |
| `FE-04` | Alto | **Resolvido** | `texto_busca_normalizado` enriquecido com rótulos `I18N`, `publico_alvo`, `instituicao` e `campus`. |
| `FE-05` | Alto | **Resolvido** | Exibição de `gerado_em`, 3 estados claros para `base_epistemologica`, nota de pendências no gráfico e `<details>` recolhido com `base_evidencias` e metadados eduCAPES. |
| `FE-06` | Alto | **Resolvido** | Ordenação padrão `ano_desc` + seletor `#leme-ordenar` (`ano_desc`, `ano_asc`, `titulo_asc`, `autor_asc`). |
| `FE-07` | Alto | **Resolvido** | `csvEscape` protege contra *Formula Injection* (`=`, `+`, `-`, `@`, `\t`, `\r`), botão desabilita com 0 resultados e colunas incluem `autores_referenciados`/`coorientadores`/`data_publicacao`. |
| `FE-08` | Alto | **Resolvido** | Filtro de `"Autores mais referenciados"` migrado para estado dedicado + `<button type="button">` acessível por teclado (posteriormente unificado em `FE-22`). |
| `FE-09` | Alto | **Resolvido** | Cores ajustadas (`#3b47e5`, `#1f7a49`, `#d62849`, `#b91c3a`, `#526075`) atingindo contraste `>= 4.5:1` (WCAG 2.1 AA). |
| `FE-10` | Médio | **Resolvido** | `formatarInstituicaoCampus` remove redundância `"IFC – IFC Blumenau"` e remove textos de campus hardcoded. |
| `FE-11` | Médio | **Resolvido** | `matchMedia("(max-width: 720px)")` garante fallback automático da Tabela para Cartões em telas pequenas. |
| `FE-12` | Médio | **Resolvido** | Botão `"Ver detalhes"` na Tabela, colunas próprias no escopo `dissertacoes`, `title` nos códigos e título do modal adaptado em `produtos`. |
| `FE-13` | Médio | **Resolvido** | *Focus trap* e restauração de foco no modal, bloqueio de scroll no `body`, `role="group"` e remoção de 10 `aria-live` excedentes. |
| `FE-14` | Médio | **Resolvido** | Blindagem Elementor/WordPress (`data-leme-init`, `overflow: clip`, `z-index: 100000`, resets escopados em `#leme-painel-ept`, `mqMobile.addListener`). |
| `FE-15` | Médio | **Resolvido** | `data-json-url` (produção) + `data-json-url-local` (local) e estado completo de erro com botão `"Tentar novamente"`. |
| `FE-16` | Médio | **Resolvido** | Fallbacks `valorPublico` em autor/orientador vazios e filtro `Ano` ordenado em ordem decrescente (`2026..2020`). |
| `FE-17` | Médio | **Resolvido** | Consolidação final em [index.html](index.html) preservando legado v3 intacto em [index-v3.html](index-v3.html). |
| `FE-18` | Baixo | **Resolvido** | Remoção de classes CSS mortas, variáveis duplicadas, IDs não lidos e retenção desnecessária de `item.raw`. |
| `FE-19` | Baixo | **Resolvido** | Padronização em `LF` com quebra final em EOF e `font-weight` padrão (`700`/`800`). |
| `FE-20` | Baixo | **Resolvido** | Lookup O(1) por `Map(id)`, *fast-path* em `highlightText`, recorte `trechoResumoCard`, cache de referências DOM e ordenação sem recalcular gráficos. |
| `FE-21` | Baixo | **Resolvido** | Validação defensiva do envelope JSON em `iniciarPainel` e remoção de `backdrop-filter` para fluidez de compositor. |
| `FE-22` | Melhoria | **Resolvido** | Dashboard 100% interativo (`data-filter-campo` / `data-filter-valor` + `alternarFiltroInterativo`): clique/teclado em qualquer um dos **9 gráficos** ou **3 cards categóricos de destaque** alterna o filtro em sincronia bidirecional com os `<select>` e chips. |
| `FE-23` | Melhoria | **Resolvido** | Dashboard compacto `3 × 3` fullscreen em `>= 1080px` (`2 × 2` em `produtos`), animações estilo BI via reconciliação de DOM (`dataset.barKey`, barras GPU `scaleX`) + modal/chips suaves e índice facetado em memória (`indiceFacetas` / `construirIndiceFacetas` / `intersecarSets`). |
| `FE-24` | Melhoria | **Resolvido** | Modais expansíveis unificados (`abrirModalRanking` / `RANKING_CONFIGS`) acionados via `"Ver todos"` nos cards **Autores mais referenciados** (corte inicial adaptável `≥ 5`) e **Orientadores** (corte inicial `Todos`), com busca por nome (+ resgate em `Todos`), pills adaptáveis (`Todos`, `≥ 2`, `≥ 5`, `≥ 10`), ordenação (`Frequência` / `A–Z`), paginação simples (`rankingPorPagina = 30` via `data-ranking-pagina`, oculta automaticamente quando `<= 30`), clique para filtrar + fechamento automático e exportação `.CSV` do ranking (`baixarCsvRanking` com `csvEscape`). |

* **Status de verificação:** Checagem estática automatizada em [index.html](index.html) **100% aprovada**.

### Backlog Futuro (Fora do Escopo Atual)

* **Otimização do Artefato JSON (`Opção C` — Etapa 4):** Minificar `dist/painel-ept-v4.json` e omitir `indice_busca.texto_busca_normalizado` do arquivo publicado (~34,8% do JSON compacto, reduzindo de `~1.171 KB` / `~241 KB` gzip para `~643 KB` / `~159 KB` gzip), reconstruindo o índice textual em ~3 ms no boot do frontend — além de eventual *split* entre catálogo leve e detalhes sob demanda caso o acervo supere ~400–500 defesas.
