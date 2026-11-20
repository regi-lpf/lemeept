import re
import unicodedata
from typing import Dict, List, Optional, Tuple

from pipeline.catalogs import (
    ALIASES_BASE_EPISTEMOLOGICA,
    ALIASES_DOCENTES,
    ALIASES_FORMATO_PRODUTO,
    ALIASES_NIVEL_APLICACAO,
    BASES_EPISTEMOLOGICAS_CANONICAS,
    FORMATOS_PRODUTO_CANONICOS,
    NIVEIS_APLICACAO_CANONICOS,
    PREPOSICOES_NOME,
)

CONTROLE_INVISIVEL_RE = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\ufeff\x00-\x08\x0b\x0c\x0e-\x1f]"
)

MAIUSCULAS_PT = "A-ZÀÁÂÃÄÅÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ"
MINUSCULAS_PT = "a-zàáâãäåçèéêëìíîïñòóôõöùúûüý"

TITULACOES_PESSOA_RE = re.compile(
    r"^\s*(?:prof(?:essor(?:a|\(a\))?|\.?[ªao])?|dr(?:a|\.?[ªa])?|doutor(?:a|\(a\))?|m[ea]|m\.?sc|esp(?:ecialista)?|ph\.?d)"
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


def formatar_nome_proprio(nome: str) -> str:
    """Converte 'GEANDRO CHIARELLI' em 'Geandro Chiarelli' mantendo preposições."""
    limpo = limpar_texto(nome).strip(" ,.;-–—:")
    if not limpo:
        return ""
    palavras = limpo.lower().split(" ")
    return " ".join(
        p if i > 0 and p in PREPOSICOES_NOME else p.capitalize()
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
    return ALIASES_DOCENTES.get(chave, limpo)


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
    if chave in ALIASES_BASE_EPISTEMOLOGICA:
        return ALIASES_BASE_EPISTEMOLOGICA[chave], True

    # Suporta composições declaradas entre matrizes canônicas (ex: "MHD e PHC")
    partes = [p.strip() for p in re.split(r"\s*(?:\be\b|,|;|\+|/)\s*", limpo) if p.strip()]
    if len(partes) > 1:
        resolvidas: List[str] = []
        for parte in partes:
            canon = ALIASES_BASE_EPISTEMOLOGICA.get(normalizar_texto_busca(parte))
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
    if chave in ALIASES_NIVEL_APLICACAO:
        return ALIASES_NIVEL_APLICACAO[chave]

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
    if chave in ALIASES_FORMATO_PRODUTO:
        return ALIASES_FORMATO_PRODUTO[chave]

    if "_" in limpo and limpo == limpo.lower():
        return None

    return limpo
