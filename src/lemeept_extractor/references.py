import re
import unicodedata
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from lemeept_extractor import catalogs
from lemeept_extractor.normalizers import (
    MAIUSCULAS_PT,
    MINUSCULAS_PT,
    limpar_texto,
    normalizar_texto_busca,
    remover_acentos,
)

_PARTICULA_INICIAL_SOBRENOME = {"DA", "DE", "DO", "DAS", "DOS"}
_SOBRENOME_TOKEN_RE = rf"[{MAIUSCULAS_PT}][{MAIUSCULAS_PT}'\-]{{1,}}"
_SOBRENOME_BLOCO_RE = (
    rf"[{MAIUSCULAS_PT}][{MAIUSCULAS_PT}'\-]{{1,}}"
    rf"(?:\s+(?:DA|DE|DO|DAS|DOS|DEL|DI|LA|LE|VAN|VON|{_SOBRENOME_TOKEN_RE})){{0,3}}"
)
_INICIO_ENTRADA_REF_RE = re.compile(
    rf"^(?:[{MAIUSCULAS_PT}][{MAIUSCULAS_PT}'\-]{{1,}}"
    rf"(?:\s+(?:DA|DE|DO|DAS|DOS|DEL|DI|LA|LE|VAN|VON|{_SOBRENOME_TOKEN_RE})){{0,4}})\s*,"
)
_SEG_AUTOR_REF_RE = re.compile(rf"\s*({_SOBRENOME_BLOCO_RE})\s*,\s*")
_PROXIMO_COAUTOR_RE = re.compile(rf"^{_SOBRENOME_BLOCO_RE}\s*,")

MARCADOR_AUTOR_REF_RE = re.compile(rf"(?:^|\n)\s*[{MAIUSCULAS_PT}]{{2,}}[^,\n]{{0,35}},")
INDICIO_ENTRADA_REF_RE = re.compile(
    r"\b(?:1[5-9]\d{2}|20[0-2]\d)\b|s\.?\s*d\.?|no\s+prelo|dispon[íi]vel\s+em|"
    r"anais|disserta[çc][ãa]o|tese|editora|\bp\.\s*\d|\bv\.\s*\d|\bed\.",
    flags=re.IGNORECASE,
)


def _eh_sobrenome_ref_valido(sobrenome_maiusc: str) -> Tuple[List[str], List[str], bool]:
    """Valida e formata sobrenome em caixa alta; retorna (particulas_iniciais, tokens_sobrenome, eh_valido)."""
    tokens = sobrenome_maiusc.split()
    if not tokens or len(tokens) > 4:
        return [], [], False

    if normalizar_texto_busca(sobrenome_maiusc) in catalogs.STOPWORDS_ENTIDADE_REF:
        return [], [], False

    particulas_iniciais: List[str] = []
    while tokens and tokens[0] in _PARTICULA_INICIAL_SOBRENOME:
        particulas_iniciais.append(tokens.pop(0).lower())
    if not tokens:
        return [], [], False

    if normalizar_texto_busca(" ".join(tokens)) in catalogs.STOPWORDS_ENTIDADE_REF:
        return [], [], False

    if any(remover_acentos(tok).lower() in catalogs.STOPWORDS_TOKEN_NAO_PESSOA for tok in tokens):
        return [], [], False

    if len(tokens) == 1 and len(tokens[0]) <= 2:
        if remover_acentos(tokens[0]).upper() not in catalogs.SOBRENOMES_CURTOS_VALIDOS:
            return [], [], False

    formatados: List[str] = []
    for idx, tok in enumerate(tokens):
        low = tok.lower()
        if idx > 0 and low in catalogs.PARTICULAS_NOME_COMPLETO:
            formatados.append(low)
        elif "-" in tok:
            formatados.append("-".join(p.capitalize() for p in tok.split("-")))
        elif "'" in tok:
            partes = tok.split("'")
            formatados.append("'".join(p.capitalize() if len(p) > 1 else p.upper() for p in partes))
        else:
            formatados.append(tok.capitalize())

    return particulas_iniciais, formatados, True


