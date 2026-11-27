import json
import re
import unicodedata
from functools import cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, Optional, Tuple

RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


@cache
def _carregar_recurso(nome_arquivo: str) -> Dict[str, Any]:
    caminho = RESOURCES_DIR / nome_arquivo
    return json.loads(caminho.read_text(encoding="utf-8"))


def _chave_normalizada_simples(texto: str) -> str:
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", (texto or "").lower()) if not unicodedata.combining(c)
    )
    limpo = re.sub(r"[^a-z0-9\s]", " ", sem_acentos)
    return re.sub(r"\s+", " ", limpo).strip()


MP_PARA_LP: Dict[str, str] = {}
BASES_EPISTEMOLOGICAS_CANONICAS: Tuple[str, ...] = ()
ALIASES_BASE_EPISTEMOLOGICA: Dict[str, str] = {}
NIVEIS_APLICACAO_CANONICOS: Tuple[str, ...] = ()
ALIASES_NIVEL_APLICACAO: Dict[str, str] = {}
FORMATOS_PRODUTO_CANONICOS: Tuple[str, ...] = ()
ALIASES_FORMATO_PRODUTO: Dict[str, str] = {}

PREPOSICOES_NOME: FrozenSet[str] = frozenset()
PARTICULAS_NOME_COMPLETO: FrozenSet[str] = frozenset()
ALIASES_DOCENTES: Dict[str, str] = {}
PLACEHOLDERS_COORIENTADOR: FrozenSet[str] = frozenset()
STOPWORDS_CONTINUACAO_NOME: FrozenSet[str] = frozenset()
STOPWORDS_PROSA_NOME: FrozenSet[str] = frozenset()
PREFIXOS_NAO_PESSOA: Tuple[str, ...] = ()

STOPWORDS_ENTIDADE_REF: FrozenSet[str] = frozenset()
STOPWORDS_TOKEN_NAO_PESSOA: FrozenSet[str] = frozenset()
SIGLAS_UF_PAIS: FrozenSet[str] = frozenset()
SOBRENOMES_CURTOS_VALIDOS: FrozenSet[str] = frozenset()
ALIASES_AUTORES_REFERENCIA: Dict[str, str] = {}
VALORES_CANONICOS_AUTORES_REF: FrozenSet[str] = frozenset()


def resetar_catalogos() -> None:
    """Restaura todas as coleções de catálogo para os valores base embutidos no pacote."""
    global MP_PARA_LP
    global BASES_EPISTEMOLOGICAS_CANONICAS
    global ALIASES_BASE_EPISTEMOLOGICA
    global NIVEIS_APLICACAO_CANONICOS
    global ALIASES_NIVEL_APLICACAO
    global FORMATOS_PRODUTO_CANONICOS
    global ALIASES_FORMATO_PRODUTO
    global PREPOSICOES_NOME
    global PARTICULAS_NOME_COMPLETO
    global ALIASES_DOCENTES
    global PLACEHOLDERS_COORIENTADOR
    global STOPWORDS_CONTINUACAO_NOME
    global STOPWORDS_PROSA_NOME
    global PREFIXOS_NAO_PESSOA
    global STOPWORDS_ENTIDADE_REF
    global STOPWORDS_TOKEN_NAO_PESSOA
    global SIGLAS_UF_PAIS
    global SOBRENOMES_CURTOS_VALIDOS
    global ALIASES_AUTORES_REFERENCIA
    global VALORES_CANONICOS_AUTORES_REF

    tax = _carregar_recurso("taxonomia.json")
    pes = _carregar_recurso("pessoas.json")
    ref = _carregar_recurso("referencias.json")

    MP_PARA_LP = dict(tax["mp_para_lp"])
    BASES_EPISTEMOLOGICAS_CANONICAS = tuple(tax["bases_epistemologicas_canonicas"])
    ALIASES_BASE_EPISTEMOLOGICA = dict(tax["aliases_base_epistemologica"])
    NIVEIS_APLICACAO_CANONICOS = tuple(tax["niveis_aplicacao_canonicos"])
    ALIASES_NIVEL_APLICACAO = dict(tax["aliases_nivel_aplicacao"])
    FORMATOS_PRODUTO_CANONICOS = tuple(tax["formatos_produto_canonicos"])
    ALIASES_FORMATO_PRODUTO = dict(tax["aliases_formato_produto"])

    PREPOSICOES_NOME = frozenset(pes["preposicoes_nome"])
    PARTICULAS_NOME_COMPLETO = frozenset(pes["particulas_nome_completo"])
    ALIASES_DOCENTES = dict(pes["aliases_docentes"])
    PLACEHOLDERS_COORIENTADOR = frozenset(pes["placeholders_coorientador"])
    STOPWORDS_CONTINUACAO_NOME = frozenset(pes["stopwords_continuacao_nome"])
    STOPWORDS_PROSA_NOME = frozenset(pes["stopwords_prosa_nome"])
    PREFIXOS_NAO_PESSOA = tuple(pes.get("prefixos_nao_pessoa", ()))

    STOPWORDS_ENTIDADE_REF = frozenset(ref["stopwords_entidade"])
    STOPWORDS_TOKEN_NAO_PESSOA = frozenset(ref["stopwords_token_nao_pessoa"]) | {
        ent for ent in STOPWORDS_ENTIDADE_REF if " " not in ent
    }
    SIGLAS_UF_PAIS = frozenset(ref["siglas_uf_pais"])
    SOBRENOMES_CURTOS_VALIDOS = frozenset(ref["sobrenomes_curtos_validos"])
    ALIASES_AUTORES_REFERENCIA = {
        **ALIASES_DOCENTES,
        **ref["aliases_autores_referencia"],
    }
    VALORES_CANONICOS_AUTORES_REF = frozenset(ALIASES_AUTORES_REFERENCIA.values())


