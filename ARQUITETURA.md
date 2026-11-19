# Arquitetura da Pipeline de Extração ProfEPT v4

Este documento resume a arquitetura de execução da pipeline de coleta, extração, inferência e compilação bibliométrica do acervo **ProfEPT (IFC Campus Blumenau)**. Para contratos detalhados, consulte [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md).

- **Acionamento Manual:** Não há monitoramento automático contínuo; a coleta e o processamento da pipeline são iniciados manualmente por um operador via CLI.

## Estrutura Modular em 4 Etapas (`pipeline/`)

- **Etapa 1 — Coleta e Pré-Extração (`pipeline/step1_collect.py`):** Consulta a API REST do WordPress do ProfEPT para descobrir defesas, preserva IDs estáveis (`EPT-XXXX`) usando os manifestos/compilados existentes, registra metadados da fonte em `data/stage1_manifest.json` e baixa os PDFs das dissertações localmente em `pdf/dissertacoes/` com validação de cabeçalho `%PDF-` e `SHA-256`. Não executa LLM nem OCR.
- **Etapa 2 — Extração Determinística (`pipeline/step2_deterministic.py`):** Extrai o texto nativo dos PDFs locais via `pymupdf` (isolando capa, ficha, sumário, resumo, palavras-chave, introdução, trechos epistemológicos, referências citadas e `autores_referenciados` em ABNT), realiza scraping com cache local do eduCAPES (`?show=full`) e aplica classificadores determinísticos para Macroprojeto, Linha de Pesquisa e Tipo de Produto.
- **Etapa 3 — Inferência Semântica e Hidratação (`pipeline/step3_llm_extract.py` + `pipeline/llm_provider.py` + `pipeline/normalizers.py` + `pipeline/SKILL.md`):** Envia exclusivamente um JSON compacto com os fragmentos selecionados (nunca o PDF inteiro) para o provedor configurado (`gemini`, `groq`, `mistral`, `openrouter` ou `ollama` local), aplica normalização canônica e trava de confiança na resposta (`RespostaInterpretativaLLM`) e hidrata deterministicamente `data/records/EPT-XXXX.json`. Também oferece ressincronização determinística não-destrutiva (`--sync-deterministico`).
- **Etapa 4 — Curadoria Bidirecional e Compilação (`pipeline/step4_compile.py`):** Importa revisões humanas (`APROVADO` / `MANTER_NULO`) da planilha `dist/revisao_epistemologica_pendente.csv` para `data/records/`, valida todos os registros contra `ContratoDefesaV4` e `PainelEptV4Output`, gera `dist/painel-ept-v4.json` e reescreve o CSV apenas com as pendências restantes.

## Regras de Domínio e Governança de Dados

- **Cardinalidade Fixa:** 1 Defesa equivale estritamente a 1 Dissertação e 1 Produto Educacional (totalizando 2 produções por defesa).
- **Vínculo Taxonômico Rígido:** Os Macroprojetos (`MP1` a `MP6`) determinam obrigatoriamente a Linha de Pesquisa (`MP1–MP3 → LP1`; `MP4–MP6 → LP2`) por regra determinística, sem inferência livre.
- **Classificação Assistida com Trava de Confiança e Vocabulário Canônico:** `base_epistemologica` exige evidência localizável (seção, página e trecho) e conformidade com o vocabulário canônico. Apenas candidatos com `confianca == "alta"` válidos são aceitos automaticamente; os demais mantêm `valor: null` e seguem para revisão humana na planilha CSV.
- **Proteção à Curadoria Humana:** Registros curados recebem `curado_humano: true` e são preservados contra sobrescritas acidentais na Etapa 3 (salvo uso explícito de `--sobrescrever --forcar-curados`).
- **Hierarquia de Fontes para Produtos:** O formato específico declarado na dissertação/ficha do produto (`dissertacao_ficha`) tem prioridade sobre os metadados do eduCAPES (`educapes_dc_type`) e sobre a inferência da LLM (`inferencia_llm`).
