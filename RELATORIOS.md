# Relatório Consolidado de Resultados e Viabilidade — Projeto LEME / ProfEPT (v4)

> **Escopo deste documento:** Fotografia empírica do acervo compilado em [dist/painel-ept-v4.json](dist/painel-ept-v4.json), orçamento de contexto/tokens (viabilidade em GPUs locais de 8 GB VRAM) e síntese executiva dos marcos técnicos alcançados por etapa. Para schemas Pydantic e implementação dos módulos, consulte [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md); para o changelog de auditoria (`AUD-01..25` e `FE-01..28`), consulte [AUDITORIA_E_REFATORACAO.md](AUDITORIA_E_REFATORACAO.md).

---

## 1. Viabilidade Operacional e Orçamento de Contexto (LLM Local — 8 GB VRAM)

A arquitetura v4 substituiu o envio de PDFs integrais por recortes determinísticos cirúrgicos em JSON compacto (`montar_prompt_enxuto`), viabilizando a execução tanto em APIs cloud quanto em hardware local com **8 GB de VRAM**:

* **Input médio enviado à LLM (Etapa 3):** **~7.104 tokens** na medição empírica dos payloads (máximo **~8.853 tokens** somando `pipeline/SKILL.md` + payload do registro, dentro do orçamento projetado de ~9.000 tokens).
* **Output estruturado (`RespostaInterpretativaLLM`):** **~400–500 tokens** de JSON enxuto, hidratado deterministicamente em Python na pós-extração.
* **Orçamento total de geração e recomendação para 8 GB VRAM:**
  * Em modelos com cadeia de pensamento ativa (*reasoning/thinking tokens*, como `gemini-2.5-flash`), o orçamento bruto de geração pode atingir até ~10.000 tokens.
  * Para execução local em **8 GB de VRAM**, recomenda-se desativar o modo *thinking* (`LLM_THINK=false` no Ollama ou `LLM_THINKING_BUDGET=0` na API Gemini) ou utilizar modelos *instruct* diretos (`qwen2.5:7b-instruct` ou `ministral-3:8b`) com janela `LLM_NUM_CTX=8192`, mantendo a saída próxima aos ~500 tokens do JSON.

---

## 2. Fotografia Empírica do Acervo Compilado ([dist/painel-ept-v4.json](dist/painel-ept-v4.json))

* **Volume e Cardinalidade:** **112 defesas** catalogadas (`EPT-0001` a `EPT-0112`), totalizando **224 produções** (`112 dissertações + 112 produtos educacionais`). *(Nota: a auditoria inicial `AUD-01..25` foi executada sobre o snapshot de 111 defesas / 222 produções, antes da incorporação da 112ª defesa e da rodada complementar de curadoria).*
* **Distribuição Temporal (2020–2026):** `2020: 24` · `2021: 6` · `2022: 6` · `2023: 12` · `2024: 36` · `2025: 21` · `2026: 7`.
* **Distribuição por Linha de Pesquisa e Macroprojeto:**
  * `LP1` (**63** defesas): `MP1: 16` · `MP2: 19` · `MP3: 28`
  * `LP2` (**49** defesas): `MP4: 12` · `MP5: 12` · `MP6: 25`
* **Orientação e Coorientação (contabilizadas separadamente):** **17** orientadores principais canônicos consolidados (em 110 defesas com orientador declarado) e **2** coorientadores distintos em **2** defesas com coorientação (`EPT-0004` e `EPT-0033`).
* **Cobertura de Metadados e Extração Determinística:**
  * `dissertacao.autores_referenciados`: **112/112** registros preenchidos (**1.570** autores únicos / **4.315** ocorrências totais; `435` citados em `≥ 2` defesas, `160` em `≥ 5` e `78` em `≥ 10`).
  * `dissertacao.resumo` e `dissertacao.palavras_chave`: **111/112** preenchidos (**0** com marcador `[PÁG. X]` residual).
  * `produto.palavras_chave`: **112/112** preenchidas.
