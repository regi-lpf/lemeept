from pipeline.extractors.classifiers import (
    classificar_produto_com_fonte,
    classificar_produto_regex,
    detectar_macroprojeto_e_linha,
    extrair_sentenca_produto,
)
from pipeline.extractors.educapes import coletar_evidencias_educapes
from pipeline.extractors.metadata import (
    extrair_coorientador,
    extrair_palavras_chave_resumo,
)
from pipeline.extractors.pdf_sections import isolar_secoes_pdf, ler_paginas_pdf

__all__ = [
    "classificar_produto_com_fonte",
    "classificar_produto_regex",
    "coletar_evidencias_educapes",
    "detectar_macroprojeto_e_linha",
    "extrair_coorientador",
    "extrair_palavras_chave_resumo",
    "extrair_sentenca_produto",
    "isolar_secoes_pdf",
    "ler_paginas_pdf",
]
