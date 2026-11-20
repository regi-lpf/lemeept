import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, Tuple

RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


@lru_cache(maxsize=None)
def _carregar_recurso(nome_arquivo: str) -> Dict[str, Any]:
    caminho = RESOURCES_DIR / nome_arquivo
    return json.loads(caminho.read_text(encoding="utf-8"))


_tax = _carregar_recurso("taxonomia.json")
_pes = _carregar_recurso("pessoas.json")
_ref = _carregar_recurso("referencias.json")

# --- Taxonomia ---
MP_PARA_LP: Dict[str, str] = dict(_tax["mp_para_lp"])
BASES_EPISTEMOLOGICAS_CANONICAS: Tuple[str, ...] = tuple(
    _tax["bases_epistemologicas_canonicas"]
)
ALIASES_BASE_EPISTEMOLOGICA: Dict[str, str] = dict(_tax["aliases_base_epistemologica"])
NIVEIS_APLICACAO_CANONICOS: Tuple[str, ...] = tuple(_tax["niveis_aplicacao_canonicos"])
ALIASES_NIVEL_APLICACAO: Dict[str, str] = dict(_tax["aliases_nivel_aplicacao"])

# --- Pessoas / Docentes / Coorientação ---
PREPOSICOES_NOME: FrozenSet[str] = frozenset(_pes["preposicoes_nome"])
PARTICULAS_NOME_COMPLETO: FrozenSet[str] = frozenset(_pes["particulas_nome_completo"])
ALIASES_DOCENTES: Dict[str, str] = dict(_pes["aliases_docentes"])
PLACEHOLDERS_COORIENTADOR: FrozenSet[str] = frozenset(_pes["placeholders_coorientador"])
STOPWORDS_CONTINUACAO_NOME: FrozenSet[str] = frozenset(_pes["stopwords_continuacao_nome"])
STOPWORDS_PROSA_NOME: FrozenSet[str] = frozenset(_pes["stopwords_prosa_nome"])

# --- Referências Bibliográficas ABNT ---
STOPWORDS_ENTIDADE_REF: FrozenSet[str] = frozenset(_ref["stopwords_entidade"])
STOPWORDS_TOKEN_NAO_PESSOA: FrozenSet[str] = frozenset(_ref["stopwords_token_nao_pessoa"]) | {
    ent for ent in STOPWORDS_ENTIDADE_REF if " " not in ent
}
SIGLAS_UF_PAIS: FrozenSet[str] = frozenset(_ref["siglas_uf_pais"])
SOBRENOMES_CURTOS_VALIDOS: FrozenSet[str] = frozenset(_ref["sobrenomes_curtos_validos"])
ALIASES_AUTORES_REFERENCIA: Dict[str, str] = {
    **ALIASES_DOCENTES,
    **_ref["aliases_autores_referencia"],
}
VALORES_CANONICOS_AUTORES_REF: FrozenSet[str] = frozenset(
    ALIASES_AUTORES_REFERENCIA.values()
)
