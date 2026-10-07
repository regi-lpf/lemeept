from typing import Any, Dict, List, Tuple

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


def _valor_texto(valor: Any) -> str:
    if isinstance(valor, list):
        return " ".join(str(item) for item in valor if item)
    return limpar_texto(valor, "")


def _texto_classificacao(registro: Dict[str, Any]) -> Tuple[str, str]:
    principal = " ".join([
        _valor_texto(registro.get("titulo")),
        _valor_texto(registro.get("produto")),
        _valor_texto(registro.get("palavrasChave")),
        _valor_texto(registro.get("resumo")),
    ])
    auxiliar = " ".join([
        _valor_texto(registro.get("base")),
        _valor_texto(registro.get("area")),
        _valor_texto(registro.get("finalidade")),
        _valor_texto(registro.get("publicoAlvo")),
        _valor_texto(registro.get("tipoProduto")),
        _valor_texto(registro.get("nivel")),
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


def _tem_foco(registro: Dict[str, Any], termos: List[str]) -> bool:
    principal, auxiliar = _texto_classificacao(registro)
    texto = normalizar_texto(principal + " " + auxiliar)
    return any(normalizar_texto(termo) in texto for termo in termos)


def _resolver_empate(registro: Dict[str, Any], empatados: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], bool]:
    codigos = {item["codigo"] for item in empatados}

    if "MP2" in codigos and _tem_foco(registro, LINHAS_OFICIAIS_PROFEPT["MP2"]["fortes"]):
        return next(item for item in empatados if item["codigo"] == "MP2"), True

    desempates = [
        ({"MP1", "MP3"}, "MP1", ["recurso didatico", "material didatico", "metodologia", "metodologia de ensino", "produto educacional", "proposta de ensino", "sequencia didatica", "oficina", "guia", "cartilha", "manual"], "MP3", ["curriculo integrado", "interdisciplinaridade", "formacao integral", "formacao humana integral", "dualidade estrutural", "trabalho como principio educativo", "praticas pedagogicas integradas"]),
        ({"MP3", "MP5"}, "MP3", ["pratica pedagogica", "praticas pedagogicas", "aula", "intervencao", "pratica avaliativa", "experiencia de ensino"], "MP5", ["organizacao", "planejamento", "estrutura curricular", "matriz curricular", "ppc", "gestao do curriculo"]),
        ({"MP4", "MP6"}, "MP4", ["historia", "memoria", "narrativas", "trajetoria", "documentos", "identidade institucional", "acervo"], "MP6", ["espaco pedagogico", "espacos pedagogicos", "gestao de espacos", "ambiente escolar", "extensao", "territorio"]),
    ]
    for par, primeiro, termos_primeiro, segundo, termos_segundo in desempates:
        if par.issubset(codigos):
            if _tem_foco(registro, termos_primeiro):
                return next(item for item in empatados if item["codigo"] == primeiro), True
            if _tem_foco(registro, termos_segundo):
                return next(item for item in empatados if item["codigo"] == segundo), True

    return sorted(empatados, key=lambda item: item["codigo"])[0], False


def _confianca(melhor: Dict[str, Any], segundo: Dict[str, Any] | None, empate_sem_resolucao: bool) -> str:
    pontos = melhor["pontos"]
    margem = pontos - segundo["pontos"] if segundo else pontos
    quantidade_termos = len(melhor["termos"])
    if pontos < 4 or quantidade_termos == 0:
        return "Baixa"
    if empate_sem_resolucao:
        return "Baixa" if pontos < 8 else "Média"
    if pontos >= 14 and margem >= 5 and quantidade_termos >= 3:
        return "Alta"
    if pontos >= 8 and margem >= 3 and quantidade_termos >= 2:
        return "Alta"
    return "Média"


def classificar_registro(registro: Dict[str, Any]) -> Dict[str, str]:
    texto_principal, texto_auxiliar = _texto_classificacao(registro)
    texto_principal_n = normalizar_texto(texto_principal)
    texto_auxiliar_n = normalizar_texto(texto_auxiliar)

    resultados = []

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

        resultados.append({
            "codigo": codigo,
            "macro": config["macro"],
            "linha": config["linha"],
            "pontos": pontos,
            "termos": termos,
        })

    resultados.sort(key=lambda item: (-item["pontos"], item["codigo"]))
    melhor = resultados[0]
    segundo = resultados[1] if len(resultados) > 1 else None
    if len(texto_principal_n) < 30 or melhor["pontos"] <= 0 or not melhor["termos"]:
        return {
            "linhaPesquisa": "Não classificado",
            "macroprojeto": "Não classificado",
            "codigoMacroprojeto": "Não classificado",
            "confiancaLinhaMacro": "Baixa",
            "termosLinhaMacro": "---",
            "justificativaLinhaMacro": "Informações insuficientes para classificação automática.",
            "revisaoManual": "Sim",
        }

    empatados = [item for item in resultados if item["pontos"] == melhor["pontos"]]
    empate_sem_resolucao = False
    if len(empatados) > 1:
        melhor, empate_resolvido = _resolver_empate(registro, empatados)
        empate_sem_resolucao = not empate_resolvido
        segundo = next(item for item in resultados if item["codigo"] != melhor["codigo"])

    confianca = _confianca(melhor, segundo, empate_sem_resolucao)
    termos = melhor["termos"][:15]
    return {
        "linhaPesquisa": melhor["linha"],
        "macroprojeto": melhor["macro"],
        "codigoMacroprojeto": melhor["codigo"],
        "confiancaLinhaMacro": confianca,
        "termosLinhaMacro": "; ".join(termos) if termos else "---",
        "justificativaLinhaMacro": (
            f"Classificado no {melhor['codigo']} por abordar {', '.join(termos[:3])}."
            if confianca != "Baixa"
            else "Há poucos termos específicos ou ambiguidade relevante; recomenda-se revisão manual."
        ),
        "revisaoManual": "Sim" if confianca == "Baixa" else "Não",
    }
