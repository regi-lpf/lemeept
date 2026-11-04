from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join("".join(char for char in raw if not unicodedata.combining(char)).casefold().split())


# O código técnico é estável; o nome é a forma de exibição do contrato.
FORMATS: list[tuple[str, str, tuple[str, ...]]] = [
    ("portal", "Portal", (r"\bportal\b",)),
    ("guia_tutorial", "Guia / Tutorial", (r"\baula\s+digital\b", r"\bguia(?:\s+digital)?\b", r"\btutorial\b")),
    ("podcast", "Podcast", (r"\bpodcasts?\b", r"\b[aá]udios?\b")),
    ("video_audiovisual", "Vídeo / audiovisual", (r"\b(?:v[ií]deo|v[ií]deos|anima[cç][aã]o|videoaula)s?\b",)),
    ("ebook", "E-book", (r"\be[ -]?books?\b", r"\blivro\s+digital\b")),
    ("cartilha", "Cartilha", (r"\bcartilhas?\b",)),
    ("historia_em_quadrinhos", "História em quadrinhos", (r"\bhist[oó]ria\s+em\s+quadrinhos\b", r"\bHQs?\b")),
    ("infografico", "Infográfico", (r"\binfogr[aá]ficos?\b",)),
    ("manual", "Manual", (r"\bmanual(?:\s+did[aá]tico)?\b",)),
    ("caderno", "Caderno", (r"\bcadernos?\b",)),
    ("aplicativo_software", "Aplicativo / software", (r"\baplicativo(?:\s+m[oó]vel)?\b", r"\bsoftware\b")),
    ("jogo", "Jogo", (r"\bjogos?\s+(?:educativos?|did[aá]ticos?)\b",)),
]

PRODUCT_TRIGGER = re.compile(
    r"produto\s+educacional|produto\s+t[eé]cnico|produto\s+pedag[oó]gico|"
    r"produto\s+desenvolvido|produto\s+elaborado|formato\s+de|intitulado",
    re.IGNORECASE,
)


def _pdf_candidates(pages: list[tuple[int, str]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for page_number, page_text in pages:
        for code, label, patterns in FORMATS:
            for pattern in patterns:
                for match in re.finditer(pattern, page_text, re.IGNORECASE):
                    start, end = match.span()
                    before = max(0, start - 1500)
                    after = min(len(page_text), end + 500)
                    context = page_text[before:after]
                    triggers = list(PRODUCT_TRIGGER.finditer(context))
                    if not triggers:
                        continue
                    distance = min(abs((before + item.start()) - start) for item in triggers)
                    # In resumos, a explicação do produto pode vir várias frases
                    # depois da primeira menção ao produto educacional.
                    if distance > 1500:
                        continue
                    excerpt = re.sub(r"\s+", " ", page_text[max(0, start - 220):min(len(page_text), end + 280)]).strip()
                    candidates.append({
                        "codigo": code, "nome": label, "pagina": page_number,
                        "trecho": excerpt[:700], "distanciaGatilho": distance,
                    })
    candidates.sort(key=lambda item: (item["distanciaGatilho"], item["pagina"], len(item["trecho"])))
    unique: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        unique.setdefault(candidate["codigo"], candidate)
    return sorted(unique.values(), key=lambda item: (item["distanciaGatilho"], item["pagina"]))


def _metadata_candidates(metadata: dict[str, Any] | None) -> list[dict[str, Any]]:
    metadata = metadata or {}
    dc = metadata.get("campos_dc") or {}
    values: list[tuple[str, str]] = []
    for value in dc.get("dc.type", []) if isinstance(dc, dict) else []:
        values.append((str(value), "dc.type"))
    for value in metadata.get("colecoes", []) or []:
        values.append((str(value), "colecaoEduCAPES"))
    candidates: dict[str, dict[str, Any]] = {}
    for raw, field in values:
        folded = _norm(raw)
        # `livro digital` é amplo; não resolve e-book, cartilha, manual ou guia.
        if "livro digital" in folded or folded in {"livro", "livros digitais"}:
            continue
        for code, label, patterns in FORMATS:
            if any(re.search(pattern, raw, re.IGNORECASE) for pattern in patterns):
                candidates.setdefault(code, {"codigo": code, "nome": label, "campo": field, "rotuloOrigem": raw})
    return list(candidates.values())


def classify_product_type(pages: list[tuple[int, str]], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Preferir formato explicitamente descrito no PDF; metadados amplos apenas sugerem."""
    pdf_candidates = _pdf_candidates(pages)
    meta_candidates = _metadata_candidates(metadata)
    if len(pdf_candidates) == 1:
        chosen = pdf_candidates[0]
        conflicts = [item for item in meta_candidates if item["codigo"] != chosen["codigo"]]
        return {
            "valor": {"codigo": chosen["codigo"], "nome": chosen["nome"]},
            "candidato": None, "confianca": "alta", "revisao": "necessaria" if conflicts else "nao_necessaria",
            "metodo": "extracao_deterministica_pdf", "rotuloOrigem": chosen["nome"],
            "campoOrigem": "PDF / descrição do produto educacional", "evidencias": [{"pagina": chosen["pagina"], "trecho": chosen["trecho"]}],
            "metadadosEduCAPES": metadata or {}, "conflitosMetadados": conflicts,
        }
    if len(pdf_candidates) > 1:
        return {
            "valor": None, "candidato": pdf_candidates, "confianca": "baixa", "revisao": "necessaria",
            "metodo": "extracao_deterministica_pdf_ambigua", "rotuloOrigem": None,
            "campoOrigem": "PDF / descrições do produto", "evidencias": [{"pagina": item["pagina"], "trecho": item["trecho"]} for item in pdf_candidates],
            "metadadosEduCAPES": metadata or {}, "conflitosMetadados": meta_candidates,
        }
    if len(meta_candidates) == 1:
        candidate = meta_candidates[0]
        return {
            "valor": None, "candidato": {"codigo": candidate["codigo"], "nome": candidate["nome"]},
            "confianca": "media", "revisao": "necessaria", "metodo": "metadado_educapes_complementar",
            "rotuloOrigem": candidate["rotuloOrigem"], "campoOrigem": candidate["campo"], "evidencias": [],
            "metadadosEduCAPES": metadata or {}, "conflitosMetadados": [],
        }
    return {
        "valor": None, "candidato": meta_candidates or None, "confianca": "baixa", "revisao": "necessaria",
        "metodo": "sem_evidencia_especifica", "rotuloOrigem": None, "campoOrigem": None,
        "evidencias": [], "metadadosEduCAPES": metadata or {}, "conflitosMetadados": meta_candidates,
    }
