# Relatório Consolidado de Arquitetura e Contratos — Pipeline v4 (LEME / ProfEPT)

## 1. Visão Geral e Viabilidade Operacional

A pipeline de extração, normalização e compilação do acervo **ProfEPT (IFC Blumenau)** está consolidada na **versão 4.0**, operando em 4 etapas modulares com validação estrita via **Pydantic v2** (`pipeline/models_v4.py`).

* **Volume do Acervo:** 111 defesas catalogadas (`EPT-0001` a `EPT-0111`), totalizando **222 produções** (111 dissertações + 111 produtos educacionais).
* **Orçamento de Contexto e Tokens (Viável em LLM Local — 8 GB VRAM):**
  * **Input médio:** ~9.000 tokens (isolamento cirúrgico de seções relevantes em JSON compacto, eliminando o envio de PDFs integrais e listas completas de referências).
  * **Output médio:**
    * **Payload JSON final (`RespostaInterpretativaLLM`):** ~400–500 tokens (campos interpretativos enxutos, hidratados deterministicamente em Python na pós-extração).
    * **Orçamento total de geração (incluindo *reasoning/thinking tokens*):** até ~10.000 tokens quando executado em modelos com cadeia de pensamento ativa (`gemini-2.5-flash` / modelos *thinking*). Para execução local em **8 GB de VRAM**, recomenda-se desativar o modo *thinking* (ex.: `think=False` no Ollama ou `thinking_budget=0` na API) ou utilizar modelos *instruct* diretos (como `qwen2.5:7b-instruct` ou `ministral-3:8b`), mantendo o consumo real de saída próximo ao tamanho do JSON (~500 tokens) e dentro da janela de `num_ctx=8192`.

---

## 2. Histórico de Execução e Fixes Técnicos por Etapa

### Etapa 1: Coleta e Pré-Extração (`pipeline/step1_collect.py`) — Concluída
Gera o manifesto `data/stage1_manifest.json` (`Stage1ManifestV4`) e realiza o download local dos PDFs em `pdf/dissertacoes/EPT-XXXX.pdf` com verificação de assinatura mágica (`%PDF-`) e hash `SHA-256`.

* **SSL Institucional (`profept.ifc.edu.br` / `.edu.br`):** Contorno de cadeia intermediária incompleta (`SSLCertVerificationError`) via `verify=False` com supressão explícita de `InsecureRequestWarning`.
* **Parser Sequencial Independente de DOM:** Contorno de listas `<ul>` mal fechadas na API do WordPress percorrendo os elementos `<li>` sequencialmente com `Acadêmico/Discente/Autor:` como delimitador.
* **Flexibilidade de Rótulos e Pontuação:** Regex tolerante a variações manuais (`Dissertação:`, `Dissertação intitulada`, `Artigo:`, `Orientador:` / `Orientadora:`).
* **Preservação do Rótulo Bruto do Produto:** Captura de prefixos declarados antes do link na página de origem no campo `titulo_produto_bruto` (ex.: `"Texto – "`, `"Podcast – "`, `"Curso – "`, `"Sequência Didática: "`).
* **Fallback de Ano:** Extração pelos cabeçalhos `DEFESAS YYYY` no DOM com fallback via regex na URL (`/uploads/sites/54/YYYY/`).

---

### Etapa 2: Extração Determinística (`pipeline/step2_deterministic.py`) — Concluída e Reprocessada (111/111)
Gera os 111 payloads estruturados em `data/stage2_payloads/EPT-0001.json` a `EPT-0111.json` (`ContratoExtracaoDeterministicaV4`).

