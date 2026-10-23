# Continuidade do trabalho — Projeto Leme EPT

Este arquivo é o ponto de entrada para continuar o projeto em outra máquina ou com outro agente. Leia na ordem: `CONTRATO_DADOS.md`, `DIAGRAMAS.md`, este documento e `LIMPEZA_TEMPORARIOS.md`.

## Estado conhecido em 2026-10-23

- Repositório: `https://github.com/regi-lpf/lemeept`.
- PR #1, [Corrige contagens do painel e documenta continuidade](https://github.com/regi-lpf/lemeept/pull/1), aparece como **merged**. Merge SHA informado pelo GitHub: `395110bb4e5bda5ba5126a0f50b80ba89bc635d2`.
- O checkout desta máquina está em `develop`, commit local `a653662` (`Corrige contagens do painel e documenta continuidade`), e aponta `origin/develop` em `6cc8d9c`. Portanto, o commit local está um commit à frente do tracking remoto neste checkout.
- Atenção à integridade do PR: o diff do PR publicado pelo GitHub mostrou alterações de finais de linha CRLF em grande parte dos arquivos, embora a alteração real local seja pequena. Antes de continuar, comparar o estado remoto com o commit/arquivos locais e evitar aceitar um diff puramente de formatação como nova base. Não fazer reset/force push. Se o remoto realmente tiver conteúdo diferente, abrir uma correção pequena e revisável.
- Branch de trabalho local: `develop`. Branch do PR: `codex/corrige-contagens-painel`.
- Este documento e o catálogo de temporários estão sendo preparados no checkout local; confirmar que ambos foram incluídos no remoto antes de depender deles na outra máquina.

## O que já foi feito

### Painel Elementor — correções prioritárias

Em `lemeept/index.html`:

- Orientadores contam defesas/alunos únicos, sem duplicar dissertação e produto.
- Tipos de produto contam uma vez por produto/defesa.
- Macroprojetos usam `codigoMacroprojeto` canônico para agrupar `MP3` e o rótulo legado “Macroprojeto 3”.
- Base conferida localmente: 110 defesas e 220 produções; MP3 consolida 42 produções (21 defesas).
- Legendas dos gráficos explicitam a unidade contada.
- O arquivo é um bloco de código para Elementor, não uma página HTML livre. Preservar sua estrutura de `<section>`, `<style>`, marcação e `<script>`; fazer mudanças focadas, revisar `<p>`/`<br>` e não substituir pelo HTML renderizado pelo editor.

### Pipeline e contrato

- `CONTRATO_DADOS.md` descreve entidades, campos, fontes, evidências e regras de contagem.
- `DIAGRAMAS.md` registra o pipeline existente e o fluxo/modelo desejados.
- As etapas de coleta, PDF e planilha foram ajustadas para transportar campos do eduCAPES e coorientador; os rótulos de coorientador são tratados em variantes.
- A estrutura de pipeline em `lemeept/pipeline/` e o construtor do JSON existente foram preparados para normalização, classificação e busca.
- O modelo de saída atualmente ainda representa defesa como registro com `quantidadeProducoes`; migrar para duas produções independentes é um objetivo posterior, não assumir que já foi implementado.

### Verificações anteriormente executadas

- `tests/test_pipeline.py`: 8 testes passaram no runtime disponível.
- Sintaxe do JavaScript embutido no painel foi validada com Node.
- `git diff --check` passou.
- `tests/test_fluxo.py` não importou no runtime usado por falta de `beautifulsoup4`; instalar dependências de `requirements.txt` antes de repetir.
- Essas verificações correspondem ao estado local anterior. Na máquina nova, repetir após conferir o remoto.

## Regras do produto já acordadas

1. Cada defesa tem acadêmico, orientador principal, dissertação (título/link) e produto educacional (título/link).
2. Há sempre uma dissertação e um produto por defesa. O modelo final deve expor **220 produções independentes**, com vínculo por `defesaId`, para 110 defesas.
3. Cada produto tem um tipo principal. “Aparece nas coleções:” do eduCAPES é evidência, mas a coleção e o tipo do produto são campos distintos.
4. Coorientadores são registrados e contados separadamente; não entram na contagem de orientadores principais.
5. Resumo, palavras-chave, introdução e títulos úteis do sumário apoiam busca específica. Guardar conteúdo e evidência/origem, sem depender de resumo truncado para busca.
6. Linhas oficiais: “Práticas Educativas em EPT” (MP1, MP2 e MP3) e “Organização e Memórias de Espaços Pedagógicos” (MP4, MP5 e MP6).
7. “Macroprojeto 3” e “MP3” são o mesmo macroprojeto. Não são categorias separadas; há uma defesa cuja classificação não foi consolidada corretamente no painel anterior.
8. Os “Resumo não disponível” do JSON antigo não serão corrigidos nesta fase; o fluxo novo deve registrar falhas de extração para revisão.
9. Bloco do painel publicado em Elementor deve ser alterado com cautela e em etapa separada da mudança de dados.

## Plano de ação detalhado

### 0. Preparar a máquina nova

1. Clonar `https://github.com/regi-lpf/lemeept` ou atualizar o clone existente.
2. Conferir `git status`, branch padrão e histórico de `develop`; localizar o merge do PR #1.
3. Revisar o diff do merge e finais de linha nos arquivos alterados. A publicação do PR apresentou diff CRLF amplo; separar mudanças funcionais de ruído antes de continuar.
4. Ler este guia, `CONTRATO_DADOS.md`, `DIAGRAMAS.md` e `LIMPEZA_TEMPORARIOS.md`.
5. Criar ambiente virtual e instalar `requirements.txt`. Não copiar caches/pastas de execução da máquina antiga.
6. Executar os testes existentes e registrar dependências/erros antes de alterar o pipeline.

