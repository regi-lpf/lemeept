import argparse
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf
import requests
import urllib3
from bs4 import BeautifulSoup

from pipeline.models_v4 import (
    ContratoExtracaoDeterministicaV4,
    DissertacaoDeterministica,
    EvidenciasEduCAPES,
    FonteTipoProduto,
    MetadadosResolvidos,
    RecortesTextuais,
    TrechoEpistemologico,
)
from pipeline.normalizers import (
    CONTROLE_INVISIVEL_RE,
    PREPOSICOES_NOME,
    limpar_nome_pessoa,
    normalizar_chave_busca,
    normalizar_espacos,
    normalizar_nome_orientador,
    remover_acentos,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Stopwords institucionais ou ruídos comuns no início de linhas ABNT que não são autores humanos
IGNORAR_ENTRADAS_REF = {
    "BRASIL", "SANTA CATARINA", "INSTITUTO", "FEDERAL", "CATARINENSE", "BLUMENAU",
    "INSTITUTO FEDERAL", "MINISTERIO", "MINISTÉRIO", "CONSELHO", "DECRETO", "LEI",
    "RESOLUCAO", "RESOLUÇÃO", "PORTARIA", "DISPONIVEL", "DISPONÍVEL", "ACESSO",
    "IN", "IBID", "IDEM", "OP", "CIT", "ORGANIZACAO", "ORGANIZAÇÃO", "UNESCO",
    "OCDE", "CAPES", "MEC", "CNE", "CEB", "REFERÊNCIAS", "REFERENCIAS",
    "EDUCAÇÃO", "EDUCACAO", "ANEXO", "APÊNDICE", "APENDICE", "TABELA", "FIGURA",
    "QUADRO", "SITE", "HTTP", "HTTPS", "REVISTA", "PROGRAMA", "PROFEPT",
    "UNIVERSIDADE", "SECRETARIA", "GOVERNO", "PRESIDÊNCIA", "PRESIDENCIA",
    "SENADO", "CÂMARA", "CAMARA", "IBGE", "INEP", "CNPQ", "FNDE",
}

# Partículas de sobrenome composto e agnomes em português/espanhol
PARTICULAS_SOBRENOME = {"DA", "DE", "DO", "DAS", "DOS", "DEL", "VON", "VAN"}
AGNOMES = {"JUNIOR", "JÚNIOR", "FILHO", "NETO", "SOBRINHO", "SEGUNDO", "TERCEIRO"}

# --- REGRAS CANÔNICAS PROFEPT ---
MAPEAMENTO_MP_LP = {
    "MP1": "LP1",
    "MP2": "LP1",
    "MP3": "LP1",
    "MP4": "LP2",
    "MP5": "LP2",
    "MP6": "LP2",
}

REGRAS_TIPO_PRODUTO: List[Tuple[str, str]] = [
    (
        "software_aplicativo",
        r"(?:^\s*aplicativo\b|\b(?:software|aplicativo\s+(?:m[oó]vel|web|educacional|de\s+\w+)|app|sistema\s+web|programa\s+de\s+computador|simulador|plataforma\s+virtual)\b)",
    ),
    ("manual_protocolo", r"\b(manual|protocolo|guia\s+de\s+instru[cç][oõ]es|procedimento\s+operacional)\b"),
    ("carta_mapa", r"\b(carta\s+pedag[oó]gica|mapa\s+conceitual|mapa\s+interativo|atlas)\b"),
    ("eventos_organizados", r"\b(exposi[cç][aã]o|mostra\s+cient[ií]fica|feira\s+de|olimp[ií]ada|semin[aá]rio|evento\s+cient[ií]fico)\b"),
    ("acervo", r"\b(acervo|curadoria|cole[cç][aã]o\s+digital|reposit[oó]rio|banco\s+de\s+dados)\b"),
    ("produto_comunicacao", r"\b(produto\s+comunicacional|programa\s+de\s+r[aá]dio|programa\s+de\s+tv|campanha\s+publicit[aá]ria|boletim|jornal|revista\s+de\s+divulga[cç][aã]o)\b"),
    ("tecnologia_social", r"\b(tecnologia\s+social|dispositivo|equipamento|inova[cç][aã]o\s+social|prot[oó]tipo)\b"),
    (
        "material_didatico_instrucional",
        r"\b(material\s+did[aá]tico|material\s+de\s+apoio|sequ[eê]ncia\s+did[aá]tica|unidade\s+did[aá]tica|cartilha|e-?book|livro\s+digital|caderno|roteiro|proposta\s+pedag[oó]gica|proposta\s+de\s+interven[cç][aã]o|jogo|hist[oó]ria\s+em\s+quadrinhos|hq|gloss[aá]rio|v[ií]deo|videoaula|anima[cç][aã]o|guia|texto\s+de\s+apoio|objeto\s+de\s+aprendizagem|folder\s+educativo|portf[oó]lio\s+formativo|podcast|ambiente\s+virtual|ava|moodle|website|site\s+educativo|blog)\b",
    ),
    ("curso_oficina", r"\b(curso\s+de\s+forma[cç][aã]o|curso\s+livre|curso\s+fic|curso\s+online|curso\s+autoformativo|oficina|minicurso|workshop)\b"),
]

# Regras restritas apenas a dc.type do eduCAPES sem ambiguidade (ignora genéricos como 'texto', 'portal', 'vídeo', etc.)
REGRAS_DC_TYPE_EDUCAPES: List[Tuple[str, str]] = [
    ("software_aplicativo", r"\b(aplicativo\s+m[oó]vel|software)\b"),
    ("curso_oficina", r"\bcurso\b"),
    ("material_didatico_instrucional", r"\b(podcast|jogo)\b"),
]

def extrair_sentenca_produto(texto: str) -> str:
    if not texto:
        return ""
    sentencas = re.split(r"(?<=[.!?])\s+", texto)
    relevantes = [s for s in sentencas if re.search(r"produto\s+educacional", s, flags=re.IGNORECASE)]
    return " ".join(relevantes)

def classificar_produto_regex(*fontes_texto: Optional[str]) -> Optional[str]:
    """Aplica regex de produto sobre fontes textuais em ordem de prioridade."""
    for fonte in fontes_texto:
        if not fonte:
            continue
        limpo = fonte.strip().lower()
        for tipo_canonico, padrao in REGRAS_TIPO_PRODUTO:
            if re.search(padrao, limpo, flags=re.IGNORECASE):
                return tipo_canonico
    return None


def classificar_produto_com_fonte(
    titulo_produto_bruto: Optional[str],
    sentenca_resumo: str,
    sentenca_corpo: str,
    titulo_capes: Optional[str],
    dc_types: List[str],
) -> Tuple[Optional[str], Optional[FonteTipoProduto]]:
    """
    Classifica o produto preservando a proveniência exata ('dissertacao_ficha' vs 'educapes_dc_type').
    """
    tipo_dissertacao = classificar_produto_regex(
        titulo_produto_bruto,
        sentenca_resumo,
        sentenca_corpo,
        titulo_capes,
    )
    if tipo_dissertacao:
        return tipo_dissertacao, "dissertacao_ficha"

    dc_texto = " ".join(dc_types).strip().lower()
    if dc_texto:
        for tipo_canonico, padrao in REGRAS_DC_TYPE_EDUCAPES:
            if re.search(padrao, dc_texto, flags=re.IGNORECASE):
                return tipo_canonico, "educapes_dc_type"

    return None, None


def detectar_macroprojeto_e_linha(texto_completo_pdf: str) -> Tuple[str, str]:
    """
    Varre o texto completo do PDF buscando assinaturas explícitas de MP1..MP6
    (por número ou título) e aplica o vínculo rígido MP1-3 -> LP1 | MP4-6 -> LP2.
    """
    # Normaliza: remove acentos, quebras de linha e espaços múltiplos
    txt_limpo = re.sub(r"\s+", " ", remover_acentos(texto_completo_pdf)).lower()
    # Versão condensada sem espaços para capturar PDFs com fontes coladas (ex: EPT-0085)
    txt_colado = re.sub(r"[^a-z0-9]", "", txt_limpo)

    # 1. Padrão numérico explícito (evitando falso positivo de "mp4" formato de vídeo)
    padroes_num = [
        r"\bmacro\s*[-]?\s*projeto(?:\s+de\s+pesquisa(?:\s+e\s+desenvolvimento)?)?\s*[:\-–]?\s*([1-6]|i{1,3}|iv|v|vi)\b",
        r"\bmp\s*[-]?\s*([1-35-6])\b",
    ]
    romanos = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}

    for padrao in padroes_num:
        m = re.search(padrao, txt_limpo)
        if m:
            val = m.group(1).lower()
            num = romanos.get(val, val)
            mp = f"MP{num}"
            return mp, MAPEAMENTO_MP_LP[mp]

    for m in re.finditer(r"(?<!\.)\bmp\s*[-]?\s*(4)\b", txt_limpo):
        antes = txt_limpo[max(0, m.start() - 25) : m.start()]
        depois = txt_limpo[m.end() : min(len(txt_limpo), m.end() + 45)]
        if re.search(r"(?:formato|arquivo|extensao|video|audio|midia|em)\s*[:(]?\s*$", antes):
            continue
        if re.match(
            r"^\s*(?:;|,|\)|\.|[-–—]?\s*(?:um\s+)?(?:padrao|formato|extensao|video|audio|duracao|mb|gb|kb)|\bde\s+\d+\s*(?:mb|gb|kb)\b)",
            depois,
        ):
            continue
        return "MP4", MAPEAMENTO_MP_LP["MP4"]

    # 2. Match pelos títulos canônicos dos Macroprojetos (tolerante a preposições e PDF sem espaço)
    assinaturas_mp = [
        ("MP1", r"propostas\s+metodologicas\s+e\s+recursos\s+didaticos", "propostasmetodologicase"),
        ("MP2", r"inclusao\s+e\s+diversidade\s+(?:em|nos)\s+espacos", "inclusaoediversidade"),
        ("MP3", r"praticas\s+educativas\s+no\s+curriculo\s+integrado", "praticaseducativasnocurriculointegrado"),
        ("MP4", r"historia\s+e\s+memorias?\s+no\s+contexto", "historiaememoriasnocontexto"),
        ("MP5", r"organizacao\s+do\s+curriculo\s+integrado", "organizacaodocurriculointegrado"),
        ("MP6", r"organizacao\s+(?:de|dos)\s+espacos\s+pedagogicos", "organizacaodeespacospedagogicos"),
    ]
    for mp, regex_espacado, slug_colado in assinaturas_mp:
        if re.search(regex_espacado, txt_limpo) or slug_colado in txt_colado:
            return mp, MAPEAMENTO_MP_LP[mp]

    # 3. Fallback apenas para Linha de Pesquisa (quando o autor declara a LP mas omite o MP)
    if re.search(r"praticas\s+(?:educativas|educacionais|pedagogicas)\s+(?:em|na)\s+(?:ept|educacao\s+profissional)", txt_limpo) or re.search(r"\blp\s*[-]?\s*1\b", txt_limpo):
        return "MP_INDEFINIDO", "LP1"

    if re.search(r"(?:organizac[aã]o\s+e\s+memorias?|memorias?\s+e\s+organizac[aã]o)\s+(?:de|dos)\s+espacos\s+pedagogicos", txt_limpo) or re.search(r"\blp\s*[-]?\s*2\b", txt_limpo):
        return "MP_INDEFINIDO", "LP2"

    return "MP_INDEFINIDO", "LP_INDEFINIDA"

