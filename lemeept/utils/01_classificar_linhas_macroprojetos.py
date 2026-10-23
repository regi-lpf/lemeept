import pandas as pd
import re
import unicodedata
from pathlib import Path

# ============================================================
# PROJETO LEME/EPT - SCRIPT 1
# Classificação oficial ProfEPT: Linhas de Pesquisa e Macroprojetos
#
# Este script NÃO gera HTML.
# Ele lê a planilha já classificada, adiciona/atualiza as colunas oficiais
# de Linha de Pesquisa e Macroprojeto e salva uma nova planilha para revisão.
# ============================================================

ARQUIVO_ENTRADA = "dados_finais_painel_ept_classificados_v4.xlsx"
ARQUIVO_SAIDA = "dados_finais_painel_ept_linhas_macroprojetos.xlsx"

COLUNAS_USADAS_CLASSIFICACAO = [
    "Título da Dissertação",
    "Produto Educacional",
    "Palavras-chave",
    "Resumo",
    "Base Epistemológica",
    "Base Epistemológica V2",
    "Área Temática",
    "Finalidade do Produto",
    "Público-alvo",
    "Tipo de Produto V2",
    "Tipo de Produto",
    "Nível de Aplicação",
    "Nível de Aplicação V2",
]

COLUNAS_NOVAS = [
    "Linha de Pesquisa",
    "Macroprojeto",
    "Código do Macroprojeto",
    "Confiança Linha/Macro",
    "Termos Detectados Linha/Macro",
    "Justificativa Linha/Macro",
    "Revisão Manual",
]


def limpar_valor(valor, padrao="---"):
    if pd.isna(valor):
        return padrao
    valor = str(valor).strip()
    if not valor or valor.lower() in ["nan", "none", "null"]:
        return padrao
    return valor


def normalizar_texto(texto):
    texto = limpar_valor(texto, "")
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


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

MACROPROJETOS_OFICIAIS = [
    "Macroprojeto 1 – Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT",
    "Macroprojeto 2 – Inclusão e diversidade em espaços formais e não formais de ensino na EPT",
    "Macroprojeto 3 – Práticas Educativas no Currículo Integrado",
    "Macroprojeto 4 – História e memórias no contexto da EPT",
    "Macroprojeto 5 – Organização do currículo integrado na EPT",
    "Macroprojeto 6 – Organização de espaços pedagógicos na EPT",
]


def detectar_termos(texto, termos):
    """Retorna termos encontrados no texto normalizado, sem duplicar."""
    texto_n = normalizar_texto(texto)
    encontrados = []
    vistos = set()

    for termo in termos:
        termo_n = normalizar_texto(termo)
        if termo_n and termo_n in texto_n and termo_n not in vistos:
            vistos.add(termo_n)
            encontrados.append(termo)

    return encontrados


def _texto_classificacao_linha_macro(row):
    """Monta os blocos de texto usados pela classificação oficial ProfEPT."""
    texto_principal = " ".join([
        limpar_valor(row.get("Título da Dissertação", ""), ""),
        limpar_valor(row.get("Produto Educacional", ""), ""),
        limpar_valor(row.get("Palavras-chave", ""), ""),
        limpar_valor(row.get("Resumo", ""), ""),
    ])

    texto_auxiliar = " ".join([
        limpar_valor(row.get("Base Epistemológica", row.get("Base Epistemológica V2", "")), ""),
        limpar_valor(row.get("Área Temática", ""), ""),
        limpar_valor(row.get("Finalidade do Produto", ""), ""),
        limpar_valor(row.get("Público-alvo", ""), ""),
        limpar_valor(row.get("Tipo de Produto V2", row.get("Tipo de Produto", "")), ""),
        limpar_valor(row.get("Nível de Aplicação", row.get("Nível de Aplicação V2", "")), ""),
    ])

    return texto_principal, texto_auxiliar


def _pontuar_termo(texto_principal_n, texto_auxiliar_n, termo, termo_forte=False):
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


def calcular_pontuacao_macroprojetos(row):
    """Calcula a pontuação dos seis macroprojetos oficiais."""
    texto_principal, texto_auxiliar = _texto_classificacao_linha_macro(row)
    texto_principal_n = normalizar_texto(texto_principal)
    texto_auxiliar_n = normalizar_texto(texto_auxiliar)

    resultados = []

    for codigo, config in LINHAS_OFICIAIS_PROFEPT.items():
        pontos = 0
        termos_encontrados = []
        vistos = set()
        fortes = {normalizar_texto(t) for t in config.get("fortes", [])}

        for termo in config.get("termos", []):
            termo_n = normalizar_texto(termo)
            pts, achou = _pontuar_termo(
                texto_principal_n,
                texto_auxiliar_n,
                termo,
                termo_forte=termo_n in fortes,
            )

            if achou:
                pontos += pts
                if termo_n not in vistos:
                    vistos.add(termo_n)
                    termos_encontrados.append(termo)

        resultados.append({
            "codigo": codigo,
            "linha": config["linha"],
            "macro": config["macro"],
            "pontos": pontos,
            "termos": termos_encontrados,
        })

    resultados.sort(key=lambda x: (-x["pontos"], x["codigo"]))
    return resultados, texto_principal, texto_auxiliar