* **Bases Epistemológicas (`dissertacao.base_epistemologica`):**
  * **No compilado atual (pós-curadoria):** **111** registros consolidados com vocabulário canônico (`Pedagogia Histórico-Crítica: 52`, `Materialismo Histórico-Dialético: 26`, `Educação Libertadora / Freireana: 23`, `Teoria Crítica: 4`, `Teoria Histórico-Cultural / Sociointeracionismo: 3`, `Aprendizagem Significativa: 1`, `Pedagogia Histórico-Crítica e Materialismo Histórico-Dialético: 1`, `Educação Libertadora / Freireana e Teoria Histórico-Cultural / Sociointeracionismo: 1`) e **1** registro em curadoria pendente (`revisao_pendente: true`).
  * *(No snapshot pré-curadoria humana da auditoria de 111 defesas: 60 bases aprovadas automaticamente com `confianca == "alta"` e 51 em revisão pendente no CSV).*
* **Níveis de Aplicação e Proveniência dos Produtos (`produto`):**
  * **Níveis de aplicação:** `Ensino Médio Integrado: 67` · `Educação Profissional e Tecnológica: 35` · `Educação Superior: 3` · `Curso Técnico Subsequente: 2` · `Formação de Professores: 2` · `Ensino Médio: 2` · `EJA / PROEJA: 1`.
  * **Proveniência da tipologia (`fonte_tipo_escolhida`):** `dissertacao_ficha: 84` · `inferencia_llm: 28`.

---

## 3. Síntese Executiva dos Marcos Técnicos por Etapa

1. **Etapa 1 — Coleta e Pré-Extração (`pipeline/step1_collect.py`):** Contorno de erro de cadeia SSL institucional (`profept.ifc.edu.br`), parser sequencial independente de DOM para listas `<ul>` mal fechadas, regex flexível para variações manuais de rótulos, captura do prefixo bruto do produto (`titulo_produto_bruto`), fallback de ano pela URL do PDF e preservação multi-referência de IDs `EPT-XXXX`.
2. **Etapa 2 — Extração Determinística (`pipeline/step2_deterministic.py`):** Varredura taxonômica integral com vínculo rígido `MP1–3 → LP1` / `MP4–6 → LP2` e filtro contextual anti-`.mp4` (corrigindo `EPT-0100`); extrator ABNT de `autores_referenciados` em até 25 páginas de referências sem inflar o prompt da LLM; extrator determinístico de `coorientadores` em páginas preliminares e ficha catalográfica; hierarquia de fontes priorizando a ficha/dissertação sobre `dc.type` do eduCAPES.
3. **Etapa 3 — Inferência Semântica e Hidratação (`pipeline/step3_llm_extract.py` + `pipeline/llm_provider.py`):** Camada modular agnóstica de provedor (`google-genai` e OpenAI-compatíveis), sanitização automática de JSON Schemas (`additionalProperties` e `$defs`/`$ref`), repasse determinístico passivo de `autores_referenciados` e `coorientadores`, trava de confiança para `base_epistemologica`, proteção a registros com `curado_humano: true` e modo `--sync-deterministico`. **Decisão operacional:** encerrada a extração automatizada via LLM, eventuais ajustes remanescentes em `base_epistemologica` ocorrem exclusivamente via curadoria humana.
4. **Etapa 4 — Curadoria e Compilação (`pipeline/step4_compile.py`):** Fluxo bidirecional com `dist/revisao_epistemologica_pendente.csv` (`UTF-8-SIG`, `;`) e validação integral do artefato `dist/painel-ept-v4.json` contra `PainelEptV4Output` ([pipeline/models_v4.py](pipeline/models_v4.py)).
5. **Frontend v4 e Empacotamento Elementor (`index.html` + `frontend/` → `dist/widget-elementor.html`):** Modularização do código-fonte com build validado por `scripts/build_frontend.py` (`--check`, zero linhas em branco, `wpautop`-safe, para colagem exclusiva no **Widget HTML (`</>`)** do Elementor); dashboard interativo `3 × 3` com animações BI por reconciliação de DOM, truncamento com reticências nos selecionáveis, índice em memória de **10 facetas** e seleção múltipla de filtros (**OU** intra-faceta / **E** entre facetas, facetamento disjuntivo nos gráficos e barra compacta de chips removíveis); autonomia da coorientação (mini-toggle no card, subtexto nos indicadores e aba/CSV próprios no modal); modais expansíveis de ranking completo (`Ver todos`, busca, cortes adaptáveis, paginação de 30 itens, seleção múltipla contínua e exportação `.CSV`); sanitização XSS/URL/CSV e acessibilidade WCAG 2.1 AA.