def _validar_prenome_ref(prenome_bruto: str) -> List[str]:
    """Valida e normaliza tokens do prenome em entrada ABNT (ex.: 'H.W.', 'João da', 'A. C.')."""
    s = (prenome_bruto or "").strip()
    s = re.sub(rf"(?<=[{MINUSCULAS_PT}])et\s*al\.?\b", "", s, flags=re.IGNORECASE)
    s = re.sub(
        r"\s*[\(\[]\s*(?:orgs?\.?|coords?\.?|eds?\.?|trads?\.?|comps?\.?|dir\.?|et\s+al\.?)\s*[\)\]]\.?\s*$",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"\s+(?:et\s+al\.?|orgs?\.?|coords?\.?|eds?\.?)\s*$", "", s, flags=re.IGNORECASE)
    s = s.strip(" ,;:-–—")
    if not s or re.search(r"[\d:/\\@\"“”<>?!]", s) or re.match(rf"^[{MINUSCULAS_PT}]", s):
        return []

    s = re.sub(rf"([{MAIUSCULAS_PT}])\.(?=[{MAIUSCULAS_PT}])", r"\1. ", s)
    tokens = s.split()
    if not (1 <= len(tokens) <= 7):
        return []

    limpos: List[str] = []
    tem_nome_ou_inicial = False
    qtd_caps = 0

    for idx, tok in enumerate(tokens):
        tc = tok.strip(",")
        if not tc:
            continue
        low_sem_ponto = remover_acentos(tc).lower().rstrip(".")
        if low_sem_ponto in {"et", "al", "org", "orgs", "coord", "coords", "ed", "eds", "trad", "comp", "in"}:
            break

        # Verificar inicial ANTES de partícula ('E.' é inicial, não conjunção 'e')
        if re.match(rf"^[{MAIUSCULAS_PT}]\.?$", tc):
            limpos.append(tc[0] + ".")
            tem_nome_ou_inicial = True
            continue

        if tc.lower() in catalogs.PARTICULAS_NOME_COMPLETO and idx > 0 and "." not in tc:
            limpos.append(tc.lower())
            continue

        if re.match(rf"^[{MAIUSCULAS_PT}]{{2,3}}$", tc):
            sem_acento = remover_acentos(tc).upper()
            if sem_acento.lower() in catalogs.STOPWORDS_TOKEN_NAO_PESSOA or sem_acento in catalogs.SIGLAS_UF_PAIS:
                return []
            limpos.extend(ch + "." for ch in tc)
            tem_nome_ou_inicial = True
            continue

        if re.match(rf"^[{MAIUSCULAS_PT}][{MINUSCULAS_PT}'\-]+(?:\.)?$", tc):
            base = tc.rstrip(".")
            if remover_acentos(base).lower() in catalogs.STOPWORDS_TOKEN_NAO_PESSOA:
                return []
            if tc.endswith(".") and low_sem_ponto not in {"jr", "st"}:
                return []
            limpos.append(tc if tc.endswith(".") else base)
            tem_nome_ou_inicial = True
            continue

        if re.match(rf"^[{MAIUSCULAS_PT}][{MAIUSCULAS_PT}\-]{{2,}}$", tc):
            if remover_acentos(tc).lower() in catalogs.STOPWORDS_TOKEN_NAO_PESSOA:
                return []
            qtd_caps += 1
            if qtd_caps > 2:
                return []
            limpos.append(tc.capitalize())
            tem_nome_ou_inicial = True
            continue

        return []

    return limpos if tem_nome_ou_inicial else []


