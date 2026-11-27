import re
from typing import Any, Dict, List, Optional

from lemeept_extractor import catalogs
from lemeept_extractor.normalizers import (
    CONTROLE_INVISIVEL_RE,
    MAIUSCULAS_PT,
    formatar_nome_proprio,
    limpar_nome_pessoa,
    normalizar_chave_busca,
    normalizar_espacos,
    normalizar_nome_orientador,
    normalizar_texto_busca,
)


def _eh_linha_continuacao_nome(linha: str, primeira_all_caps: bool) -> bool:
    candidato = linha.strip().rstrip(".")
    if not candidato or re.search(r"[\d:;()\"'/\-–—.]", candidato):
        return False
    tokens = candidato.split()
    if not (1 <= len(tokens) <= 4):
        return False

    norm_linha = normalizar_chave_busca(candidato)
    if norm_linha in catalogs.STOPWORDS_CONTINUACAO_NOME or norm_linha in catalogs.PLACEHOLDERS_COORIENTADOR:
        return False

    tem_nome_proprio = False
    for tok in tokens:
        tok_norm = normalizar_chave_busca(tok)
        if tok_norm in catalogs.STOPWORDS_CONTINUACAO_NOME or tok_norm in catalogs.STOPWORDS_PROSA_NOME:
            return False
        if tok_norm in catalogs.PREPOSICOES_NOME:
            continue
        if not tok[0].isupper():
            return False
        if len(tok) > 1 and tok == tok.upper() and not primeira_all_caps:
            return False
        tem_nome_proprio = True

    return tem_nome_proprio


def _eh_nome_pessoa_valido(nome: str) -> bool:
    if not (4 <= len(nome) <= 90) or re.search(r"\d", nome):
        return False

    norm = normalizar_chave_busca(nome)
    norm_sem_pont = normalizar_texto_busca(nome)
    if (
        norm in catalogs.PLACEHOLDERS_COORIENTADOR
        or norm_sem_pont in catalogs.PLACEHOLDERS_COORIENTADOR
        or any(p in norm_sem_pont for p in ("nao se aplica", "sem coorient"))
    ):
        return False
    if catalogs.PREFIXOS_NAO_PESSOA and norm.startswith(catalogs.PREFIXOS_NAO_PESSOA):
        return False

    tokens = nome.split()
    if not (2 <= len(tokens) <= 9):
        return False

    nomes_capitalizados = 0
    for tok in tokens:
        tok_norm = normalizar_chave_busca(tok)
        if tok_norm in catalogs.STOPWORDS_PROSA_NOME:
            return False
        if tok_norm in catalogs.PREPOSICOES_NOME:
            continue
        if not tok[0].isupper():
            return False
        nomes_capitalizados += 1

    return nomes_capitalizados >= 2


def _registrar_candidato_pessoa(
    encontrados: List[str],
    candidato: str,
    orientador_norm: str,
) -> None:
    limpo = normalizar_nome_orientador(candidato)
    if not _eh_nome_pessoa_valido(limpo):
        return
    cand_norm = normalizar_chave_busca(limpo)
    if orientador_norm and cand_norm == orientador_norm:
        return

    for idx, existente in enumerate(encontrados):
        ex_norm = normalizar_chave_busca(existente)
        if cand_norm == ex_norm or ex_norm.startswith(cand_norm + " "):
            return
        if cand_norm.startswith(ex_norm + " "):
            encontrados[idx] = limpo
            return

    encontrados.append(limpo)


def extrair_coorientador(
    texto_preliminar: str,
    orientador_principal: Optional[str] = None,
) -> List[str]:
    """Extrai nomes de coorientadores a partir de rótulos preliminares e ficha catalográfica."""
    texto = CONTROLE_INVISIVEL_RE.sub("", texto_preliminar or "")
    if not texto:
        return []

    orient_limpo = normalizar_nome_orientador(orientador_principal or "")
    orient_norm = normalizar_chave_busca(orient_limpo)
    encontrados: List[str] = []

    padrao_rotulo = re.compile(
        r"(?:^|\n|;)\s*co[\-–—]?orienta(?:dor(?:a|\(a\))?|[çc][ãa]o)\s*:\s*([^\n\r]*)",
        flags=re.IGNORECASE,
    )
    for m in padrao_rotulo.finditer(texto):
        linha1 = m.group(1).strip()
        pos_fim = m.end()

        if not linha1:
            m_prox = re.match(r"^\r?\n[ \t]*([^\n\r]+)", texto[pos_fim:])
            if m_prox:
                linha1 = m_prox.group(1).strip()
                pos_fim += m_prox.end()

        if not linha1:
            continue

        capturado = linha1
        if not linha1.endswith((".", ";")):
            m_cont = re.match(r"^\r?\n(?![ \t]*\r?\n)[ \t]*([^\n\r]+)", texto[pos_fim:])
            if m_cont:
                linha2 = m_cont.group(1).strip()
                primeira_all_caps = linha1 == linha1.upper() and any(c.isalpha() for c in linha1)
                if _eh_linha_continuacao_nome(linha2, primeira_all_caps):
                    capturado = f"{linha1} {linha2}"

        _registrar_candidato_pessoa(encontrados, capturado, orient_norm)

    padrao_ficha = re.compile(
        rf";\s*(?i:co[\-–—]?orientador(?:a|\(a\))?)\s+([{MAIUSCULAS_PT}].*?)"
        r"(?=(?<!\bProf)(?<!\bProfa)(?<!\bProfª)(?<!\bDr)(?<!\bDra)(?<!\bDrª)(?<!\bMe)(?<!\bMa)\.\s*(?:--|\s|$)|;|\n\s*\n|$)",
        flags=re.DOTALL,
    )
    for m in padrao_ficha.finditer(texto):
        _registrar_candidato_pessoa(encontrados, m.group(1), orient_norm)

    return encontrados


