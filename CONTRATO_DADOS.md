# Contrato Conceitual de Dados e Taxonomia de Domínio — LEME / ProfEPT (v4)

> **Escopo deste documento:** Especificação canônica do domínio bibliométrico CAPES/ProfEPT (estrutura conceitual v4, Linhas de Pesquisa, Macroprojetos, 9 Tipos de Produto, 5 Públicos-Alvo, 8 Níveis de Aplicação, 7 Matrizes Epistemológicas e regras de evidência). Para a implementação dos schemas em Pydantic v2, consulte [pipeline/models_v4.py](pipeline/models_v4.py) e a Seção 2 de [DOCUMENTACAO_TECNICA.md](DOCUMENTACAO_TECNICA.md).

---

## 1. Estrutura Conceitual do Registro (`ContratoDefesaV4`)

* **`Defesa`**
  * `id` (`EPT-XXXX`), `ano`, `autor`, `orientador`, `coorientadores[]` *(contabilizados de forma estritamente separada do orientador principal)*, `instituicao`, `campus`
  * `linha_pesquisa` (`LP1` | `LP2`) e `macroprojeto` (`MP1`..`MP6`)
  * **`dissertacao`**: `titulo`, `link`, `resumo`, `palavras_chave[]`, `autores_referenciados[]`, `base_epistemologica` (`valor`, `candidato`, `confianca`, `revisao_pendente`, `curado_humano`, `justificativa`, `evidencias[]`)
  * **`produto`**: `titulo`, `tipo` (1 dos 9 slugs CAPES), `link`, `publico_alvo[]` (1 ou mais dos 5 slugs), `nivel_aplicacao`, `palavras_chave[]`, `data_publicacao`, `autores_colaboradores[]`, `identificadores[]`, `proveniencia` (`fonte_tipo_escolhida`, `rotulo_original_declarado`, `colecao_educapes`, `dc_type_educapes[]`)
  * **`indice_busca`**: `texto_busca_normalizado`, `termos_unificados[]`, `tem_produto_vinculado`, `tem_resumo`

---

## 2. Linhas de Pesquisa e Macroprojetos (`MP1–3 → LP1` | `MP4–6 → LP2`)

* **`LP1` — Práticas Educativas em EPT**
  * `MP1`: Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT
  * `MP2`: Inclusão e diversidade em espaços formais e não formais de ensino na EPT
  * `MP3`: Práticas educativas no currículo integrado
* **`LP2` — Organização e Memórias de Espaços Pedagógicos**
  * `MP4`: História e memórias no contexto da EPT
  * `MP5`: Organização do currículo integrado na EPT
  * `MP6`: Organização de espaços pedagógicos na EPT

---

## 3. Tipos Oficiais de Produto Educacional CAPES (`TipoProdutoSlug`)

A todo produto educacional aplica-se **exatamente um** tipo principal canônico. Os metadados `dc.type` e coleção do eduCAPES são preservados separadamente em `proveniencia` como evidência complementar e não substituem automaticamente o formato específico declarado na dissertação/ficha do produto (`dissertacao_ficha` > `educapes_dc_type` > `inferencia_llm`).

1. **`material_didatico_instrucional` — Material Didático ou Instrucional:** Propostas de ensino (sugestões de experimentos, atividades práticas, sequências didáticas, propostas de intervenção, roteiros de oficinas); material textual (manuais didáticos, guias, textos de apoio, artigos em revistas técnicas/divulgação, livros didáticos/paradidáticos, histórias em quadrinhos, dicionários, folders educativos, portfólios formativos); mídias e ambientes educacionais (vídeos, podcasts, simulações, animações, videoaulas, experimentos virtuais, áudios, objetos e ambientes virtuais de aprendizagem como Moodle/AVA, páginas de internet, sites educativos, blogs, jogos educacionais de mesa ou virtuais e afins).
2. **`curso_oficina` — Curso ou Oficina de Formação Profissional:** Cursos, oficinas e formações estruturadas com proposta pedagógica detalhada vinculada à APCN.
3. **`tecnologia_social` — Tecnologia Social:** Produtos, dispositivos ou equipamentos; processos, procedimentos, técnicas ou metodologias; serviços e inovações sociais organizacionais ou de gestão.
4. **`software_aplicativo` — Software ou Aplicativo:** Aplicativos de modelagem, aquisição e análise de dados, sistemas web desenvolvidos como software, simuladores e programas de computador *(não inclui sequências didáticas que apenas utilizam aplicativos de terceiros)*.
5. **`eventos_organizados` — Evento Organizado:** Exposições científicas, olimpíadas, expedições, feiras, mostras científicas e atividades estruturadas de divulgação científica.
6. **`acervo` — Acervo:** Curadoria de mostras e exposições realizadas, acervos históricos/documentais produzidos e curadoria de coleções.
7. **`produto_comunicacao` — Produto de Comunicação:** Produtos de mídia, criação de programa de rádio ou TV, campanhas publicitárias e similares.
8. **`manual_protocolo` — Manual ou Protocolo:** Guias de instruções técnicas, protocolos tecnológicos experimentais, manuais de operação, gestão, normas e/ou procedimentos institucionais.
9. **`carta_mapa` — Carta, Mapa ou Similar:** Cartas cartográficas, mapas temáticos e representações espaciais similares.

