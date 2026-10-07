from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from lemeept.pipeline.builder import GeradorPainel
from lemeept.pipeline.classifier import LINHAS_OFICIAIS_PROFEPT, classificar_registro
from lemeept.pipeline.normalizer import limpar_texto, normalizar_registro, normalizar_texto, montar_search_text


RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_PLANILHA = RAIZ / "dados" / "dados_finais_painel_ept.xlsx"
ARQUIVO_SAIDA = Path(__file__).resolve().with_name("painel-ept.json")

MAPEAMENTO_COLUNAS = {
    "id": ("id", "identificador", "id permanente"),
    "ano": ("ano", "ano limpo", "ano de defesa", "ano defesa"),
    "autor": ("autor", "autora", "discente", "mestrando", "mestranda"),
    "orientador": ("orientador", "orientadora", "professor orientador", "professora orientadora"),
    "titulo": ("titulo", "titulo da dissertacao", "titulo provavel", "nome do trabalho"),
    "produto": ("produto", "produto educacional", "titulo do produto", "nome do produto"),
    "linkPdf": ("link pdf", "link do pdf", "pdf", "link da dissertacao"),
    "linkProduto": ("link do produto", "link do produto educacional", "link produto", "link pe"),
    "palavrasChave": ("palavras chave", "keywords"),
    "tipoProduto": ("tipo de produto v2", "tipo de produto educacional", "tipo de produto", "tipo produto", "tipo"),
    "resumo": ("resumo sintetizado", "resumo", "resumo do trabalho", "resumo limpo"),
    "nivel": ("nivel de aplicacao v2", "nivel de aplicacao", "nivel"),
    "base": ("base epistemologica v2", "base epistemologica"),
    "area": ("area tematica", "area"),
    "finalidade": ("finalidade do produto", "finalidade", "objetivo do produto", "uso do produto"),
    "publicoAlvo": ("publico alvo", "publico", "publico alvo classes"),
    "instituicaoCampus": ("instituicao campus", "ifc campus", "campus"),
    "linhaPesquisa": ("linha de pesquisa", "linha pesquisa", "linha"),
    "macroprojeto": ("macroprojeto", "macro projeto", "macro-projeto"),
    "codigoMacroprojeto": ("codigo do macroprojeto", "codigo macroprojeto", "codigo"),
    "confiancaLinhaMacro": ("confianca linha macro", "confianca linha/macro"),
    "termosLinhaMacro": ("termos detectados linha macro", "termos linha macro", "termos linha/macro"),
    "justificativaLinhaMacro": ("justificativa linha macro", "justificativa macro", "justificativa"),
    "revisaoManual": ("revisao manual", "revisao"),
}


def ler_registros(caminho: Path, estrito: bool = False) -> Tuple[List[Dict[str, Any]], int]:
    extensao = caminho.suffix.casefold()
    if extensao == ".json":
        documento = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(documento, dict):
            documento = documento.get("registros", documento.get("trabalhos"))
        if not isinstance(documento, list):
            raise ValueError("O JSON de origem deve ser uma lista de registros.")
        linhas = documento
    elif extensao in {".xlsx", ".xlsm"}:
        import pandas as pd

        linhas = pd.read_excel(caminho, dtype=str).fillna("").to_dict(orient="records")
    elif extensao == ".csv":
        import pandas as pd

        linhas = pd.read_csv(caminho, dtype=str, keep_default_na=False).to_dict(orient="records")
    else:
        raise ValueError(f"Formato de entrada não suportado: {extensao or '(sem extensão)'}")

    registros = []
    ignorados = 0
    for indice, linha in enumerate(linhas, start=1):
        if not isinstance(linha, dict):
            if estrito:
                raise ValueError(f"Registro {indice} não é um objeto JSON/linha tabular.")
            ignorados += 1
            continue
        registros.append(linha)
    return registros, ignorados


def extrair_campos(linha: Dict[str, Any]) -> Dict[str, Any]:
    indice = {normalizar_texto(str(chave)): chave for chave in linha}
    extraido: Dict[str, Any] = {}
    for campo, aliases in MAPEAMENTO_COLUNAS.items():
        for alias in (campo, *aliases):
            chave_original = indice.get(normalizar_texto(alias))
            if chave_original is None:
                continue
            valor = linha[chave_original]
            if limpar_texto(valor, ""):
                extraido[campo] = valor
                break
    return extraido


def processar_registros(linhas: Iterable[Dict[str, Any]], reclassificar: bool = False) -> List[Dict[str, Any]]:
    processados = []
    for linha in linhas:
        registro = normalizar_registro(extrair_campos(linha))
        codigo = registro.get("codigoMacroprojeto", "---")

        if reclassificar or codigo not in LINHAS_OFICIAIS_PROFEPT:
            registro.update(classificar_registro(registro))
        else:
            config = LINHAS_OFICIAIS_PROFEPT[codigo]
            registro["linhaPesquisa"] = registro.get("linhaPesquisa") or config["linha"]
            registro["macroprojeto"] = registro.get("macroprojeto") or config["macro"]
            registro["confiancaLinhaMacro"] = registro.get("confiancaLinhaMacro") or "Média"
            registro["termosLinhaMacro"] = registro.get("termosLinhaMacro") or "---"
            registro["justificativaLinhaMacro"] = registro.get("justificativaLinhaMacro") or "Classificação oficial preservada da fonte revisada."
            registro["revisaoManual"] = registro.get("revisaoManual") or "Não"

        registro["searchText"] = montar_search_text(registro)
        processados.append(registro)
    return processados


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera o JSON leve consumido pelo painel ProfEPT.")
    parser.add_argument("--entrada", type=Path, default=ARQUIVO_PLANILHA, help="Planilha XLSX, CSV ou JSON consolidado.")
    parser.add_argument("--saida", type=Path, default=ARQUIVO_SAIDA, help="Destino do JSON estático do painel.")
    parser.add_argument("--reclassificar", action="store_true", help="Ignora classificações existentes e reaplica as regras oficiais.")
    parser.add_argument("--estrito", action="store_true", help="Interrompe ao encontrar itens que não sejam registros.")
    return parser.parse_args()


def main() -> int:
    args = argumentos()
    entrada = args.entrada.resolve()
    saida = args.saida.resolve()
    try:
        linhas, ignorados = ler_registros(entrada, estrito=args.estrito)
        registros = processar_registros(linhas, reclassificar=args.reclassificar)
        arquivo = GeradorPainel(str(saida)).salvar(registros)
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"Erro ao gerar os dados do painel: {erro}", file=sys.stderr)
        return 1

    if ignorados:
        print(f"Aviso: {ignorados} item(ns) inválido(s) da fonte foram ignorados.", file=sys.stderr)
    print(f"JSON atualizado: {arquivo}")
    print(f"Registros publicados: {len(registros)}")
    print(f"Tamanho: {arquivo.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())