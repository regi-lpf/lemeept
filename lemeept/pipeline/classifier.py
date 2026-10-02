import re
import unicodedata
from typing import Dict, List, Tuple

from .normalizer import limpar_texto, normalizar_texto

LINHAS_OFICIAIS_PROFEPT = {
    "MP1": {
        "linha": "Práticas Educativas em Educação Profissional e Tecnológica (EPT)",
        "macro": "Macroprojeto 1 – Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT",
        "termos": [
            "metodologia de ensino", "metodologias de ensino", "proposta metodologica", "recurso didatico",
            "recursos didaticos", "material didatico", "sequencia didatica", "produto educacional",
            "ensino-aprendizagem", "ensino aprendizagem", "pratica pedagogica", "praticas pedagogicas",
            "sala de aula", "laboratorio", "campo", "museu", "internet", "ambiente virtual",
            "tecnologia educacional", "aplicativo", "app", "site", "jogo", "jogo digital",
            "video", "podcast", "oficina", "curso", "guia", "cartilha", "manual",
            "recurso educacional", "proposta de ensino", "intervencao pedagogica", "atividade pedagogica",
            "objeto de aprendizagem", "gamificacao", "moodle", "ava", "plataforma", "audiovisual"
        ],
        "fortes": [
            "sequencia didatica", "produto educacional", "material didatico", "recurso didatico",
            "metodologia de ensino", "proposta de ensino", "intervencao pedagogica", "oficina", "cartilha", "guia"
        ],
    },
    "MP2": {
        "linha": "Práticas Educativas em Educação Profissional e Tecnológica (EPT)",
        "macro": "Macroprojeto 2 – Inclusão e diversidade em espaços formais e não formais de ensino na EPT",
        "termos": [
            "inclusao", "diversidade", "acessibilidade", "deficiencia", "pcd", "pessoas com deficiencia",
            "educacao inclusiva", "educacao especial", "eja", "proeja", "jovens e adultos",
            "educacao indigena", "educacao quilombola", "educacao do campo", "relacoes etnico-raciais",
            "relacoes etnicoraciais", "raca", "etnia", "genero", "mulheres", "lgbtqia",
            "direitos humanos", "vulnerabilidade", "permanencia", "exito", "evasao",
            "estudantes trabalhadores", "juventudes", "aee", "libras", "surdos", "cotas", "equidade"
        ],
        "fortes": [
            "inclusao", "acessibilidade", "deficiencia", "pcd", "educacao inclusiva", "eja", "proeja",
            "relacoes etnico-raciais", "genero", "direitos humanos", "permanencia", "exito", "evasao"
        ],
    },
    "MP3": {
        "linha": "Práticas Educativas em Educação Profissional e Tecnológica (EPT)",
        "macro": "Macroprojeto 3 – Práticas Educativas no Currículo Integrado",
        "termos": [
            "curriculo integrado", "ensino medio integrado", "emi", "integracao curricular",
            "interdisciplinaridade", "pratica integrada", "praticas pedagogicas integradas",
            "avaliacao integrada", "pratica avaliativa", "formacao humana integral", "formacao omnilateral",
            "omnilateralidade", "politecnia", "dualidade estrutural", "trabalho como principio educativo",
            "ciencia tecnologia e cultura", "trabalho ciencia tecnologia e cultura", "mundo do trabalho",
            "articulacao entre formacao geral e formacao tecnica", "formacao geral e formacao tecnica",
            "praticas integradoras", "projeto integrador", "experiencia de ensino", "aula", "intervencao"
        ],
        "fortes": [
            "curriculo integrado", "ensino medio integrado", "emi", "integracao curricular",
            "interdisciplinaridade", "praticas pedagogicas integradas", "formacao humana integral",
            "trabalho como principio educativo", "dualidade estrutural"
        ],
    },
    "MP4": {
        "linha": "Organização e Memórias de Espaços Pedagógicos na Educação Profissional e Tecnológica (EPT)",
        "macro": "Macroprojeto 4 – História e memórias no contexto da EPT",
        "termos": [
            "historia", "memoria", "memorias", "historia da ept", "memoria institucional",
            "historia oral", "narrativas", "trajetoria", "instituicao", "instituicoes", "eventos",
            "documentos historicos", "arquivo", "acervo", "patrimonio", "cultura escolar",
            "identidade institucional", "espacos de formacao", "historia de curso", "historia de campus",
            "historia de escola", "educacao profissional no tempo", "fotografia", "fontes historicas",
            "preservacao da memoria", "instituicoes escolares", "historia da educacao profissional"
        ],
        "fortes": [
            "historia da ept", "memoria", "memoria institucional", "historia oral", "narrativas",
            "documentos historicos", "arquivo", "acervo", "cultura escolar", "identidade institucional"
        ],
    },
    "MP5": {
        "linha": "Organização e Memórias de Espaços Pedagógicos na Educação Profissional e Tecnológica (EPT)",
        "macro": "Macroprojeto 5 – Organização do currículo integrado na EPT",
        "termos": [
            "organizacao curricular", "planejamento curricular", "matriz curricular", "projeto pedagogico",
            "ppc", "curriculo integrado", "planejamento do curriculo integrado",
            "organizacao do curriculo integrado", "gestao do curriculo", "estrutura curricular",
            "componentes curriculares", "itinerario formativo", "interdisciplinaridade no planejamento",
            "articulacao curricular", "curriculo da ept", "analise curricular", "concepcao curricular",
            "reorganizacao curricular", "desenho curricular", "plano de curso"
        ],
        "fortes": [
            "organizacao curricular", "planejamento curricular", "matriz curricular", "projeto pedagogico",
            "ppc", "organizacao do curriculo integrado", "gestao do curriculo", "estrutura curricular"
        ],
    },
    "MP6": {
        "linha": "Organização e Memórias de Espaços Pedagógicos na Educação Profissional e Tecnológica (EPT)",
        "macro": "Macroprojeto 6 – Organização de espaços pedagógicos na EPT",
        "termos": [
            "espaco pedagogico", "espacos pedagogicos", "organizacao de espacos", "planejamento de espacos",
            "ambiente escolar", "laboratorio", "biblioteca", "museu", "arquivo", "sala de aula",
            "setor produtivo", "espacos nao formais", "espacos formais", "extensao", "gestao da ept",
            "pesquisa", "ensino", "movimentos sociais", "comunidade", "territorio", "mundo do trabalho",
            "ambientes de aprendizagem", "organizacao institucional", "gestao de espacos", "arranjos produtivos",
            "espaco de aprendizagem", "ambientes formais", "ambientes nao formais"
        ],
        "fortes": [
            "espaco pedagogico", "espacos pedagogicos", "organizacao de espacos", "planejamento de espacos",
            "ambiente escolar", "espacos nao formais", "extensao", "gestao da ept", "territorio", "gestao de espacos"
        ],
    },
}