---

## 4. Públicos-Alvo (`PublicoAlvoSlug`) e Níveis de Aplicação

### 5 Agrupamentos Canônicos de Público-Alvo (permite múltiplos por produto)
1. `docentes_professores` — Docentes e Professores
2. `estudantes_alunos` — Estudantes e Alunos
3. `gestores_coordenadores` — Gestores e Coordenadores Escolares
4. `tecnicos_profissionais_educacao` — Técnicos e Profissionais da Educação
5. `comunidade_externa` — Comunidade Externa

### 8 Níveis de Aplicação Padronizados (`normalizar_nivel_aplicacao`)
* `Ensino Médio Integrado`
* `Curso Técnico Subsequente`
* `EJA / PROEJA`
* `Formação de Professores`
* `Educação Superior`
* `Ensino Fundamental`
* `Gestão Institucional`
* `Educação Profissional e Tecnológica` *(rótulo transversal quando o produto abrange a modalidade EPT de forma ampla)*

---

## 5. Base Epistemológica: Vocabulário Canônico e Regra de Evidência

### 7 Matrizes Canônicas Preferenciais (`normalizar_base_epistemologica`)
1. `Materialismo Histórico-Dialético`
2. `Pedagogia Histórico-Crítica`
3. `Educação Libertadora / Freireana`
4. `Teoria Histórico-Cultural / Sociointeracionismo`
5. `Aprendizagem Significativa`
6. `Teoria Crítica`
7. `Pensamento Complexo / Interdisciplinaridade`
*(Quando o texto sustenta explicitamente duas matrizes canônicas articuladas sem predominância única, admite-se a composição ligada por `" e "`, ex.: `"Pedagogia Histórico-Crítica e Materialismo Histórico-Dialético"`.)*

### Protocolo de Extração e Classificação Assistida
`base_epistemologica` é um campo interpretativo e **nunca** deve ser deduzido apenas pela lista de referências finais, pelo tema da pesquisa, pela linha/macroprojeto ou pelo objetivo do produto:

1. **Busca de evidência no texto:** localizar trechos no resumo, introdução, referencial teórico e seção metodológica onde a filiação teórica/epistemológica é declarada ou fundamenta o argumento, registrando seção e página (`[PÁG. X]`).
2. **Cruzamento com referências:** selecionar na seção de referências apenas as entradas correspondentes às citações presentes nesses trechos.
3. **Recorte enxuto para a LLM:** enviar somente o resumo, os trechos epistemológicos localizados e as referências correspondentes (nunca o PDF inteiro).
4. **Trava de confiança:**
   * Apenas classificações com `confianca == "alta"`, termo pertencente ao vocabulário canônico e evidência localizável (`secao`, `pagina`, `trecho`) preenchem `valor` (`revisao_pendente: false`).
   * Casos com `confianca` `"media"`, `"baixa"`, `"abstencao"` ou termo fora do vocabulário canônico mantêm `valor: null`, registram o termo em `candidato` com justificativa/evidências e seguem para curadoria humana (`revisao_pendente: true` em `dist/revisao_epistemologica_pendente.csv`).

---

## 6. Metadados Determinísticos de Origem (Etapa 2)

* **Da Dissertação (`RecortesTextuais` + `DissertacaoDeterministica`):** `capa` (instituição, campus, autor, título, orientador, ano), `ficha_catalografica`, `sumario`, `resumo`, `introducao`, `palavras_chave` (extraídas do resumo), `autores_referenciados` (nomes completos normalizados e reconciliados extraídos das referências ABNT) e `coorientadores` (extraídos das páginas preliminares e ficha catalográfica).
* **Do Produto Educacional (`EvidenciasEduCAPES`):** `autores_colaboradores` (nomes e papéis `creator`/`contributor`), `identificadores` (esquema, valor e URL), `data_publicacao` (`YYYY-MM-DD`, `YYYY-MM` ou `YYYY`), `colecao_educapes`, `dc_type_educapes` e `palavras_chave_educapes`.
