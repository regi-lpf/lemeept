"""Gera contexto enxuto de texto teórico + referências para a amostra local."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "dados" / "revisao" / "amostra_extracao_6_v2.json"
OUTPUT_JSON = ROOT / "dados" / "revisao" / "contexto_base_epistemologica_6_v1.json"
OUTPUT_XLSX = ROOT / "dados" / "revisao" / "contexto_base_epistemologica_6_v1.xlsx"
PDF_DIR = ROOT / "pdf" / "dissertacoes"
MAX_REFERENCE_PAGES = 45
MAX_THEORY_EVIDENCE = 10
NON_AUTHOR_LABELS = {"ifc", "brasil", "blumenau", "informática", "eletromecânica", "pae", "capes", "campus", "município"}

EPISTEMIC_TERMS = re.compile(
    r"epistemolog|ontolog|materialismo|dial[eé]tic|fenomenolog|positiv|hermen[eê]ut|"
    r"marxista|marxismo|pedagogia hist[oó]rico|concep[cç][aã]o te[oó]rica|"
    r"base te[oó]rica|pressuposto te[oó]rico|fundamento te[oó]rico|"
    r"trabalho como princ[ií]pio educativo|perspectiva te[oó]rica|orienta[cç][aã]o te[oó]rica|"
    r"educa[cç][aã]o cr[ií]tica|emancipat[oó]ri|freirean|omnilateral|politecnia|forma[cç][aã]o humana integral",
    re.I,
)


def norm(text: str) -> str:
    value = unicodedata.normalize("NFKD", text)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).casefold()


def citations_from(texts: list[str]) -> list[dict[str, str]]:
    """Find common ABNT author-year citations; keep them as search hints only."""
    patterns = (
        re.compile(r"\b([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ'’.-]{1,40})(?:\s+et\s+al\.?)?,?\s*\(?((?:19|20)\d{2})\)?"),
        re.compile(r"\b([A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’-]{2,40})(?:\s+et\s+al\.?)?\s*[, ]*\(?((?:19|20)\d{2})\)?"),
    )
    found: dict[tuple[str, str], dict[str, str]] = {}
    for text in texts:
        for pattern in patterns:
            for match in pattern.finditer(text):
                author = re.sub(r"\s+", " ", match.group(1)).strip(" .,-")
                year = match.group(2)
                if len(author) < 3 or author.casefold() in NON_AUTHOR_LABELS | {"capitulo", "secao", "introducao"}:
                    continue
                key = (norm(author), year)
                found.setdefault(key, {"autor": author, "ano": year})
    return list(found.values())


def named_authors_from(texts: list[str]) -> list[str]:
    """Capture named theorists only when the document explicitly introduces an author list."""
    found: dict[str, str] = {}
    names_pattern = re.compile(r"autores? como\s+(.{0,500}?)(?:\.|;)", re.I)
    word_pattern = re.compile(r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'’-]{2,}")
    for text in texts:
        for match in names_pattern.finditer(text):
            for part in re.split(r",|\s+e\s+|;", match.group(1)):
                names = word_pattern.findall(part)
                if len(names) >= 2:
                    surname = names[-1]
                    if norm(surname) not in {"educacao", "trabalho", "pesquisa", "politicas", "institutos", "curriculo"}:
                        found.setdefault(norm(surname), surname)
    return list(found.values())


def extract_theory_evidence(doc: pymupdf.Document, candidate: str | None) -> list[dict[str, Any]]:
    candidate_terms = {
        "educacao critica": r"freire|critica|emancipat|dialog|conscientiza",
        "pedagogia historico critica": r"pedagogia historico|saviani|historico critica",
        "formacao humana integral": r"formacao humana|omnilateral|politecnia|integralidade",
        "trabalho como principio educativo": r"trabalho como principio educativo|trabalho e educacao|principio educativo",
        "materialismo historico": r"materialismo historico|dialetico|marx|totalidade|contradicao",
    }
    folded_candidate = norm(candidate or "")
    extra = next((pattern for key, pattern in candidate_terms.items() if key in folded_candidate), "")
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    patterns = [re.compile(extra, re.I)] if extra else []
    patterns.append(EPISTEMIC_TERMS)
    for pattern in patterns:
        for index, page in enumerate(doc):
            text = page.get_text("text")
            for match in pattern.finditer(text):
                start = max(0, match.start() - 320)
                end = min(len(text), match.end() + 500)
                excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
                key = (index + 1, excerpt)
                if len(excerpt) >= 70 and key not in seen:
                    seen.add(key)
                    candidates.append({"pagina": index + 1, "trecho": excerpt[:820]})
                    if len(candidates) >= MAX_THEORY_EVIDENCE:
                        return candidates
    return candidates


def locate_reference_section(doc: pymupdf.Document) -> tuple[int | None, list[tuple[int, str]]]:
    heading = re.compile(r"(?im)^\s*(?:\d+(?:\.\d+)*\s+)?(?:REFER[EÊ]NCIAS(?:\s+BIBLIOGR[AÁ]FICAS)?|BIBLIOGRAFIA)\s*$")
    appendix = re.compile(r"(?im)^\s*(?:AP[EÊ]NDICE|ANEXO|GLOSS[AÁ]RIO)\b")
    threshold = int(len(doc) * 0.2)
    candidates: list[int] = []
    for index, page in enumerate(doc):
        text = page.get_text("text")
        if index >= threshold and heading.search(text) and len(text.strip()) >= 300:
            candidates.append(index)
    if not candidates:
        return None, []

    start = candidates[0]
    section: list[tuple[int, str]] = []
    for index in range(start, min(len(doc), start + MAX_REFERENCE_PAGES)):
        text = doc[index].get_text("text")
        if index > start and appendix.search(text):
            break
        section.append((index + 1, text))
    return start + 1, section


def match_references(citations: list[dict[str, str]], pages: list[tuple[int, str]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for citation in citations:
        surname = norm(citation["autor"])
        year = citation["ano"]
        matched_citation = False
        for page_number, text in pages:
            lines = text.splitlines()
            for line_index in range(len(lines)):
                surrounding = " ".join(lines[line_index : line_index + 5])
                normalized = norm(surrounding)
                if surname in normalized and year in normalized:
                    excerpt = " ".join(lines[max(0, line_index - 1) : min(len(lines), line_index + 5)])
                    excerpt = re.sub(r"\s+", " ", excerpt).strip()
                    key = (surname, year, page_number)
                    if excerpt and key not in seen:
                        seen.add(key)
                        matches.append({
                            "autorCitado": citation["autor"],
                            "anoCitado": year,
                            "paginaPDFReferencia": page_number,
                            "trechoReferencia": excerpt[:600],
                            "metodoCorrespondencia": "sobrenome_ano_na_mesma_pagina",
                        })
                        matched_citation = True
                        break
                if matched_citation:
                    break
            if matched_citation:
                break
    return matches


def match_named_authors(authors: list[str], pages: list[tuple[int, str]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for author in authors:
        surname = norm(author)
        matched_author = False
        for page_number, text in pages:
            lines = text.splitlines()
            for line_index, line in enumerate(lines):
                if surname not in norm(" ".join(lines[line_index : line_index + 3])):
                    continue
                excerpt = re.sub(r"\s+", " ", " ".join(lines[max(0, line_index - 1) : min(len(lines), line_index + 5)])).strip()
                key = (surname, page_number)
                if excerpt and key not in seen:
                    seen.add(key)
                    matches.append({
                        "autorCitado": author,
                        "anoCitado": None,
                        "paginaPDFReferencia": page_number,
                        "trechoReferencia": excerpt[:600],
                        "metodoCorrespondencia": "sobrenome_de_autor_nomeado_no_argumento",
                    })
                    matched_author = True
                    break
            if matched_author:
                break
    return matches


def build_context() -> dict[str, Any]:
    sample = json.loads(INPUT.read_text(encoding="utf-8"))
    dissertations = {item["defesaId"]: item for item in sample.get("producoes", []) if item.get("tipo") == "dissertacao"}
    old = json.loads((ROOT / "dados" / "revisao" / "classificacao_assistida_6_v2.json").read_text(encoding="utf-8"))
    classifications = {item["id"]: item for item in old.get("trabalhos", [])}
    contexts = []

    for defense_id, dissertation in dissertations.items():
        pdf = PDF_DIR / f"{defense_id}.pdf"
        if not pdf.is_file():
            contexts.append({"id": defense_id, "status": "pdf_local_ausente", "referenciasCorrespondentes": []})
            continue
        gpt_input = next((item for item in sample.get("entradaClassificacaoGPT", {}).get("trabalhos", []) if item.get("id") == defense_id), {})
        summary = str(gpt_input.get("resumo") or "")
        previous = classifications.get(defense_id, {}).get("baseEpistemologica", {})
        dissertation_path = PDF_DIR / f"{defense_id}.pdf"
        with pymupdf.open(dissertation_path) as doc:
            reference_page, reference_pages = locate_reference_section(doc)
            theory = extract_theory_evidence(doc, previous.get("candidato") or previous.get("valor"))
        theory_texts = [str(item["trecho"]) for item in theory]
        citations = citations_from(theory_texts)
        named_authors = named_authors_from(theory_texts)
        matched = match_references(citations, reference_pages) + match_named_authors(named_authors, reference_pages)

        contexts.append({
            "id": defense_id,
            "status": "referencias_encontradas" if reference_page and reference_pages else "secao_referencias_nao_localizada",
            "pdfLocal": dissertation.get("pdfLocal"),
            "paginaPDFInicioReferencias": reference_page,
            "resumoDissertacao": summary[:2500],
            "trechosReferencialTeorico": [{"paginaPDF": item.get("pagina"), "trecho": item.get("trecho")} for item in theory],
            "citacoesAutorAnoDetectadas": citations,
            "autoresMencionadosEmListaTeorica": named_authors,
            "referenciasCorrespondentes": matched,
            "classificacaoAnterior": {
                "valor": previous.get("valor"), "candidato": previous.get("candidato"),
                "confianca": previous.get("confianca"), "evidencia": previous.get("evidencia"),
            },
            "regra": "Use a bibliografia apenas para corroborar citações ligadas ao argumento teórico. A mera presença de uma obra não comprova a base. Se a evidência conceitual for insuficiente, abstenha-se.",
        })

    return {
        "schemaVersion": "leme-contexto-epistemologia-v1",
        "fonteAmostra": str(INPUT.relative_to(ROOT)),
        "metodo": "PyMuPDF nativo; extração local de trechos e busca autor-ano na seção de referências; nenhuma chamada GPT/OCR é feita por este script.",
        "instrucaoClassificacao": "Classifique somente a base epistemológica. Use argumento do resumo/referencial; use referências correspondentes às citações como corroboração. Retorne valor canônico ou null, confiança alta/media/baixa, justificativa breve e páginas/trechos. Não infira pela lista de referências isoladamente. Adote somente confiança alta; deixe demais casos para revisão humana.",
        "trabalhos": contexts,
    }


def write_workbook(document: dict[str, Any]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Base epistemológica"
    sheet.append(["ID", "Status", "Confiança anterior", "Candidato anterior", "Resumo", "Trecho teórico", "Citações detectadas", "Referências correspondentes", "Regra de uso"])
    for item in document["trabalhos"]:
        refs = "\n\n".join(
            f"{ref['autorCitado']} ({ref['anoCitado']}) — p. PDF {ref['paginaPDFReferencia']}: {ref['trechoReferencia']}"
            for ref in item.get("referenciasCorrespondentes", [])
        )
        theory = "\n\n".join(f"p. PDF {part.get('paginaPDF')}: {part.get('trecho', '')}" for part in item.get("trechosReferencialTeorico", []))
        citations = "; ".join(f"{c['autor']} ({c['ano']})" for c in item.get("citacoesAutorAnoDetectadas", []))
        prior = item.get("classificacaoAnterior", {})
        sheet.append([item.get("id"), item.get("status"), prior.get("confianca"), prior.get("candidato") or prior.get("valor"), item.get("resumoDissertacao"), theory, citations, refs, item.get("regra")])

    header_fill = PatternFill("solid", fgColor="243B64")
    for cell in sheet[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    widths = [16, 30, 18, 38, 70, 80, 40, 90, 70]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[chr(64 + index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        sheet.row_dimensions[row[0].row].height = 100
    if sheet.max_row > 1:
        table = Table(displayName="RevisaoBaseEpistemologica", ref=sheet.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
        sheet.add_table(table)

    decisions = workbook.create_sheet("Decisão proposta")
    decisions.append(["ID", "Base anterior", "Confiança anterior", "Valor proposto", "Confiança proposta", "Ação", "Justificativa"])
    for item in document["trabalhos"]:
        prior = item.get("classificacaoAnterior", {})
        accepted = item.get("recomendacao") == "adotar_valor_de_trabalho"
        decisions.append([
            item.get("id"), prior.get("valor"), prior.get("confianca"),
            item.get("valorProposto") or prior.get("candidato") or prior.get("valor"),
            "alta" if accepted else prior.get("confianca"),
            "Adotar no JSON de trabalho" if accepted else "Manter na fila de revisão",
            item.get("justificativaDecisao") or "A evidência atual não sustenta adoção automática com confiança alta.",
        ])
    for cell in decisions[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for col, width in zip("ABCDEFG", [16, 40, 20, 40, 20, 34, 100]):
        decisions.column_dimensions[col].width = width
    decisions.freeze_panes = "A2"
    decisions.auto_filter.ref = decisions.dimensions
    for row in decisions.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        decisions.row_dimensions[row[0].row].height = 55
    if decisions.max_row > 1:
        table = Table(displayName="DecisaoBaseEpistemologica", ref=decisions.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium4", showRowStripes=True, showColumnStripes=False)
        decisions.add_table(table)
    OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT_XLSX)


def main() -> int:
    document = build_context()
    proposal_source = json.loads((ROOT / "dados" / "revisao" / "classificacao_assistida_6_v2.json").read_text(encoding="utf-8"))
    proposals = {item["id"]: item for item in proposal_source.get("trabalhos", [])}
    for context in document["trabalhos"]:
        record = proposals.get(context["id"])
        if not record:
            continue
        base = record.get("baseEpistemologica", {})
        direct_evidence = next((item for item in context.get("trechosReferencialTeorico", []) if item.get("paginaPDF") == 18 and "materialista hist" in norm(item.get("trecho", ""))), None)
        named_refs = [item for item in context.get("referenciasCorrespondentes", []) if item.get("autorCitado") in {"Gramsci", "Marx", "Frigotto", "Ciavatta", "Ramos"}]
        if context["id"] == "EPT-0007" and direct_evidence and named_refs:
            context["recomendacao"] = "adotar_valor_de_trabalho"
            context["valorProposto"] = "Materialismo Histórico-Dialético"
            context["justificativaDecisao"] = "A dissertação nomeia uma análise materialista histórico-dialética da realidade (p. PDF 18) e explicita, no referencial, autores marxistas/gramscianos; obras de Gramsci e autores correlatos aparecem na bibliografia. A evidência direta e a corroboração bibliográfica elevam o candidato médio anterior a alta confiança."
            base["confiancaAnterior"] = base.get("confianca")
            base["confianca"] = "alta"
            base["revisaoManual"] = False
            base["metodo"] = "classificacao_assistida_com_corroboração_bibliografica"
            base["evidenciasBibliograficas"] = [
                {"autor": item["autorCitado"], "paginaPDF": item["paginaPDFReferencia"], "trecho": item["trechoReferencia"]}
                for item in named_refs[:4]
            ]
            base["evidenciaComplementar"] = {"paginaPDF": direct_evidence["paginaPDF"], "trecho": direct_evidence["trecho"]}
        else:
            context["recomendacao"] = "revisao_humana"
            context["valorProposto"] = base.get("valor") or base.get("candidato")
            context["justificativaDecisao"] = "Os trechos e referências localizados não demonstram com confiança alta que o candidato seja a base epistemológica; manter para revisão humana."
        context["classificacaoAnterior"] = base

    proposal = {
        "schemaVersion": "leme-classificacao-assistida-v3",
        "metodo": "Reavaliação contextual do Codex com evidência textual e bibliográfica selecionada; nenhuma API GPT foi chamada.",
        "origem": "classificacao_assistida_6_v2.json + contexto_base_epistemologica_6_v1.json",
        "regra": "Adotar somente valores com confiança alta e evidência conceitual direta. Referências bibliográficas corroboram citações/argumentos; presença isolada não prova a base.",
        "trabalhos": [
            {"id": item["id"], "baseEpistemologica": item.get("classificacaoAnterior"), "recomendacao": item.get("recomendacao"), "justificativa": item.get("justificativaDecisao")}
            for item in document["trabalhos"]
        ],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_JSON.parent / "classificacao_assistida_6_v3.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_workbook(document)
    for item in document["trabalhos"]:
        print(f"{item['id']}: {item['status']}; citações={len(item.get('citacoesAutorAnoDetectadas', []))}; referências={len(item.get('referenciasCorrespondentes', []))}")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"Planilha: {OUTPUT_XLSX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