def extrair_palavras_chave_resumo(bloco_resumo: str) -> List[str]:
    """Extrai palavras-chave do bloco de resumo suportando separadores ';', ',' ou '.'."""
    match = re.search(
        r"(?:^|\n)\s*Palavras[\s\-–]+chaves?\s*:?\s*(.+?)(?=\n\s*\n|(?:^|\n)\s*(?:Abstract|Keywords)\b|$)",
        bloco_resumo,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    bruto = re.sub(r"\s+", " ", match.group(1)).strip().rstrip(".")
    sep = ";" if ";" in bruto else ("," if "," in bruto else ".")
    return [
        limpa
        for item in bruto.split(sep)
        if 2 <= len(limpa := item.strip(" .;-–—")) <= 80
    ]


_PADRAO_LINHA_INSTITUICAO_RE = re.compile(
    r"^(?:INSTITUTO\s+FEDERAL|UNIVERSIDADE|CENTRO\s+FEDERAL|FACULDADE|FUNDA[ÇC][ÃA]O)\b.*",
    flags=re.IGNORECASE,
)
_PADRAO_LINHA_CAMPUS_RE = re.compile(r"^CAMPUS\s+(.+)$", flags=re.IGNORECASE)
_PADRAO_PREFIXO_RUIDO_CAPA_RE = re.compile(
    r"^(?:MINIST[ÉE]RIO|SECRETARIA|PR[ÓO]-?REITORIA|DIRETORIA|PROGRAMA\s+DE\s+P[ÓO]S|"
    r"MESTRADO|DOUTORADO|CURSO|LINHA\s+DE\s+PESQUISA|MACROPROJETO|DISCENTE|AUTOR|"
    r"ORIENTA|CO[\-–—]?ORIENTA|DISSERTA[ÇC][ÃA]O|TESE|PRODUTO\s+EDUCACIONAL|BANCA|FICHA)",
    flags=re.IGNORECASE,
)


def _limpar_titulo_de_arquivo(nome_arquivo: str) -> str:
    if not nome_arquivo:
        return ""
    base = re.sub(r"\.pdf$", "", nome_arquivo.strip(), flags=re.IGNORECASE)
    base = re.sub(r"[_\-]+", " ", base)
    return normalizar_espacos(base)


def _extrair_ano_preliminar(ficha: str, capa: str, nome_arquivo: str) -> int:
    for texto in (ficha, capa):
        if not texto:
            continue
        m_ficha = re.search(r",\s*((?:19|20)\d{2})\s*\.", texto)
        if m_ficha:
            return int(m_ficha.group(1))
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        for linha in reversed(linhas[-8:]):
            m_linha = re.search(r"\b((?:19|20)\d{2})\b", linha)
            if m_linha:
                return int(m_linha.group(1))
    m_arq = re.search(r"\b((?:19|20)\d{2})\b", nome_arquivo or "")
    return int(m_arq.group(1)) if m_arq else 0


def _extrair_autor_e_titulo_ficha(ficha: str) -> tuple[str, str]:
    if not ficha:
        return "", ""
    linhas = [l.strip() for l in ficha.splitlines() if l.strip()]
    autor = ""
    titulo = ""
    idx_autor = -1

    padrao_abnt_autor = re.compile(
        rf"^([{MAIUSCULAS_PT}][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+(?:\s+(?:da|de|do|das|dos|e)\s+[{MAIUSCULAS_PT}][A-Za-zÀ-ÖØ-öø-ÿ\'\-]+)?),\s+([^.]+)\.?$"
    )
    for idx, linha in enumerate(linhas):
        if any(tok in linha.upper() for tok in ("FICHA CATALOGRÁFICA", "CDD", "CDU", "BIBLIOTEC")):
            continue
        m = padrao_abnt_autor.match(linha)
        if m:
            sobrenome = m.group(1).strip()
            prenome = m.group(2).strip(" .")
            cand = limpar_nome_pessoa(f"{prenome} {sobrenome}")
            if _eh_nome_pessoa_valido(cand):
                autor = formatar_nome_proprio(cand)
                idx_autor = idx
                break

    if idx_autor >= 0 and idx_autor + 1 < len(linhas):
        acum: List[str] = []
        for linha in linhas[idx_autor + 1 : idx_autor + 6]:
            acum.append(linha)
            junto = " ".join(acum)
            if " / " in junto:
                titulo = normalizar_espacos(junto.split(" / ", 1)[0]).strip(" .:-–—")
                break
        if not titulo and acum:
            titulo = normalizar_espacos(acum[0]).strip(" .:-–—")

    return autor, titulo


def _extrair_orientador_preliminar(capa: str, ficha: str) -> str:
    for padrao, texto in (
        (r"(?:^|\n)\s*(?!co[\-–—]?orient)orientador(?:a|\(a\))?\s*:\s*([^\n\r]+)", f"{capa}\n{ficha}"),
        (
            rf"(?<![Cc]o[\-–—])(?<![Cc]o)\bOrientador(?:a|\(a\))?\s*:?\s*([{MAIUSCULAS_PT}][^\n;]+?)"
            r"(?=(?<!\bProf)(?<!\bProfa)(?<!\bProfª)(?<!\bDr)(?<!\bDra)(?<!\bDrª)(?<!\bMe)(?<!\bMa)\.|;|\n|$)",
            ficha,
        ),
    ):
        if not texto:
            continue
        m = re.search(padrao, texto, flags=re.IGNORECASE if padrao.startswith("(?:") else 0)
        if m:
            cand = normalizar_nome_orientador(m.group(1))
            if _eh_nome_pessoa_valido(cand):
                return cand
    return ""


def _extrair_campos_capa(capa: str, autor_atual: str) -> tuple[str, str, str, List[str]]:
    instituicao = ""
    campus = ""
    autor = autor_atual
    candidatos_titulo: List[str] = []

    for linha in (normalizar_espacos(l) for l in capa.splitlines()):
        if not linha:
            continue
        if not instituicao and _PADRAO_LINHA_INSTITUICAO_RE.match(linha) and len(linha) <= 120:
            instituicao = formatar_nome_proprio(linha) if linha == linha.upper() else linha
            continue
        if not campus and (m_camp := _PADRAO_LINHA_CAMPUS_RE.match(linha)) and len(linha) <= 80:
            campus = formatar_nome_proprio(m_camp.group(1))
            continue
        if (
            re.fullmatch(r"(?:19|20)\d{2}", linha)
            or _PADRAO_PREFIXO_RUIDO_CAPA_RE.match(linha)
            or re.search(r"^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\s]+,\s*(?:19|20)\d{2}\.?$", linha)
        ):
            continue
        if not autor and len(linha.split()) <= 6:
            cand_pessoa = formatar_nome_proprio(limpar_nome_pessoa(linha))
            if cand_pessoa and _eh_nome_pessoa_valido(cand_pessoa):
                autor = cand_pessoa
                continue
        if len(linha) >= 12 and not _PADRAO_LINHA_INSTITUICAO_RE.match(linha):
            candidatos_titulo.append(linha)

    return autor, instituicao, campus, candidatos_titulo


def extrair_metadados_preliminares_pdf(
    capa: str,
    ficha_catalografica: str = "",
    nome_arquivo: str = "",
) -> Dict[str, Any]:
    """
    Extrai metadados preliminares (titulo, autor, orientador, ano, instituicao, campus)
    a partir da capa e da ficha catalográfica de um PDF local, para uso quando o
    manifesto de entrada não fornece esses campos.
    """
    capa_limpa = CONTROLE_INVISIVEL_RE.sub("", capa or "")
    ficha_limpa = CONTROLE_INVISIVEL_RE.sub("", ficha_catalografica or "")

    ano = _extrair_ano_preliminar(ficha_limpa, capa_limpa, nome_arquivo)
    autor, titulo = _extrair_autor_e_titulo_ficha(ficha_limpa)
    orientador = _extrair_orientador_preliminar(capa_limpa, ficha_limpa)
    autor, instituicao, campus, candidatos_titulo = _extrair_campos_capa(capa_limpa, autor)

    if not titulo and candidatos_titulo:
        titulo = normalizar_espacos(" ".join(candidatos_titulo[:3]))[:300]
    if not titulo:
        titulo = _limpar_titulo_de_arquivo(nome_arquivo)

    return {
        "titulo": titulo,
        "autor": autor,
        "orientador": orientador,
        "ano": ano,
        "instituicao": instituicao,
        "campus": campus,
    }