* **Varredura Taxonômica Integral & Vínculo Rígido (`MP1–3 → LP1` | `MP4–6 → LP2`):** Busca integral no PDF com normalização de espaços colados e numeração romana/arábica. Correção de regex em `detectar_macroprojeto_e_linha` adicionando grupo de captura explícito `(4)` com *negative lookahead* anti-extensão de vídeo (`.mp4`), resolvendo falha `IndexError: no such group` no registro `EPT-0100`.
* **Mapeamento Determinístico de Autores Referenciados (`autores_referenciados`):**
  * Assinatura de `isolar_secoes_pdf` atualizada para retornar `(RecortesTextuais, texto_refs)`, expondo até 25 páginas a partir de `REFERÊNCIAS` / `REFERÊNCIAS BIBLIOGRÁFICAS` sem inflar o recorte `referencias_filtradas` enviado à LLM.
  * Extrator ABNT (`extrair_autores_referencias`) captura sobrenomes em caixa alta (`SOBRENOME, Nome` com suporte a acentuação e cedilha), normaliza partículas compostas (`DA`, `DE`, `DO`, `DAS`, `DOS`, `DEL`, `VON`, `VAN`) e descarta entidades institucionais/legais (`BRASIL`, `SANTA CATARINA`, `MINISTÉRIO`, `CAPES`, `MEC`, `IBID`, `IDEM`, `DISPONÍVEL`, etc.), gerando lista única, ordenada e capitalizada (ex.: `["Ciavatta", "Freire", "Frigotto", "Saviani"]`).
* **Hierarquia de Fontes para Produto Educacional:** Priorização do `titulo_produto_bruto` e da sentença exata onde ocorre *"produto educacional"* no corpo da dissertação, evitando falsos positivos com termos do contexto da pesquisa. Metadados do eduCAPES (`dc.type`, coleção, `<meta>` Dublin Core e `?show=full`, com cache em `data/cache_educapes/`) são preservados como evidência complementar.
* **Isolamento Cirúrgico de Recortes Textuais:** Extração isolada de capa, ficha catalográfica, sumário, resumo, introdução, descrição do produto, trechos com marcadores epistemológicos (preservando `[PÁG. X]`) e apenas as referências bibliográficas correspondentes às citações detectadas.

---

### Etapa 3: Inferência Semântica Estruturada (`pipeline/llm_provider.py` + `pipeline/step3_llm_extract.py`) — Concluída
Consome `pipeline/SKILL.md` e os payloads da Etapa 2, gerando registros individuais validados em `data/records/EPT-XXXX.json` (`ContratoDefesaV4`).

* **Camada Modular Agnóstica (`LLMClient`):** Suporte intercambiável entre SDK oficial `google-genai` (`gemini-2.5-flash`) e endpoints OpenAI-compatíveis (`ollama` local, `groq`, `openrouter`, `mistral`) via variáveis de ambiente.
* **Sanitização de Schemas e Serialização:** Remoção de `additionalProperties` incompatível com OpenAPI Schema do Gemini, expansão inline de `$defs`/`$ref` e serialização explícita de submodelos via `.model_dump()`.
* **Hidratação Determinística e Repasse Passivo (`montar_registro_final`):**
  * Imposição obrigatória do vínculo taxonômico `MP1–3 → LP1` e `MP4–6 → LP2`.
  * Repasse direto de `dis_det.autores_referenciados` para `dissertacao.autores_referenciados` sem trafegar a lista no prompt da LLM (zero impacto em tokens e isolamento estrito entre referências gerais e evidência epistemológica).
  * Incorporação dos `autores_referenciados` ao `indice_busca.texto_busca_normalizado` (`construir_indice_busca`).
  * Trava de confiança na `base_epistemologica`: apenas classificações com `confianca == "alta"` e evidência localizável (`secao`, `pagina`, `trecho`) preenchem `valor`; demais casos mantêm `valor: null` e `revisao_pendente: true`.
* **Decisão Operacional:** A extração automatizada foi encerrada; ajustes remanescentes em `base_epistemologica` serão realizados exclusivamente via curadoria humana.

---

### Etapa 4: Compilação e Curadoria (`pipeline/step4_compile.py`) — Concluída
Consolida os registros individuais de `data/records/` nos artefatos finais de publicação e revisão:

* **`dist/painel-ept-v4.json`:** Artefato único validado contendo metadados de compilação, contadores totais e a lista completa de `ContratoDefesaV4` com `indice_busca` pré-calculado.
* **`dist/revisao_epistemologica_pendente.csv`:** Planilha delimitada por ponto e vírgula (`UTF-8-SIG`) exportando apenas registros com `revisao_pendente == true`, acompanhados de candidato sugerido, justificativa, seção, página e trecho de evidência.

---

## 3. Contratos de Dados (Modelos Pydantic v2 — `pipeline/models_v4.py`)

### Enums e Tipos Canônicos

```python
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

LinhaPesquisaCode = Literal["LP1", "LP2"]
MacroprojetoCode = Literal["MP1", "MP2", "MP3", "MP4", "MP5", "MP6"]

TipoProdutoSlug = Literal[
    "material_didatico_instrucional",
    "curso_oficina",
    "tecnologia_social",
    "software_aplicativo",
    "eventos_organizados",
    "acervo",
    "produto_comunicacao",
    "manual_protocolo",
    "carta_mapa",
]

PublicoAlvoSlug = Literal[
    "docentes_professores",
    "estudantes_alunos",
    "gestores_coordenadores",
    "tecnicos_profissionais_educacao",
    "comunidade_externa",
]

ConfiancaEpistemologica = Literal["alta", "media", "baixa", "abstencao"]
FonteTipoProduto = Literal["dissertacao_ficha", "educapes_dc_type", "inferencia_llm"]

```

---

### Contrato 1: Saída da Pré-Extração (`Stage1ManifestV4`)

```python
class FonteProfeptV4(BaseModel):
    titulo_bruto: str
    autor_bruto: str
    orientador_bruto: Optional[str] = None
    ano: int
    campus: str = "IFC Blumenau"
    url_dissertacao: str
    titulo_produto_bruto: Optional[str] = None
    handle_educapes: Optional[str] = None


class ArquivosDefesaV4(BaseModel):
    pdf_dissertacao_path: str
    sha256_dissertacao: str
    pdf_produto_path: Optional[str] = None
    status_download: Literal["OK", "ERRO_HTTP", "CORROMPIDO"]


class PreExtracaoItemV4(BaseModel):
    id: str = Field(..., pattern=r"^EPT-[0-9]{4}$")
    coletado_em: str = Field(default_factory=lambda: datetime.now().astimezone().isoformat())
    fonte_profept: FonteProfeptV4
    arquivos: ArquivosDefesaV4


class Stage1ManifestV4(BaseModel):
    schema_version: str = "4.0"
    gerado_em: str = Field(default_factory=lambda: datetime.now().astimezone().isoformat())
    total_registros: int
    registros: List[PreExtracaoItemV4]

```

---

### Contrato 2: Saída da Extração Determinística (`ContratoExtracaoDeterministicaV4`)

```python
class AutorColaboradorV4(BaseModel):
    nome: str
    papel: Optional[str] = None


class IdentificadorProdutoV4(BaseModel):
    esquema: str
    valor: str
    url: Optional[str] = None


class MetadadosResolvidos(BaseModel):
    ano: int
    autor: str
    orientador: str
    coorientadores: List[str] = Field(default_factory=list)
    instituicao: str = "Instituto Federal Catarinense (IFC)"
    campus: str = "Blumenau"
    linha_pesquisa: str
    macroprojeto: str


class DissertacaoDeterministica(BaseModel):
    titulo: str
    link: str
    palavras_chave: List[str] = Field(default_factory=list)
    autores_referenciados: List[str] = Field(default_factory=list)


class EvidenciasEduCAPES(BaseModel):
    handle_url: Optional[str] = None
    titulo_produto: Optional[str] = None
    data_publicacao: Optional[str] = None
    autores_colaboradores: List[AutorColaboradorV4] = Field(default_factory=list)
    identificadores: List[IdentificadorProdutoV4] = Field(default_factory=list)
    colecao_educapes: Optional[str] = None
    dc_type_educapes: List[str] = Field(default_factory=list)
    palavras_chave_educapes: List[str] = Field(default_factory=list)
    tipo_produto_regex: Optional[str] = None


class TrechoEpistemologico(BaseModel):
    secao: str
    pagina: int
    texto: str
    citacoes_detectadas: List[str] = Field(default_factory=list)


class RecortesTextuais(BaseModel):
    capa: str = ""
    ficha_catalografica: str = ""
    sumario: str = ""
    resumo: str = ""
    introducao: str = ""
    descricao_produto_na_dissertacao: str = ""
    trechos_epistemologicos: List[TrechoEpistemologico] = Field(default_factory=list)
    referencias_filtradas: List[str] = Field(default_factory=list)


class ContratoExtracaoDeterministicaV4(BaseModel):
    id: str
    metadados_resolvidos: MetadadosResolvidos
    dissertacao_deterministica: DissertacaoDeterministica
    evidencias_educapes: EvidenciasEduCAPES
    recortes_textuais: RecortesTextuais

```