_PLACEHOLDERS_COORIENTADOR = {
    "nao se aplica",
    "nao ha",
    "nenhum",
    "nenhuma",
    "n a",
    "na",
    "sem coorientador",
    "sem coorientadora",
    "sem coorientacao",
    "inexistente",
    "a definir",
    "nao informado",
    "nao informada",
}

_STOPWORDS_CONTINUACAO_NOME = {
    "blumenau",
    "camboriu",
    "concordia",
    "ibirama",
    "rio",
    "sao",
    "santa",
    "catarina",
    "brasil",
    "instituto",
    "federal",
    "campus",
    "programa",
    "mestrado",
    "dissertacao",
    "orientador",
    "orientadora",
    "coorientador",
    "coorientadora",
    "coorientacao",
    "linha",
    "macroprojeto",
    "area",
    "banca",
    "aprovada",
    "ficha",
    "cdd",
    "cdu",
    "profept",
    "ifc",
    "ifsc",
}

_STOPWORDS_PROSA_NOME = {
    "pela",
    "pelo",
    "para",
    "como",
    "com",
    "que",
    "esta",
    "este",
    "mestrado",
    "trabalho",
    "pesquisa",
    "dissertacao",
    "projeto",
    "visualidade",
    "material",
    "didatico",
    "ensino",
    "estudante",
    "estudantes",
    "curso",
    "area",
}