def _tem_foco(row, termos):
    texto_principal, texto_auxiliar = _texto_classificacao_linha_macro(row)
    texto = normalizar_texto(texto_principal + " " + texto_auxiliar)
    return any(normalizar_texto(t) in texto for t in termos)


def _resolver_empate_macroprojeto(row, empatados):
    """Aplica os critérios oficiais de desempate entre macroprojetos próximos."""
    codigos = {item["codigo"] for item in empatados}

    termos_mp2 = LINHAS_OFICIAIS_PROFEPT["MP2"]["fortes"]
    if "MP2" in codigos and _tem_foco(row, termos_mp2):
        return next(item for item in empatados if item["codigo"] == "MP2"), "desempate_mp2"

    if {"MP1", "MP3"}.issubset(codigos):
        foco_mp1 = [
            "recurso didatico", "material didatico", "metodologia", "metodologia de ensino",
            "produto educacional", "proposta de ensino", "sequencia didatica", "oficina", "guia", "cartilha", "manual"
        ]
        foco_mp3 = [
            "curriculo integrado", "interdisciplinaridade", "formacao integral", "formacao humana integral",
            "dualidade estrutural", "trabalho como principio educativo", "praticas pedagogicas integradas"
        ]
        if _tem_foco(row, foco_mp1):
            return next(item for item in empatados if item["codigo"] == "MP1"), "desempate_mp1_mp3"
        if _tem_foco(row, foco_mp3):
            return next(item for item in empatados if item["codigo"] == "MP3"), "desempate_mp1_mp3"

    if {"MP3", "MP5"}.issubset(codigos):
        foco_mp3 = ["pratica pedagogica", "praticas pedagogicas", "aula", "intervencao", "pratica avaliativa", "experiencia de ensino"]
        foco_mp5 = ["organizacao", "planejamento", "estrutura curricular", "matriz curricular", "ppc", "gestao do curriculo"]
        if _tem_foco(row, foco_mp3):
            return next(item for item in empatados if item["codigo"] == "MP3"), "desempate_mp3_mp5"
        if _tem_foco(row, foco_mp5):
            return next(item for item in empatados if item["codigo"] == "MP5"), "desempate_mp3_mp5"

    if {"MP4", "MP6"}.issubset(codigos):
        foco_mp4 = ["historia", "memoria", "narrativas", "trajetoria", "documentos", "identidade institucional", "acervo"]
        foco_mp6 = ["espaco pedagogico", "espacos pedagogicos", "gestao de espacos", "ambiente escolar", "extensao", "territorio"]
        if _tem_foco(row, foco_mp4):
            return next(item for item in empatados if item["codigo"] == "MP4"), "desempate_mp4_mp6"
        if _tem_foco(row, foco_mp6):
            return next(item for item in empatados if item["codigo"] == "MP6"), "desempate_mp4_mp6"

    return sorted(empatados, key=lambda x: x["codigo"])[0], "empate_sem_desempate_claro"


def definir_confianca(melhor, segundo, empate_resolvido=False, empate_sem_desempate=False):
    pontos = melhor.get("pontos", 0)
    margem = pontos - segundo.get("pontos", 0) if segundo else pontos
    qtd_termos = len(melhor.get("termos", []))

    if pontos < 4 or qtd_termos == 0:
        return "Baixa"

    if empate_sem_desempate:
        return "Baixa" if pontos < 8 else "Média"

    if pontos >= 14 and margem >= 5 and qtd_termos >= 3 and not empate_resolvido:
        return "Alta"

    if pontos >= 8 and margem >= 3 and qtd_termos >= 2:
        return "Alta"

    return "Média"


def gerar_justificativa(melhor, confianca):
    termos = melhor.get("termos", [])[:3]
    termos_txt = ", ".join(termos) if termos else "termos gerais da EPT"

    if melhor["codigo"] == "Não classificado":
        return "Informações insuficientes para classificação automática."

    if confianca == "Baixa":
        return "Há poucos termos específicos ou ambiguidade relevante; recomenda-se revisão manual."

    return f"Classificado no {melhor['codigo']} por abordar {termos_txt}."


