from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from .classifier import LINHAS_OFICIAIS_PROFEPT
from .normalizer import normalizar_rotulo_macroprojeto, normalizar_texto


SCHEMA_VERSION = "2.0"


def _value(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if not text or normalizar_texto(text) in {"---", "a revisar", "nao classificado", "nan", "none", "null"}:
        return ""
    return text


def _values(value: Any) -> List[str]:
    values = value if isinstance(value, list) else [value]
    return list(dict.fromkeys(text for item in values if (text := _value(item))))


def _metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    value = raw.get("metadadosEduCAPES") or {}
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else {}
        except json.JSONDecodeError:
            value = {}
    return value if isinstance(value, dict) else {}


def _field_classification(value: Any, confidence: Any, review: bool) -> Dict[str, Any]:
    return {
        "valor": _value(value) or None,
        "metodo": "classificacao_historica",
        "confianca": _value(confidence).casefold() or "baixa",
        "revisao": "necessaria" if review else "nao_necessaria",
        "evidencias": [],
    }


def _search_text(*values: Any) -> str:
    return normalizar_texto(" ".join(text for value in values for text in _values(value)))


def _dc_values(dc: Dict[str, Any], key: str) -> List[str]:
    return _values(dc.get(key, []))


def build_production_dataset(
    records: Iterable[Dict[str, Any]], generated_at: str | None = None,
    extractions: Dict[str, Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    """Split each legacy defense record into one dissertation and one product."""
    defenses: List[Dict[str, Any]] = []
    productions: List[Dict[str, Any]] = []
    seen_defense_ids: set[str] = set()
    extractions = extractions or {}

    for row_number, raw in enumerate(records, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Registro {row_number} não é um objeto.")
        defense_id = _value(raw.get("id"))
        if not defense_id:
            raise ValueError(f"Registro {row_number} não tem ID de defesa.")
        if defense_id in seen_defense_ids:
            raise ValueError(f"ID de defesa duplicado: {defense_id}")
        seen_defense_ids.add(defense_id)

        author = _value(raw.get("autor"))
        advisor = _value(raw.get("orientador"))
        coadvisor = _value(raw.get("coorientador"))
        advisor_key = _value(raw.get("orientadorChave")) or normalizar_texto(advisor)
        coadvisor_key = _value(raw.get("coorientadorChave")) or normalizar_texto(coadvisor)
        code = _value(raw.get("codigoMacroprojeto")).upper()
        official = LINHAS_OFICIAIS_PROFEPT.get(code, {})
        macro_label = normalizar_rotulo_macroprojeto(code, raw.get("macroprojeto"))
        line_label = _value(official.get("linha")) or _value(raw.get("linhaPesquisa")) or None
        macro_name = _value(macro_label) or None
        manual_review = normalizar_texto(raw.get("revisaoManual")) not in {"nao", "nao necessaria", "false", "0"}
        confidence = _value(raw.get("confiancaLinhaMacro")) or "baixa"

        defenses.append({
            "id": defense_id,
            "ano": _value(raw.get("ano")) or None,
            "academico": {"nome": author or None, "chave": normalizar_texto(author)},
            "orientador": {"nome": advisor or None, "chave": advisor_key},
            "coorientador": ({"nome": coadvisor, "chave": coadvisor_key} if coadvisor else None),
            "classificacoes": {
                "baseEpistemologica": _field_classification(raw.get("base"), confidence, manual_review),
                "nivelAplicacao": _field_classification(raw.get("nivel"), confidence, manual_review),
            },
            "linhaPesquisa": {"codigo": ("LP1" if code in {"MP1", "MP2", "MP3"} else "LP2") if code in LINHAS_OFICIAIS_PROFEPT else None, "nome": line_label},
            "macroprojeto": {"codigo": code or None, "nome": macro_name},
            "instituicaoCampus": _value(raw.get("instituicaoCampus")) or None,
            "revisaoManual": "necessaria" if manual_review else "nao_necessaria",
        })

        dc_metadata = _metadata(raw)
        dc = dc_metadata.get("campos_dc", {})
        if not isinstance(dc, dict):
            dc = {}
        product_authors = _dc_values(dc, "dc.contributor.author")
        product_ids = _dc_values(dc, "dc.identifier")
        keywords = list(dict.fromkeys(_values(raw.get("palavrasChave")) + _dc_values(dc, "dc.subject")))
        collections = list(dict.fromkeys(_values(raw.get("colecoesEduCAPES")) + _values(dc_metadata.get("colecoes", []))))
        product_type = _value(raw.get("tipoProduto"))
        type_obj = ({
            "codigo": normalizar_texto(product_type).replace(" ", "_"),
            "nome": product_type,
            "rotuloOrigem": product_type,
            "campoOrigem": "classificacao_historica",
        } if product_type else None)

        extraction = extractions.get(defense_id, {})
        summary = _value(extraction.get("resumo")) or None
        dissertation_keywords = _values(extraction.get("palavrasChave", []))
        evidence = extraction.get("evidenciasCampos", {})
        if not isinstance(evidence, dict):
            evidence = {}
        specs = [
            {
                "suffix": "DIS", "tipo": "dissertacao", "titulo": _value(raw.get("titulo")),
                "url": _value(raw.get("linkPdf")),
                "metadados": {"resumo": summary, "fichaCatalografica": {}, "sumario": [], "introducao": None, "palavrasChave": dissertation_keywords},
                "buscaTexto": _search_text(raw.get("titulo"), raw.get("ano"), author, advisor, line_label, macro_name, raw.get("base"), raw.get("nivel"), summary, dissertation_keywords),
                "estado": "parcial" if summary or dissertation_keywords else "pendente",
                "fontes": [{"url": _value(raw.get("linkPdf")), "tipo": "pdf_dissertacao", "campos": [field for field, value in (("resumo", summary), ("palavrasChave", dissertation_keywords)) if value], "evidencias": evidence}],
                "proveniencia": {"titulo": {"metodo": "metadado_explicito", "fonte": "painel-ept.json"}, "conteudo": {"metodo": "extracao_texto_pdf" if summary or dissertation_keywords else "nao_tentado", "evidencias": evidence}},
            },
            {
                "suffix": "PRO", "tipo": "produto_educacional", "titulo": _value(raw.get("produto")),
                "url": _value(raw.get("linkProduto")),
                "metadados": {
                    "autoresColaboradores": [{"nome": name, "papel": "autor"} for name in product_authors],
                    "identificadores": [{"esquema": "dc.identifier", "valor": value, "url": value if value.startswith(("http://", "https://")) else None} for value in product_ids],
                    "dataPublicacao": (_dc_values(dc, "dc.date.issued") or [None])[0],
                    "colecaoEduCAPES": collections,
                    "tipoProduto": type_obj,
                    "palavrasChave": keywords,
                },
                "buscaTexto": _search_text(raw.get("produto"), product_type, keywords, collections, line_label, macro_name),
                "estado": "parcial" if dc_metadata else "pendente",
                "fontes": [{"url": _value(raw.get("linkProduto")), "tipo": "registro_educapes", "campos": sorted(dc.keys())}],
                "proveniencia": {"titulo": {"metodo": "metadado_explicito", "fonte": "painel-ept.json"}, "metadadosEduCAPES": {"metodo": "metadado_explicito" if dc_metadata else "nao_consultado"}},
            },
        ]
        for item in specs:
            if not item["titulo"] or not item["url"]:
                raise ValueError(f"{defense_id}: {item['tipo']} precisa de título e URL.")
            productions.append({
                "id": f"{defense_id}-{item['suffix']}",
                "defesaId": defense_id,
                "tipo": item["tipo"],
                "titulo": item["titulo"],
                "url": item["url"],
                "metadados": item["metadados"],
                "buscaTexto": item["buscaTexto"],
                "fontes": item["fontes"],
                "proveniencia": item["proveniencia"],
                "estadoEnriquecimento": item["estado"],
            })

    defense_ids = {item["id"] for item in defenses}
    production_ids = [item["id"] for item in productions]
    counts: Dict[str, int] = {defense_id: 0 for defense_id in defense_ids}
    for item in productions:
        if item["defesaId"] not in counts:
            raise ValueError(f"Produção órfã: {item['id']}")
        counts[item["defesaId"]] += 1
    if len(production_ids) != len(set(production_ids)):
        raise ValueError("Há IDs de produção duplicados.")
    if any(count != 2 for count in counts.values()):
        raise ValueError("Cada defesa deve ter exatamente duas produções.")

    return {
        "schemaVersion": SCHEMA_VERSION,
        "geradoEm": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "defesas": defenses,
        "producoes": productions,
    }
