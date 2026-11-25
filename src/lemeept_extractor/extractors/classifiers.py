import re
from typing import Dict, List, Optional, Tuple

from lemeept_extractor.catalogs import MP_PARA_LP
from lemeept_extractor.models import FonteTipoProduto
from lemeept_extractor.normalizers import remover_acentos

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

# Regras de extração do formato específico do produto educacional (rótulos legíveis padronizados)
REGRAS_FORMATO_PRODUTO: List[Tuple[str, str]] = [
    ("História em Quadrinhos (HQ)", r"\b(?:hist[oó]rias?\s+em\s+quadrinhos?|quadrinhos|hqs?)\b"),
    ("Infográfico", r"\binfogr[aá]ficos?\b"),
    ("Podcast", r"\bpodcasts?\b"),
    ("Sequência Didática", r"\b(?:sequ[eê]ncias?\s+did[aá]ticas?|unidades?\s+did[aá]ticas?)\b"),
    ("Jogo Educacional", r"\b(?:jogos?\s+(?:educaciona(?:l|is)|did[aá]ticos?|pedag[oó]gicos?|de\s+tabuleiro|digitais?|interativos?|educativos?)|quiz)\b"),
    ("Aplicativo / Software", r"(?:^\s*aplicativos?\b|\b(?:softwares?|aplicativos?\s+(?:m[oó]ve(?:l|is)|web|educaciona(?:l|is)|de\s+\w+)|sistemas?\s+web|simuladores?|plataformas?\s+virtua(?:l|is))\b)"),
    ("Animação", r"\banima[cç](?:[ãa]o|[õo]es)\b"),
    ("Site / Portal", r"\b(?:sites?|websites?|s[ií]tios?\s+eletr[oô]nicos?|portais?|portal(?:\s+eletr[oô]nico)?|p[aá]ginas?\s+de\s+internet|blogs?|tour\s+360)\b"),
    ("Glossário", r"\bgloss[aá]rios?\b"),
    ("Portfólio Formativo", r"\bportf[oó]lios?\s+formativos?\b"),
    ("Folder / Panfleto", r"\b(?:folders?(?:\s+educativos?)?|panfletos?(?:\s+digitais?)?)\b"),
    ("Cartilha", r"\bcartilhas?\b"),
    ("Caderno Pedagógico", r"\bcadernos?(?:\s+(?:did[aá]tico[\-\s]?pedag[oó]gicos?|pedag[oó]gicos?|de\s+orienta[cç][õo]es|tem[aá]ticos?|formativos?))?\b"),
    ("Manual / Protocolo", r"\b(?:manuais?|manual(?:\s+(?:pr[aá]tico|t[eé]cnico|de\s+opera[cç][ãa]o))?|protocolos?|tutoriais?|tutorial(?:\s+pedag[oó]gico)?|prontu[aá]rios?\s+unificados?)\b"),
    ("Minuta / Norma", r"\b(?:minutas?(?:\s+de\s+\w+)?|normativas?|norma\s+de\s+afastamento)\b"),
    ("Guia", r"\bguias?(?:\s+(?:did[aá]ticos?|pedag[oó]gicos?|educaciona(?:l|is)|digitais?|orientadores?|de\s+\w+))?\b"),
    ("E-book / Livro Digital", r"(?:\b(?:e[\-\s]?books?|livros?\s+digitais?|livros?\s+did[aá]ticos?|livros?\s+paradid[aá]ticos?)\b|formatodee-?book)"),
    ("Curso", r"(?:^\s*cursos?\s*[–—\-:]|\b(?:cursos?\s+de\s+forma[cç][ãa]o|cursos?\s+livres?|cursos?\s+fic|cursos?\s+online|cursos?\s+autoformativos?|minicursos?|workshops?|capacita[cç][ãa]o\s+de\s+servidores|o\s+curso\s+[“\"])\b)"),
    ("Oficina", r"\boficinas?(?:\s+(?:pedag[oó]gicas?|formativas?|tem[aá]ticas?))?\b"),
    ("Palestra / Apresentação", r"(?:^\s*aprese?nta[cç][ãa]o\s*[–—\-:]|\b(?:ciclos?\s+de\s+palestras?|palestras?)\b)"),
    ("Exposição / Evento", r"\b(?:exposi[cç](?:[ãa]o|[õo]es)|feiras?\s+de\s+\w+|mostras?\s+cient[ií]ficas?|olimp[ií]adas?|semin[aá]rios?|eventos?\s+cient[ií]ficos?)\b"),
    ("Memorial / Acervo", r"\b(?:memoriais?(?:\s+virtua(?:l|is))?|memorial(?:\s+virtual)?|reposit[oó]rios?|acervos?|cole[cç][õo]es?\s+digitais?)\b"),
    ("Vídeo / Audiovisual", r"\b(?:v[ií]deo[\s\-–]?aulas?|v[ií]deos?(?:\s+curtos?)?|document[aá]rios?(?:\s+audiovisuais?)?|narrativas?\s+audiovisuais?|audiovisual|lives?\s+registradas?)\b"),
    ("Roteiro / Proposta Pedagógica", r"\b(?:roteiros?(?:\s+de\s+\w+)?|propostas?\s+(?:pedag[oó]gicas?|de\s+interven[cç][ãa]o|de\s+ensino|de\s+pr[aá]ticas?\s+curricular\w*)|viv[eê]ncias?\s+intercooperativas?|projetos?\s+de\s+extens[ãa]o)\b"),
]

