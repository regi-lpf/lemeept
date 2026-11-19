# Auditoria Técnica, Discrepâncias e Backlog de Refatoração — Pipeline v4

> **Status Atual:** **Refatoração Concluída (25/25 itens resolvidos).** Todas as fases do roteiro (`Fase 1` a `Fase 4`) foram implementadas em `pipeline/`, `pyproject.toml`, `.env.dev`, `tests/test_pipeline_v4.py` e documentação, e validadas offline nos 111 registros do acervo (`step2_deterministic` -> `step3_llm_extract --sync-deterministico` -> `step4_compile`).

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