---

### Contrato Intermediário: Saída Enxuta da LLM (`RespostaInterpretativaLLM`)

```python
class EvidenciaCurtaLLM(BaseModel):
    secao: str
    pagina: int
    trecho_curto: str = Field(..., description="Citação literal curta de até 180 caracteres")
    referencia_correspondente: Optional[str] = None


class BaseEpistemologicaLLM(BaseModel):
    valor: Optional[str] = None
    candidato: Optional[str] = None
    confianca: ConfiancaEpistemologica
    justificativa: str = Field(..., description="Explicação objetiva em no máximo 2 frases")
    evidencias: List[EvidenciaCurtaLLM] = Field(default_factory=list)


class RespostaInterpretativaLLM(BaseModel):
    macroprojeto: MacroprojetoCode
    produto_titulo: str
    produto_tipo: TipoProdutoSlug
    produto_publico_alvo: List[PublicoAlvoSlug] = Field(default_factory=list)
    produto_nivel_aplicacao: str
    base_epistemologica: BaseEpistemologicaLLM

```

---

### Contrato 3: Registro Final Validado (`ContratoDefesaV4`)

```python
class EvidenciaEpistemologicaV4(BaseModel):
    secao: str
    pagina: int
    trecho: str
    referencia_correspondente: Optional[str] = None


class BaseEpistemologicaV4(BaseModel):
    valor: Optional[str] = None
    candidato: Optional[str] = None
    confianca: ConfiancaEpistemologica
    revisao_pendente: bool
    justificativa: str
    evidencias: List[EvidenciaEpistemologicaV4] = Field(default_factory=list)


class DissertacaoFinalV4(BaseModel):
    titulo: str
    link: str
    resumo: str
    palavras_chave: List[str] = Field(default_factory=list)
    autores_referenciados: List[str] = Field(default_factory=list)
    base_epistemologica: BaseEpistemologicaV4


class ProvenienciaProdutoV4(BaseModel):
    fonte_tipo_escolhida: FonteTipoProduto
    rotulo_original_declarado: Optional[str] = None
    colecao_educapes: Optional[str] = None
    dc_type_educapes: List[str] = Field(default_factory=list)


class ProdutoFinalV4(BaseModel):
    titulo: str
    tipo: TipoProdutoSlug
    link: Optional[str] = None
    publico_alvo: List[PublicoAlvoSlug] = Field(default_factory=list)
    nivel_aplicacao: str
    palavras_chave: List[str] = Field(default_factory=list)
    data_publicacao: Optional[str] = None
    autores_colaboradores: List[AutorColaboradorV4] = Field(default_factory=list)
    identificadores: List[IdentificadorProdutoV4] = Field(default_factory=list)
    proveniencia: ProvenienciaProdutoV4


class IndiceBuscaV4(BaseModel):
    texto_busca_normalizado: str
    termos_unificados: List[str] = Field(default_factory=list)
    tem_produto_vinculado: bool
    tem_resumo: bool


class ContratoDefesaV4(BaseModel):
    schema_version: str = "4.0"
    id: str = Field(..., pattern=r"^EPT-[0-9]{4}$")
    ano: int
    autor: str
    orientador: str
    coorientadores: List[str] = Field(default_factory=list)
    instituicao: str
    campus: str
    linha_pesquisa: LinhaPesquisaCode
    macroprojeto: MacroprojetoCode
    dissertacao: DissertacaoFinalV4
    produto: ProdutoFinalV4
    indice_busca: IndiceBuscaV4

```