**Aceite:** checkout limpo e entendido; commit/PR de referência identificado; testes de base registrados.

### 1. Fechar validação do painel atual

1. Conferir no JSON a relação 110 defesas → 220 produções, hoje codificada por `quantidadeProducoes`.
2. Conferir orientadores por defesa única, coorientadores separados, e tipos por produto único.
3. Conferir MP3 consolidado (42 produções/21 defesas) e a defesa que estava sob rótulo “Macroprojeto 3”.
4. Validar em ambiente de teste WordPress/Elementor com cache limpo; só então copiar o bloco para o site publicado.
5. Fazer uma inspeção visual do bloco após salvar no Elementor, incluindo quebras e parágrafos, filtros, busca e contagens.

**Aceite:** números e comportamento batem com o JSON e não há regressão no editor/renderização Elementor. Não considerar implementação local como publicação automática no WordPress.

### 2. Preparar amostra de extração

1. Obter um pequeno conjunto representativo de defesas reais, cobrindo PDF legível, variação de ficha/resumo/sumário, coorientador, campos eduCAPES ausentes e metadados divergentes.
2. Guardar fixtures de teste em pasta dedicada e documentada, evitando redistribuir PDFs protegidos ou dados pessoais além do necessário. Preferir textos mínimos anonimizados quando bastarem.
3. Registrar resultado esperado e evidências (campo, página/trecho ou URL) manualmente para esse conjunto.

**Aceite:** existe amostra reproduzível que cobre casos comuns e casos-limite; origem e restrições estão documentadas.

### 3. Implementar extração determinística primeiro

1. Extrair metadados estruturados da página oficial e eduCAPES (autores/colaboradores, identificadores, publicação, tipo, palavras-chave e coleção).
2. Baixar/ler PDF e extrair texto com prioridade para ficha catalográfica, resumo, palavras-chave, sumário e introdução.
3. Extrair coorientador por rótulos conhecidos, com teste de variações de gênero/acentuação/hífen.
4. Guardar evidência, método, confiança/estado e erro por campo, sem descartar conteúdo bruto útil para busca.
5. Usar OCR como fallback somente quando a extração textual não cobrir o campo.

**Aceite:** campos estáveis são obtidos sem GPT e cada campo extraído pode ser auditado até a fonte; falhas são explícitas.

### 4. Adicionar classificação e pesquisa específica

1. Definir vocabulários/aliases explícitos para linha de pesquisa e macroprojetos, incluindo MP3 canônico.
2. Procurar evidências nos metadados, resumo, introdução e sumário; não confiar em uma única posição fixa do PDF.
3. Usar regras determinísticas quando houver evidência direta; encaminhar ambiguidade para busca/classificador assistido e revisão humana.
4. Preservar termos de busca específicos (resumo, palavras-chave, introdução e termos extraídos), separando-os do resumo curto de exibição.
5. Comparar resultados com classificação histórica e registrar divergências, sem sobrescrever decisões validadas silenciosamente.

**Aceite:** toda classificação tem evidência rastreável; casos duvidosos ficam marcados para revisão, não recebem certeza artificial.

### 5. Migrar o contrato de saída e contagens

1. Representar dissertação e produto como registros distintos com IDs próprios e `defesaId` comum.
2. Manter uma dissertação e um produto por defesa; representar 220 produções mesmo quando certos metadados faltarem.
3. Contar tipos de produto sobre produtos; orientadores/alunos sobre defesas; coorientadores em dimensão própria.
4. Validar invariantes e IDs únicos no gerador de JSON; rejeitar duplicação estrutural.
5. Só depois da saída estável adaptar o painel para o novo esquema.

**Aceite:** 220 registros de produção, 110 vínculos de defesa completos, sem duplicação de orientador/tipo; painel e JSON concordam.

### 6. Atualizar o site Elementor em etapa própria

1. Planejar o novo painel com Linha de Pesquisa antes de Macroprojetos.
2. Usar “trabalhos analisados” conforme a unidade e exibir contagens derivadas do JSON, sem números fixos em placeholders.
3. Preservar filtros, acessibilidade e integração atual; editar o bloco Elementor com diff mínimo.
4. Validar primeiro em staging/rascunho; depois publicar e verificar caches.

**Aceite:** conteúdo e contagens são dinâmicos; Linha de Pesquisa está no local combinado; nenhuma estrutura Elementor foi quebrada.

## Limpeza e preservação

Consultar `LIMPEZA_TEMPORARIOS.md` antes de remover qualquer arquivo. O catálogo distingue caches regeneráveis de artefatos potencialmente revisados ou fontes que exigem cópia de segurança. Arquivos locais ignorados pelo Git não são sincronizados para outra máquina.

## Instruções para agentes futuros

- Comece verificando o estado do Git e lendo o contrato; não assuma que o diretório sincronizou dados não versionados.
- Não fazer reset/force push para “limpar” o PR sem comparar conteúdo e obter um caminho de correção revisável.
- Não contar cada defesa duas vezes como orientador ou tipo; as duas produções são unidades independentes apenas para a contagem de produções.
- Canonicalizar macroprojeto por código, não por rótulo bruto.
- Não inferir tipo específico somente pela coleção eduCAPES.
- Não modificar o JSON legado nem corrigir os resumos ausentes durante a nova extração sem escopo específico.
- Não colar no Elementor HTML renderizado/copiado do navegador; preservar `<br>`/`<p>` e a estrutura do widget.

