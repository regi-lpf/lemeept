"""Importa decisões explícitas da planilha de revisão para o JSON v2."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "lemeept" / "painel-ept-v2.json"
DEFAULT_WORKBOOK = ROOT / "dados" / "revisao" / "revisao_classificacao_6_v4.xlsx"
DEFAULT_BASE_PROPOSALS = ROOT / "dados" / "revisao" / "classificacao_assistida_6_v4.json"
DEFAULT_PRODUCT_PROPOSALS = ROOT / "dados" / "revisao" / "classificacao_produtos_5_v1.json"
DEFAULT_MATERIALISTIC = ROOT / "dados" / "revisao" / "classificacao_assistida_6_v3.json"
TYPE_LABELS = {
    "portal": "Portal", "guia_tutorial": "Guia / Tutorial", "podcast": "Podcast",
    "video_audiovisual": "Vídeo / audiovisual", "ebook": "E-book", "cartilha": "Cartilha",
    "historia_em_quadrinhos": "História em quadrinhos", "infografico": "Infográfico",
    "manual": "Manual", "caderno": "Caderno", "aplicativo_software": "Aplicativo / software",
    "jogo": "Jogo",
}


def read_table(path: Path, sheet_name: str) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"A aba obrigatória '{sheet_name}' não existe em {path}.")
    sheet = workbook[sheet_name]
    headers = [str(value or "").strip() for value in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))]
    rows = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if not values or not values[0]:
            continue
        rows.append({headers[index]: values[index] for index in range(min(len(headers), len(values)))} )
    workbook.close()
    return rows


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--planilha", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--propostas-base", type=Path, default=DEFAULT_BASE_PROPOSALS)
    parser.add_argument("--propostas-produto", type=Path, default=DEFAULT_PRODUCT_PROPOSALS)
    parser.add_argument("--materialismo", type=Path, default=DEFAULT_MATERIALISTIC)
    parser.add_argument("--saida", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--dry-run", action="store_true", help="relata as mudanças sem gravar o JSON")
    args = parser.parse_args()

    dataset = json.loads(args.entrada.read_text(encoding="utf-8"))
    base_proposals = json.loads(args.propostas_base.read_text(encoding="utf-8"))
    product_proposals = json.loads(args.propostas_produto.read_text(encoding="utf-8"))
    base_by_id = {item["id"]: item["baseEpistemologica"] for item in base_proposals.get("trabalhos", [])}
    product_by_id = {item["id"]: item["tipoProduto"] for item in product_proposals.get("produtos", [])}
    defenses = {item["id"]: item for item in dataset.get("defesas", [])}
    productions = {item["id"]: item for item in dataset.get("producoes", [])}
    changes: list[str] = []

    for row in read_table(args.planilha, "Base epistemológica"):
        identifier = str(row.get("ID defesa") or "").strip()
        decision = str(row.get("Decisão humana / correção") or "").strip()
        if not decision:
            continue
        proposal = base_by_id.get(identifier)
        defense = defenses.get(identifier)
        if not proposal or not defense:
            raise ValueError(f"Decisão de base sem proposta/defesa correspondente: {identifier}")
        classification = defense.setdefault("classificacoes", {}).setdefault("baseEpistemologica", {})
        old_value = classification.get("valor")
        manual_empty = bool(re.search(r"manter\s+sem\s+valor|sem\s+valor\s+confirmado|revis[aã]o\s+manual", decision, re.I))
        if manual_empty:
            classification.update({
                "valor": None,
                "candidato": proposal.get("candidato"),
                "metodo": "classificacao_assistida_GPT",
                "confianca": proposal.get("confianca", "baixa"),
                "revisao": "necessaria",
                "estadoRevisao": "manual_posterior",
                "justificativa": proposal.get("justificativa"),
                "evidencias": proposal.get("evidencias", []),
                "decisaoHumana": decision,
                "valorAnterior": old_value,
            })
        else:
            classification.update({
                "valor": decision,
                "metodo": "revisao_humana",
                "confianca": "alta",
                "revisao": "nao_necessaria",
                "estadoRevisao": "decidido_humanamente",
                "evidencias": proposal.get("evidencias", []),
                "decisaoHumana": decision,
                "valorAnterior": old_value,
            })
        defense["revisaoManual"] = "necessaria" if manual_empty else defense.get("revisaoManual", "nao_necessaria")
        changes.append(f"{identifier}: base {'mantida pendente' if manual_empty else 'decisão humana aplicada'}")

    # A classificação do EPT-0007 já foi aceita como de alta confiança na rodada anterior.
    materialistic = json.loads(args.materialismo.read_text(encoding="utf-8"))
    item_0007 = next((item for item in materialistic.get("trabalhos", []) if item.get("id") == "EPT-0007"), None)
    if item_0007 and item_0007.get("recomendacao") == "adotar_valor_de_trabalho" and "EPT-0007" in defenses:
        value = item_0007["baseEpistemologica"].get("valor")
        evidence = item_0007["baseEpistemologica"].get("evidenciaComplementar", {})
        defenses["EPT-0007"].setdefault("classificacoes", {})["baseEpistemologica"] = {
            "valor": value, "metodo": "classificacao_assistida_com_corroboraçao_bibliografica",
            "confianca": "alta", "revisao": "nao_necessaria", "estadoRevisao": "aceito_como_valor_de_trabalho",
            "evidencias": [{"pagina": evidence.get("paginaPDF"), "trecho": evidence.get("trecho"), "secao": "referencial teórico"}],
            "evidenciasBibliograficas": item_0007["baseEpistemologica"].get("evidenciasBibliograficas", []),
            "justificativa": item_0007.get("justificativa"),
        }
        changes.append("EPT-0007: base de alta confiança aplicada")

    for row in read_table(args.planilha, "Tipo de produto"):
        production_id = str(row.get("ID produção") or "").strip()
        decision = str(row.get("Decisão humana / correção") or "").strip()
        if not decision:
            continue
        proposal = product_by_id.get(production_id)
        production = productions.get(production_id)
        if not proposal or not production:
            raise ValueError(f"Decisão de produto sem proposta/produção correspondente: {production_id}")
        if "confirm" not in decision.casefold():
            raise ValueError(f"Correção manual de tipo ainda não normalizada; revisar {production_id}: {decision}")
        code = str(row.get("Tipo canônico proposto") or proposal.get("valor") or "").strip()
        if not code:
            raise ValueError(f"Tipo canônico vazio para {production_id}")
        if code not in TYPE_LABELS:
            raise ValueError(f"Tipo canônico fora do vocabulário para {production_id}: {code}")
        previous_type = copy.deepcopy((production.get("metadados") or {}).get("tipoProduto"))
        metadata = production.setdefault("metadados", {})
        metadata["tipoProduto"] = {
            "codigo": code,
            "nome": TYPE_LABELS[code],
            "rotuloOrigem": str(row.get("Rótulo declarado") or proposal.get("rotuloDeclarado") or code),
            "campoOrigem": str(row.get("Fonte/localizador") or proposal.get("campoOrigem") or "PDF"),
            "metodo": "revisao_humana_confirmada",
            "confianca": "alta",
            "revisao": "nao_necessaria",
            "evidencias": proposal.get("evidencias", []),
        }
        metadata["dcTypeEduCAPES"] = proposal.get("dcType", [])
        collections = proposal.get("colecaoEduCAPES", [])
        if collections:
            metadata["colecaoEduCAPES"] = list(dict.fromkeys((metadata.get("colecaoEduCAPES") or []) + collections))
        source = (production.get("fontes") or [{}])[0]
        fields = set(source.get("campos", []))
        if proposal.get("dcType"):
            fields.add("dc.type")
        if collections:
            fields.add("colecaoEduCAPES")
        fields.add("tipoProduto")
        source["campos"] = sorted(fields)
        source.setdefault("evidencias", {})["tipoProduto"] = proposal.get("evidencias", [])
        source["evidencias"]["metadadosTipoProduto"] = [{"dcType": proposal.get("dcType", []), "colecaoEduCAPES": collections}]
        provenance = production.setdefault("proveniencia", {})
        provenance["tipoProduto"] = {
            "metodo": "revisao_humana_confirmada", "confianca": "alta", "revisao": "nao_necessaria",
            "evidencias": proposal.get("evidencias", []), "valorAnterior": previous_type,
            "conflitoMetadadosPreservado": proposal.get("conflito", False), "decisaoHumana": decision,
        }
        search = str(production.get("buscaTexto") or "")
        from lemeept.pipeline.normalizer import normalizar_texto
        for term in [metadata["tipoProduto"]["nome"], code]:
            normalized = normalizar_texto(term)
            if normalized and normalized not in search:
                search = f"{search} {normalized}".strip()
        production["buscaTexto"] = search
        changes.append(f"{production_id}: {metadata['tipoProduto']['nome']} confirmado")

    if not changes:
        print("Nenhuma decisão explícita para importar.")
        return 0
    if not args.dry_run:
        atomic_write(args.saida, dataset)
    print("\n".join(changes))
    print(f"Total: {len(changes)}; saída: {args.saida}{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
