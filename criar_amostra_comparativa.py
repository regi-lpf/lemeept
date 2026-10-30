"""Extrai uma amostra reproduzível e compara-a com o JSON legado."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parent
SAMPLE_IDS = ["EPT-0001", "EPT-0003", "EPT-0005", "EPT-0007", "EPT-0008", "EPT-0010"]
LEGACY_JSON = ROOT / "lemeept" / "painel-ept.json"
VOCABULARY_JSON = ROOT / "dados" / "referencia" / "vocabularios.json"
PDF_DIR = ROOT / "pdf" / "dissertacoes"
OUTPUT_DIR = ROOT / "dados" / "revisao"
JSON_OUTPUT = OUTPUT_DIR / "amostra_extracao_6_v2.json"
XLSX_OUTPUT = OUTPUT_DIR / "comparacao_amostra_6_v2.xlsx"
MAX_PAGES = 80


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Não foi possível carregar {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def norm(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return re.sub(r"\W+", " ", raw.casefold()).strip()


def clean_value(value: Any) -> Any:
    """Remove invólucros comuns do scraping sem alterar pontuação interna."""
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    if not isinstance(value, str):
        return value
    text = value.strip()
    wrappers = {'"': '"', "'": "'", "[": "]", "“": "”", "‘": "’"}
    changed = True
    while changed and len(text) >= 2:
        changed = False
        for opening, closing in wrappers.items():
            if text.startswith(opening) and text.endswith(closing):
                text = text[1:-1].strip()
                changed = True
                break
    return text


def proposed_product_enum(dc_type: str, collection: str) -> tuple[str, str]:
    """Aplicar apenas equivalências de formato explicitamente definidas pelo usuário."""
    kind, group = norm(dc_type), norm(collection)
    if "portal" in group or "portal" in kind:
        return "Portal", "Correspondência direta: Portal"
    if "aula digital" in group or "aula digital" in kind:
        return "Guia / Tutorial", "Correspondência provisória: Aula Digital"
    if "audio" in group or "audio" in kind:
        return "Podcast", "Correspondência direta: Áudios / áudio"
    if any(term in group or term in kind for term in ("animacao", "video", "videos")):
        return "Vídeo / audiovisual", "Correspondência direta: animação / Vídeos"
    if "livro digital" in group or "livro digital" in kind:
        return "", "Conferir formato proposto na dissertação"
    return "", "Sem equivalência definida; revisar"


def snippet(page: str, pattern: str, before: int = 250, after: int = 1300) -> str:
    match = re.search(pattern, page, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(0, match.start() - before)
    return re.sub(r"\s+", " ", page[start : match.end() + after]).strip()


def section_evidence(pages: list[dict], pattern: str, limit: int = 3) -> list[dict]:
    found = []
    for page in pages:
        excerpt = snippet(page["texto"], pattern)
        if excerpt:
            found.append({"pagina": page["pagina"], "trecho": excerpt[:1800], "metodo": "texto_pdf"})
            if len(found) >= limit:
                break
    return found


def extract_dissertation(record: dict, extractor, max_pages: int) -> dict:
    pdf_path = PDF_DIR / f"{record['id']}.pdf"
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF local ausente: {pdf_path}")
    pages = []
    with pymupdf.open(pdf_path) as doc:
        total = len(doc)
        for index in range(min(total, max_pages)):
            pages.append({"pagina": index + 1, "texto": extractor.limpar_texto_pdf(doc[index].get_text("text"))})
    joined = "\n\n".join(item["texto"] for item in pages)
    fields = extractor.extrair_campos(joined)
    summary_ev = section_evidence(pages, r"(?:^|\n)\s*RESUMO\s*[:\-]?", 1)
    keyword_ev = section_evidence(pages, r"Palavras[- ]chave\s*:", 1)
    intro_ev = section_evidence(pages, r"(?:^|\n)\s*(?:1\s*[.\-–]?\s*)?INTRODU[CÇ][AÃ]O\b", 4)
    theory_ev = section_evidence(pages, r"(?:referencial te[oó]rico|fundamenta[cç][aã]o te[oó]rica|pressupostos te[oó]ricos|marco te[oó]rico)", 5)
    methodology_ev = section_evidence(pages, r"(?:procedimentos metodol[oó]gicos|metodologia|percurso metodol[oó]gico)", 4)
    epistemology_ev = section_evidence(pages, r"(?:epistemolog\w*|ontolog\w*|materialismo hist[oó]rico|dial[eé]tic\w*|fenomenolog\w*|positiv\w*|hermen[eê]utic\w*)", 8)
    line_ev = section_evidence(pages, r"(?:linha de pesquisa|pr[aá]ticas educativas em educa[cç][aã]o profissional|organiza[cç][aã]o e mem[oó]rias)", 3)
    macro_ev = section_evidence(pages, r"(?:macroprojeto|\bMP[1-6]\b)", 3)

    result_fields = {
        "resumoPdf": clean_value(fields.get("resumo")),
        "palavrasChavePdf": clean_value(fields.get("palavras_chave", [])),
        "abstract": clean_value(fields.get("abstract")),
        "coorientadorPdf": clean_value(fields.get("coorientador")),
        "objetivoGeral": clean_value(fields.get("objetivos")),
        "metodologiaExtraida": clean_value(fields.get("metodologia")),
        "linhaPesquisaEncontrada": clean_value(fields.get("linha_pesquisa_encontrada")),
        "macroprojetoEncontrado": clean_value(fields.get("macroprojeto_encontrado")),
        "trechoReferencialTeorico": [e["trecho"] for e in theory_ev],
        "trechoIntroducao": [e["trecho"] for e in intro_ev],
        "baseEpistemologicaCandidata": None,
        "statusBaseEpistemologica": "aguarda_classificacao_assistida_com_evidencia",
        "indiciosEpistemologicos": epistemology_ev,
    }
    evidence = {
        "resumoPdf": summary_ev,
        "palavrasChavePdf": keyword_ev,
        "introducao": intro_ev,
        "referencialTeorico": theory_ev,
        "metodologia": methodology_ev,
        "indiciosEpistemologicos": epistemology_ev,
        "linhaPesquisaEncontrada": line_ev,
        "macroprojetoEncontrado": macro_ev,
    }
    return {
        "id": f"{record['id']}-DIS",
        "defesaId": record["id"],
        "tipo": "dissertacao",
        "titulo": record.get("titulo"),
        "url": record.get("linkPdf"),
        "statusExtracao": "texto_nativo",
        "paginasTotais": total,
        "paginasLidas": len(pages),
        "metadadosExtraidos": result_fields,
        "evidenciasCampos": evidence,
        "pdfLocal": str(pdf_path.relative_to(ROOT)),
    }


def extract_product(record: dict, collector, session, collector_args) -> dict:
    try:
        metadata = collector.consultar_educapes(session, record.get("linkProduto") or "", collector_args)
    except Exception as error:
        metadata = {"status": "erro", "erro": f"{type(error).__name__}: {error}", "handle": "", "campos_dc": {}, "colecoes": [], "bitstreams": []}
    metadata = clean_value(metadata)
    dc = metadata.get("campos_dc") or {}
    return {
        "id": f"{record['id']}-PRO",
        "defesaId": record["id"],
        "tipo": "produto_educacional",
        "titulo": record.get("produto"),
        "url": record.get("linkProduto"),
        "statusExtracao": metadata.get("status"),
        "metadadosEduCAPES": metadata,
        "camposComparaveis": {
            "tituloEduCAPES": dc.get("dc.title", []),
            "tipoEduCAPES": dc.get("dc.type", []),
            "autoresEduCAPES": dc.get("dc.contributor.author", []) or dc.get("dc.creator", []),
            "palavrasChaveEduCAPES": dc.get("dc.subject", []),
            "dataPublicacaoEduCAPES": dc.get("dc.date.issued", []),
            "identificadoresEduCAPES": dc.get("dc.identifier", []),
            "colecoesEduCAPES": metadata.get("colecoes", []),
            "bitstreams": metadata.get("bitstreams", []),
        },
    }


def compare_rows(records: list[dict], dissertation_by_id: dict, product_by_id: dict) -> list[list[Any]]:
    rows = []

    def cell_value(value):
        value = clean_value(value)
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return value

    def add(record, entity, field, legacy, extracted, status, source="", page="", evidence="", url=""):
        rows.append([record["id"], entity, field, cell_value(legacy), cell_value(extracted), status, source, page, evidence, url])

    for record in records:
        ident = record["id"]
        dissertation = dissertation_by_id[ident]
        product = product_by_id[ident]
        ext = dissertation["metadadosExtraidos"]
        ev = dissertation["evidenciasCampos"]
        for field, legacy_value, new_key, evid_key in (
            ("Título da dissertação", record.get("titulo"), None, None),
        ("Resumo legado (curto/sintético)", record.get("resumo"), None, None),
        ("Resumo integral do PDF", "", "resumoPdf", "resumoPdf"),
            ("Palavras-chave", record.get("palavrasChave"), "palavrasChavePdf", "palavrasChavePdf"),
            ("Coorientador", record.get("coorientador"), "coorientadorPdf", None),
            ("Linha de pesquisa", record.get("linhaPesquisa"), "linhaPesquisaEncontrada", "linhaPesquisaEncontrada"),
            ("Macroprojeto", record.get("macroprojeto"), "macroprojetoEncontrado", "macroprojetoEncontrado"),
            ("Nível de aplicação", record.get("nivel"), None, None),
            ("Base epistemológica", record.get("base"), None, "indiciosEpistemologicos"),
        ):
            new_value = ext.get(new_key) if new_key else None
            evidence_list = ev.get(evid_key, []) if evid_key else []
            if field == "Título da dissertação":
                status, extracted = "Valor legado; PDF não reclassificado nesta comparação", legacy_value or ""
            elif field == "Resumo legado (curto/sintético)":
                status, extracted = "Preservado para decisão editorial; comparar ao resumo integral do PDF", legacy_value or ""
            elif field == "Base epistemológica":
                status = "Sem classificação automática; evidências candidatas para GPT/revisão"
                extracted = json.dumps(evidence_list, ensure_ascii=False)
            elif field == "Nível de aplicação":
                status = "Não reclassificado nesta amostra"
                extracted = ""
            elif field in {"Linha de pesquisa", "Macroprojeto"}:
                status = "Trecho candidato; requer classificação" if new_value else "Trecho não localizado"
                extracted = new_value or ""
            elif new_value in (None, "", []):
                status = "Não localizado automaticamente" if field in {"Resumo", "Palavras-chave"} else "Sem dado extraído"
                extracted = ""
            elif field == "Resumo integral do PDF":
                status = "Resumo integral extraído; comparar visualmente com o resumo sintético legado"
                extracted = new_value
            else:
                equal = norm(legacy_value) == norm(new_value)
                status = "Igual" if equal else "Divergente"
                extracted = new_value
            ev0 = evidence_list[0] if evidence_list else {}
            add(record, "Dissertação", field, legacy_value, extracted, status,
                "PDF ProfEPT" if new_key else "Banco legado", ev0.get("pagina", ""), ev0.get("trecho", ""), record.get("linkPdf", ""))

        product_fields = product.get("camposComparaveis", {})
        pairs = [
            ("Título do produto", record.get("produto"), product_fields.get("tituloEduCAPES", [])),
            ("Tipo de produto (legado) vs dc.type", record.get("tipoProduto"), product_fields.get("tipoEduCAPES", [])),
            ("Palavras-chave eduCAPES", [], product_fields.get("palavrasChaveEduCAPES", [])),
            ("Coleção eduCAPES", record.get("colecoesEduCAPES", []), product_fields.get("colecoesEduCAPES", [])),
            ("Autores eduCAPES", [], product_fields.get("autoresEduCAPES", [])),
            ("Data eduCAPES", [], product_fields.get("dataPublicacaoEduCAPES", [])),
        ]
        for field, legacy_value, new_value in pairs:
            if field == "Tipo de produto (legado) vs dc.type":
                status = "Comparar tipo legado com dc.type; campo pode descrever gênero ou formato" if new_value else "dc.type ausente; comparar com coleção eduCAPES"
                extracted = new_value or ""
            elif field == "Palavras-chave eduCAPES":
                status = "Metadado eduCAPES; escopo distinto das palavras-chave do legado" if new_value else "Campo vazio no registro eduCAPES"
                extracted = new_value or ""
            elif not new_value:
                status, extracted = "Não retornado pelo scraping" if product.get("statusExtracao") != "sucesso" else "Campo vazio no registro eduCAPES", ""
            else:
                extracted = new_value
                status = "Igual" if norm(legacy_value) == norm(new_value) else "Divergente" if legacy_value else "Novo dado eduCAPES"
            add(record, "Produto", field, legacy_value, extracted, status, "eduCAPES mode=full", "", "", record.get("linkProduto", ""))
    return rows


def style_table(ws, name: str, widths: dict[str, int]) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="174A5B")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        status = str(row[5].value or "") if len(row) >= 6 else ""
        fill = PatternFill("solid", fgColor="FCE4D6" if status == "Divergente" else "FFF2CC" if status else "FFFFFF")
        for cell in row:
            cell.fill = fill
        if len(row) >= 10 and row[9].value and str(row[9].value).startswith(("http://", "https://")):
            row[9].hyperlink = str(row[9].value)
            row[9].style = "Hyperlink"
    if ws.max_row > 1:
        table = Table(displayName=name, ref=ws.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(table)


def write_workbook(records: list[dict], disserations: list[dict], products: list[dict], output: Path) -> None:
    wb = Workbook()
    summary = wb.active
    summary.title = "Leia primeiro"
    summary.append(["Amostra comparativa LEME EPT", "Resultado"])
    summary.append(["Defesas amostradas", len(records)])
    summary.append(["Dissertações extraídas", len(disserations)])
    summary.append(["Produtos consultados no eduCAPES", len(products)])
    summary.append(["Método PDF", "Texto nativo, até 80 páginas por dissertação; sem OCR/GPT nesta execução."])
    summary.append(["Base epistemológica", "Não foi inferida automaticamente. A planilha compara o valor legado com trechos candidatos e páginas para próxima análise GPT/revisão."])
    summary.append(["Produtos", "Scraping por Handle com mode=full; compare os campos Dublin Core retornados com os dados legados."])
    summary.append(["Propostas tipo eduCAPES", "Aba Tipo x coleção contém equivalências propostas. Livros digitais permanecem para conferência da dissertação."])
    summary.append(["Dicionário GPT", "Lista linhas, MPs compatíveis e bases legadas; usar como vocabulário controlado e permitir abstenção quando faltar evidência."])
    style_table(summary, "ResumoAmostra", {"A": 33, "B": 110})

    comparison = wb.create_sheet("Comparação")
    comparison.append(["ID", "Entidade", "Campo", "JSON legado", "Extração amostral", "Comparação", "Fonte nova", "Página", "Evidência", "URL"])
    dissertation_map = {item["defesaId"]: item for item in disserations}
    product_map = {item["defesaId"]: item for item in products}
    for row in compare_rows(records, dissertation_map, product_map):
        comparison.append(row)
    style_table(comparison, "Comparacao", {"A": 15, "B": 18, "C": 28, "D": 55, "E": 65, "F": 45, "G": 22, "H": 10, "I": 70, "J": 50})

    ds = wb.create_sheet("Dissertações")
    ds.append(["ID", "Título legado", "Resumo legado curto/sintético", "Resumo integral do PDF", "Palavras-chave PDF", "Palavras-chave legado", "Base legado", "Trechos epistemológicos candidatos", "Status", "Páginas lidas", "PDF"])
    for record in records:
        item = dissertation_map[record["id"]]
        fields = item["metadadosExtraidos"]
        ds.append([record["id"], record.get("titulo"), record.get("resumo"), fields.get("resumoPdf"), "; ".join(fields.get("palavrasChavePdf") or []), "; ".join(record.get("palavrasChave") or []), record.get("base"),
                   json.dumps(fields.get("indiciosEpistemologicos", []), ensure_ascii=False), fields.get("statusBaseEpistemologica"),
                   f"{item['paginasLidas']}/{item['paginasTotais']}", record.get("linkPdf")])
    style_table(ds, "DissertacoesAmostra", {"A": 15, "B": 60, "C": 65, "D": 80, "E": 45, "F": 45, "G": 40, "H": 75, "I": 42, "J": 15, "K": 50})

    ps = wb.create_sheet("Produtos")
    ps.append(["ID", "Título legado", "Tipo legado", "Handle", "Status scraping", "Título eduCAPES", "dc.type", "Autores", "Palavras-chave", "Coleções", "Data", "Identificadores", "Bitstreams", "URL"])
    for record in records:
        item = product_map[record["id"]]
        fields = item.get("camposComparaveis", {})
        ps.append([record["id"], record.get("produto"), record.get("tipoProduto"), (item.get("metadadosEduCAPES") or {}).get("handle"),
                   item.get("statusExtracao"), "; ".join(fields.get("tituloEduCAPES", [])), "; ".join(fields.get("tipoEduCAPES", [])), "; ".join(fields.get("autoresEduCAPES", [])),
                   "; ".join(fields.get("palavrasChaveEduCAPES", [])), "; ".join(fields.get("colecoesEduCAPES", [])),
                   "; ".join(fields.get("dataPublicacaoEduCAPES", [])), "; ".join(fields.get("identificadoresEduCAPES", [])),
                   "; ".join(fields.get("bitstreams", [])), record.get("linkProduto")])
    style_table(ps, "ProdutosAmostra", {"A": 15, "B": 55, "C": 25, "D": 18, "E": 20, "F": 60, "G": 30, "H": 45, "I": 50, "J": 35, "K": 20, "L": 55, "M": 65, "N": 50})

    mapping = wb.create_sheet("Tipo x coleção")
    mapping.append(["Tipo de produto legado", "dc.type eduCAPES", "Coleção eduCAPES", "Quantidade", "IDs da amostra", "ENUM proposto", "Base da proposta / revisão"])
    grouped = {}
    for record in records:
        item = product_map[record["id"]]
        fields = item.get("camposComparaveis", {})
        types = fields.get("tipoEduCAPES") or [""]
        collections = fields.get("colecoesEduCAPES") or [""]
        for edu_type in types:
            for collection in collections:
                key = (record.get("tipoProduto") or "", edu_type, collection)
                grouped.setdefault(key, []).append(record["id"])
    for (legacy_type, edu_type, collection), ids in sorted(grouped.items()):
        enum_value, rationale = proposed_product_enum(edu_type, collection)
        mapping.append([legacy_type, edu_type, collection, len(ids), ", ".join(ids), enum_value, rationale])
    style_table(mapping, "TipoColecao", {"A": 32, "B": 35, "C": 50, "D": 14, "E": 45, "F": 30, "G": 48})

    vocab = json.loads(VOCABULARY_JSON.read_text(encoding="utf-8"))
    dictionary = wb.create_sheet("Dicionário GPT")
    full_records = json.loads(LEGACY_JSON.read_text(encoding="utf-8"))
    dictionary.append(["Campo", "Valor canônico / código", "Descrição ou relação", "Ocorrências no banco legado", "Orientação para classificação"])
    line_macro = vocab.get("relacao_linha_macro", {})
    for line, aliases in vocab.get("linhas_de_pesquisa", {}).items():
        allowed_mps = ", ".join(line_macro.get(line, []))
        count = sum(norm(r.get("linhaPesquisa")) == norm(line) for r in full_records)
        dictionary.append(["Linha de pesquisa", line, f"MPs compatíveis: {allowed_mps}; aliases: {'; '.join(aliases)}", count,
                           "Classificar pelo trecho que nomeia a linha; não inferir apenas pelo tema."])
    for code, description in vocab.get("macroprojetos", {}).items():
        parent_lines = [line for line, codes in line_macro.items() if code in codes]
        count = sum(norm(r.get("codigoMacroprojeto")) == norm(code) for r in full_records)
        dictionary.append(["Macroprojeto", code, f"{description}; linha compatível: {'; '.join(parent_lines)}", count,
                           "Usar a descrição como dicionário semântico; exigir trecho de objetivo/produto que sustente a escolha."])
    bases = vocab.get("categorias", {}).get("Base Epistemológica", {}).get("canonicos", {})
    for base, config in bases.items():
        count = sum(norm(r.get("base")) == norm(base) for r in full_records)
        aliases = "; ".join(config.get("aliases", []))
        dictionary.append(["Base epistemológica", base, f"Aliases cadastrados: {aliases}", count,
                           "Campo interpretativo: classificar apenas com evidência conceitual explícita; permitir abstenção."])
    style_table(dictionary, "DicionarioGPT", {"A": 24, "B": 62, "C": 100, "D": 18, "E": 85})
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", nargs="*", default=SAMPLE_IDS)
    parser.add_argument("--max-paginas", type=int, default=MAX_PAGES)
    parser.add_argument("--json", type=Path, default=JSON_OUTPUT)
    parser.add_argument("--xlsx", type=Path, default=XLSX_OUTPUT)
    args = parser.parse_args()
    if not args.ids or len(set(args.ids)) != len(args.ids) or args.max_paginas < 1:
        parser.error("Informe ao menos um ID único e --max-paginas deve ser >= 1.")

    legacy = json.loads(LEGACY_JSON.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in legacy}
    missing = [identifier for identifier in args.ids if identifier not in by_id]
    if missing:
        parser.error(f"IDs ausentes do JSON legado: {missing}")
    records = [by_id[identifier] for identifier in args.ids]

    extractor = load_module("extrator_pdf_amostra", ROOT / "2_PdfParaJson.py")
    collector = load_module("coletor_educapes_amostra", ROOT / "1_PegarDadosSiteIfc.py")
    from util import criar_sessao_http

    session = criar_sessao_http()
    collector_args = SimpleNamespace(offline=False, inseguro_tls=False)
    dissertations = []
    products = []
    for record in records:
        try:
            dissertations.append(extract_dissertation(record, extractor, args.max_paginas))
        except Exception as error:
            dissertations.append({"id": f"{record['id']}-DIS", "defesaId": record["id"], "tipo": "dissertacao",
                                  "titulo": record.get("titulo"), "url": record.get("linkPdf"), "statusExtracao": "erro",
                                  "erro": f"{type(error).__name__}: {error}", "metadadosExtraidos": {}, "evidenciasCampos": {}})
        products.append(extract_product(record, collector, session, collector_args))
        print(f"{record['id']}: PDF={dissertations[-1].get('statusExtracao')}; eduCAPES={products[-1].get('statusExtracao')}")

    dissertations_by_id = {item["defesaId"]: item for item in dissertations}
    vocab = json.loads(VOCABULARY_JSON.read_text(encoding="utf-8"))
    gpt_dictionary = {
        "linhas_de_pesquisa": vocab.get("linhas_de_pesquisa", {}),
        "macroprojetos": vocab.get("macroprojetos", {}),
        "relacao_linha_macro": vocab.get("relacao_linha_macro", {}),
        "bases_epistemologicas": vocab.get("categorias", {}).get("Base Epistemológica", {}).get("canonicos", {}),
    }
    document = {
        "schemaVersion": "leme-amostra-extracao-v1",
        "geradoEm": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonteLegado": "lemeept/painel-ept.json",
        "metodoPDF": {"extracao": "PyMuPDF texto nativo", "maxPaginas": args.max_paginas, "ocr": False, "gpt": False},
        "metodoProdutos": "Scraping do Handle eduCAPES em mode=full, metadados Dublin Core",
        "quantidadeDefesas": len(records),
        "quantidadeProducoes": len(dissertations) + len(products),
        "entradaClassificacaoGPT": {
            "instrucao": "Classifique apenas linha de pesquisa, macroprojeto e base epistemológica com base nos trechos e valores permitidos. Retorne valor canônico, evidência literal, página, confiança alta/media/baixa e revisaoManual. Não use apenas tema para inferir linha ou macroprojeto. Para base epistemológica, exija evidência conceitual explícita e permita null/A revisar.",
            "dicionario": gpt_dictionary,
            "trabalhos": [{
                "id": r["id"], "titulo": r.get("titulo"), "resumo": dissertations_by_id[r["id"]]["metadadosExtraidos"].get("resumoPdf"),
                "valoresLegados": {"linhaPesquisa": r.get("linhaPesquisa"), "macroprojeto": r.get("macroprojeto"), "baseEpistemologica": r.get("base")},
                "evidencias": {
                    "linhaPesquisa": dissertations_by_id[r["id"]]["evidenciasCampos"].get("linhaPesquisaEncontrada", []),
                    "macroprojeto": dissertations_by_id[r["id"]]["evidenciasCampos"].get("macroprojetoEncontrado", []),
                    "introducao": dissertations_by_id[r["id"]]["evidenciasCampos"].get("introducao", [])[:2],
                    "referencialTeorico": dissertations_by_id[r["id"]]["evidenciasCampos"].get("referencialTeorico", [])[:2],
                    "indiciosEpistemologicos": dissertations_by_id[r["id"]]["evidenciasCampos"].get("indiciosEpistemologicos", [])[:3],
                }
            } for r in records],
        },
        "defesas": [{"id": r["id"], "ano": r.get("ano"), "academico": r.get("autor"), "orientador": r.get("orientador"),
                     "tituloDissertacao": r.get("titulo"), "tituloProduto": r.get("produto"), "fontes": {"pdf": r.get("linkPdf"), "eduCAPES": r.get("linkProduto")},
                     "camposLegado": {"resumoCurto": r.get("resumo"), "palavrasChave": r.get("palavrasChave"), "coorientador": r.get("coorientador"), "baseEpistemologica": r.get("base"), "nivelAplicacao": r.get("nivel"), "linhaPesquisa": r.get("linhaPesquisa"), "macroprojeto": r.get("macroprojeto"), "tipoProduto": r.get("tipoProduto")},
                     "classificacaoLegada": {"baseEpistemologica": r.get("base"), "nivelAplicacao": r.get("nivel"), "linhaPesquisa": r.get("linhaPesquisa"), "macroprojeto": r.get("macroprojeto"), "tipoProduto": r.get("tipoProduto")}}
                    for r in records],
        "producoes": dissertations + products,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_workbook(records, dissertations, products, args.xlsx)
    print(f"JSON: {args.json}")
    print(f"Planilha: {args.xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
