# Contrato de dados do painel LEME / ProfEPT (v3)

- Defesa
  - ID
  - Ano
  - Autor
  - Orientador
  - Co-Orientador(es)?[]
  - Instituição
  - Campus
  - Linha de Pesquisa
  - Dissertação
    - Título
    - Link
    - Resumo
    - Palavras-Chave[]
    - Base Epistemológica
  - Produto Educacional
    - Tipo
    - Link
    - Público-Alvo[]
    - Nivel de Aplicação
    - Palavras-Chave[]

## Linhas de Pesquisa e Macroprojetos
- LP1: Práticas Educativas em EPT
  - MP1: Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT
  - MP2: Inclusão e diversidade em espaços formais e não formais de ensino na EPT
  - MP3: Práticas educativas no currículo integrado
- LP2: Organização e Memórias de Espaços Pedagógicos
  - MP4: História e memórias no contexto da EPT
  - MP5: Organização do currículo integrado na EPT
  - MP6: Organização de espaços pedagógicos na EPT

## Tipos de Produto

### No processo de extração
- eduCAPES `dc.type` e coleção são evidência complementar. Não substituem automaticamente o formato específico declarado na dissertação/ficha do produto.

### Classificação dos tipos
São 9 os tipos oficiais de produto educacional. A todo e qualquer produto se aplica um único tipo. Os tipos são: 

1. Material didático/instrucional  
  Propostas  de  ensino,  envolvendo  sugestões  de  experimentos  e  outras atividades práticas, sequências didáticas, propostas de intervenção, roteiros de oficinas; material textual, como manuais, guias,  textos  de apoio, artigos em  revistas  técnicas  ou  de  divulgação, livros  didáticos  e  paradidáticos,  histórias  em  quadrinhos  e  similares,  dicionários;  mídias educacionais, como vídeos, simulações, animações, videoaulas, experimentos virtuais e áudios; objetos  de  aprendizagem;  ambientes  de  aprendizagem;  páginas  de  internet  e  blogs;  jogos educacionais  de  mesa  ou  virtuais,  e  afins;  entre  outros;  

2. Curso/Oficina  de  Formação Profissional
  Cursos, oficinas, entre outros), com proposta detalhada, que tenha relação com a APCN; 

3. Tecnologia social 
  Produtos, dispositivos ou equipamentos; processos, procedimentos, técnicas  ou  metodologias;  serviços;  inovações  sociais  organizacionais;  inovações  sociais  de gestão, entre outros; 

4. Software/Aplicativo
  Aplicativos de modelagem, aplicativos de aquisição e análise de dados, plataformas virtuais e similares, programas de computador, entre outros; 

5. Evento Organizados
  Exposições científicas, olímpiadas, expedições, feiras e mostras científicas e atividades  de  divulgação  científica; 

6. Acervo
  Curadoria  de mostras e exposições  realizadas, acervos produzidos, curadoria de coleções, entre outros; 

7. Produto de comunicação
  Produto de  mídia,  criação  de  programa  de  rádio  ou  TV,  campanha  publicitária,  entre  outros;  

8. Manual/Protocolo
  Guia  de  instruções,  protocolo  tecnológico  experimental/  aplicação  ou adequação  tecnológica;  manual  de  operação,  manual  de  gestão,  manual  de  normas  e/ou procedimentos, entre outros; 

9. Carta/Mapa ou similar.

## Públicos-Alvo

Há 5 agrupamentos no que diz respeito ao público-alvo de um produto educacional. São eles:

1. Docentes e Professores
2. Estudantes e Alunos
3. Gestores e Coordenadores Escolares
4. Técnicos e Profissionais da Educação
5. Comunidade Externa


## Regra específica da base epistemológica

Base epistemológica é um campo interpretativo e não deve ser deduzido por lista de autores. O fluxo focado deve:

1. procurar evidência no resumo, introdução, referencial/fundamentação teórica e seção metodológica;
2. identificar autores/obras citados nos trechos que sustentam o argumento, com páginas;
3. localizar na seção de referências apenas as entradas correspondentes a essas citações (autor e, quando possível, ano/título);
4. pedir classificação assistida usando esses trechos e referências correspondentes, sem enviar o PDF inteiro;
5. retornar valor canônico ou abstenção, confiança, justificativa curta e evidências de texto e referência;
6. aceitar valor de alta confiança no JSON de trabalho; manter os demais para revisão na planilha.

Uma referência bibliográfica que não esteja ligada a uma citação/argumento pertinente não sustenta a classificação. Se só houver tema geral, nome isolado ou associação implícita, usar abstenção ou confiança baixa.

## Uso de GPT na etapa de dissertação

Quando a extração determinística não resolver a base, o GPT recebe somente o resumo e trechos localizados do referencial/fundamentação/metodologia, mais referências que correspondam a citações desses trechos. O modelo deve propor um candidato, justificar sua leitura e apontar evidência com página; não deve converter tema de pesquisa, linha/macroprojeto, objetivo do produto ou lista de referências em base epistemológica por associação. A saída é uma classificação assistida: só `alta` preenche `valor`; `media`, `baixa` ou abstenção mantêm `valor: null` e registram `candidato`, evidências e revisão pendente. Quando o texto sustenta mais de uma tradição sem declarar uma base dominante, registrar a formulação composta como hipótese ou abster-se, sem forçar uma categoria única.

## Metadados da dissertação

- `capa`: contém instituição, campus, autor, título, orientador, ano
- `resumo`: resumo da dissertação;
- `fichaCatalografica`: texto/campos bibliográficos úteis;
- `sumario`: títulos e hierarquia de seções, incluindo a introdução;
- `introducao`: texto extraído da seção de introdução;
- `palavrasChave`: lista, em geral extraída do resumo, quando disponível.

## Metadados do produto educacional

- `autoresColaboradores`: pessoas e seus papéis quando a fonte informar;
- `identificadores`: esquema, valor e URL, incluindo identificadores de outros hospedeiros;
- `dataPublicacao`: data ISO `YYYY-MM-DD` ou precisão menor se a fonte só fornecer ano/mês;
- `colecaoEduCAPES`: rótulo original de “Aparece nas coleções:”, separado do tipo educacional;
- `dcTypeEduCAPES`: valores originais de `dc.type`, separados da coleção e do tipo educacional canônico;
- `tipoProduto`: exatamente um tipo principal canônico; priorizar formato explicitamente descrito na dissertação/ficha do produto. Preservar `dc.type`, coleção, rótulo original e campo consultado em campos separados;
- `palavrasChave`: lista de termos fornecidos pelo eduCAPES.



