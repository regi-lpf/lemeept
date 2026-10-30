# Continuidade do trabalho — Projeto LEME EPT

Ponto de entrada para continuar o projeto em outra máquina ou com outro agente. Leia na ordem: `CONTRATO_DADOS.md`, `DIAGRAMAS.md`, este arquivo e `LIMPEZA_TEMPORARIOS.md`. Depois leia o guia operacional necessário.

## Estado do checkout em 2026-10-30

- Repositório: `https://github.com/regi-lpf/lemeept`; branch local `develop`.
- HEAD conhecido: `8e81bc24ae935d81b5d9aa6305e2748b18b62b90` (`Publica atualizacao do extrator e amostra v2`). A referência de rastreamento `origin/develop` aponta para o mesmo SHA. A tentativa de `git fetch origin develop` falhou por permissão de escrita em `.git/FETCH_HEAD`; portanto, não foi possível confirmar agora se há commits remotos posteriores.
- PR #1 (contagens do painel) e PR #4 (continuidade/limpeza) aparecem no histórico local como merges (`395110b`, `8c30bbe`). A auditoria dos finais de linha do PR #1 está registrada abaixo e no histórico. O painel usa CRLF; preservar o arquivo Elementor e evitar diff de formatação amplo.
- Arquivos locais modificados/não rastreados encontrados antes desta atualização: mudança de link em `README.md`; novos `GUIA_REVISAO.md`, `criar_amostra_comparativa.py`, `gerar_planilha_revisao.py` e `sincronizar_revisao.py`. São trabalho do fluxo de revisão e devem ser avaliados/guardados, não descartados como temporários.
- O fluxo continua parcialmente manual: execução da sincronização é iniciada por uma pessoa; a planilha é revisão visual; decisões da planilha ainda não são importadas automaticamente para o JSON v2; publicação do painel no Elementor continua separada.

## O que está implementado

### Painel legado e contagens

- `lemeept/index.html` é o bloco do widget HTML do Elementor. Preserva a estrutura e exige edição de diff mínimo.
- Correções existentes contam orientadores por defesa/aluno único, tipo por produto único e MP3 pelo código canônico.
- Base observada: 110 defesas, 220 produções; MP3 consolida 42 produções (21 defesas).
- O JSON do widget continua `lemeept/painel-ept.json`. `lemeept/painel-ept-v2.json` é uma saída separada com 110 defesas e 220 produções independentes vinculadas por `defesaId`; não trocar o consumidor do painel sem uma migração específica.

### Coleta e revisão local

- `baixar_dissertacoes.py` baixa/valida PDFs por ID para `pdf/dissertacoes/` e grava manifesto com URL, bytes, status e SHA-256. A pasta é local/ignorável pelo Git. 110 PDFs estavam presentes na inspeção desta sessão.
- `sincronizar_revisao.py` consulta a API oficial ProfEPT quando executado, compara IDs com o JSON v2, baixa/extrai até cinco defesas novas por padrão e atualiza `dados/revisao/revisao_ept.xlsx`.
- A extração atual usa texto nativo PyMuPDF, limitada por páginas. Não executa OCR nem GPT e não altera o banco final. eduCAPES é consultado no script de amostra por Handle, não no sincronizador.
- `gerar_planilha_revisao.py` monta a fila e mantém abas de revisão/histórico; ver `GUIA_REVISAO.md`.

### Amostra exploratória atual

