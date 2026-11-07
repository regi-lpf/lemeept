from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import requests

from .util import criar_sessao_http, salvar_json_atomico


ROOT = Path(__file__).resolve().parents[1]
ARQUIVO_INDICE = ROOT / "painel-ept.json"
PASTA_PDFS = ROOT / "pdf" / "dissertações"
PADRAO_ID = re.compile(r"EPT-\d{4}\Z")
HOST_OFICIAL = "profept.ifc.edu.br"


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa as dissertações do índice LEME.")
    parser.add_argument("--entrada", type=Path, default=ARQUIVO_INDICE, help="JSON com IDs e linkPdf")
    parser.add_argument("--saida", type=Path, default=PASTA_PDFS, help="diretório dos PDFs")
    parser.add_argument("--limite", type=int, default=0, help="limita downloads para diagnóstico")
    return parser.parse_args()


def carregar_registros(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as arquivo:
        registros = json.load(arquivo)
    if not isinstance(registros, list):
        raise ValueError(f"O índice deve conter uma lista de registros: {caminho}")

    ids: set[str] = set()
    for posicao, registro in enumerate(registros, 1):
        if not isinstance(registro, dict):
            raise ValueError(f"Registro {posicao} não é um objeto JSON")
        identificador = registro.get("id", "")
        if not isinstance(identificador, str) or not PADRAO_ID.fullmatch(identificador):
            raise ValueError(f"ID inválido no registro {posicao}: {identificador!r}")
        if identificador in ids:
            raise ValueError(f"ID duplicado no índice: {identificador}")
        ids.add(identificador)

        url = registro.get("linkPdf", "")
        partes = urlsplit(url) if isinstance(url, str) else None
        if (
            partes is None
            or partes.scheme != "https"
            or partes.hostname != HOST_OFICIAL
            or not partes.path.lower().endswith(".pdf")
        ):
            raise ValueError(f"Link PDF inválido para {identificador}: {url!r}")

    return registros


def pdf_valido(caminho: Path) -> bool:
    if not caminho.is_file():
        return False
    with caminho.open("rb") as arquivo:
        return arquivo.read(5) == b"%PDF-"


def baixar_pdf(sessao: requests.Session, registro: dict, pasta_saida: Path) -> str:
    identificador = registro["id"]
    destino = pasta_saida / f"{identificador}.pdf"
    if destino.exists():
        if pdf_valido(destino):
            return "existente"
        raise ValueError(f"Arquivo local não é um PDF válido; não será sobrescrito: {destino}")

    temporario = destino.with_name(f"{destino.name}.tmp")
    try:
        with sessao.get(registro["linkPdf"], timeout=180, stream=True) as resposta:
            resposta.raise_for_status()
            with temporario.open("wb") as arquivo:
                for bloco in resposta.iter_content(1024 * 1024):
                    if bloco:
                        arquivo.write(bloco)
        if not pdf_valido(temporario):
            raise ValueError(f"Conteúdo baixado para {identificador} não é um PDF válido")
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)
    return "baixado"


def salvar_manifesto(registros: list[dict], pasta_saida: Path) -> None:
    manifesto = {
        "schema_version": "leme-pdfs-v1",
        "dissertacoes": [
            {
                "id": registro["id"],
                "arquivo_pdf": f"{registro['id']}.pdf",
                "link_pdf": registro["linkPdf"],
                "link_educapes": registro.get("linkProduto") or None,
            }
            for registro in registros
        ],
    }
    salvar_json_atomico(manifesto, pasta_saida / "manifesto.json")


def executar(
    entrada: Path = ARQUIVO_INDICE,
    saida: Path = PASTA_PDFS,
    limite: int = 0,
    sessao: requests.Session | None = None,
) -> dict[str, int]:
    if limite < 0:
        raise ValueError("--limite deve ser zero ou positivo")
    registros = carregar_registros(entrada)
    if limite:
        registros = registros[:limite]

    saida.mkdir(parents=True, exist_ok=True)
    cliente = sessao or criar_sessao_http()
    resumo = {"baixados": 0, "existentes": 0}
    for numero, registro in enumerate(registros, 1):
        resultado = baixar_pdf(cliente, registro, saida)
        resumo["baixados" if resultado == "baixado" else "existentes"] += 1
        print(f"[{numero}/{len(registros)}] {registro['id']}: {resultado}")
    salvar_manifesto(registros, saida)
    return resumo


def main() -> int:
    args = argumentos()
    resumo = executar(args.entrada, args.saida, args.limite)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())