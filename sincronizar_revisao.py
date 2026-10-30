"""Consulta a API do ProfEPT e gera uma planilha das lacunas e novidades."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pymupdf

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from util import criar_sessao_http  # noqa: E402
from gerar_planilha_revisao import DEFAULT_OUTPUT, generate  # noqa: E402
from lemeept.pipeline.product_classifier import classify_product_type  # noqa: E402


def load_file_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def extract_pdf(pdf_path: Path, extractor, max_pages: int) -> dict:
    pages = []
    with pymupdf.open(pdf_path) as doc:
        total = len(doc)
        for index in range(min(total, max_pages)):
            pages.append((index + 1, doc[index].get_text("text")))
    raw_text = "\n\n".join(content for _, content in pages)
    fields = extractor.extrair_campos(extractor.limpar_texto_pdf(raw_text))
    summary_page = next((n for n, content in pages if "RESUMO" in content.upper()), None)
    summary_evidence = ""
    if summary_page:
        page_content = next(content for n, content in pages if n == summary_page)
        summary_evidence = extractor.limpar_texto_pdf(page_content)[:500]
    return {
        "resumo": fields.get("resumo"),
        "palavras_chave": fields.get("palavras_chave", []),
        "coorientador": fields.get("coorientador"),
        "pagina_resumo": summary_page,
        "evidencia_resumo": summary_evidence,
        "paginas_lidas": len(pages),
        "paginas_total": total,
        "_paginasTexto": pages,
    }


def update_manifest(download_results: list[dict]) -> None:
    manifest_path = ROOT / "pdf" / "dissertacoes" / "manifesto.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = []
    by_id = {str(item.get("id")): item for item in previous if isinstance(item, dict) and item.get("id")}
    for item in download_results:
        if item.get("id"):
            by_id[str(item["id"])] = item
    manifest_path.write_text(
        json.dumps(sorted(by_id.values(), key=lambda item: item.get("id", "")), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite-novos", type=int, default=5,
                        help="máximo de PDFs novos baixados e extraídos nesta execução (padrão: 5; 0 = sem limite)")
    parser.add_argument("--max-paginas", type=int, default=20,
                        help="máximo de páginas por PDF para extração de texto nativo (padrão: 20)")
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.limite_novos < 0 or args.max_paginas < 1:
        parser.error("--limite-novos deve ser >= 0 e --max-paginas deve ser >= 1")

    collector = load_file_module("coletor_profept_legacy", ROOT / "1_PegarDadosSiteIfc.py")
    downloader = load_file_module("downloader_dissertacoes", ROOT / "baixar_dissertacoes.py")
    extractor = load_file_module("extrator_pdf_legado", ROOT / "2_PdfParaJson.py")

    session = criar_sessao_http()
    collector_args = SimpleNamespace(offline=False, inseguro_tls=False)
    html, source_meta = collector.obter_pagina_oficial(session, collector_args)
    works = collector.extrair_trabalhos_html(html)
    identities = copy.deepcopy(collector.carregar_identidades())
    collector.resolver_identidades(works, identities)

    dataset_path = ROOT / "lemeept" / "painel-ept-v2.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    known = {str(item.get("id")) for item in dataset.get("defesas", [])}
    discovered = [work for work in works if work.get("id") and work["id"] not in known]
    if args.limite_novos:
        discovered = discovered[:args.limite_novos]

    new_items = []
    download_results = []
    for work in discovered:
        record = {
            "id": work["id"], "ano": work.get("ano"), "autor": work.get("autor"),
            "orientador": work.get("orientador"), "coorientador": work.get("coorientador"),
            "titulo": work.get("titulo"), "url_pdf": work.get("url_pdf"),
            "produto_educacional": work.get("produto_educacional"),
            "url_produto": work.get("url_produto"), "url_oficial": source_meta.get("url"),
            "status_extracao": "PDF pendente", "erro": "",
        }
        try:
            download = downloader.baixar({"id": work["id"], "linkPdf": work.get("url_pdf")})
            download_results.append(download)
            record["status_download"] = download.get("status")
            if download.get("status") in {"erro", "url_ausente"}:
                record["status_extracao"] = "Falha no download"
                record["erro"] = download.get("erro", download.get("status"))
            else:
                extraction = extract_pdf(Path(download["arquivo"]), extractor, args.max_paginas)
                record.update(extraction)
                record["status_extracao"] = "Texto nativo extraído" if extraction.get("resumo") or extraction.get("palavras_chave") else "Sem campos detectados; OCR legado disponível"
                if not extraction.get("resumo") and not extraction.get("palavras_chave"):
                    record["erro"] = f"Texto nativo sem resumo/palavras-chave nas {extraction['paginas_lidas']} páginas lidas. OCR/GPT legado não foi executado."
        except Exception as error:
            record["status_extracao"] = "Erro"
            record["erro"] = f"{type(error).__name__}: {error}"

        product_metadata = {}
        if work.get("url_produto"):
            try:
                product_metadata = collector.consultar_educapes(session, work["url_produto"], collector_args)
            except Exception as error:
                product_metadata = {"status": "erro", "erro": f"{type(error).__name__}: {error}", "handle": "", "campos_dc": {}, "colecoes": [], "bitstreams": []}
        page_text = record.pop("_paginasTexto", [])
        type_result = classify_product_type(page_text[:12], product_metadata)
        record["tipo_produto_classificacao"] = type_result
        record["status_tipo_produto"] = (
            "Tipo específico extraído; verificar metadados divergentes"
            if type_result.get("valor") and type_result.get("revisao") == "necessaria"
            else "Tipo específico extraído com confiança alta"
            if type_result.get("valor") and type_result.get("confianca") == "alta"
            else "Tipo pendente de revisão"
        )
        record["dc_type_educapes"] = (product_metadata.get("campos_dc") or {}).get("dc.type", [])
        record["colecoes_educapes"] = product_metadata.get("colecoes", [])
        print(f"{record['id']}: {record['status_extracao']}")
        new_items.append(record)

    if download_results:
        update_manifest(download_results)
    count = generate(dataset, args.saida, new_items)
    print(f"API ProfEPT consultada; registros na página: {len(works)}; novas identificadas: {len(discovered)}; fila: {count}")
    print(f"Planilha de revisão: {args.saida}")
    print("PDFs novos, se houver, ficam em pdf/dissertacoes/ (ignorado pelo Git). Nenhuma referência versionada foi alterada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