def _texto_classificacao(registro: Dict[str, str]) -> Tuple[str, str]:
    principal = " ".join([
        limpar_texto(registro.get("titulo"), ""),
        limpar_texto(registro.get("produto"), ""),
        limpar_texto(registro.get("palavrasChave"), ""),
        limpar_texto(registro.get("resumo"), ""),
    ])
    auxiliar = " ".join([
        limpar_texto(registro.get("base"), ""),
        limpar_texto(registro.get("area"), ""),
        limpar_texto(registro.get("finalidade"), ""),
        limpar_texto(registro.get("publicoAlvo"), ""),
        limpar_texto(registro.get("tipoProduto"), ""),
        limpar_texto(registro.get("nivel"), ""),
    ])
    return principal, auxiliar


def _pontuar_termo(texto_principal_n: str, texto_auxiliar_n: str, termo: str, termo_forte: bool = False) -> Tuple[int, bool]:
    termo_n = normalizar_texto(termo)
    if not termo_n:
        return 0, False

    pontos = 0
    achou = False

    if termo_n in texto_principal_n:
        pontos += 4 if termo_forte else 3
        achou = True

    if termo_n in texto_auxiliar_n:
        pontos += 2
        achou = True

    return pontos, achou


def classificar_registro(registro: Dict[str, str]) -> Dict[str, str]:
    texto_principal, texto_auxiliar = _texto_classificacao(registro)
    texto_principal_n = normalizar_texto(texto_principal)
    texto_auxiliar_n = normalizar_texto(texto_auxiliar)

    melhor_codigo = "---"
    melhor_macro = "---"
    melhor_linha = "---"
    melhor_pontos = -1
    termos_encontrados = []

    for codigo, config in LINHAS_OFICIAIS_PROFEPT.items():
        pontos = 0
        termos = []
        vistos = set()
        fortes = {normalizar_texto(t) for t in config.get("fortes", [])}

        for termo in config.get("termos", []):
            termo_n = normalizar_texto(termo)
            pts, achou = _pontuar_termo(texto_principal_n, texto_auxiliar_n, termo, termo_forte=termo_n in fortes)
            if achou:
                pontos += pts
                if termo_n not in vistos:
                    vistos.add(termo_n)
                    termos.append(termo)

        if pontos > melhor_pontos:
            melhor_pontos = pontos
            melhor_codigo = codigo
            melhor_macro = config["macro"]
            melhor_linha = config["linha"]
            termos_encontrados = termos

    return {
        "linhaPesquisa": melhor_linha,
        "macroprojeto": melhor_macro,
        "codigoMacroprojeto": melhor_codigo,
        "confiancaLinhaMacro": str(melhor_pontos),
        "termosLinhaMacro": "; ".join(termos_encontrados),
    }
