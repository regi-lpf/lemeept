import re
from typing import List, Optional

from pipeline.catalogs import (
    PLACEHOLDERS_COORIENTADOR,
    PREPOSICOES_NOME,
    STOPWORDS_CONTINUACAO_NOME,
    STOPWORDS_PROSA_NOME,
)
from pipeline.normalizers import (
    CONTROLE_INVISIVEL_RE,
    MAIUSCULAS_PT,
    normalizar_chave_busca,
    normalizar_nome_orientador,
)


def _eh_linha_continuacao_nome(linha: str, primeira_all_caps: bool) -> bool:
    candidato = linha.strip().rstrip(".")
    if not candidato or re.search(r"[\d:;()\"'/\-–—.]", candidato):
        return False
    tokens = candidato.split()
    if not (1 <= len(tokens) <= 4):
        return False

    norm_linha = normalizar_chave_busca(candidato)
    if norm_linha in STOPWORDS_CONTINUACAO_NOME or norm_linha in PLACEHOLDERS_COORIENTADOR:
        return False

    tem_nome_proprio = False
    for tok in tokens:
        tok_norm = normalizar_chave_busca(tok)
        if tok_norm in STOPWORDS_CONTINUACAO_NOME or tok_norm in STOPWORDS_PROSA_NOME:
            return False
        if tok_norm in PREPOSICOES_NOME:
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
    if norm in PLACEHOLDERS_COORIENTADOR or any(p in norm for p in ("nao se aplica", "sem coorient")):
        return False
    if norm.startswith(("instituto federal", "campus ", "programa de ", "blumenau")):
        return False

    tokens = nome.split()
    if not (2 <= len(tokens) <= 9):
        return False

    nomes_capitalizados = 0
    for tok in tokens:
        tok_norm = normalizar_chave_busca(tok)
        if tok_norm in STOPWORDS_PROSA_NOME:
            return False
        if tok_norm in PREPOSICOES_NOME:
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
        rf";\s*(?i:co[\-–—]?orientador(?:a|\(a\))?)\s+([{MAIUSCULAS_PT}].*?)(?=\.\s*--|\.|;|\n\s*\n|$)",
        flags=re.DOTALL,
    )
    for m in padrao_ficha.finditer(texto):
        _registrar_candidato_pessoa(encontrados, m.group(1), orient_norm)

    return encontrados


def extrair_palavras_chave_resumo(bloco_resumo: str) -> List[str]:
    """Extrai palavras-chave do bloco de resumo suportando separadores ';', '.' ou ','."""
    match = re.search(
        r"(?:^|\n)\s*Palavras[\s\-–]+chaves?\s*:?\s*(.+?)(?=\n\s*\n|(?:^|\n)\s*(?:Abstract|Keywords)\b|$)",
        bloco_resumo,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    bruto = re.sub(r"\s+", " ", match.group(1)).strip().rstrip(".")
    sep = ";" if ";" in bruto else ("." if "." in bruto else ",")
    return [
        limpa
        for item in bruto.split(sep)
        if 2 <= len(limpa := item.strip(" .;-–—")) <= 80
    ]