EXCLUSOES_CONTEXTO_FORMATO: Dict[str, str] = {
    "Aplicativo / Software": r"(?:envolvendo|atrav[eé]s\s+do|uso\s+do|utiliza[cç][ãa]o\s+do|com\s+o|por\s+meio\s+do|media[cç][ãa]o\s+com\s+a)\s+(?:aplicativo|software|plataforma)",
    "Vídeo / Audiovisual": r"produ[cç][ãa]o\s+audiovisual",
}

REGRAS_DC_TYPE_FORMATO: List[Tuple[str, str]] = [
    ("Aplicativo / Software", r"\b(?:aplicativo\s+m[oó]vel|software)\b"),
    ("Jogo Educacional", r"\bjogo\b"),
    ("Animação", r"\banima[cç][ãa]o\b"),
    ("Podcast", r"\b[áa]udio\b"),
    ("Vídeo / Audiovisual", r"\bv[ií]deo\b"),
    ("E-book / Livro Digital", r"\blivro\s+digital\b"),
    ("Site / Portal", r"\bportal\b"),
    ("Curso", r"\b(?:curso|aula\s+digital)\b"),
    ("Palestra / Apresentação", r"\bapresenta[cç][ãa]o\b"),
]

_ANCORA_FORMATO_RE = re.compile(
    r"(?:"
    r"(?:em|no|na)\s+formato\s*(?:de\s*)?(?:um[a]?\s*)?"
    r"|(?:em|na)\s+forma\s+de\s+(?:um[a]?\s*)?"
    r"|consist(?:e|indo|iu)\s+em\s+(?:um[a]?\s*)?"
    r"|resultou\s+(?:em\s+um[a]?|num[a]?)\s+"
    r"|caracterizad[oa]\s+(?:por|como)\s+(?:um[a]?\s*)?"
    r"|produtos?\s+educaciona(?:l|is)\s*(?:\(pe\))?\s*(?:[,:]\s*|é\s+|foi\s+|constitui[- ]se\s+(?:em|como)\s+)?(?:um[a]?|o|a|ou)\s+"
    r"|(?:elaborad[oa]|desenvolvid[oa]|constru[íi]d[oa]|criad[oa]|produzid[oa]|confeccionad[oa]|elaboramos|desenvolvemos|constru[íi]mos|criamos|produzimos)\s+(?:como\s+produto\s+educacional\s+)?(?:um[a]?|o|a)\s+"
    r")([^.,;!?]{1,55})",
    flags=re.IGNORECASE,
)


def extrair_sentenca_produto(texto: str) -> str:
    if not texto:
        return ""
    sentencas = re.split(r"(?<=[.!?])\s+", texto)
    return " ".join(
        s for s in sentencas if re.search(r"produto\s+educacional", s, flags=re.IGNORECASE)
    )


def extrair_contexto_produto(texto: str) -> str:
    """Extrai sentenças sobre o produto educacional incluindo a sentença imediatamente seguinte."""
    if not texto:
        return ""
    sentencas = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", texto).strip())
    selecionadas: List[str] = []
    for idx, sent in enumerate(sentencas):
        if re.search(r"\bprodutos?\s+educaciona(?:l|is)\b", sent, flags=re.IGNORECASE):
            selecionadas.append(sent)
            if idx + 1 < len(sentencas):
                selecionadas.append(sentencas[idx + 1])
    return " ".join(selecionadas)


