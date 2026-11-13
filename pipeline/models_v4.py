from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
# ENUMS / LITERALS CANÔNICOS (v4)
# =====================================================================

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


# =====================================================================
# CONTRATO 1: PRÉ-EXTRAÇÃO (STAGE 1)
# =====================================================================

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


# =====================================================================
# CONTRATO 2: EXTRAÇÃO DETERMINÍSTICA / PAYLOAD LLM (STAGE 2)
# =====================================================================

class AutorColaboradorV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str
    papel: Optional[str] = None


class IdentificadorProdutoV4(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


# =====================================================================
# CONTRATO 3: REGISTRO FINAL VALIDADO / SAÍDA LLM (STAGE 3 & 4)
# =====================================================================

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