def classificar_linha_macroprojeto(row):
    """
    Classifica cada trabalho nas linhas e macroprojetos oficiais do ProfEPT.

    Retorna:
    linha_pesquisa, macroprojeto, codigo_macroprojeto, confianca,
    termos_detectados, justificativa, revisao_manual
    """
    resultados, texto_principal, texto_auxiliar = calcular_pontuacao_macroprojetos(row)

    texto_minimo = normalizar_texto(texto_principal)
    if len(texto_minimo) < 30:
        return (
            "Não classificado",
            "Não classificado",
            "Não classificado",
            "Baixa",
            "---",
            "Informações insuficientes para classificação automática.",
            "Sim",
        )

    melhor = resultados[0]
    segundo = resultados[1] if len(resultados) > 1 else None

    if melhor["pontos"] <= 0 or not melhor["termos"]:
        return (
            "Não classificado",
            "Não classificado",
            "Não classificado",
            "Baixa",
            "---",
            "Informações insuficientes para classificação automática.",
            "Sim",
        )

    maior_pontuacao = melhor["pontos"]
    empatados = [r for r in resultados if r["pontos"] == maior_pontuacao]
    empate_resolvido = False
    empate_sem_desempate = False

    if len(empatados) > 1:
        melhor, motivo_empate = _resolver_empate_macroprojeto(row, empatados)
        empate_resolvido = motivo_empate != "empate_sem_desempate_claro"
        empate_sem_desempate = motivo_empate == "empate_sem_desempate_claro"
        restantes = [r for r in resultados if r["codigo"] != melhor["codigo"]]
        segundo = restantes[0] if restantes else None

    confianca = definir_confianca(melhor, segundo, empate_resolvido, empate_sem_desempate)
    revisao_manual = "Sim" if confianca == "Baixa" else "Não"
    termos_detectados = "; ".join(melhor.get("termos", [])[:15]) if melhor.get("termos") else "---"
    justificativa = gerar_justificativa(melhor, confianca)

    return (
        melhor["linha"],
        melhor["macro"],
        melhor["codigo"],
        confianca,
        termos_detectados,
        justificativa,
        revisao_manual,
    )



def garantir_colunas_para_classificacao(df):
    """Cria colunas ausentes com '---' e avisa no terminal."""
    faltantes = [col for col in COLUNAS_USADAS_CLASSIFICACAO if col not in df.columns]
    if faltantes:
        print("ATENÇÃO: estas colunas esperadas não foram encontradas e serão preenchidas com '---':")
        for col in faltantes:
            print(f"- {col}")
            df[col] = "---"
    return df


def aplicar_classificacao(df):
    df_saida = df.copy().fillna("---")
    df_saida = garantir_colunas_para_classificacao(df_saida)

    resultados = df_saida.apply(lambda row: classificar_linha_macroprojeto(row.to_dict()), axis=1)

    df_saida["Linha de Pesquisa"] = [r[0] for r in resultados]
    df_saida["Macroprojeto"] = [r[1] for r in resultados]
    df_saida["Código do Macroprojeto"] = [r[2] for r in resultados]
    df_saida["Confiança Linha/Macro"] = [r[3] for r in resultados]
    df_saida["Termos Detectados Linha/Macro"] = [r[4] for r in resultados]
    df_saida["Justificativa Linha/Macro"] = [r[5] for r in resultados]
    df_saida["Revisão Manual"] = [r[6] for r in resultados]

    return df_saida


def main():
    entrada = Path(ARQUIVO_ENTRADA)
    if not entrada.exists():
        raise FileNotFoundError(
            f"Planilha de entrada não encontrada: {ARQUIVO_ENTRADA}\n"
            "Coloque este script na mesma pasta da planilha ou ajuste ARQUIVO_ENTRADA."
        )

    print(f"Lendo planilha: {ARQUIVO_ENTRADA}")
    df = pd.read_excel(entrada).fillna("---")

    print("Aplicando classificação oficial de Linhas de Pesquisa e Macroprojetos do ProfEPT...")
    df_saida = aplicar_classificacao(df)

    df_saida.to_excel(ARQUIVO_SAIDA, index=False)

    total = len(df_saida)
    revisar = int((df_saida["Revisão Manual"] == "Sim").sum())

    print("Classificação concluída!")
    print(f"Planilha gerada para revisão: {ARQUIVO_SAIDA}")
    print(f"Total de registros: {total}")
    print(f"Registros para revisão manual: {revisar}")


if __name__ == "__main__":
    main()
