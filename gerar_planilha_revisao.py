"""Gera uma planilha filtrável com a fila de revisão do banco LEME EPT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "lemeept" / "painel-ept-v2.json"
DEFAULT_OUTPUT = ROOT / "dados" / "revisao" / "revisao_ept.xlsx"
HEADER_FILL = PatternFill("solid", fgColor="174A5B")
HEADER_FONT = Font(color="FFFFFF", bold=True)
REVIEW_FILL = PatternFill("solid", fgColor="FFF2CC")
MISSING_FILL = PatternFill("solid", fgColor="FCE4D6")


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def evidence_for(production: dict, field: str) -> tuple[str, str]:
    for source in production.get("fontes", []):
        evidence = source.get("evidencias", {}).get(field, [])
        if evidence:
            item = evidence[0]
            return str(item.get("pagina", "")), text(item.get("trecho"))
    return "", ""


def review_rows(dataset: dict, new_items: list[dict]) -> list[list[str]]:
    rows: list[list[str]] = []

    def add(identifier: str, entity: str, field: str, status: str, value: Any,
            source: str = "", page: str = "", evidence: str = "", url: str = "") -> None:
        rows.append([identifier, entity, field, status, text(value), source, page, evidence, url, ""])

    productions = {item["defesaId"]: item for item in dataset.get("producoes", []) if item.get("tipo") == "dissertacao"}
    products = {item["defesaId"]: item for item in dataset.get("producoes", []) if item.get("tipo") == "produto_educacional"}
    for defense in dataset.get("defesas", []):
        identifier = text(defense.get("id"))
        dissertation = productions.get(identifier, {})
        product = products.get(identifier, {})
        for field, value in (("Ano", defense.get("ano")), ("Acadêmico", (defense.get("academico") or {}).get("nome")),
                             ("Orientador", (defense.get("orientador") or {}).get("nome")),
                             ("Linha de pesquisa", (defense.get("linhaPesquisa") or {}).get("nome")),
                             ("Macroprojeto", (defense.get("macroprojeto") or {}).get("codigo")),
                             ("Base epistemológica", ((defense.get("classificacoes") or {}).get("baseEpistemologica") or {}).get("valor")),
                             ("Nível de aplicação", ((defense.get("classificacoes") or {}).get("nivelAplicacao") or {}).get("valor"))):
            if not text(value):
                add(identifier, "Defesa", field, "Ausente", "", "Registro ProfEPT / base atual")

        classifications = defense.get("classificacoes", {})
        for field, label in (("baseEpistemologica", "Base epistemológica"), ("nivelAplicacao", "Nível de aplicação")):
            item = classifications.get(field) or {}
            if field == "baseEpistemologica" and item.get("metodo") == "classificacao_historica" and not item.get("evidencias"):
                add(identifier, "Defesa", label, "Reanalisar com OCR/GPT segmentado", item.get("valor"),
                    "Valor herdado; buscar evidências no resumo, introdução, referencial teórico e metodologia")
            elif item.get("revisao") == "necessaria":
                add(identifier, "Defesa", label, "Conferência sinalizada", item.get("valor"),
                    "Sinal de revisão herdado da classificação histórica")

        dmeta = dissertation.get("metadados", {})
        durl = text(dissertation.get("url"))
        evidences = (dissertation.get("fontes") or [{}])[0].get("evidencias", {})
        for field, label, value in (("resumo", "Resumo", dmeta.get("resumo")),
                                    ("palavrasChave", "Palavras-chave", dmeta.get("palavrasChave"))):
            page, excerpt = evidence_for(dissertation, field)
            if not value:
                method = dissertation.get("proveniencia", {}).get("conteudo", {}).get("metodo")
                status = "Pendente de extração automática" if method in {None, "nao_tentado"} else "Não localizado automaticamente; conferir PDF"
                add(identifier, "Dissertação", label, status, "", "PDF — seção/campo esperado pela ABNT", url=durl)
            elif not evidences.get(field):
                add(identifier, "Dissertação", label, "Conferir evidência", value, "PDF", url=durl)

        pmeta = product.get("metadados", {})
        provenance = product.get("proveniencia", {}).get("metadadosEduCAPES", {})
        if provenance.get("metodo") == "nao_consultado":
            add(identifier, "Produto", "Metadados eduCAPES", "Consulta pendente", "", "eduCAPES", url=text(product.get("url")))
        elif not (pmeta.get("tipoProduto") or {}).get("nome"):
            add(identifier, "Produto", "Tipo de produto", "Ausente", "", "eduCAPES / classificação", url=text(product.get("url")))

    for item in new_items:
        identifier = text(item.get("id")) or "ID pendente"
        add(identifier, "Nova defesa", "Revisão inicial", "Nova na API", "Conferir os dados oficiais e o resultado do PDF", "API ProfEPT", url=text(item.get("url_oficial")))
        for field, key in (("Acadêmico", "autor"), ("Orientador", "orientador"),
                           ("Título da dissertação", "titulo"), ("Link do PDF", "url_pdf"),
                           ("Produto educacional", "produto_educacional"), ("Link do produto", "url_produto")):
            if not text(item.get(key)):
                add(identifier, "Nova defesa", field, "Ausente na fonte", "", "API ProfEPT", url=text(item.get("url_oficial")))
        status = text(item.get("status_extracao")) or "Extração pendente"
        add(identifier, "Nova defesa", "PDF / extração", status, item.get("resumo"), "PDF ProfEPT",
            text(item.get("pagina_resumo")), text(item.get("evidencia_resumo")), text(item.get("url_pdf")))
        if item.get("erro"):
            add(identifier, "Nova defesa", "Erro de processamento", "Conferir", item.get("erro"), "Sincronização", url=text(item.get("url_pdf")))
        type_result = item.get("tipo_produto_classificacao") or {}
        proposed = type_result.get("valor") or type_result.get("candidato")
        if isinstance(proposed, dict):
            proposed = proposed.get("nome") or proposed.get("codigo") or json.dumps(proposed, ensure_ascii=False)
        elif isinstance(proposed, list):
            proposed = "; ".join(str(value.get("nome") or value.get("codigo") or value) if isinstance(value, dict) else str(value) for value in proposed)
        evidence = (type_result.get("evidencias") or [{}])[0]
        add(identifier, "Produto", "Tipo de produto", item.get("status_tipo_produto", "Tipo pendente de revisão"), proposed,
            type_result.get("campoOrigem") or "PDF / eduCAPES", evidence.get("pagina", ""), evidence.get("trecho", ""), text(item.get("url_produto")))
    return rows


def style_sheet(ws, table_name: str, widths: dict[str, int]) -> None:
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30
    for column, width in widths.items():
        ws.column_dimensions[column].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        status = str(row[3].value or "") if len(row) > 3 else ""
        if status in {"Ausente", "Ausente na fonte"}:
            for cell in row:
                cell.fill = MISSING_FILL
        elif status:
            for cell in row:
                cell.fill = REVIEW_FILL
        for cell in row:
            if cell.column == len(row) and cell.value is None:
                cell.value = ""
    if ws.max_row > 1:
        table = Table(displayName=table_name, ref=ws.dimensions)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True,
                                              showColumnStripes=False, showFirstColumn=False,
                                              showLastColumn=False)
        ws.add_table(table)


def generate(dataset: dict, output: Path, new_items: list[dict] | None = None) -> int:
    new_items = new_items or []
    decisions: dict[tuple[str, str, str], str] = {}
    history: dict[tuple[str, str, str], list[str]] = {}
    if output.exists():
        previous = load_workbook(output, read_only=True, data_only=True)
        for sheet_name in ("Fila de revisão", "Histórico de revisão"):
            if sheet_name not in previous.sheetnames:
                continue
            sheet = previous[sheet_name]
            for values in sheet.iter_rows(min_row=2, values_only=True):
                if len(values) < 10 or not values[0]:
                    continue
                key = (str(values[0]), str(values[1] or ""), str(values[2] or ""))
                decision = str(values[9] or "").strip()
                if sheet_name == "Fila de revisão" and decision:
                    decisions[key] = decision
                elif sheet_name == "Histórico de revisão":
                    history[key] = [str(value or "") for value in values[:10]]
        previous.close()

    wb = Workbook()
    summary = wb.active
    summary.title = "Leia primeiro"
    summary.append(["Revisão do banco LEME EPT", "Quantidade"])
    summary.append(["Defesas na base atual", len(dataset.get("defesas", []))])
    summary.append(["Produções independentes", len(dataset.get("producoes", []))])
    summary.append(["Novas defesas encontradas na API", len(new_items)])
    summary.append(["Itens na fila de revisão", len(review_rows(dataset, new_items))])
    summary.append(["Como usar", "Filtre a aba Fila de revisão pela coluna Status. Preencha Decisão / correção; preserve Valor extraído e Evidência como referência."])
    style_sheet(summary, "ResumoRevisao", {"A": 44, "B": 110})

    queue = wb.create_sheet("Fila de revisão")
    queue.append(["ID", "Entidade", "Campo", "Status", "Valor extraído", "Fonte", "Página", "Evidência", "URL da fonte", "Decisão / correção"])
    current_rows = review_rows(dataset, new_items)
    current_keys = {(row[0], row[1], row[2]) for row in current_rows}
    for row in current_rows:
        row[9] = decisions.get((row[0], row[1], row[2]), "")
        queue.append(row)
    style_sheet(queue, "FilaRevisao", {"A": 16, "B": 20, "C": 27, "D": 24, "E": 55, "F": 24, "G": 10, "H": 65, "I": 50, "J": 45})
    for row in queue.iter_rows(min_row=2):
        url_cell = row[8]
        if url_cell.value and str(url_cell.value).startswith(("http://", "https://")):
            url_cell.hyperlink = str(url_cell.value)
            url_cell.style = "Hyperlink"

    resolved = wb.create_sheet("Histórico de revisão")
    resolved.append(["ID", "Entidade", "Campo", "Status anterior", "Valor extraído", "Fonte", "Página", "Evidência", "URL da fonte", "Decisão / correção"])
    archived = dict(history)
    for values in (list(row) for row in queue.iter_rows(min_row=2, values_only=True)):
        key = (str(values[0]), str(values[1] or ""), str(values[2] or ""))
        if key in decisions:
            archived[key] = [str(value or "") for value in values[:10]]
    for key, values in archived.items():
        if key not in current_keys:
            resolved.append(values)
    style_sheet(resolved, "HistoricoRevisao", {"A": 16, "B": 20, "C": 27, "D": 24, "E": 55, "F": 24, "G": 10, "H": 65, "I": 50, "J": 45})

    recent = wb.create_sheet("Novas defesas")
    recent.append(["ID", "Ano", "Acadêmico", "Orientador", "Coorientador", "Título da dissertação", "PDF", "Produto educacional", "Link do produto", "Status PDF / texto", "Resumo extraído", "Página", "Evidência curta", "Erro", "Tipo canônico proposto", "Confiança tipo", "Status tipo", "Evidência tipo", "dc.type eduCAPES", "Coleção eduCAPES"])
    for item in new_items:
        type_result = item.get("tipo_produto_classificacao") or {}
        value = type_result.get("valor")
        if isinstance(value, dict):
            value = value.get("nome") or value.get("codigo")
        type_evidence = (type_result.get("evidencias") or [{}])[0]
        recent.append([item.get("id"), item.get("ano"), item.get("autor"), item.get("orientador"),
                       item.get("coorientador"), item.get("titulo"), item.get("url_pdf"),
                       item.get("produto_educacional"), item.get("url_produto"),
                       item.get("status_extracao"), item.get("resumo"), item.get("pagina_resumo"),
                       item.get("evidencia_resumo"), item.get("erro"), value, type_result.get("confianca"),
                       item.get("status_tipo_produto"), type_evidence.get("trecho"),
                       "; ".join(item.get("dc_type_educapes", []) or []),
                       "; ".join(item.get("colecoes_educapes", []) or [])])
    style_sheet(recent, "NovasDefesas", {"A": 16, "B": 10, "C": 32, "D": 32, "E": 32, "F": 60, "G": 48, "H": 55, "I": 48, "J": 22, "K": 65, "L": 10, "M": 65, "N": 50, "O": 28, "P": 16, "Q": 28, "R": 70, "S": 30, "T": 30})

    bank = wb.create_sheet("Banco atual")
    bank.append(["ID defesa", "Ano", "Acadêmico", "Orientador", "Coorientador", "Linha", "Macroprojeto", "Base epistemológica", "Nível de aplicação", "Dissertação", "URL dissertação", "Estado extração", "Produto", "URL produto", "Estado produto"])
    dissertations = {item["defesaId"]: item for item in dataset.get("producoes", []) if item.get("tipo") == "dissertacao"}
    products = {item["defesaId"]: item for item in dataset.get("producoes", []) if item.get("tipo") == "produto_educacional"}
    for defense in dataset.get("defesas", []):
        identifier = defense.get("id", "")
        dissertation, product = dissertations.get(identifier, {}), products.get(identifier, {})
        classes = defense.get("classificacoes", {})
        bank.append([identifier, defense.get("ano"), (defense.get("academico") or {}).get("nome"),
                     (defense.get("orientador") or {}).get("nome"), ((defense.get("coorientador") or {}).get("nome")),
                     (defense.get("linhaPesquisa") or {}).get("nome"), (defense.get("macroprojeto") or {}).get("codigo"),
                     (classes.get("baseEpistemologica") or {}).get("valor"), (classes.get("nivelAplicacao") or {}).get("valor"),
                     dissertation.get("titulo"), dissertation.get("url"), dissertation.get("estadoEnriquecimento"),
                     product.get("titulo"), product.get("url"), product.get("estadoEnriquecimento")])
    style_sheet(bank, "BancoAtual", {"A": 16, "B": 10, "C": 35, "D": 35, "E": 35, "F": 50, "G": 15, "H": 34, "I": 30, "J": 60, "K": 50, "L": 18, "M": 55, "N": 50, "O": 18})
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    return queue.max_row - 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--novos", type=Path, help="JSON local com novas entradas da API ProfEPT")
    args = parser.parse_args()
    dataset = json.loads(args.entrada.read_text(encoding="utf-8"))
    new_items = json.loads(args.novos.read_text(encoding="utf-8")) if args.novos and args.novos.exists() else []
    count = generate(dataset, args.saida, new_items)
    print(f"Planilha: {args.saida}; fila: {count}; defesas: {len(dataset.get('defesas', []))}; produções: {len(dataset.get('producoes', []))}; novas: {len(new_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