---

## 4. Integração e Consolidação do Frontend (Painel Bibliométrico v4) — Concluída

Com o artefato `dist/painel-ept-v4.json` validado por `PainelEptV4Output` / `ContratoDefesaV4`, o widget HTML/CSS/JS autocontido para Elementor (WordPress) e servidor HTTP local foi consolidado em [index.html](index.html), preservando o legado v3 em [index-v3.html](index-v3.html):

1. **Adaptação Integral ao Contrato v4 e Regras de Domínio:**
   * Leitura de `gerado_em`, `dissertacao.autores_referenciados`, `dissertacao.base_epistemologica` (distinguindo bases consolidadas, registros `revisao_pendente: true` e não declarados), `produto.tipo`, `produto.publico_alvo`, `produto.nivel_aplicacao`, `produto.data_publicacao`, `produto.proveniencia`, `produto.identificadores` e `indice_busca`.
   * Camada `I18N` completa para `LP1`..`LP2`, `MP1`..`MP6`, 9 tipos CAPES, 5 públicos-alvo e fontes de tipologia, com enriquecimento de `texto_busca_normalizado` e consolidação canônica de orientadores (**21** chaves únicas) e instituição/campus.
   * Resolução automática entre `data-json-url-local` (`./dist/painel-ept-v4.json` em `localhost`) e `data-json-url` (publicação em produção).

2. **Dashboard Interativo (*Cross-Filtering*), Layout Compacto e Rankings Completos:**
   * Separação de escopos (**Todas**, **Dissertações** e **Produtos Educacionais**), grade compacta `3 × 3` (`2 × 2` em **Produtos**) com animações estilo BI por reconciliação de DOM (`dataset.barKey`), ordenação configurável (`ano_desc` padrão) e modo **Tabela** com acesso ao modal de detalhes e fallback responsivo automático para **Cartões** em telas menores (`<= 720px`).
   * Todos os **9 gráficos** e os **3 cards categóricos de destaque** operam como filtros interativos bidirecionais (clique/teclado alterna o filtro em sincronia com os `<select>` e chips ativos), mantendo evidências epistemológicas e proveniência eduCAPES em um bloco `<details>` recolhido no modal.
   * Botão `"Ver todos"` nos cards **Autores mais referenciados** e **Orientadores** abre modal expansível unificado (`abrirModalRanking` / `RANKING_CONFIGS`) com busca por nome, cortes adaptáveis (`Todos`, `≥ 2`, `≥ 5`, `≥ 10` — iniciando em `≥ 5` para autores e `Todos` para orientadores), ordenação, paginação (`30` itens/página), clique para filtrar com fechamento automático e exportação `.CSV` do ranking.

3. **Segurança, Acessibilidade e Performance (`FE-01` a `FE-24`):**
   * Sanitização resiliente (`escapeHtml` Unicode, `sanitizarUrl` `http:`/`https:`, `csvEscape` anti-*Formula Injection*), contraste WCAG 2.1 AA (`>= 4.5:1`), *focus trap* no modal, remoção de `backdrop-filter`, índice facetado em memória (`indiceFacetas`) e otimização de busca/destaque (*fast-path* e recorte de resumo nos cards). Detalhes completos em [AUDITORIA_E_REFATORACAO.md](AUDITORIA_E_REFATORACAO.md).