def _normalizar_conjunto_str(itens: Optional[Iterable[str]]) -> FrozenSet[str]:
    if not itens:
        return frozenset()
    return frozenset(chave for s in itens if s and (chave := _chave_normalizada_simples(s)))


def _normalizar_dict_chaves(mapa: Optional[Dict[str, str]]) -> Dict[str, str]:
    if not mapa:
        return {}
    out: Dict[str, str] = {}
    for k, v in mapa.items():
        chave = _chave_normalizada_simples(k)
        val = (v or "").strip()
        if chave and val:
            out[chave] = val
    return out


def _estender_tupla_unica(base: Tuple[str, ...], extras: Optional[Iterable[str]], *, lower: bool = False) -> Tuple[str, ...]:
    if not extras:
        return base
    atuais = list(base)
    vistas = set(atuais)
    for item in extras:
        if lower:
            val = "".join(
                c for c in unicodedata.normalize("NFKD", item.lower()) if not unicodedata.combining(c)
            )
        else:
            val = item.strip()
        if val and val not in vistas:
            atuais.append(val)
            vistas.add(val)
    return tuple(atuais)


def _mesclar_bases_canonicas(
    bases_atual: Tuple[str, ...],
    aliases_atual: Dict[str, str],
    extras: Optional[Iterable[str]],
) -> Tuple[Tuple[str, ...], Dict[str, str]]:
    if not extras:
        return bases_atual, aliases_atual
    novas_bases = _estender_tupla_unica(bases_atual, extras, lower=False)
    novos_aliases = {
        chave: b
        for b in novas_bases
        if b not in bases_atual and (chave := _chave_normalizada_simples(b))
    }
    return novas_bases, ({**aliases_atual, **novos_aliases} if novos_aliases else aliases_atual)


def aplicar_overlay(
    *,
    aliases_docentes: Optional[Dict[str, str]] = None,
    aliases_autores_referencia: Optional[Dict[str, str]] = None,
    stopwords_continuacao_nome: Optional[Iterable[str]] = None,
    stopwords_entidade: Optional[Iterable[str]] = None,
    stopwords_token_nao_pessoa: Optional[Iterable[str]] = None,
    prefixos_nao_pessoa: Optional[Iterable[str]] = None,
    bases_epistemologicas_canonicas: Optional[Iterable[str]] = None,
    aliases_base_epistemologica: Optional[Dict[str, str]] = None,
) -> None:
    """Mescla overlays específicos da instância sobre os catálogos base ativos."""
    global BASES_EPISTEMOLOGICAS_CANONICAS
    global ALIASES_BASE_EPISTEMOLOGICA
    global ALIASES_DOCENTES
    global STOPWORDS_CONTINUACAO_NOME
    global PREFIXOS_NAO_PESSOA
    global STOPWORDS_ENTIDADE_REF
    global STOPWORDS_TOKEN_NAO_PESSOA
    global ALIASES_AUTORES_REFERENCIA
    global VALORES_CANONICOS_AUTORES_REF

    docentes_norm = _normalizar_dict_chaves(aliases_docentes)
    autores_ref_norm = _normalizar_dict_chaves(aliases_autores_referencia)
    bases_alias_norm = _normalizar_dict_chaves(aliases_base_epistemologica)

    if docentes_norm:
        ALIASES_DOCENTES = {**ALIASES_DOCENTES, **docentes_norm}

    STOPWORDS_CONTINUACAO_NOME = STOPWORDS_CONTINUACAO_NOME | _normalizar_conjunto_str(stopwords_continuacao_nome)
    PREFIXOS_NAO_PESSOA = _estender_tupla_unica(PREFIXOS_NAO_PESSOA, prefixos_nao_pessoa, lower=True)

    novas_ent = _normalizar_conjunto_str(stopwords_entidade)
    if novas_ent:
        STOPWORDS_ENTIDADE_REF = STOPWORDS_ENTIDADE_REF | novas_ent
        STOPWORDS_TOKEN_NAO_PESSOA = STOPWORDS_TOKEN_NAO_PESSOA | {e for e in novas_ent if " " not in e}

    STOPWORDS_TOKEN_NAO_PESSOA = STOPWORDS_TOKEN_NAO_PESSOA | _normalizar_conjunto_str(stopwords_token_nao_pessoa)

    if docentes_norm or autores_ref_norm:
        ALIASES_AUTORES_REFERENCIA = {
            **ALIASES_AUTORES_REFERENCIA,
            **docentes_norm,
            **autores_ref_norm,
        }
        VALORES_CANONICOS_AUTORES_REF = frozenset(ALIASES_AUTORES_REFERENCIA.values())

    BASES_EPISTEMOLOGICAS_CANONICAS, ALIASES_BASE_EPISTEMOLOGICA = _mesclar_bases_canonicas(
        BASES_EPISTEMOLOGICAS_CANONICAS,
        ALIASES_BASE_EPISTEMOLOGICA,
        bases_epistemologicas_canonicas,
    )
    if bases_alias_norm:
        ALIASES_BASE_EPISTEMOLOGICA = {**ALIASES_BASE_EPISTEMOLOGICA, **bases_alias_norm}


resetar_catalogos()
