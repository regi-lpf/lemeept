import re
import unicodedata
import hashlib
from typing import Any, Dict, List


def limpar_texto(valor: Any, padrao: str = "---") -> str:
    if valor is None:
        return padrao
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    if not texto or texto.lower() in {"nan", "none", "null", "nat", "---"}:
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
    match = re.search(r"(19\d{2}|20\d{2})", texto)
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
    partes_entrada = texto if isinstance(texto, list) else [texto]
    if not partes_entrada:
        return []
    tags = []
    vistos = set()
    for entrada in partes_entrada:
        texto_limpo = limpar_texto(entrada, "")
        for parte in re.split(r"[;,|\n]+", texto_limpo):
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
        raw.get("produto"), raw.get("resumoCurto", raw.get("resumo")), raw.get("base"), raw.get("nivel"),
        raw.get("area"), raw.get("finalidade"), raw.get("publicoAlvo"),
        raw.get("tipoProduto"), raw.get("instituicaoCampus"), raw.get("linhaPesquisa"),
        raw.get("macroprojeto"), raw.get("codigoMacroprojeto"), raw.get("termosLinhaMacro"),
        raw.get("justificativaLinhaMacro"),
        " ".join(dividir_tags(raw.get("palavrasChave") or []))
    ]
    return normalizar_texto(" ".join(str(item or "") for item in campos))


def limitar_texto(texto: Any, limite: int = 280) -> str:
    valor = limpar_texto(texto, "")
    if len(valor) <= limite:
        return valor
    return valor[:limite].rsplit(" ", 1)[0].rstrip(".,;:") + "..."


def normalizar_registro(raw: Dict[str, Any]) -> Dict[str, Any]:
    registro = dict(raw)
    campos_texto = (
        "id", "ano", "autor", "orientador", "titulo", "produto", "linkPdf", "linkProduto",
        "linhaPesquisa", "macroprojeto", "codigoMacroprojeto", "instituicaoCampus", "nivel",
        "base", "area", "finalidade", "publicoAlvo", "tipoProduto", "confiancaLinhaMacro",
        "termosLinhaMacro", "justificativaLinhaMacro", "revisaoManual", "resumo",
    )
    campos_vazios = {"linkPdf", "linkProduto", "resumo"}
    for campo in campos_texto:
        padrao = "" if campo in campos_vazios else "---"
        registro[campo] = limpar_texto(registro.get(campo), padrao)

    registro["ano"] = extrair_ano(registro["ano"])
    registro["orientador"] = limpar_nome_orientador(registro["orientador"])
    registro["orientadorChave"] = normalizar_chave_orientador(registro["orientador"])
    if registro["id"] == "---":
        base_id = "|".join((registro["ano"], registro["autor"], registro["titulo"]))
        registro["id"] = "AUTO-" + hashlib.sha1(base_id.encode("utf-8")).hexdigest()[:12]
    registro["palavrasChave"] = dividir_tags(registro.get("palavrasChave"))
    registro["resumoCurto"] = limitar_texto(registro["resumo"])
    registro["searchText"] = montar_search_text(registro)
    return registro
