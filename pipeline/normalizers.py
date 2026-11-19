import re
import unicodedata
from typing import Dict, List, Optional, Tuple


BASES_EPISTEMOLOGICAS_CANONICAS: Tuple[str, ...] = (
    "Materialismo Histórico-Dialético",
    "Pedagogia Histórico-Crítica",
    "Educação Libertadora / Freireana",
    "Teoria Histórico-Cultural / Sociointeracionismo",
    "Aprendizagem Significativa",
    "Teoria Crítica",
    "Pensamento Complexo / Interdisciplinaridade",
)

NIVEIS_APLICACAO_CANONICOS: Tuple[str, ...] = (
    "Ensino Médio Integrado",
    "Curso Técnico Subsequente",
    "EJA / PROEJA",
    "Formação de Professores",
    "Educação Superior",
    "Ensino Fundamental",
    "Gestão Institucional",
    "Educação Profissional e Tecnológica",
)


def normalizar_texto_busca(texto: str) -> str:
    """Normaliza texto para chave de busca (sem acentos, minúscula e alfanumérica)."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    sem_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-z0-9\s]", " ", sem_acentos)
    return re.sub(r"\s+", " ", limpo).strip()


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


_ALIASES_BASE_EPISTEMOLOGICA: Dict[str, str] = {
    "materialismo historico dialetico": "Materialismo Histórico-Dialético",
    "materialismo historico e dialetico": "Materialismo Histórico-Dialético",
    "mhd": "Materialismo Histórico-Dialético",
    "pedagogia historico critica": "Pedagogia Histórico-Crítica",
    "pedagogia historico critica de saviani": "Pedagogia Histórico-Crítica",
    "pedagogia historico critica de dermeval saviani": "Pedagogia Histórico-Crítica",
    "pedagogia historico critica de demerval saviani": "Pedagogia Histórico-Crítica",
    "educacao libertadora freireana": "Educação Libertadora / Freireana",
    "educacao libertadora": "Educação Libertadora / Freireana",
    "pedagogia freireana": "Educação Libertadora / Freireana",
    "educacao freireana": "Educação Libertadora / Freireana",
    "pedagogia libertadora": "Educação Libertadora / Freireana",
    "teoria historico cultural sociointeracionismo": "Teoria Histórico-Cultural / Sociointeracionismo",
    "teoria historico cultural": "Teoria Histórico-Cultural / Sociointeracionismo",
    "sociointeracionismo": "Teoria Histórico-Cultural / Sociointeracionismo",
    "historico cultural": "Teoria Histórico-Cultural / Sociointeracionismo",
    "aprendizagem significativa": "Aprendizagem Significativa",
    "teoria da aprendizagem significativa": "Aprendizagem Significativa",
    "teoria critica": "Teoria Crítica",
    "pensamento complexo interdisciplinaridade": "Pensamento Complexo / Interdisciplinaridade",
    "pensamento complexo": "Pensamento Complexo / Interdisciplinaridade",
    "interdisciplinaridade": "Pensamento Complexo / Interdisciplinaridade",
}


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
    if chave in _ALIASES_BASE_EPISTEMOLOGICA:
        return _ALIASES_BASE_EPISTEMOLOGICA[chave], True

    # Suporta composições declaradas entre matrizes canônicas (ex: "MHD e PHC")
    partes = [p.strip() for p in re.split(r"\s*(?:\be\b|,|;|\+|/)\s*", limpo) if p.strip()]
    if len(partes) > 1:
        resolvidas: List[str] = []
        for parte in partes:
            chave_parte = normalizar_texto_busca(parte)
            canon = _ALIASES_BASE_EPISTEMOLOGICA.get(chave_parte)
            if not canon:
                return limpo, False
            if canon not in resolvidas:
                resolvidas.append(canon)
        return " e ".join(resolvidas), True

    return limpo, False


_ALIASES_NIVEL_APLICACAO: Dict[str, str] = {
    "ensino medio integrado": "Ensino Médio Integrado",
    "curso tecnico integrado ao ensino medio": "Ensino Médio Integrado",
    "medio integrado": "Ensino Médio Integrado",
    "tecnico integrado": "Ensino Médio Integrado",
    "ensino medio tecnico integrado": "Ensino Médio Integrado",
    "curso tecnico subsequente": "Curso Técnico Subsequente",
    "tecnico subsequente": "Curso Técnico Subsequente",
    "ensino tecnico subsequente": "Curso Técnico Subsequente",
    "ensino medio profissional": "Curso Técnico Subsequente",
    "eja proeja": "EJA / PROEJA",
    "eja": "EJA / PROEJA",
    "proeja": "EJA / PROEJA",
    "educacao de jovens e adultos": "EJA / PROEJA",
    "formacao de professores": "Formação de Professores",
    "formacao docente": "Formação de Professores",
    "formacao continuada": "Formação de Professores",
    "capacitacao docente": "Formação de Professores",
    "educacao superior": "Educação Superior",
    "ensino superior": "Educação Superior",
    "universitario": "Educação Superior",
    "graduacao": "Educação Superior",
    "pos graduacao": "Educação Superior",
    "ensino fundamental": "Ensino Fundamental",
    "gestao institucional": "Gestão Institucional",
    "gestao escolar": "Gestão Institucional",
    "educacao profissional e tecnologica": "Educação Profissional e Tecnológica",
    "ept": "Educação Profissional e Tecnológica",
    "educacional academico": "Educação Profissional e Tecnológica",
    "educacional": "Educação Profissional e Tecnológica",
    "ensino medio superior": "Educação Profissional e Tecnológica",
    "ensino medio integral e superior": "Educação Profissional e Tecnológica",
}


def normalizar_nivel_aplicacao(nivel: Optional[str]) -> str:
    """Padroniza o nível/modalidade de aplicação para rótulo legível e consistente."""
    if not nivel or not isinstance(nivel, str):
        return "Educação Profissional e Tecnológica"

    limpo = re.sub(r"\s+", " ", nivel).strip(" .;-–—")
    if not limpo:
        return "Educação Profissional e Tecnológica"

    chave = normalizar_texto_busca(limpo)
    if chave in _ALIASES_NIVEL_APLICACAO:
        return _ALIASES_NIVEL_APLICACAO[chave]

    # Evita que slugs snake_case não mapeados da LLM vazem para o frontend
    if "_" in limpo and limpo == limpo.lower():
        return "Educação Profissional e Tecnológica"

    return limpo
