import re
import unicodedata
from typing import Any, Dict, Iterable, List


def limpar_texto(valor: Any, padrao: str = "---") -> str:
    if valor is None:
        return padrao
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "null", "---"}:
        return padrao
    return texto


def normalizar_texto(texto: Any) -> str:
    texto = limpar_texto(texto, "")
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def extrair_ano(valor: Any) -> str:
    texto = limpar_texto(valor, "")
    match = re.search(r"(20\d{2})", texto)
    return match.group(1) if match else "---"


def limpar_nome_orientador(valor: Any) -> str:
    nome = limpar_texto(valor, "")
    if not nome:
        return "---"
    nome = re.sub(r"[:;]+", "", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome


def normalizar_chave_orientador(valor: Any) -> str:
    nome = limpar_nome_orientador(valor)
    if nome == "---":
        return ""
    nome = nome.lower()
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    nome = re.sub(r"\bdr[aª]?\b\.?\s?", "", nome, flags=re.IGNORECASE)
    nome = re.sub(r"\bprof[aª]?\b\.?\s?", "", nome, flags=re.IGNORECASE)
    nome = re.sub(r"[^a-z0-9\s]", " ", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome


def dividir_tags(texto: Any) -> List[str]:
    texto = limpar_texto(texto, "")
    if not texto:
        return []
    partes = re.split(r"[;,|\n]+", texto)
    tags = []
    vistos = set()
    for parte in partes:
        tag = re.sub(r"\s+", " ", parte).strip(" .;,-")
        if not tag or tag == "---":
            continue
        chave = normalizar_texto(tag)
        if chave not in vistos:
            vistos.add(chave)
            tags.append(tag)
    return tags


def montar_search_text(raw: Dict[str, Any]) -> str:
    campos = [
        raw.get("ano"), raw.get("autor"), raw.get("orientador"), raw.get("titulo"),
        raw.get("produto"), raw.get("resumo"), raw.get("base"), raw.get("nivel"),
        raw.get("area"), raw.get("finalidade"), raw.get("publicoAlvo"),
        raw.get("tipoProduto"), raw.get("instituicaoCampus"), raw.get("linhaPesquisa"),
        raw.get("macroprojeto"), raw.get("codigoMacroprojeto"), raw.get("termosLinhaMacro"),
        raw.get("justificativaLinhaMacro"),
        " ".join(raw.get("palavrasChave") or [])
    ]
    return " ".join(str(item or "") for item in campos)
