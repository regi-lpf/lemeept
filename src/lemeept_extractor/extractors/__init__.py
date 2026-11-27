from lemeept_extractor.extractors.classifiers import (
    classificar_formato_produto_com_fonte,
    classificar_produto_com_fonte,
    classificar_produto_regex,
    detectar_macroprojeto_e_linha,
    extrair_contexto_produto,
    extrair_sentenca_produto,
)
from lemeept_extractor.extractors.educapes import coletar_evidencias_educapes
from lemeept_extractor.extractors.metadata import (
    extrair_coorientador,
    extrair_metadados_preliminares_pdf,
    extrair_palavras_chave_resumo,
)
from lemeept_extractor.extractors.pdf_sections import (
    extrair_capa_e_ficha,
    isolar_secoes_pdf,
    ler_paginas_pdf,
)

__all__ = [
    "classificar_formato_produto_com_fonte",
    "classificar_produto_com_fonte",
    "classificar_produto_regex",
    "coletar_evidencias_educapes",
    "detectar_macroprojeto_e_linha",
    "extrair_capa_e_ficha",
    "extrair_contexto_produto",
    "extrair_coorientador",
    "extrair_metadados_preliminares_pdf",
    "extrair_palavras_chave_resumo",
    "extrair_sentenca_produto",
    "isolar_secoes_pdf",
    "ler_paginas_pdf",
]