def _eh_linha_continuacao_nome(linha: str, primeira_all_caps: bool) -> bool:
    candidato = linha.strip().rstrip(".")
    if not candidato:
        return False
    if re.search(r"[\d:;()\"'/\-–—]", candidato):
        return False
    if "." in candidato:
        return False
    tokens = candidato.split()
    if not (1 <= len(tokens) <= 4):
        return False

    norm_linha = normalizar_chave_busca(candidato)
    if norm_linha in _STOPWORDS_CONTINUACAO_NOME or norm_linha in _PLACEHOLDERS_COORIENTADOR:
        return False

    tem_nome_proprio = False
    for tok in tokens:
        tok_norm = normalizar_chave_busca(tok)
        if tok_norm in _STOPWORDS_CONTINUACAO_NOME or tok_norm in _STOPWORDS_PROSA_NOME:
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
    if not (4 <= len(nome) <= 90):
        return False
    if re.search(r"\d", nome):
        return False

    norm = normalizar_chave_busca(nome)
    if norm in _PLACEHOLDERS_COORIENTADOR or any(p in norm for p in ("nao se aplica", "sem coorient")):
        return False
    if norm.startswith(("instituto federal", "campus ", "programa de ", "blumenau")):
        return False

    tokens = nome.split()
    if not (2 <= len(tokens) <= 9):
        return False

    nomes_capitalizados = 0
    for tok in tokens:
        tok_norm = normalizar_chave_busca(tok)
        if tok_norm in _STOPWORDS_PROSA_NOME:
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
    texto = CONTROLE_INVISIVEL_RE.sub("", texto_preliminar or "")
    if not texto:
        return []

    orient_limpo = normalizar_nome_orientador(orientador_principal or "")
    orient_norm = normalizar_chave_busca(orient_limpo)
    encontrados: List[str] = []

    # 1. Rótulo explícito com dois-pontos (capa, folha de rosto, ficha com ':')
    padrao_rotulo = re.compile(
        r"(?:^|\n|;)\s*co[\-–—]?orienta(?:dor(?:a|\(a\))?|[çc][ãa]o)\s*:\s*([^\n\r]*)",
        flags=re.IGNORECASE,
    )
    for m in padrao_rotulo.finditer(texto):
        linha1 = m.group(1).strip()
        pos_fim = m.end()

        if not linha1:
            resto = texto[pos_fim:]
            m_prox = re.match(r"^\r?\n[ \t]*([^\n\r]+)", resto)
            if m_prox:
                linha1 = m_prox.group(1).strip()
                pos_fim += m_prox.end()

        if not linha1:
            continue

        capturado = linha1
        if not linha1.endswith((".", ";")):
            resto = texto[pos_fim:]
            m_cont = re.match(r"^\r?\n(?![ \t]*\r?\n)[ \t]*([^\n\r]+)", resto)
            if m_cont:
                linha2 = m_cont.group(1).strip()
                primeira_all_caps = linha1 == linha1.upper() and any(c.isalpha() for c in linha1)
                if _eh_linha_continuacao_nome(linha2, primeira_all_caps):
                    capturado = f"{linha1} {linha2}"

        _registrar_candidato_pessoa(encontrados, capturado, orient_norm)

    # 2. Ficha catalográfica ABNT sem dois-pontos (ex.: '; coorientadora Nome Sobrenome. -- Blumenau')
    padrao_ficha = re.compile(
        r";\s*(?i:co[\-–—]?orientador(?:a|\(a\))?)\s+([A-ZÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ].*?)(?=\.\s*--|\.|;|\n\s*\n|$)",
        flags=re.DOTALL,
    )
    for m in padrao_ficha.finditer(texto):
        _registrar_candidato_pessoa(encontrados, m.group(1), orient_norm)

    return encontrados


