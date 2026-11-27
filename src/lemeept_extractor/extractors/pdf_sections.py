import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

import pymupdf

from lemeept_extractor.models import RecortesTextuais, TrechoEpistemologico
from lemeept_extractor.normalizers import (
    CONTROLE_INVISIVEL_RE,
    MAIUSCULAS_PT,
    normalizar_espacos,
)
from lemeept_extractor.references import (
    INDICIO_ENTRADA_REF_RE,
    MARCADOR_AUTOR_REF_RE,
    _reconstruir_entradas_referencias,
)

_PADRAO_INTRO = re.compile(
    r"(^|\n)\s*(?:\d+(?:\.\d+)*\.?\s+)?INTRODU[ÇC][ÃA]O\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

_PADRAO_REFS = re.compile(
    r"(?:^|\n)\s*(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(?:"
    r"REFER[ÊE]NCIAS(?:\s+(?:BIBLIOGR[ÁA]FICAS|BIBLOGR[ÁA]FICAS|CONSULTADAS))?"
    r"|Refer[êe]ncias(?:\s+(?:[Bb]ibliogr[áa]ficas|[Cc]onsultadas))?"
    r"|BIBLIOGRAFIA(?:\s*/\s*FONTES\s+DE\s+REFER[ÊE]NCIAS?)?"
    r"|Bibliografia(?:\s*/\s*Fontes\s+de\s+Refer[êe]ncias?)?"
    r"|OBRAS\s+QUE\s+EMBASARAM(?:\s+ESTA\s+COMPOSI[ÇC][ÃA]O)?"
    r")\s*[:\-–—]?\s*(?=\n|$)",
    flags=re.MULTILINE,
)

_PADRAO_FIM_REFS_ESTRUTURAL = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(?:AP[ÊE]NDICES?(?:\s+[A-Z0-9]+|\b)"
    r"|ANEXOS?(?:\s+[A-Z0-9]+|\b)"
    r"|FICHA\s+CATALOGR[ÁA]FICA\b"
    r"|ORIGEM\s+DO\s+PRODUTO\s+EDUCACIONAL\b"
    r"|APRESENTA[ÇC][ÃA]O\s+DO\s+PRODUTO\s+EDUCACIONAL\b"
    r"|SUM[ÁA]RIO\s*$"
    r"|AUTOR(?:AS|ES)?\s*:\s*$)",
    flags=re.IGNORECASE,
)

_PADRAO_FIM_REFS_TOPO = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(?:GLOSS[ÁA]RIO\b"
    r"|POSF[ÁA]CIO\b"
    r"|SE[ÇC][ÃA]O\s+[IVX0-9]+\b"
    r"|CAP[ÍI]TULO\s+[IVX0-9]+\b"
    r"|CONSIDERA[ÇC][ÕO]ES\s+FINAIS\b"
    r"|TERMO\s+DE\s+(?:CONSENTIMENTO|ASSENTIMENTO|AUTORIZA[ÇC][ÃA]O)\b"
    r"|ROTEIRO\s+(?:DE|DA|DO|PARA)\b"
    r"|QUESTION[ÁA]RIO\b)"
)

_MARCADORES_EPISTEMOLOGICOS_RE = re.compile(
    r"\b(epistemol[óo]g|ontol[óo]g|materialismo\s+hist[óo]rico|dial[ée]tic|freire|saviani|"
    r"ciavatta|frigotto|ramos|gramsci|kosik|luk[áa]cs|vygotsky|vigotski|bakhtin|foucault|"
    r"bourdieu|morin|positivis|fenomenolog|hermeneut|construtivis|omnilateral|politecnia|"
    r"trabalho\s+como\s+princ[íi]pio\s+educativo|curr[íi]culo\s+integrado|"
    r"aprendizagem\s+significativa|ausubel|subsun[çc]or|moreira|"
    r"teoria\s+cr[íi]tica|adorno|horkheimer|marcuse|frankfurt|"
    r"marx|kuenzer|manacorda|hist[óo]rico[\s\-]cultural|interdisciplinar)\b",
    flags=re.IGNORECASE,
)
_PRODUTO_EDUCACIONAL_RE = re.compile(r"\bproduto\s+educacional\b", flags=re.IGNORECASE)

_CITACAO_PARENTETICA_RE = re.compile(
    rf"\(([{MAIUSCULAS_PT}][A-Za-zÀ-ÖØ-öø-ÿ\s;&.\-]+?,\s*\d{{4}}[a-z]?(?:,\s*p\.\s*\d+(?:-\d+)?)?)\)"
)


def ler_paginas_pdf(pdf_path: Path) -> List[Tuple[int, str]]:
    """Retorna lista de tuplas (numero_pagina_1_based, texto_limpo)."""
    paginas: List[Tuple[int, str]] = []
    with pymupdf.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            txt = page.get_text("text") or ""
            paginas.append((idx, normalizar_espacos(txt)))
    return paginas


def _eh_pagina_sumario(txt: str) -> bool:
    if re.search(r"(^|\n)\s*SUM[ÁA]RIO\s*(\n|$)", txt, flags=re.IGNORECASE):
        return True
    if len(re.findall(r"\.{4,}", txt)) >= 3:
        return True
    linhas_toc = re.findall(
        r"^\s*(?:\d+(?:\.\d+)*\.?\s+|AP[ÊE]NDICE|ANEXO|REFER[ÊE]NCIAS|OBRAS\s+QUE\s+EMBASARAM).+\s\d{1,3}\s*$",
        txt,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return len(linhas_toc) >= 3


def _eh_linha_fim_secao_refs(linha: str, idx_nao_vazio: int, pagina_inicial: bool) -> bool:
    s = linha.strip()
    if not s or len(s) >= 100:
        return False
    if _PADRAO_FIM_REFS_ESTRUTURAL.match(s):
        return True
    return not pagina_inicial and idx_nao_vazio < 6 and bool(_PADRAO_FIM_REFS_TOPO.match(s))


def _recortar_bloco_refs_pagina(texto: str, pagina_inicial: bool) -> Tuple[str, bool]:
    """Recorta linhas até um marcador pós-textual; retorna (texto_recortado, interrompido)."""
    linhas_validas: List[str] = []
    idx_nao_vazio = 0
    for linha in texto.splitlines():
        s = linha.strip()
        if s and not re.match(r"^\d{1,4}$", s):
            if _eh_linha_fim_secao_refs(s, idx_nao_vazio, pagina_inicial):
                return "\n".join(linhas_validas), True
            idx_nao_vazio += 1
        linhas_validas.append(linha)
    return "\n".join(linhas_validas), False


def _pagina_tem_indicio_bib(texto: str) -> bool:
    return bool(
        MARCADOR_AUTOR_REF_RE.search(texto)
        or re.search(r"https?://|Dispon[íi]vel\s+em:|Acesso\s+em:", texto, flags=re.IGNORECASE)
    )


def _extrair_pre_textuais(paginas: List[Tuple[int, str]]) -> Tuple[str, str, str, str]:
    pre_textuais = paginas[:18]
    capa = "\n\n".join(txt for _, txt in pre_textuais[:2])
    ficha = ""
    resumo = ""
    sumario = ""

    for idx_pre, (num_pag, txt) in enumerate(pre_textuais):
        upper = txt.upper()
        if not ficha and ("FICHA CATALOGRÁFICA" in upper or "CDD" in upper or "CDU" in upper):
            ficha = f"[PÁG. {num_pag}]\n{txt}"
        if not resumo and re.search(r"(^|\n)\s*RESUMO\s*[:\-–—]?\s*(\n|$)", upper):
            bloco_resumo = txt
            if not re.search(r"(?:^|\n)\s*palavras[\s\-–]+chaves?", bloco_resumo, flags=re.IGNORECASE) and idx_pre + 1 < len(paginas):
                prox_txt = paginas[idx_pre + 1][1]
                if not re.match(r"^\s*ABSTRACT\b", prox_txt, flags=re.IGNORECASE) and re.search(
                    r"(?:^|\n)\s*palavras[\s\-–]+chaves?", prox_txt, flags=re.IGNORECASE
                ):
                    corte = re.split(r"(?:^|\n)\s*ABSTRACT\b", prox_txt, maxsplit=1, flags=re.IGNORECASE)[0]
                    bloco_resumo = f"{bloco_resumo}\n{corte.strip()}"
            resumo = f"[PÁG. {num_pag}]\n{bloco_resumo}"
        if not sumario and re.search(r"(^|\n)\s*SUM[ÁA]RIO\s*(\n|$)", upper):
            prox = paginas[idx_pre + 1][1] if idx_pre + 1 < len(paginas) else ""
            sumario = f"[PÁG. {num_pag}]\n{txt}\n{prox[:1500]}"

    return capa, ficha, resumo, sumario


def _localizar_introducao(paginas: List[Tuple[int, str]]) -> Optional[int]:
    for i, (num_pag, txt) in enumerate(paginas):
        if num_pag <= 5 or _eh_pagina_sumario(txt):
            continue
        linhas_topo = "\n".join(txt.splitlines()[:10])
        if _PADRAO_INTRO.search(linhas_topo):
            return i
    return None


def _coletar_secoes_referencias(
    paginas: List[Tuple[int, str]],
    min_idx_refs: int,
) -> Tuple[Optional[int], str]:
    blocos_refs: List[str] = []
    idx_refs: Optional[int] = None
    i = min_idx_refs

    while i < len(paginas):
        _, txt = paginas[i]
        if _eh_pagina_sumario(txt):
            i += 1
            continue
        match_ref = _PADRAO_REFS.search(txt)
        if not match_ref:
            i += 1
            continue

        trecho_ini, interrompido = _recortar_bloco_refs_pagina(txt[match_ref.start() :], pagina_inicial=True)
        paginas_bloco = [trecho_ini]
        j = i + 1
        if not interrompido:
            while j < min(len(paginas), i + 25):
                _, ptxt = paginas[j]
                if _eh_pagina_sumario(ptxt):
                    break
                trecho_pag, parou = _recortar_bloco_refs_pagina(ptxt, pagina_inicial=False)
                if not _pagina_tem_indicio_bib(trecho_pag) and len(trecho_pag.strip()) > 150:
                    break
                paginas_bloco.append(trecho_pag)
                j += 1
                if parou:
                    break

        bloco = "\n".join(paginas_bloco).strip()
        if bloco and (MARCADOR_AUTOR_REF_RE.search(bloco) or INDICIO_ENTRADA_REF_RE.search(bloco)):
            if idx_refs is None:
                idx_refs = i
            blocos_refs.append(bloco)
        i = j

    return idx_refs, "\n\n".join(blocos_refs)


def _recortar_janela_centrada(
    texto: str,
    match: re.Match[str],
    max_chars: int = 1200,
    antes: int = 400,
) -> str:
    limpo = texto.strip()
    if len(limpo) <= max_chars:
        return limpo
    offset_ws = len(texto) - len(texto.lstrip())
    pos_match = max(0, match.start() - offset_ws)
    inicio = max(0, pos_match - antes)
    fim = min(len(limpo), inicio + max_chars)
    if fim == len(limpo):
        inicio = max(0, fim - max_chars)
    if inicio > 0:
        prox_espaco = limpo.find(" ", inicio)
        if 0 <= prox_espaco < pos_match and prox_espaco - inicio < 80:
            inicio = prox_espaco + 1
    if fim < len(limpo):
        ult_espaco = limpo.rfind(" ", pos_match, fim)
        if ult_espaco > inicio and fim - ult_espaco < 80:
            fim = ult_espaco
    return limpo[inicio:fim].strip()


def _extrair_descricao_produto(corpo_paginas: List[Tuple[int, str]]) -> str:
    trechos_produto: List[str] = []
    for p, t in corpo_paginas:
        if not _PRODUTO_EDUCACIONAL_RE.search(t):
            continue
        for paragrafo in t.split("\n\n"):
            m_prod = _PRODUTO_EDUCACIONAL_RE.search(paragrafo)
            if m_prod and len(paragrafo) > 80:
                recorte = _recortar_janela_centrada(paragrafo, m_prod, max_chars=900, antes=250)
                trechos_produto.append(f"[PÁG. {p}] {recorte}")
                if len(trechos_produto) >= 6:
                    return "\n\n".join(trechos_produto)[:3500]
    return "\n\n".join(trechos_produto)[:3500]


def _extrair_trechos_epistemologicos(
    corpo_paginas: List[Tuple[int, str]],
    pagina_intro_inicio: Optional[int],
) -> Tuple[List[TrechoEpistemologico], Set[str]]:
    trechos_epist: List[TrechoEpistemologico] = []
    citacoes_unicas: Set[str] = set()
    qtd_intro = 0
    qtd_corpo = 0

    for p, t in corpo_paginas:
        secao = (
            "Introdução"
            if (pagina_intro_inicio is not None and p <= pagina_intro_inicio + 4)
            else "Corpo/Fundamentação"
        )
        if secao == "Introdução" and qtd_intro >= 4:
            continue
        if secao == "Corpo/Fundamentação" and qtd_corpo >= 8:
            continue

        for paragrafo in t.split("\n\n"):
            if len(paragrafo) < 120:
                continue
            m_epist = _MARCADORES_EPISTEMOLOGICOS_RE.search(paragrafo)
            if not m_epist:
                continue
            recorte = _recortar_janela_centrada(paragrafo, m_epist, max_chars=1200, antes=400)
            cits = _CITACAO_PARENTETICA_RE.findall(recorte)
            for c in cits:
                sobrenome = c.split(",")[0].strip().split()[0].upper()
                if len(sobrenome) >= 3:
                    citacoes_unicas.add(sobrenome)
            trechos_epist.append(
                TrechoEpistemologico(
                    secao=secao,
                    pagina=p,
                    texto=recorte,
                    citacoes_detectadas=cits[:8],
                )
            )
            if secao == "Introdução":
                qtd_intro += 1
            else:
                qtd_corpo += 1
            if len(trechos_epist) >= 12 or (qtd_intro >= 4 and qtd_corpo >= 8):
                return trechos_epist, citacoes_unicas
            break

    return trechos_epist, citacoes_unicas


def _filtrar_referencias_citadas(texto_refs: str, citacoes_unicas: Set[str]) -> List[str]:
    if not texto_refs or not citacoes_unicas:
        return []
    referencias_filtradas: List[str] = []
    entradas = _reconstruir_entradas_referencias(texto_refs)
    for entrada_limpa in entradas:
        if len(entrada_limpa) < 25:
            continue
        primeiro_token = re.split(r"[,.\s]", entrada_limpa)[0].upper()
        if primeiro_token in citacoes_unicas:
            referencias_filtradas.append(entrada_limpa[:400])
            if len(referencias_filtradas) >= 25:
                break
    return referencias_filtradas


def isolar_secoes_pdf(paginas: List[Tuple[int, str]]) -> Tuple[RecortesTextuais, str]:
    """Isola recortes textuais estruturados do PDF e o texto delimitado das referências."""
    if not paginas:
        return RecortesTextuais(), ""

    paginas = [(num_pag, CONTROLE_INVISIVEL_RE.sub("", txt)) for num_pag, txt in paginas]
    capa, ficha, resumo, sumario = _extrair_pre_textuais(paginas)

    idx_intro = _localizar_introducao(paginas)
    min_idx_refs = (idx_intro + 1) if idx_intro is not None else min(5, len(paginas) // 2)
    idx_refs, texto_refs = _coletar_secoes_referencias(paginas, min_idx_refs)

    introducao_paginas = paginas[idx_intro : idx_intro + 5] if idx_intro is not None else paginas[8:13]
    introducao = "\n\n".join(f"[PÁG. {p}]\n{t}" for p, t in introducao_paginas)[:8000]

    fim_corpo = idx_refs if idx_refs is not None else len(paginas)
    corpo_paginas = paginas[(idx_intro or 8) : fim_corpo]

    descricao_produto = _extrair_descricao_produto(corpo_paginas)
    pagina_intro_inicio = paginas[idx_intro][0] if idx_intro is not None else None
    trechos_epist, citacoes_unicas = _extrair_trechos_epistemologicos(corpo_paginas, pagina_intro_inicio)
    referencias_filtradas = _filtrar_referencias_citadas(texto_refs, citacoes_unicas)

    recortes = RecortesTextuais(
        capa=capa[:2500],
        ficha_catalografica=ficha[:2500],
        sumario=sumario[:3000],
        resumo=resumo[:4500],
        introducao=introducao,
        descricao_produto_na_dissertacao=descricao_produto,
        trechos_epistemologicos=trechos_epist,
        referencias_filtradas=referencias_filtradas,
    )
    return recortes, texto_refs