def _consumir_segmento_prenome(restante: str) -> Tuple[str, bool, Optional[int]]:
    """
    Lê tokens do prenome a partir do trecho após 'SOBRENOME,' até o delimitador da obra ou coautor.
    Retorna (prenome_bruto, eh_ultimo_autor, deslocamento_proximo_autor).
    """
    tokens_fn: List[str] = []
    for tm in re.finditer(r"[^\s]+", restante):
        tk = tm.group(0)
        apos = restante[tm.end() :]
        apos_strip = apos.lstrip()

        if re.match(r"^[\(\[]?(?:orgs?|coords?|eds?|trads?|comps?)\.?[\)\]]?\.?$", tk, flags=re.IGNORECASE):
            return " ".join(tokens_fn), True, tm.end()
        if tk.lower() == "et" and apos_strip.lower().startswith("al"):
            return " ".join(tokens_fn), True, tm.end()
        if tk == "&":
            return " ".join(tokens_fn), False, tm.end()
        if tk.lower() == "e" and _PROXIMO_COAUTOR_RE.match(apos_strip):
            return " ".join(tokens_fn), False, tm.end()
        if tk.endswith(";"):
            tokens_fn.append(tk[:-1])
            return " ".join(tokens_fn), False, tm.end()

        if tk.endswith("."):
            if re.match(rf"^(?:[{MAIUSCULAS_PT}]\.)+$", tk):
                tokens_fn.append(tk)
                if not apos_strip:
                    return " ".join(tokens_fn), True, None
                if apos_strip.startswith((";", "&")):
                    offset_sep = tm.end() + (len(apos) - len(apos_strip)) + 1
                    return " ".join(tokens_fn), False, offset_sep
                prox_tok = apos_strip.split()[0]
                prox_low = remover_acentos(prox_tok).lower().rstrip(".;,")
                if (
                    re.match(rf"^(?:[{MAIUSCULAS_PT}]\.)+[;,]?$", prox_tok)
                    or prox_tok.lower() in catalogs.PARTICULAS_NOME_COMPLETO
                    or re.match(r"^[\(\[]?(?:orgs?|coords?|eds?)\.?[\)\]]?", prox_tok, flags=re.IGNORECASE)
                    or prox_low in {"et", "&"}
                    or (prox_low == "e" and _PROXIMO_COAUTOR_RE.match(apos_strip[len(prox_tok) :].lstrip()))
                ):
                    continue
                return " ".join(tokens_fn), True, None

            tokens_fn.append(tk[:-1])
            return " ".join(tokens_fn), True, tm.end()

        if tk.endswith(","):
            tokens_fn.append(tk[:-1])
            return " ".join(tokens_fn), not _PROXIMO_COAUTOR_RE.match(apos_strip), tm.end()

        # Trata colagem sem espaço após ponto final (ex.: 'Miriam.Coord.Juventudes...')
        if "." in tk and not re.match(rf"^(?:[{MAIUSCULAS_PT}]\.)+$", tk):
            antes_ponto = tk.split(".", 1)[0]
            if re.match(rf"^[{MAIUSCULAS_PT}][{MINUSCULAS_PT}'\-]{{2,}}$", antes_ponto):
                tokens_fn.append(antes_ponto)
                return " ".join(tokens_fn), True, tm.end()

        tokens_fn.append(tk)
        if len(tokens_fn) >= 7:
            return "", True, None

    return " ".join(tokens_fn), True, None


def _montar_nome_ordem_natural(
    fn_tokens: List[str],
    particulas_iniciais: List[str],
    sur_tokens: List[str],
) -> Optional[str]:
    fn_limpos = list(fn_tokens)
    sur_norm = [normalizar_texto_busca(t) for t in sur_tokens]
    if len(fn_limpos) > len(sur_tokens) and [
        normalizar_texto_busca(t) for t in fn_limpos[-len(sur_tokens) :]
    ] == sur_norm:
        fn_limpos = fn_limpos[: -len(sur_tokens)]

    if particulas_iniciais and (
        not fn_limpos or fn_limpos[-1].lower() not in catalogs.PARTICULAS_NOME_COMPLETO
    ):
        nome_completo = " ".join(fn_limpos + particulas_iniciais + sur_tokens)
    else:
        nome_completo = " ".join(fn_limpos + sur_tokens)

    if normalizar_texto_busca(nome_completo) in catalogs.STOPWORDS_ENTIDADE_REF:
        return None
    norm = normalizar_autor_referencia(nome_completo)
    if not norm or normalizar_texto_busca(norm) in catalogs.STOPWORDS_ENTIDADE_REF:
        return None
    return norm