def extrair_palavras_chave_resumo(bloco_resumo: str) -> List[str]:
    match = re.search(
        r"(?:^|\n)\s*Palavras[\s\-–]+chaves?\s*:?\s*(.+?)(?=\n\s*\n|(?:^|\n)\s*(?:Abstract|Keywords)\b|$)",
        bloco_resumo,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    bruto = re.sub(r"\s+", " ", match.group(1)).strip().rstrip(".")
    # Suporta separadores por ponto, ponto-e-vírgula ou vírgula
    sep = ";" if ";" in bruto else ("." if "." in bruto else ",")
    tags = []
    for item in bruto.split(sep):
        limpa = item.strip(" .;-–—")
        if 2 <= len(limpa) <= 80:
            tags.append(limpa)
    return tags


_MAIUSCULAS_PT = "A-ZÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ"
_MINUSCULAS_PT = "a-zàáâãäåçèéêëìíîïñòóôõöùúûüý"


def extrair_autores_referencias(texto_secao_referencias: str) -> List[str]:
    """
    Extrai sobrenomes de autores a partir das entradas bibliográficas no padrão ABNT
    (ex: 'SAVIANI, Dermeval...' -> 'Saviani', 'SILVA, João da...' -> 'Silva').
    """
    if not texto_secao_referencias:
        return []

    autores_encontrados = set()

    # Captura início de linha (ou após quebra) com SOBRENOME EM CAIXA ALTA seguido de vírgula
    padrao_abnt = re.compile(
        rf"(?:^|\n)\s*([{_MAIUSCULAS_PT}]{{2,}}(?:\s+(?:DA|DE|DO|DAS|DOS|[{_MAIUSCULAS_PT}]{{2,}}))*)\s*,\s*[{_MAIUSCULAS_PT}{_MINUSCULAS_PT}]"
    )

    for match in padrao_abnt.finditer(texto_secao_referencias):
        bruto = re.sub(r"\s+", " ", match.group(1)).strip()
        tokens = bruto.split()

        # Remove partículas iniciais soltas (ex: "DE SOUZA" -> "SOUZA")
        while tokens and tokens[0] in PARTICULAS_SOBRENOME:
            tokens.pop(0)
        while tokens and tokens[-1] in AGNOMES:
            tokens.pop()

        if not tokens:
            continue

        # Descarta se o bloco inteiro ou qualquer token principal for stopword institucional/editorial
        if bruto in IGNORAR_ENTRADAS_REF or any(t in IGNORAR_ENTRADAS_REF for t in tokens):
            continue

        if len(tokens[0]) < 3:
            continue

        # Mantém até 2 tokens relevantes para preservar sobrenomes compostos reais (ex.: Espírito Santo)
        if len(tokens) > 2 and tokens[1] not in PARTICULAS_SOBRENOME:
            tokens = tokens[:2]
        elif len(tokens) > 3:
            tokens = tokens[:3]

        formatado = " ".join(
            t.lower() if t in PARTICULAS_SOBRENOME else t.capitalize()
            for t in tokens
        )
        autores_encontrados.add(formatado)

    return sorted(autores_encontrados)

# --- EXTRAÇÃO DE TEXTO E RECORTES DO PDF ---
def ler_paginas_pdf(pdf_path: Path) -> List[Tuple[int, str]]:
    """Retorna lista de tuplas (numero_pagina_1_based, texto_limpo)."""
    paginas = []
    with pymupdf.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            txt = page.get_text("text") or ""
            paginas.append((idx, normalizar_espacos(txt)))
    return paginas


def _eh_pagina_sumario(txt: str) -> bool:
    if re.search(r"(^|\n)\s*SUM[ÁA]RIO\s*(\n|$)", txt, flags=re.IGNORECASE):
        return True
    return len(re.findall(r"\.{4,}", txt)) >= 3


_PADRAO_INTRO = re.compile(
    r"(^|\n)\s*(?:\d+(?:\.\d+)*\.?\s+)?INTRODU[ÇC][ÃA]O\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)

_PADRAO_REFS = re.compile(
    r"(?:^|\n)\s*(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(?:"
    r"REFER[ÊE]NCIAS(?:\s+(?:BIBLIOGR[ÁA]FICAS|BIBLOGR[ÁA]FICAS|CONSULTADAS))?"
    r"|Refer[êe]ncias(?:\s+(?:Bibliogr[áa]ficas|Consultadas))?"
    r"|BIBLIOGRAFIA(?:\s*/\s*FONTES\s+DE\s+REFER[ÊE]NCIAS?)?"
    r"|Bibliografia(?:\s*/\s*Fontes\s+de\s+Refer[êe]ncias?)?"
    r"|OBRAS\s+QUE\s+EMBASARAM(?:\s+ESTA\s+COMPOSI[ÇC][ÃA]O)?"
    r")\s*[:|\-]?(?:\s*\d+)?\s*(?=\n|$)",
    flags=re.MULTILINE,
)


def isolar_secoes_pdf(paginas: List[Tuple[int, str]]) -> Tuple[RecortesTextuais, str]:
    if not paginas:
        return RecortesTextuais(), ""

    paginas = [(num_pag, CONTROLE_INVISIVEL_RE.sub("", txt)) for num_pag, txt in paginas]

    # 1. Pré-textuais (primeiras 18 páginas cobrem capa, folha de rosto, ficha, ata, resumo e sumário)
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
            # Se Palavras-chave estiver na página seguinte antes do Abstract, incorpora ao recorte
            if not re.search(r"(?:^|\n)\s*palavras[\s\-–]+chaves?", bloco_resumo, flags=re.IGNORECASE) and idx_pre + 1 < len(paginas):
                prox_txt = paginas[idx_pre + 1][1]
                if not re.match(r"^\s*ABSTRACT\b", prox_txt, flags=re.IGNORECASE) and re.search(
                    r"(?:^|\n)\s*palavras[\s\-–]+chaves?", prox_txt, flags=re.IGNORECASE
                ):
                    corte = re.split(r"(?:^|\n)\s*ABSTRACT\b", prox_txt, maxsplit=1, flags=re.IGNORECASE)[0]
                    bloco_resumo = f"{bloco_resumo}\n{corte.strip()}"
            resumo = f"[PÁG. {num_pag}]\n{bloco_resumo}"
        if not sumario and re.search(r"(^|\n)\s*SUM[ÁA]RIO\s*(\n|$)", upper):
            # Captura página do sumário e a seguinte caso seja longo
            prox = paginas[idx_pre + 1][1] if idx_pre + 1 < len(paginas) else ""
            sumario = f"[PÁG. {num_pag}]\n{txt}\n{prox[:1500]}"

    # 2. Localizar início da Introdução e das Referências
    idx_intro = None
    for i, (num_pag, txt) in enumerate(paginas):
        if num_pag <= 5 or _eh_pagina_sumario(txt):
            continue
        linhas_topo = "\n".join(txt.splitlines()[:10])
        if _PADRAO_INTRO.search(linhas_topo):
            idx_intro = i
            break

    min_idx_refs = (idx_intro + 1) if idx_intro is not None else min(5, len(paginas) // 2)
    idx_refs = None
    refs_match_pos = 0
    for i in range(min_idx_refs, len(paginas)):
        _, txt = paginas[i]
        if _eh_pagina_sumario(txt):
            continue
        match_ref = _PADRAO_REFS.search(txt)
        if match_ref:
            idx_refs = i
            refs_match_pos = match_ref.start()
            break

    introducao_paginas = paginas[idx_intro : idx_intro + 5] if idx_intro is not None else paginas[8:13]
    introducao = "\n\n".join(f"[PÁG. {p}]\n{t}" for p, t in introducao_paginas)[:8000]

    # 3. Seção de descrição do Produto Educacional (geralmente no capítulo metodológico ou capítulo final antes das referências)
    fim_corpo = idx_refs if idx_refs is not None else len(paginas)
    corpo_paginas = paginas[(idx_intro or 8) : fim_corpo]

    trechos_produto = []
    for p, t in corpo_paginas:
        if re.search(r"\bproduto\s+educacional\b", t, flags=re.IGNORECASE):
            # Extrai apenas parágrafos relevantes onde "produto educacional" aparece
            for paragrafo in t.split("\n\n"):
                if re.search(r"produto\s+educacional", paragrafo, flags=re.IGNORECASE) and len(paragrafo) > 80:
                    trechos_produto.append(f"[PÁG. {p}] {paragrafo.strip()}")
                    if len(trechos_produto) >= 6:
                        break
        if len(trechos_produto) >= 6:
            break

    descricao_produto = "\n\n".join(trechos_produto)[:3500]

    # 4. Evidências Epistemológicas (Introdução + Referencial/Metodologia) + Citações detectadas
    trechos_epist: List[TrechoEpistemologico] = []
    citacoes_unicas = set()

    marcadores_epist = re.compile(
        r"\b(epistemol[óo]g|ontol[óo]g|materialismo\s+hist[óo]rico|dial[ée]tic|freire|saviani|ciavatta|frigotto|ramos|gramsci|kosik|luk[áa]cs|vygotsky|vigotski|bakhtin|foucault|bourdieu|morin|positivis|fenomenolog|hermeneut|construtivis|omnilateral|politecnia|trabalho\s+como\s+princ[íi]pio\s+educativo|curr[íi]culo\s+integrado)\b",
        flags=re.IGNORECASE,
    )
    padrao_citacao = re.compile(r"\(([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s;&.-]+?,\s*\d{4}[a-z]?(?:,\s*p\.\s*\d+(?:-\d+)?)?)\)")

    for p, t in corpo_paginas:
        if len(trechos_epist) >= 12:
            break
        for paragrafo in t.split("\n\n"):
            if len(paragrafo) < 120:
                continue
            if marcadores_epist.search(paragrafo):
                cits = padrao_citacao.findall(paragrafo)
                for c in cits:
                    sobrenome = c.split(",")[0].strip().split()[0].upper()
                    if len(sobrenome) >= 3:
                        citacoes_unicas.add(sobrenome)
                trechos_epist.append(
                    TrechoEpistemologico(
                        secao="Introdução" if (idx_intro is not None and p <= paginas[idx_intro][0] + 4) else "Corpo/Fundamentação",
                        pagina=p,
                        texto=paragrafo.strip()[:1200],
                        citacoes_detectadas=cits[:8],
                    )
                )
                if len(trechos_epist) >= 12:
                    break

    # 5. Isolar seção de Referências integral (para autores_referenciados) e filtrar obras citadas
    texto_refs = ""
    referencias_filtradas = []
    if idx_refs is not None:
        primeira_pag_refs = paginas[idx_refs][1][refs_match_pos:]
        paginas_restantes = [t for _, t in paginas[idx_refs + 1 : idx_refs + 25]]
        texto_refs = "\n".join([primeira_pag_refs, *paginas_restantes])
        if citacoes_unicas:
            entradas = re.split(rf"\n(?=[{_MAIUSCULAS_PT}]{{2,}}[,\s])", texto_refs)
            for entrada in entradas:
                entrada_limpa = re.sub(r"\s+", " ", entrada).strip()
                if len(entrada_limpa) < 25:
                    continue
                primeiro_token = re.split(r"[,.\s]", entrada_limpa)[0].upper()
                if primeiro_token in citacoes_unicas:
                    referencias_filtradas.append(entrada_limpa[:400])
                    if len(referencias_filtradas) >= 25:
                        break

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


def _adicionar_unico(lista: List[str], valor: str) -> None:
    chave = valor.strip().lower()
    if chave and all(item.strip().lower() != chave for item in lista):
        lista.append(valor.strip())


def _adicionar_colaborador_unico(lista: List[Dict[str, Optional[str]]], nome: str, papel: Optional[str]) -> None:
    chave = (nome.strip().lower(), (papel or "").strip().lower())
    if not chave[0]:
        return
    for item in lista:
        if (item.get("nome", "").strip().lower(), (item.get("papel") or "").strip().lower()) == chave:
            return
    lista.append({"nome": nome.strip(), "papel": papel})


def _adicionar_identificador_unico(
    lista: List[Dict[str, str]],
    esquema: str,
    valor: str,
    url: str = "",
) -> None:
    chave = (esquema.strip().lower(), valor.strip().lower())
    if not chave[1]:
        return
    for item in lista:
        if (item.get("esquema", "").strip().lower(), item.get("valor", "").strip().lower()) == chave:
            return
    lista.append({"esquema": esquema.strip(), "valor": valor.strip(), "url": url})


# --- SCRAPING RESILIENTE DO EDUCAPES ---
def coletar_evidencias_educapes(
    handle_url: Optional[str],
    titulo_produto_bruto: Optional[str],
    resumo_pdf: str,
    descricao_produto_pdf: str,
    cache_dir: Path,
) -> EvidenciasEduCAPES:
    sentenca_resumo = extrair_sentenca_produto(resumo_pdf)
    sentenca_corpo = extrair_sentenca_produto(descricao_produto_pdf)

    if not handle_url:
        tipo_regex, fonte_tipo = classificar_produto_com_fonte(
            titulo_produto_bruto=titulo_produto_bruto,
            sentenca_resumo=sentenca_resumo,
            sentenca_corpo=sentenca_corpo,
            titulo_capes=None,
            dc_types=[],
        )
        return EvidenciasEduCAPES(
            titulo_produto=titulo_produto_bruto,
            titulo_produto_bruto=titulo_produto_bruto,
            tipo_produto_regex=tipo_regex,
            fonte_tipo_regex=fonte_tipo,
        )

    # Normaliza URL para carregar a página completa (?show=full no DSpace revela todos os campos Dublin Core)
    base_url = handle_url.strip().rstrip("/")
    full_url = base_url if "show=full" in base_url else f"{base_url}?show=full"

    slug_cache = re.sub(r"[^a-zA-Z0-9_-]", "_", base_url.split("handle/")[-1])
    cache_file = cache_dir / f"{slug_cache}.html"

    html = ""
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8", errors="ignore")
    else:
        try:
            resp = requests.get(
                full_url,
                timeout=20,
                verify=False,
                headers={"User-Agent": "Mozilla/5.0 (LEME-EPT Bibliometric Pipeline)"},
            )
            if resp.status_code == 200:
                html = resp.text
                cache_file.write_text(html, encoding="utf-8")
                time.sleep(0.6)  # Respeita rate-limit institucional
        except requests.RequestException as e:
            print(f"  [eduCAPES] Falha ao acessar {full_url}: {e}")

    titulo_capes = None
    data_pub = None
    dc_types: List[str] = []
    keywords: List[str] = []
    autores_colab: List[Dict[str, Optional[str]]] = []
    identificadores: List[Dict[str, str]] = [
        {"esquema": "handle", "valor": base_url.split("handle/")[-1], "url": base_url}
    ]
    colecao = None

    if html:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Tags <meta> Dublin Core no <head> (padrão universal DSpace/eduCAPES)
        for meta in soup.find_all("meta"):
            nome_meta = (meta.get("name") or "").lower().strip()
            conteudo = (meta.get("content") or "").strip()
            if not conteudo:
                continue

            if nome_meta == "dc.title" and not titulo_capes:
                titulo_capes = conteudo
            elif nome_meta in ("dcterms.issued", "dc.date.issued") and not data_pub:
                data_pub = conteudo[:10]
            elif nome_meta == "dc.type":
                _adicionar_unico(dc_types, conteudo)
            elif nome_meta in ("dc.subject", "dcterms.subject"):
                _adicionar_unico(keywords, conteudo)
            elif nome_meta in ("dc.contributor", "dc.creator"):
                papel = meta.get("scheme") or nome_meta.replace("dc.", "")
                _adicionar_colaborador_unico(autores_colab, conteudo, papel)
            elif nome_meta in ("dc.identifier", "dcterms.identifier") and "handle" not in conteudo:
                _adicionar_identificador_unico(identificadores, "identifier", conteudo, "")

        # 2. Tabela Dublin Core do DSpace (?show=full)
        for tr in soup.select("table tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            campo = tds[0].get_text(strip=True).lower()
            valor = tds[1].get_text(" ", strip=True)
            if not valor:
                continue

            if campo == "dc.title" and not titulo_capes:
                titulo_capes = valor
            elif campo == "dc.date.issued" and not data_pub:
                data_pub = valor[:10]
            elif campo == "dc.type":
                _adicionar_unico(dc_types, valor)
            elif campo in ("dc.subject", "dc.subject.other"):
                _adicionar_unico(keywords, valor)
            elif campo.startswith("dc.contributor"):
                papel = campo.replace("dc.contributor.", "") if "." in campo[14:] else "colaborador"
                _adicionar_colaborador_unico(autores_colab, valor, papel)
            elif campo.startswith("dc.identifier.") and campo != "dc.identifier.uri":
                _adicionar_identificador_unico(identificadores, campo.replace("dc.identifier.", ""), valor, "")

        # Coleção ("Aparece nas coleções:")
        for li in soup.select("ul.ds-referenceSet-list li a, .item-page-field-wrapper a[href*='/handle/']"):
            href = li.get("href", "")
            texto_link = li.get_text(strip=True)
            if texto_link and "capes" in href and href not in base_url:
                colecao = texto_link
                break

    # Hierarquia de fontes: Rótulo/dissertação primeiro, dc.type do eduCAPES apenas como evidência complementar
    tipo_regex, fonte_tipo = classificar_produto_com_fonte(
        titulo_produto_bruto=titulo_produto_bruto,
        sentenca_resumo=sentenca_resumo,
        sentenca_corpo=sentenca_corpo,
        titulo_capes=titulo_capes,
        dc_types=dc_types,
    )

    return EvidenciasEduCAPES(
        handle_url=base_url,
        titulo_produto=titulo_capes or titulo_produto_bruto,
        titulo_produto_bruto=titulo_produto_bruto,
        data_publicacao=data_pub,
        autores_colaboradores=autores_colab,
        identificadores=identificadores,
        colecao_educapes=colecao,
        dc_type_educapes=dc_types,
        palavras_chave_educapes=keywords,
        tipo_produto_regex=tipo_regex,
        fonte_tipo_regex=fonte_tipo,
    )


# --- ORQUESTRAÇÃO DA ETAPA 2 ---
def executar_etapa2(
    manifest_path: Path = Path("data/stage1_manifest.json"),
    output_dir: Path = Path("data/stage2_payloads"),
    cache_dir: Path = Path("data/cache_educapes"),
    target_id: Optional[str] = None,
):
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifesto da Etapa 1 não encontrado: {manifest_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifesto = json.load(f)

    registros = manifesto if isinstance(manifesto, list) else manifesto.get("registros", manifesto.get("defesas", []))
    if target_id:
        registros = [r for r in registros if r.get("id") == target_id]
    print(f"Iniciando Etapa 2 para {len(registros)} defesas...")

    processados = 0
    erros = []

    for item in registros:
        cod = item["id"]
        fonte = item["fonte_profept"]
        arquivos = item["arquivos"]
        pdf_path = Path(arquivos["pdf_dissertacao_path"])

        try:
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF ausente: {pdf_path}")

            paginas = ler_paginas_pdf(pdf_path)
            texto_full_pdf = "\n".join(txt for _, txt in paginas)
            recortes, texto_integral_referencias = isolar_secoes_pdf(paginas)

            paginas_prelim = "\n".join(txt for _, txt in paginas[:5])
            bloco_coorientador = f"{paginas_prelim}\n{recortes.ficha_catalografica}".strip()
            autor_limpo = limpar_nome_pessoa(fonte["autor_bruto"])
            orientador_limpo = normalizar_nome_orientador(fonte.get("orientador_bruto"))
            mp, lp = detectar_macroprojeto_e_linha(texto_full_pdf)
            coorientadores = extrair_coorientador(
                bloco_coorientador,
                orientador_principal=orientador_limpo,
            )
            kw_dissertacao = extrair_palavras_chave_resumo(recortes.resumo)

            titulo_bruto_prod = fonte.get("titulo_produto_bruto")
            evidencias_capes = coletar_evidencias_educapes(
                handle_url=fonte.get("handle_educapes"),
                titulo_produto_bruto=titulo_bruto_prod,
                resumo_pdf=recortes.resumo,
                descricao_produto_pdf=recortes.descricao_produto_na_dissertacao,
                cache_dir=cache_dir,
            )

            payload = ContratoExtracaoDeterministicaV4(
                id=cod,
                metadados_resolvidos=MetadadosResolvidos(
                    ano=int(fonte["ano"]),
                    autor=autor_limpo,
                    orientador=orientador_limpo,
                    coorientadores=coorientadores,
                    instituicao="Instituto Federal Catarinense (IFC)",
                    campus=fonte.get("campus") or "Blumenau",
                    linha_pesquisa=lp,
                    macroprojeto=mp,
                ),
                dissertacao_deterministica=DissertacaoDeterministica(
                    titulo=fonte["titulo_bruto"].strip(),
                    link=fonte["url_dissertacao"],
                    palavras_chave=kw_dissertacao,
                    autores_referenciados=extrair_autores_referencias(texto_integral_referencias)
                ),
                evidencias_educapes=evidencias_capes,
                recortes_textuais=recortes,
            )

            out_file = output_dir / f"{cod}.json"
            with open(out_file, "w", encoding="utf-8") as out:
                json.dump(payload.model_dump(), out, ensure_ascii=False, indent=2)

            processados += 1
            if processados % 15 == 0 or processados == len(registros):
                print(f"  [{processados}/{len(registros)}] {cod} -> MP:{mp} | LP:{lp} | TipoRegex:{evidencias_capes.tipo_produto_regex}")

        except Exception as e:
            erros.append((cod, str(e)))
            print(f"  [ERRO] {cod}: {e}")

    print("\n--- Resumo Etapa 2 ---")
    print(f"Payloads gerados com sucesso: {processados}/{len(registros)}")
    if erros:
        print(f"Falhas ({len(erros)}): {erros}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 2: Extração determinística de PDFs e eduCAPES.")
    parser.add_argument("--manifesto", type=Path, default=Path("data/stage1_manifest.json"))
    parser.add_argument("--saida-dir", type=Path, default=Path("data/stage2_payloads"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache_educapes"))
    parser.add_argument("--id", dest="target_id", default=None, help="Processar apenas um ID específico (ex: EPT-0001).")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    executar_etapa2(
        manifest_path=args.manifesto,
        output_dir=args.saida_dir,
        cache_dir=args.cache_dir,
        target_id=args.target_id,
    )