- Amostra corrente: IDs únicos EPT-0001, 0003, 0005, 0007, 0008 e 0010; seis dissertações e seis produtos.
- Artefatos locais ignorados: `dados/revisao/amostra_extracao_6_v2.json`, `comparacao_amostra_6_v2.xlsx` e `classificacao_assistida_6_v2.json`.
- Os seis PDFs foram extraídos via texto nativo. Dois Handles foram consultados pelo coletor; para três casos houve consulta de fallback às páginas oficiais; metadados do produto EPT-0008 seguem pendentes. Conferir a proveniência específica no JSON/planilha antes de tratar dado eduCAPES como confirmado.
- A classificação contextual encontrou linha/macroprojeto com confiança alta na amostra. Base epistemológica permanece sem resolução segura na maioria dos casos; EPT-0007 tem sugestão média com evidência de adesão teórico-metodológica ao materialismo histórico-dialético.
- O script `extrair_contexto_base_epistemologica.py` cria `contexto_base_epistemologica_6_v1.json/.xlsx` e `classificacao_assistida_6_v3.json` com trechos teóricos e referências correspondentes, sem GPT/OCR/rede.
- Na proposta v3, somente EPT-0007 passou de média para alta: o PDF explicita análise materialista histórico-dialética (p. PDF 18) e relaciona autores/obras correspondentes. Os outros cinco candidatos seguem para revisão humana. A ligação autor-ano/nome é heurística e deve ser conferida visualmente antes de usar em lote.
- A avaliação assistida v4 dos cinco casos pendentes está em `dados/revisao/classificacao_assistida_6_v4.json`. Nenhum recebeu valor confirmado automaticamente: os candidatos ainda não provam uma base epistemológica única/dominante. EPT-0001 (freireana/crítico-emancipatória), EPT-0003 (aproximação à Pedagogia Histórico-Crítica) e EPT-0010 (trabalho como princípio educativo) ficaram como candidatos médios; EPT-0005 ficou baixo/composto e EPT-0008 sem candidato confiável. A decisão preserva `valor: null` para não converter interpretação fraca em dado certo.
- O contrato do tipo de produto foi detalhado em `CONTRATO_DADOS.md`, com procedimento em `GUIA_CLASSIFICACAO_PRODUTOS.md`. O usuário confirmou confiança alta para os cinco tipos: Cartilha, E-book, Infográfico, História em quadrinhos e E-book. EPT-0005 tem conflito de metadados (coleção “Vídeos” e `dc.type` “livro digital”), mantido visível sem sobrescrever “Infográfico”; EPT-0008 não tem metadados eduCAPES recuperados, mas o PDF declara o formato.
- Decisão do usuário para as bases difíceis: deixar `valor` sem preenchimento e revisar manualmente depois. Não usar “Outros” como sinônimo de indeterminado. A decisão está refletida na planilha v4 e no JSON de classificação; integração ao banco v2 ainda é uma etapa separada.
- A primeira amostra de 11 itens e seu XLSX continuam locais como histórico comparativo, não são substituídos integralmente pela amostra menor. Consultar `LIMPEZA_TEMPORARIOS.md` antes de apagar qualquer um.

## História relevante

- PR #1: `lemeept/index.html` foi convertido de LF (1.086 linhas) para CRLF (1.128 linhas). Diff do PR: 5.456 adições/5.195 remoções sem ignorar CRLF; com `--ignore-cr-at-eol`, 279 adições/18 remoções. Mudança funcional do widget: +54/-12. Confirmar finais de linha antes de qualquer alteração.
- PR #4 adicionou este handoff e o inventário de limpeza; merge local `8c30bbe`.
- Atualizações posteriores adicionaram o downloader local, JSON v2, amostra e geradores/guia de revisão.

## Próximas etapas

1. Revisar na planilha os quatro candidatos de base epistemológica e a abstenção de EPT-0008; aceitar, corrigir ou manter pendente com nota curta.
2. Resolver a discrepância do Handle EPT-0005 e recuperar metadados do EPT-0008, sem rebaixar o formato explicitamente declarado no PDF sem evidência específica contrária.
3. Depois da decisão humana, integrar os campos da amostra ao JSON de trabalho com proveniência; não alterar o JSON do painel legado.
4. Ensaiar sincronização e revisão com uma defesa nova quando publicada; só depois planejar integração e publicação.

## Restrições de preservação

- Não alterar `dados/referencia/` como parte de limpeza.
- Não substituir nem reescrever o JSON legado enquanto a migração do widget não for aprovada.
- Não apagar PDFs, planilhas com revisão ou amostras históricas automaticamente.
- Consultar `LIMPEZA_TEMPORARIOS.md` antes de qualquer remoção e atualizar o inventário após gerar artefatos.
