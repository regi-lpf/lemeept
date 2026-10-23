import re
import unicodedata
import hashlib
import json
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


def normalizar_rotulo_macroprojeto(codigo: Any, nome: Any) -> str:
    """Gera um único rótulo público por código, mesmo com alias histórico no nome."""
    codigo_limpo = limpar_texto(codigo, "")
    nome_limpo = limpar_texto(nome, "")
    if not re.fullmatch(r"MP[1-6]", codigo_limpo, flags=re.IGNORECASE):
        return nome_limpo or "---"
    codigo_limpo = codigo_limpo.upper()
    descricao = re.sub(
        rf"^(?:Macroprojeto\s*{codigo_limpo[2:]}|{codigo_limpo})\s*[–—-]\s*",
        "",
        nome_limpo,
        flags=re.IGNORECASE,
    ).strip()
    if not descricao or normalizar_texto(descricao) == normalizar_texto(nome_limpo):
        return nome_limpo or codigo_limpo
    return f"{codigo_limpo} – {descricao}"


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


def _texto_metadados_educapes(valor: Any) -> str:
    if isinstance(valor, str):
        try:
            valor = json.loads(valor) if valor.strip() else {}
        except json.JSONDecodeError:
            return ""
    if not isinstance(valor, dict):
        return ""
    campos_dc = valor.get("campos_dc", {})
    if not isinstance(campos_dc, dict):
        return ""
    chaves_pesquisaveis = (
        "dc.contributor", "dc.contributor.author", "dc.subject", "dc.description.abstract",
        "dc.title", "dc.type", "dc.identifier", "dc.identifier.other", "dc.date.issued",
    )
    partes = []
    for chave in chaves_pesquisaveis:
        conteudos = campos_dc.get(chave, [])
        if not isinstance(conteudos, (list, tuple)):
            conteudos = [conteudos]
        partes.extend(str(item) for item in conteudos if item)
    return " ".join(partes)


def montar_search_text(raw: Dict[str, Any]) -> str:
    campos = [
        raw.get("ano"), raw.get("autor"), raw.get("orientador"), raw.get("coorientador"), raw.get("titulo"),
        raw.get("produto"), raw.get("resumoCompleto") or raw.get("resumo") or raw.get("resumoCurto"),
        " ".join(dividir_tags(raw.get("palavrasChave") or [])), raw.get("introducao"),
        raw.get("sumario"), raw.get("base"), raw.get("nivel"),
        raw.get("area"), raw.get("finalidade"), raw.get("publicoAlvo"),
        raw.get("tipoProduto"), raw.get("instituicaoCampus"), raw.get("linhaPesquisa"),
        raw.get("macroprojeto"), raw.get("codigoMacroprojeto"), raw.get("termosLinhaMacro"),
        raw.get("justificativaLinhaMacro"),
        " ".join(dividir_tags(raw.get("colecoesEduCAPES") or [])),
        _texto_metadados_educapes(raw.get("metadadosEduCAPES")),
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
        "id", "ano", "autor", "orientador", "coorientador", "titulo", "produto", "linkPdf", "linkProduto",
        "linhaPesquisa", "macroprojeto", "codigoMacroprojeto", "instituicaoCampus", "nivel",
        "base", "area", "finalidade", "publicoAlvo", "tipoProduto", "confiancaLinhaMacro",
        "termosLinhaMacro", "justificativaLinhaMacro", "revisaoManual", "resumo",
    )
    campos_vazios = {"linkPdf", "linkProduto", "resumo", "coorientador"}
    for campo in campos_texto:
        padrao = "" if campo in campos_vazios else "---"
        registro[campo] = limpar_texto(registro.get(campo), padrao)

    registro["ano"] = extrair_ano(registro["ano"])
    registro["orientador"] = limpar_nome_orientador(registro["orientador"])
    registro["orientadorChave"] = normalizar_chave_orientador(registro["orientador"])
    registro["coorientador"] = limpar_nome_orientador(registro["coorientador"]) if registro["coorientador"] else ""
    registro["coorientadorChave"] = normalizar_chave_orientador(registro["coorientador"])
    registro["macroprojeto"] = normalizar_rotulo_macroprojeto(
        registro["codigoMacroprojeto"], registro["macroprojeto"]
    )
    if registro["id"] == "---":
        base_id = "|".join((registro["ano"], registro["autor"], registro["titulo"]))
        registro["id"] = "AUTO-" + hashlib.sha1(base_id.encode("utf-8")).hexdigest()[:12]
    registro["palavrasChave"] = dividir_tags(registro.get("palavrasChave"))
    registro["colecoesEduCAPES"] = dividir_tags(registro.get("colecoesEduCAPES"))
    metadados_educapes = registro.get("metadadosEduCAPES")
    if isinstance(metadados_educapes, str):
        try:
            metadados_educapes = json.loads(metadados_educapes) if metadados_educapes.strip() else {}
        except json.JSONDecodeError:
            metadados_educapes = {}
    registro["metadadosEduCAPES"] = metadados_educapes if isinstance(metadados_educapes, dict) else {}
    registro["resumoCompleto"] = registro["resumo"]
    registro["resumoCurto"] = limitar_texto(registro["resumo"])
    registro["searchText"] = montar_search_text(registro)
    return registro

