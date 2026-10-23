"""Baixa as dissertações do painel para pdf/dissertacoes sem alterar referências."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit

import requests
from requests.exceptions import SSLError


ARQUIVO_PAINEL = Path("lemeept/painel-ept.json")
PASTA_DESTINO = Path("pdf/dissertacoes")
HOST_IFC = "profept.ifc.edu.br"


def requisicao_pdf(url: str):
    try:
        return requests.get(url, timeout=(20, 180), stream=True)
    except SSLError:
        if (urlsplit(url).hostname or "").casefold() != HOST_IFC:
            raise
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )
        return requests.get(url, timeout=(20, 180), stream=True, verify=False)


def sha256_arquivo(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def baixar(registro: dict) -> dict:
    identificador = registro["id"]
    destino = PASTA_DESTINO / f"{identificador}.pdf"
    if destino.exists() and destino.stat().st_size:
        with destino.open("rb") as arquivo:
            valido = arquivo.read(5) == b"%PDF-"
        if valido:
            return {"id": identificador, "arquivo": str(destino), "url": registro.get("linkPdf"), "status": "ja_existia", "bytes": destino.stat().st_size, "sha256": sha256_arquivo(destino)}

    # Reaproveita os três PDFs da amostra quando o ID consta no nome local.
    existente = next((p for p in Path("pdf").glob(f"{identificador}_*.pdf") if p != destino), None)
    if existente:
        with existente.open("rb") as arquivo:
            valido = arquivo.read(5) == b"%PDF-"
        if valido:
            shutil.copy2(existente, destino)
            return {"id": identificador, "arquivo": str(destino), "url": registro.get("linkPdf"), "status": "copiado_da_amostra", "bytes": destino.stat().st_size, "sha256": sha256_arquivo(destino)}

    url = registro.get("linkPdf")
    if not url:
        return {"id": identificador, "arquivo": str(destino), "status": "url_ausente"}
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        digest = hashlib.sha256()
        cabecalho = bytearray()
        with requisicao_pdf(url) as resposta:
            resposta.raise_for_status()
            with tempfile.NamedTemporaryFile(dir=destino.parent, suffix=".part", delete=False) as tmp:
                temporario = Path(tmp.name)
                for bloco in resposta.iter_content(1024 * 1024):
                    if bloco:
                        if len(cabecalho) < 5:
                            cabecalho.extend(bloco[: 5 - len(cabecalho)])
                        digest.update(bloco)
                        tmp.write(bloco)
        if bytes(cabecalho) != b"%PDF-":
            raise ValueError("resposta não começa com assinatura PDF")
        temporario.replace(destino)
        return {"id": identificador, "arquivo": str(destino), "url": url, "status": "baixado", "bytes": destino.stat().st_size, "sha256": digest.hexdigest()}
    except Exception as erro:
        if temporario:
            temporario.unlink(missing_ok=True)
        return {"id": identificador, "arquivo": str(destino), "url": url, "status": "erro", "erro": str(erro)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=0, help="limita registros para diagnóstico")
    parser.add_argument("--workers", type=int, default=4, help="downloads simultâneos (padrão: 4)")
    args = parser.parse_args()
    registros = json.loads(ARQUIVO_PAINEL.read_text(encoding="utf-8"))
    if args.limite:
        registros = registros[: args.limite]
    PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
    resultados = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futuros = [pool.submit(baixar, registro) for registro in registros]
        for futuro in as_completed(futuros):
            item = futuro.result()
            resultados.append(item)
            print(f"{item['id']}: {item['status']}")
    resultados.sort(key=lambda item: item["id"])
    manifesto = PASTA_DESTINO / "manifesto.json"
    manifesto.write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    falhas = [item for item in resultados if item["status"] in {"erro", "url_ausente"}]
    print(f"Concluído: {len(resultados) - len(falhas)}/{len(registros)} PDFs disponíveis; manifesto: {manifesto}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
