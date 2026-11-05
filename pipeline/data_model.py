from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

class TipoProduto(str, Enum):
    MATERIAL_DIDATICO="material_didatico_instrucional"
    CURSO_OFICINA="curso_oficina"
    TECNOLOGIA_SOCIAL="tecnologia_social"
    SOFTWARE_APLICATIVO="software_aplicativo"
    EVENTOS_ORGANIZADOS="eventos_organizados"
    ACERVO="acervo"
    PRODUTO_COMUNICACAO="produto_comunicacao"
    MANUAL_PROTOCOLO="manual_protocolo"
    CARTA_MAPA="carta_mapa"
    PENDENTE_REVISAO="pendente_revisao"

class PublicoAlvo(str, Enum):
    ESTUDANTES="estudantes"
    DOCENTES="docentes"
    DISCENTES="discentes"
    SERVIDORES_PROFISSIONAIS="servidores_profissionais"
    GESTAO_EQUIPES_INSTITUCIONAIS="gestao_equipes_institucionais"

@dataclass
class Pessoa:
    nome: str
    id: Optional[str] = None

@dataclass
class MacroProjeto:
    codigo: str
    nome: str

@dataclass
class LinhaPesquisa:
    codigo: str
    nome: str

@dataclass
class Defesa:
    cod: str
    titulo: str
    autor: Pessoa
    orientador: Pessoa
    campus: str
    linha_pesquisa: LinhaPesquisa
    macroprojeto: MacroProjeto
    dissertacao: Dissertacao
    produto: Produto
    coorientador: Optional[Pessoa] = None
    ano: Optional[int] = None

@dataclass
class Dissertacao:    
    id: str
    titulo: str
    resumo: str
    palavras_chave: List[str]
    link: Optional[str] = None
    area_tematica: Optional[str] = None

@dataclass
class Produto:
    id: str
    titulo: str
    tipo_produto: TipoProduto
    palavras_chave: List[str] = field(default_factory=list)
    link: Optional[str] = None
    nivel_aplicacao: Optional[str] = None
    publico_alvo: Optional[List[PublicoAlvo]] = None
    score_classificacao: float = 0.0

@dataclass
class PainelV3:
    versao: str = "3.0"
    total_defesas: int = 0
    defesas: List[Defesa] = field(default_factory=list)