def _reconstruir_entradas_referencias(texto_secao_referencias: str) -> List[str]:
    """Agrupa linhas quebradas das referências em entradas bibliográficas lógicas."""
    entradas: List[str] = []
    atual: List[str] = []

    for bruto in texto_secao_referencias.splitlines():
        linha = bruto.strip()
        if not linha:
            if atual:
                entradas.append(" ".join(atual))
                atual = []
            continue
        if re.match(r"^\d{1,4}$", linha):
            continue
        if atual and (
            atual[-1].endswith(";")
            or re.match(rf"^[{MAIUSCULAS_PT}\s'\-]+,$", atual[-1])
        ):
            atual.append(linha)
            continue
        if _INICIO_ENTRADA_REF_RE.match(linha):
            if atual and re.search(r"\bIn:\s*$", atual[-1], flags=re.IGNORECASE):
                atual.append(linha)
                continue
            if atual:
                entradas.append(" ".join(atual))
            atual = [linha]
        elif atual:
            atual.append(linha)

    if atual:
        entradas.append(" ".join(atual))
    return entradas


def normalizar_autor_referencia(nome: Optional[str]) -> str:
    """Limpa pontuação residual, normaliza iniciais ('A.C.' -> 'A. C.') e resolve aliases canônicos."""
    if not nome or not isinstance(nome, str):
        return ""
    limpo = limpar_texto(nome).strip(" ,;-–—:")
    limpo = re.sub(rf"([{MAIUSCULAS_PT}])\.(?=[{MAIUSCULAS_PT}])", r"\1. ", limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip()
    if re.search(rf"[^{MAIUSCULAS_PT}]\.$", limpo):
        limpo = limpo[:-1].rstrip()
    if not limpo:
        return ""
    return catalogs.ALIASES_AUTORES_REFERENCIA.get(normalizar_texto_busca(limpo), limpo)


def _eh_token_inicial(token: str) -> bool:
    return bool(re.match(rf"^[{MAIUSCULAS_PT}]\.?$", token))


def _tokens_nucleares_nome(nome: str) -> List[str]:
    return [t for t in nome.split() if t.lower() not in catalogs.PARTICULAS_NOME_COMPLETO]


def _contar_diacriticos(texto: str) -> int:
    return sum(1 for c in unicodedata.normalize("NFKD", texto) if unicodedata.combining(c))


def _particionar_nome_iniciais(nome: str) -> Optional[Tuple[List[str], List[str]]]:
    """Separa prefixo de iniciais e tokens de sobrenome se o nome for composto só de iniciais + sobrenome."""
    nucleares = _tokens_nucleares_nome(nome)
    if len(nucleares) < 2:
        return None
    primeiro_nao_inicial = next(
        (idx for idx, tok in enumerate(nucleares) if not _eh_token_inicial(tok)),
        None,
    )
    if primeiro_nao_inicial is None or primeiro_nao_inicial == 0:
        return None
    if any(_eh_token_inicial(tok) for tok in nucleares[primeiro_nao_inicial:]):
        return None
    inits = [normalizar_texto_busca(t) for t in nucleares[:primeiro_nao_inicial]]
    surnames = [normalizar_texto_busca(t) for t in nucleares[primeiro_nao_inicial:]]
    return inits, surnames


def _iniciais_compativeis_em_ordem(iniciais: List[str], tokens_completos: List[str]) -> bool:
    if not iniciais or not tokens_completos or not tokens_completos[0].startswith(iniciais[0]):
        return False
    idx_tok = 1
    for init in iniciais[1:]:
        while idx_tok < len(tokens_completos) and not tokens_completos[idx_tok].startswith(init):
            idx_tok += 1
        if idx_tok >= len(tokens_completos):
            return False
        idx_tok += 1
    return True


def _nomes_completos_compativeis(
    raw_toks: List[str],
    norm_toks: List[str],
    cand_raw_toks: List[str],
    cand_norm_toks: List[str],
) -> bool:
    if any(_eh_token_inicial(rt) for rt in cand_raw_toks):
        return False
    tem_inicial_meio = any(_eh_token_inicial(rt) for rt in raw_toks[1:-1])
    if len(cand_norm_toks) < len(norm_toks):
        return False
    if len(cand_norm_toks) == len(norm_toks) and not tem_inicial_meio:
        return False

    idx_cand = 0
    for rtok, ntok in zip(raw_toks[1:-1], norm_toks[1:-1], strict=True):
        eh_init = _eh_token_inicial(rtok)
        while idx_cand < len(cand_norm_toks) - 2:
            c_tok = cand_norm_toks[1 + idx_cand]
            idx_cand += 1
            if (eh_init and c_tok.startswith(ntok)) or (not eh_init and c_tok == ntok):
                break
        else:
            return False
    return True


def _passo_reconciliar_autores(
    autores_por_registro: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    # Passo 0: Aliases explícitos por entrada
    etapa0 = {
        eid: [n for n in (normalizar_autor_referencia(a) for a in (lista or [])) if n]
        for eid, lista in autores_por_registro.items()
    }
    freq0 = Counter(a for lista in etapa0.values() for a in set(lista))

    # Passo 1: Unificação ignorando diacríticos e preposições
    grupos1: Dict[str, List[str]] = defaultdict(list)
    for nome in freq0:
        chave1 = " ".join(normalizar_texto_busca(t) for t in _tokens_nucleares_nome(nome))
        if chave1:
            grupos1[chave1].append(nome)

    mapa1: Dict[str, str] = {}
    for variantes in grupos1.values():
        melhor = max(
            variantes,
            key=lambda v: (
                v in catalogs.VALORES_CANONICOS_AUTORES_REF,
                _contar_diacriticos(v) > 0,
                _contar_diacriticos(v),
                freq0[v],
                len(v),
            ),
        )
        for v in variantes:
            mapa1[v] = melhor

    etapa1 = {eid: [mapa1[a] for a in lista if a in mapa1] for eid, lista in etapa0.items()}
    freq1 = Counter(a for lista in etapa1.values() for a in set(lista))

    # Passo 2: Expansão inequívoca de nomes do meio omitidos ou abreviados
    candidatos_completos = [
        n
        for n in freq1
        if len(_tokens_nucleares_nome(n)) >= 2 and not _eh_token_inicial(_tokens_nucleares_nome(n)[0])
    ]
    por_extremos: Dict[Tuple[str, str], List[Tuple[str, List[str], List[str]]]] = defaultdict(list)
    for fn in candidatos_completos:
        rtoks = _tokens_nucleares_nome(fn)
        ntoks = [normalizar_texto_busca(t) for t in rtoks]
        por_extremos[(ntoks[0], ntoks[-1])].append((fn, rtoks, ntoks))

    mapa2: Dict[str, str] = {}
    for nome in candidatos_completos:
        if nome in catalogs.VALORES_CANONICOS_AUTORES_REF:
            continue
        rtoks = _tokens_nucleares_nome(nome)
        ntoks = [normalizar_texto_busca(t) for t in rtoks]
        compativeis = [
            fn
            for fn, c_rtoks, c_ntoks in por_extremos[(ntoks[0], ntoks[-1])]
            if fn != nome and _nomes_completos_compativeis(rtoks, ntoks, c_rtoks, c_ntoks)
        ]
        if len(compativeis) == 1:
            mapa2[nome] = compativeis[0]

    for origem in list(mapa2):
        atual = mapa2[origem]
        vistos = {origem}
        while atual in mapa2 and atual not in vistos:
            vistos.add(atual)
            atual = mapa2[atual]
        mapa2[origem] = atual

    etapa2 = {eid: [mapa2.get(a, a) for a in lista] for eid, lista in etapa1.items()}
    freq2 = Counter(a for lista in etapa2.values() for a in set(lista))

    # Passo 3: Resolução inequívoca de iniciais ("D. L. Lima Filho", "G. Kaplún")
    por_ultimo_sobrenome: Dict[str, List[Tuple[str, List[str]]]] = defaultdict(list)
    for nome in freq2:
        rtoks = _tokens_nucleares_nome(nome)
        if len(rtoks) >= 2 and not _eh_token_inicial(rtoks[0]) and not any(_eh_token_inicial(t) for t in rtoks):
            ntoks = [normalizar_texto_busca(t) for t in rtoks]
            por_ultimo_sobrenome[ntoks[-1]].append((nome, ntoks))

    mapa3: Dict[str, str] = {}
    for nome in freq2:
        particao = _particionar_nome_iniciais(nome)
        if not particao:
            continue
        inits, sur_toks = particao
        qtd_sur = len(sur_toks)
        compativeis = [
            cand_nome
            for cand_nome, cand_ntoks in por_ultimo_sobrenome.get(sur_toks[-1], [])
            if len(cand_ntoks) >= len(inits) + qtd_sur
            and cand_ntoks[-qtd_sur:] == sur_toks
            and _iniciais_compativeis_em_ordem(inits, cand_ntoks[:-qtd_sur])
        ]
        if len(compativeis) == 1:
            mapa3[nome] = compativeis[0]

    return {
        eid: sorted(
            {mapa3.get(a, a) for a in lista},
            key=lambda s: (normalizar_texto_busca(s), s),
        )
        for eid, lista in etapa2.items()
    }


def reconciliar_autores_referenciados(
    autores_por_registro: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Normaliza e reconcilia nomes de autores referenciados em 4 passos determinísticos até convergência:
      0) Aliases explícitos e normalização sintática (normalizar_autor_referencia);
      1) Equivalência sem acentos e preposições (priorizando grafia com diacríticos e maior frequência);
      2) Expansão inequívoca de nomes do meio omitidos/abreviados para o nome completo único no acervo;
      3) Resolução inequívoca de iniciais para nome completo único compatível (preservando homônimos ambíguos).
    """
    if not autores_por_registro:
        return {}

    atual = autores_por_registro
    for _ in range(5):
        proximo = _passo_reconciliar_autores(atual)
        if proximo == atual:
            return proximo
        atual = proximo
    return atual


def extrair_autores_referencias(texto_secao_referencias: str) -> List[str]:
    """
    Extrai nomes completos normalizados de autores a partir de entradas bibliográficas ABNT
    (ex.: 'SAVIANI, Dermeval. Pedagogia. 2007.' -> 'Dermeval Saviani', incluindo coautores).
    """
    if not texto_secao_referencias:
        return []

    brutos: List[str] = []
    for entrada in _reconstruir_entradas_referencias(texto_secao_referencias):
        if len(entrada) < 20 or not INDICIO_ENTRADA_REF_RE.search(entrada):
            continue

        pos = 0
        while pos < len(entrada):
            match_sur = _SEG_AUTOR_REF_RE.match(entrada, pos)
            if not match_sur:
                break

            particulas, sur_tokens, sur_ok = _eh_sobrenome_ref_valido(match_sur.group(1).strip())
            if not sur_ok:
                break

            fn_bruto, eh_ultimo, deslocamento = _consumir_segmento_prenome(entrada[match_sur.end() :])
            fn_tokens = _validar_prenome_ref(fn_bruto)
            if not fn_tokens:
                break

            nome = _montar_nome_ordem_natural(fn_tokens, particulas, sur_tokens)
            if nome:
                brutos.append(nome)

            if eh_ultimo or deslocamento is None:
                break
            pos = match_sur.end() + deslocamento

    if not brutos:
        return []
    return reconciliar_autores_referenciados({"_": brutos})["_"]
