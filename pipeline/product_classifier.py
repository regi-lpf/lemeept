import re
from typing import Tuple
from pipeline.data_model import TipoProduto 

PADROES_CAPES = {
    TipoProduto.MATERIAL_DIDATICO: [
        r"sequ[êe]ncia did[áa]tica", r"guia", r"manual", r"e-?book", 
        r"cartilha", r"jogo", r"v[íi]deo", r"videoaula", r"texto de apoio",
        r"hist[óo]ria em quadrinhos", r"hq", r"objeto de aprendizagem",
        r"proposta de interven[çc][ãa]o"
    ],
    TipoProduto.CURSO_OFICINA: [
        r"oficina", r"curso de capacita[çc][ãa]o", r"workshop", r"curso de forma[çc][ãa]o"
    ],
    TipoProduto.TECNOLOGIA_SOCIAL: [
        r"tecnologia social", r"inova[çc][ãa]o social", r"dispositivo social"
    ],
    TipoProduto.SOFTWARE_APLICATIVO: [
        r"aplicativo", r"software", r"plataforma web", r"app", r"programa de computador"
    ],
    TipoProduto.EVENTOS_ORGANIZADOS: [
        r"exposi[çc][ãa]o", r"feira de ci[êe]ncias", r"olimp[íi]ada s?".replace(" ", ""), r"mostra cient[íi]fica"
    ],
    TipoProduto.ACERVO: [
        r"acervo", r"curadoria", r"cole[çc][ãa]o"
    ],
    TipoProduto.PRODUTO_COMUNICACAO: [
       r"programa de televis[ãa]o", r"m[íi]dia", r"podcast", r"programa de r[áa]dio", r"programa de tv", r"campanha"
    ],
    TipoProduto.MANUAL_PROTOCOLO: [
        r"manual", r"procedimentos", r"instru[çc][õo]es", r"protocolo", r"manual de opera[çc]([ãa]o|[õo]es)", r"manual de normas"
    ],
    TipoProduto.CARTA_MAPA: [
        r"carta", r"mapa", r"cartograma", r"carta geogr[áa]fica"
    ]
}


def classificar_tipo_produto(texto: str) -> Tuple[TipoProduto, float]:
    """Retorna a categoria canônica e um score simples de confiança."""
    if not texto:
        return TipoProduto.PENDENTE_REVISAO, 0.0

    texto_lower = texto.lower()
    for categoria, patterns in PADROES_CAPES.items():
        for pat in patterns:
            if re.search(r"\b" + pat + r"\b", texto_lower):
                return categoria, 1.0

    return TipoProduto.PENDENTE_REVISAO, 0.0
