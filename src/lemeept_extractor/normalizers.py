import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from lemeept_extractor import catalogs

CONTROLE_INVISIVEL_RE = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\ufeff\x00-\x08\x0b\x0c\x0e-\x1f]"
)

MAIUSCULAS_PT = "A-ZÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ"
MINUSCULAS_PT = "a-zàáâãäåçèéêëìíîïñòóôõöùúûüý"

TITULACOES_PESSOA_RE = re.compile(
    r"^\s*(?:prof(?:essor(?:a|\(a\))?|\.?[ªao])?|dr(?:a|\.?[ªa])?|doutor(?:a|\(a\))?|mestr[ea](?:\(a\))?|m[ea](?=\.)|m\.?sc|esp(?:ecialista)?|ph\.?d)"
    rf"(?:\.(?=\s|:|$|[{MAIUSCULAS_PT}])|(?=[\s:]|$))\s*",
    flags=re.IGNORECASE,
)


def remover_acentos(texto: str) -> str:
    """Remove marcas diacríticas Unicode preservando o texto base."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def limpar_texto(texto: str) -> str:
    """Remove caracteres invisíveis de controle e colapsa espaços em branco."""
    if not texto:
        return ""
    sem_controle = CONTROLE_INVISIVEL_RE.sub("", texto)
    return re.sub(r"\s+", " ", sem_controle).strip()


def normalizar_espacos(texto: str) -> str:
    """Remove caracteres invisíveis preservando quebras de parágrafo."""
    if not texto:
        return ""
    texto_limpo = CONTROLE_INVISIVEL_RE.sub("", texto)
    texto_limpo = re.sub(r"[ \t]+\n", "\n", texto_limpo)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", texto_limpo)).strip()


def normalizar_chave_busca(texto: str) -> str:
    """Gera chave limpa (sem acentos, minúscula) para cruzar registros e pessoas."""
    return limpar_texto(remover_acentos(texto)).lower()


def normalizar_texto_busca(texto: str) -> str:
    """Normaliza texto para chave de busca (sem acentos, minúscula e alfanumérica)."""
    if not texto:
        return ""
    sem_acentos = remover_acentos(texto.lower())
    limpo = re.sub(r"[^a-z0-9\s]", " ", sem_acentos)
    return re.sub(r"\s+", " ", limpo).strip()


_INICIO_SUBNOME_RE = re.compile(r"(^|[\-'])([^\W\d_])")


def formatar_nome_proprio(nome: str) -> str:
    """Converte 'GEANDRO CHIARELLI' em 'Geandro Chiarelli' mantendo preposições e hífens/apóstrofos."""
    limpo = limpar_texto(nome).strip(" ,.;-–—:")
    if not limpo:
        return ""
    palavras = limpo.lower().split(" ")
    return " ".join(
        p
        if i > 0 and p in catalogs.PREPOSICOES_NOME
        else _INICIO_SUBNOME_RE.sub(lambda m: m.group(1) + m.group(2).upper(), p)
        for i, p in enumerate(palavras)
    )


def limpar_nome_pessoa(bruto: str) -> str:
    """Remove filiações entre parênteses, titulações acadêmicas e pontuação residual."""
    nome = re.sub(r"\s*\(.*?\)", "", bruto or "")
    nome = limpar_texto(nome).strip(" ,.;-–—:")
    while True:
        novo = TITULACOES_PESSOA_RE.sub("", nome).lstrip(" ,.;-–—:")
        if novo == nome:
            break
        nome = novo
    nome = nome.strip(" ,.;-–—:")
    if not nome:
        return ""
    if nome == nome.upper():
        return formatar_nome_proprio(nome)
    return nome


def normalizar_nome_orientador(nome: Optional[str]) -> str:
    """Limpa titulações/pontuação de orientadores e resolve aliases canônicos conhecidos."""
    limpo = limpar_nome_pessoa(nome or "")
    if not limpo:
        return ""
    chave = normalizar_texto_busca(limpo)
    return catalogs.ALIASES_DOCENTES.get(chave, limpo)


def limpar_prefixo_orientador(texto: str) -> str:
    """Remove 'Orientador(a):', titulações acadêmicas e normaliza para nome canônico."""
    txt = re.sub(r"^orientador(?:a|\(a\))?\s*:\s*", "", texto or "", flags=re.IGNORECASE)
    return normalizar_nome_orientador(txt)


def limpar_palavras_chave(tags: List[str]) -> List[str]:
    """Remove ruídos de pontuação, deduplica ignorando acentos/caixa e capitaliza."""
    vistas: Dict[str, str] = {}
    for tag in tags:
        if not isinstance(tag, str):
            continue
        limpa = re.sub(r"^[\s\-–—.;:]+|[\s\-–—.;:]+$", "", tag).strip()
        if len(limpa) < 2:
            continue
        chave = normalizar_texto_busca(limpa)
        if chave and chave not in vistas:
            vistas[chave] = limpa[0].upper() + limpa[1:]
    return list(vistas.values())


def limpar_resumo_publico(resumo: str) -> str:
    """Remove marcação interna '[PÁG. X]' e cabeçalho 'RESUMO' do texto público."""
    if not resumo:
        return ""
    texto = re.sub(r"(?:^|\n)\s*\[PÁG\.\s*\d+\]\s*", "\n", resumo, flags=re.IGNORECASE)
    texto = re.sub(r"^\s*RESUMO\b[:\s\-–—]*\n*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"[ \t]+\n", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _proteger_matrizes_compostas(sem_acentos: str) -> Tuple[str, Dict[str, str]]:
    """Substitui nomes/aliases com '/' ou ' e ' internos antes do split de composições."""
    candidatos: List[Tuple[str, str]] = []
    for base in catalogs.BASES_EPISTEMOLOGICAS_CANONICAS:
        if "/" in base or re.search(r"\be\b", remover_acentos(base), flags=re.IGNORECASE):
            candidatos.append((remover_acentos(base).lower(), base))
    for alias, canon in catalogs.ALIASES_BASE_EPISTEMOLOGICA.items():
        if re.search(r"\be\b", alias):
            candidatos.append((alias, canon))
    candidatos.sort(key=lambda item: len(item[0]), reverse=True)

    protegidos: Dict[str, str] = {}
    atual = sem_acentos
    for idx, (frase, canon) in enumerate(candidatos):
        tokens = [re.escape(tk) for tk in re.split(r"[\s/\-]+", frase) if tk]
        if len(tokens) < 2:
            continue
        padrao = r"(?<![a-z0-9])" + r"[\s/\-]+".join(tokens) + r"(?![a-z0-9])"
        token_marcador = f"__LEME_BASE_{idx}__"
        novo, qtd = re.subn(padrao, token_marcador, atual, flags=re.IGNORECASE)
        if qtd > 0:
            protegidos[token_marcador] = canon
            atual = novo
    return atual, protegidos


def normalizar_base_epistemologica(valor: Optional[str]) -> Tuple[Optional[str], bool]:
    """
    Mapeia uma matriz epistemológica (ou composição válida de matrizes canônicas)
    para o vocabulário canônico. Retorna (termo_normalizado, eh_canonico).
    """
    if not valor or not isinstance(valor, str):
        return None, False

    limpo = re.sub(r"\s+", " ", valor).strip(" .;-–—")
    if not limpo:
        return None, False

    chave = normalizar_texto_busca(limpo)
    if chave in catalogs.ALIASES_BASE_EPISTEMOLOGICA:
        return catalogs.ALIASES_BASE_EPISTEMOLOGICA[chave], True

    # Suporta composições declaradas entre matrizes canônicas (ex: "MHD e PHC")
    sem_acentos = remover_acentos(limpo).lower()
    protegido, mapa_protegidos = _proteger_matrizes_compostas(sem_acentos)
    partes = [
        p.strip()
        for p in re.split(r"\s*(?:\be\b|,|;|\+|/)\s*", protegido, flags=re.IGNORECASE)
        if p.strip()
    ]
    if len(partes) > 1:
        resolvidas: List[str] = []
        for parte in partes:
            canon = mapa_protegidos.get(parte) or catalogs.ALIASES_BASE_EPISTEMOLOGICA.get(
                normalizar_texto_busca(parte)
            )
            if not canon:
                return limpo, False
            if canon not in resolvidas:
                resolvidas.append(canon)
        return " e ".join(resolvidas), True

    return limpo, False


def normalizar_nivel_aplicacao(nivel: Optional[str]) -> str:
    """Padroniza o nível/modalidade de aplicação para rótulo legível e consistente."""
    if not nivel or not isinstance(nivel, str):
        return "Educação Profissional e Tecnológica"

    limpo = re.sub(r"\s+", " ", nivel).strip(" .;-–—")
    if not limpo:
        return "Educação Profissional e Tecnológica"

    chave = normalizar_texto_busca(limpo)
    if chave in catalogs.ALIASES_NIVEL_APLICACAO:
        return catalogs.ALIASES_NIVEL_APLICACAO[chave]

    # Evita que slugs snake_case não mapeados da LLM vazem para o frontend
    if "_" in limpo and limpo == limpo.lower():
        return "Educação Profissional e Tecnológica"

    return limpo


def normalizar_formato_produto(formato: Optional[str]) -> Optional[str]:
    """Padroniza o formato específico do produto para rótulo legível e consistente."""
    if not formato or not isinstance(formato, str):
        return None

    limpo = re.sub(r"\s+", " ", formato).strip(" .;-–—:")
    if not limpo:
        return None

    chave = normalizar_texto_busca(limpo)
    if chave in catalogs.ALIASES_FORMATO_PRODUTO:
        return catalogs.ALIASES_FORMATO_PRODUTO[chave]

    if "_" in limpo and limpo == limpo.lower():
        return None

    return limpo
