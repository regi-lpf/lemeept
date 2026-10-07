from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


def _tem_valor(valor: Any) -> bool:
    texto = str(valor or "").strip()
    return bool(texto and texto.casefold() not in {
        "---", "a revisar", "não classificado", "nao classificado", "nan", "none", "null"
    })


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
    quantidadeProducoes: int = 0
    instituicaoCampus: str = "---"
    orientadorChave: str = ""
    palavrasChave: List[str] = field(default_factory=list)
    resumo: str = ""
    nivel: str = "---"
    base: str = "---"
    area: str = "---"
    finalidade: str = "---"
    publicoAlvo: str = "---"
    tipoProduto: str = "---"
    confiancaLinhaMacro: str = "Baixa"
    termosLinhaMacro: str = "---"
    justificativaLinhaMacro: str = ""
    revisaoManual: str = "Sim"

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "Registro":
        tem_dissertacao = _tem_valor(raw.get("titulo"))
        tem_produto = _tem_valor(raw.get("produto")) or _tem_valor(raw.get("linkProduto"))
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
            quantidadeProducoes=int(tem_dissertacao) + int(tem_produto),
            searchText=str(raw.get("searchText") or ""),
            instituicaoCampus=str(raw.get("instituicaoCampus") or "---"),
            orientadorChave=str(raw.get("orientadorChave") or ""),
            palavrasChave=list(raw.get("palavrasChave") or []),
            resumo=str(raw.get("resumoCurto") or raw.get("resumo") or ""),
            nivel=str(raw.get("nivel") or "---"),
            base=str(raw.get("base") or "---"),
            area=str(raw.get("area") or "---"),
            finalidade=str(raw.get("finalidade") or "---"),
            publicoAlvo=str(raw.get("publicoAlvo") or "---"),
            tipoProduto=str(raw.get("tipoProduto") or "---"),
            confiancaLinhaMacro=str(raw.get("confiancaLinhaMacro") or "Baixa"),
            termosLinhaMacro=str(raw.get("termosLinhaMacro") or "---"),
            justificativaLinhaMacro=str(raw.get("justificativaLinhaMacro") or ""),
            revisaoManual=str(raw.get("revisaoManual") or "Sim"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