def _encontrar_formato_em_texto(
    texto: Optional[str],
    preferir_mais_cedo: bool = False,
) -> Optional[str]:
    if not texto:
        return None
    low = texto.strip().lower()
    candidatos: List[Tuple[int, int, str]] = []
    for idx_regra, (formato, padrao) in enumerate(REGRAS_FORMATO_PRODUTO):
        m = re.search(padrao, low, flags=re.IGNORECASE)
        if not m:
            continue
        exclusao = EXCLUSOES_CONTEXTO_FORMATO.get(formato)
        if exclusao and re.search(exclusao, low[max(0, m.start() - 35) : m.end() + 20], flags=re.IGNORECASE):
            continue
        if not preferir_mais_cedo:
            return formato
        candidatos.append((m.start(), idx_regra, formato))
    if candidatos:
        return min(candidatos)[2]
    return None


def _extrair_prefixo_declarado_produto(titulo_bruto: Optional[str]) -> str:
    if not titulo_bruto:
        return ""
    limpo = re.sub(r"^(?:s\s+)?(?:produto\s+)?educ(?:ac)?ional\s*:\s*", "", titulo_bruto.strip(), flags=re.IGNORECASE)
    m = re.match(r"^([^–—\-:]{2,35})\s*[–—\-:]", limpo)
    if not m:
        return ""
    prefixo = m.group(1).strip()
    if re.match(
        r"^(?:textos?|material\s+did[aá]tico(?:\s+instrucional)?|outros?|v[ií]deos?)$",
        prefixo,
        flags=re.IGNORECASE,
    ):
        return ""
    return f"{prefixo} –"


def classificar_formato_produto_com_fonte(
    resumo_pdf: str,
    descricao_produto_pdf: str,
    titulo_produto_bruto: Optional[str],
    titulo_capes: Optional[str],
    dc_types: List[str],
) -> Tuple[Optional[str], Optional[FonteTipoProduto]]:
    """
    Infere o formato específico do produto priorizando declarações da dissertação/título
    e usando dc.type do eduCAPES apenas como fallback de menor prioridade.
    """
    ctx_resumo = extrair_contexto_produto(resumo_pdf)
    ctx_corpo = extrair_contexto_produto(descricao_produto_pdf)

    # 1. Declaração ancorada explícita no resumo (prioridade máxima)
    for m in _ANCORA_FORMATO_RE.finditer(ctx_resumo):
        fmt = _encontrar_formato_em_texto(m.group(1), preferir_mais_cedo=True)
        if fmt:
            return fmt, "dissertacao_ficha"

    # 2. Prefixo específico declarado no título ProfEPT/dissertação (ex.: 'Curso –', 'HQ –')
    prefixo = _extrair_prefixo_declarado_produto(titulo_produto_bruto)
    if prefixo:
        fmt = _encontrar_formato_em_texto(prefixo)
        if fmt:
            return fmt, "dissertacao_ficha"

    # 3. Declaração ancorada na descrição do produto no corpo da dissertação
    for m in _ANCORA_FORMATO_RE.finditer(ctx_corpo):
        fmt = _encontrar_formato_em_texto(m.group(1), preferir_mais_cedo=True)
        if fmt:
            return fmt, "dissertacao_ficha"

    # 4. Ocorrência direta no contexto do resumo, títulos ou contexto do corpo
    for fonte in (ctx_resumo, titulo_produto_bruto, titulo_capes, ctx_corpo):
        fmt = _encontrar_formato_em_texto(fonte)
        if fmt:
            return fmt, "dissertacao_ficha"

    # 5. Fallback ancorado no resumo completo (quando omite o termo 'produto educacional')
    resumo_plano = re.sub(r"\s+", " ", resumo_pdf or "")
    for m in _ANCORA_FORMATO_RE.finditer(resumo_plano):
        fmt = _encontrar_formato_em_texto(m.group(1), preferir_mais_cedo=True)
        if fmt:
            return fmt, "dissertacao_ficha"

    # 6. Fallback de menor prioridade em dc.type do eduCAPES
    dc_texto = " ".join(dc_types).strip().lower()
    if dc_texto:
        for fmt, padrao in REGRAS_DC_TYPE_FORMATO:
            if re.search(padrao, dc_texto, flags=re.IGNORECASE):
                return fmt, "educapes_dc_type"

    return None, None


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
