# Este documento apresenta a estrutura de execução do pipeline de extração de dados do site ProfEPT.

- Acionamento Manual: Não há monitoramento automático contínuo; a coleta e o processamento da pipeline são iniciados manualmente por um operador.   
AGENTS.md+ 1

## Estrutura Modular em 3 Etapas (Pipeline):

    Etapa 1 (Coleta e Pré-Extração): Consulta a API do site ProfEPT para descobrir novas defesas, registra os metadados básicos da fonte e baixa os PDFs das dissertações localmente em pdf/dissertações/. Não executa LLM nem OCR.   

    Etapa 2 (Extração Determinística): Extrai o texto nativo dos PDFs locais (isolando recortes pré-textuais, introdução e referências citadas), realiza o scraping dos metadados correspondentes no eduCAPES via Handle e aplica classificadores determinísticos (regras/regex) para resolver o máximo possível dos campos regulares.

    Etapa 3 (Inferência Híbrida / Interpretativa): Envia exclusivamente os fragmentos textuais selecionados (nunca o PDF inteiro) para uma LLM local, guiada por arquivo de instruções (SKILL.md), para classificar apenas os campos irregulares ou interpretativos.

Isolamento e Persistência Granular: Os registros processados são armazenados individualmente em arquivos JSON separados (data/records/), que posteriormente são validados e compilados em um artefato único para publicação.

## Regras de Domínio e Governança de Dados:

    Cardinalidade Fixa: 1 Defesa equivale estritamente a 1 Dissertação e 1 Produto Educacional (totalizando 2 produções por defesa).   

    Vínculo Taxonômico Rígido: Os Macroprojetos (MP1 a MP6) determinam obrigatoriamente a Linha de Pesquisa (MP1–MP3 → LP1; MP4–MP6 → LP2) por regra determinística, sem inferência livre.

    Classificação Assistida com Trava de Confiança: Campos interpretativos (como Base Epistemológica) exigem evidência localizável (seção, página e trecho). Apenas candidatos com confiança alta são aceitos automaticamente; confiança média, baixa ou abstenção mantêm o valor nulo e seguem para revisão humana.

    Hierarquia de Fontes para Produtos: O formato específico declarado na dissertação/ficha do produto tem prioridade sobre os metadados genéricos (dc.type e coleção) extraídos do eduCAPES.
