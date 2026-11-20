import re
from typing import List, Optional, Tuple

from pipeline.catalogs import MP_PARA_LP
from pipeline.models_v4 import FonteTipoProduto
from pipeline.normalizers import remover_acentos

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
    return " ".join(
        s for s in sentencas if re.search(r"produto\s+educacional", s, flags=re.IGNORECASE)
    )


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
    """Classifica o produto preservando a proveniência exata ('dissertacao_ficha' vs 'educapes_dc_type')."""
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
    txt_limpo = re.sub(r"\s+", " ", remover_acentos(texto_completo_pdf)).lower()
    txt_colado = re.sub(r"[^a-z0-9]", "", txt_limpo)

    padroes_num = [
        r"\bmacro\s*[-]?\s*projeto(?:\s+de\s+pesquisa(?:\s+e\s+desenvolvimento)?)?\s*[:\-–]?\s*([1-6]|i{1,3}|iv|v|vi)\b",
        r"\bmp\s*[-]?\s*([1-35-6])\b",
    ]
    romanos = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}

    for padrao in padroes_num:
        m = re.search(padrao, txt_limpo)
        if m:
            val = m.group(1).lower()
            mp = f"MP{romanos.get(val, val)}"
            return mp, MP_PARA_LP[mp]

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
        return "MP4", MP_PARA_LP["MP4"]

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
            return mp, MP_PARA_LP[mp]

    if re.search(r"praticas\s+(?:educativas|educacionais|pedagogicas)\s+(?:em|na)\s+(?:ept|educacao\s+profissional)", txt_limpo) or re.search(r"\blp\s*[-]?\s*1\b", txt_limpo):
        return "MP_INDEFINIDO", "LP1"

    if re.search(r"(?:organizacao\s+e\s+memorias?|memorias?\s+e\s+organizacao)\s+(?:de|dos)\s+espacos\s+pedagogicos", txt_limpo) or re.search(r"\blp\s*[-]?\s*2\b", txt_limpo):
        return "MP_INDEFINIDO", "LP2"

    return "MP_INDEFINIDO", "LP_INDEFINIDA"
