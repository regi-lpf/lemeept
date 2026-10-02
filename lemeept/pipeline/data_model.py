from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Registro:
    id: str
    ano: str
    autor: str
    orientador: str
    titulo: str
    produto: str
    linhaPesquisa: str
    macroprojeto: str
    codigoMacroprojeto: str
    linkPdf: str
    linkProduto: str
    searchText: str
    instituicaoCampus: Optional[str] = None
    palavrasChave: Optional[List[str]] = None
    resumo: Optional[str] = None
    nivel: Optional[str] = None
    base: Optional[str] = None
    area: Optional[str] = None
    finalidade: Optional[str] = None
    publicoAlvo: Optional[str] = None
    tipoProduto: Optional[str] = None
    confiancaLinhaMacro: Optional[str] = None
    termosLinhaMacro: Optional[str] = None
    justificativaLinhaMacro: Optional[str] = None
    revisaoManual: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "Registro":
        return cls(
            id=str(raw.get("id") or raw.get("titulo") or raw.get("autor") or ""),
            ano=str(raw.get("ano") or "---"),
            autor=str(raw.get("autor") or "---"),
            orientador=str(raw.get("orientador") or "---"),
            titulo=str(raw.get("titulo") or "---"),
            produto=str(raw.get("produto") or "---"),
            linhaPesquisa=str(raw.get("linhaPesquisa") or "---"),
            macroprojeto=str(raw.get("macroprojeto") or "---"),
            codigoMacroprojeto=str(raw.get("codigoMacroprojeto") or "---"),
            linkPdf=str(raw.get("linkPdf") or ""),
            linkProduto=str(raw.get("linkProduto") or ""),
            searchText=str(raw.get("searchText") or ""),
            instituicaoCampus=raw.get("instituicaoCampus"),
            palavrasChave=raw.get("palavrasChave"),
            resumo=raw.get("resumo"),
            nivel=raw.get("nivel"),
            base=raw.get("base"),
            area=raw.get("area"),
            finalidade=raw.get("finalidade"),
            publicoAlvo=raw.get("publicoAlvo"),
            tipoProduto=raw.get("tipoProduto"),
            confiancaLinhaMacro=raw.get("confiancaLinhaMacro"),
            termosLinhaMacro=raw.get("termosLinhaMacro"),
            justificativaLinhaMacro=raw.get("justificativaLinhaMacro"),
            revisaoManual=raw.get("revisaoManual"),
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get("palavrasChave") is None:
            data["palavrasChave"] = []
        return data
