import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import urllib3
from bs4 import BeautifulSoup

from pipeline.extractors.classifiers import (
    classificar_formato_produto_com_fonte,
    classificar_produto_com_fonte,
    extrair_sentenca_produto,
)
from pipeline.models_v4 import EvidenciasEduCAPES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _adicionar_unico(lista: List[str], valor: str) -> None:
    chave = valor.strip().lower()
    if chave and all(item.strip().lower() != chave for item in lista):
        lista.append(valor.strip())


def _adicionar_colaborador_unico(
    lista: List[Dict[str, Optional[str]]],
    nome: str,
    papel: Optional[str],
) -> None:
    chave = (nome.strip().lower(), (papel or "").strip().lower())
    if not chave[0]:
        return
    for item in lista:
        if (item.get("nome", "").strip().lower(), (item.get("papel") or "").strip().lower()) == chave:
            return
    lista.append({"nome": nome.strip(), "papel": papel})


def _adicionar_identificador_unico(
    lista: List[Dict[str, str]],
    esquema: str,
    valor: str,
    url: str = "",
) -> None:
    chave = (esquema.strip().lower(), valor.strip().lower())
    if not chave[1]:
        return
    for item in lista:
        if (item.get("esquema", "").strip().lower(), item.get("valor", "").strip().lower()) == chave:
            return
    lista.append({"esquema": esquema.strip(), "valor": valor.strip(), "url": url})


def _extrair_metadados_html_educapes(html: str, base_url: str) -> Dict[str, Any]:
    titulo_capes: Optional[str] = None
    data_pub: Optional[str] = None
    dc_types: List[str] = []
    keywords: List[str] = []
    autores_colab: List[Dict[str, Optional[str]]] = []
    identificadores: List[Dict[str, str]] = [
        {"esquema": "handle", "valor": base_url.split("handle/")[-1], "url": base_url}
    ]
    colecao: Optional[str] = None

    if not html:
        return {
            "titulo_capes": titulo_capes,
            "data_pub": data_pub,
            "dc_types": dc_types,
            "keywords": keywords,
            "autores_colab": autores_colab,
            "identificadores": identificadores,
            "colecao": colecao,
        }

    soup = BeautifulSoup(html, "html.parser")

    # 1. Tags <meta> Dublin Core no <head> (padrão universal DSpace/eduCAPES)
    for meta in soup.find_all("meta"):
        nome_meta = (meta.get("name") or "").lower().strip()
        conteudo = (meta.get("content") or "").strip()
        if not conteudo:
            continue

        if nome_meta == "dc.title" and not titulo_capes:
            titulo_capes = conteudo
        elif nome_meta in ("dcterms.issued", "dc.date.issued") and not data_pub:
            data_pub = conteudo[:10]
        elif nome_meta == "dc.type":
            _adicionar_unico(dc_types, conteudo)
        elif nome_meta in ("dc.subject", "dcterms.subject"):
            _adicionar_unico(keywords, conteudo)
        elif nome_meta in ("dc.contributor", "dc.creator"):
            papel = meta.get("scheme") or nome_meta.replace("dc.", "")
            _adicionar_colaborador_unico(autores_colab, conteudo, papel)
        elif nome_meta in ("dc.identifier", "dcterms.identifier") and "handle" not in conteudo:
            _adicionar_identificador_unico(identificadores, "identifier", conteudo, "")

    # 2. Tabela Dublin Core do DSpace (?show=full)
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        campo = tds[0].get_text(strip=True).lower()
        valor = tds[1].get_text(" ", strip=True)
        if not valor:
            continue

        if campo == "dc.title" and not titulo_capes:
            titulo_capes = valor
        elif campo == "dc.date.issued" and not data_pub:
            data_pub = valor[:10]
        elif campo == "dc.type":
            _adicionar_unico(dc_types, valor)
        elif campo in ("dc.subject", "dc.subject.other"):
            _adicionar_unico(keywords, valor)
        elif campo.startswith("dc.contributor"):
            papel = campo.replace("dc.contributor.", "") if "." in campo[14:] else "colaborador"
            _adicionar_colaborador_unico(autores_colab, valor, papel)
        elif campo.startswith("dc.identifier.") and campo != "dc.identifier.uri":
            _adicionar_identificador_unico(identificadores, campo.replace("dc.identifier.", ""), valor, "")

    # 3. Coleção ("Aparece nas coleções:")
    for li in soup.select("ul.ds-referenceSet-list li a, .item-page-field-wrapper a[href*='/handle/']"):
        href = li.get("href", "")
        texto_link = li.get_text(strip=True)
        if texto_link and "capes" in href and href not in base_url:
            colecao = texto_link
            break

    return {
        "titulo_capes": titulo_capes,
        "data_pub": data_pub,
        "dc_types": dc_types,
        "keywords": keywords,
        "autores_colab": autores_colab,
        "identificadores": identificadores,
        "colecao": colecao,
    }


def coletar_evidencias_educapes(
    handle_url: Optional[str],
    titulo_produto_bruto: Optional[str],
    resumo_pdf: str,
    descricao_produto_pdf: str,
    cache_dir: Path,
) -> EvidenciasEduCAPES:
    """Coleta metadados do produto educacional no eduCAPES (com cache HTML local) e classifica o tipo."""
    sentenca_resumo = extrair_sentenca_produto(resumo_pdf)
    sentenca_corpo = extrair_sentenca_produto(descricao_produto_pdf)

    if not handle_url:
        tipo_regex, fonte_tipo = classificar_produto_com_fonte(
            titulo_produto_bruto=titulo_produto_bruto,
            sentenca_resumo=sentenca_resumo,
            sentenca_corpo=sentenca_corpo,
            titulo_capes=None,
            dc_types=[],
        )
        formato_regex, fonte_formato = classificar_formato_produto_com_fonte(
            resumo_pdf=resumo_pdf,
            descricao_produto_pdf=descricao_produto_pdf,
            titulo_produto_bruto=titulo_produto_bruto,
            titulo_capes=None,
            dc_types=[],
        )
        return EvidenciasEduCAPES(
            titulo_produto=titulo_produto_bruto,
            titulo_produto_bruto=titulo_produto_bruto,
            tipo_produto_regex=tipo_regex,
            fonte_tipo_regex=fonte_tipo,
            formato_produto_regex=formato_regex,
            fonte_formato_regex=fonte_formato,
        )

    base_url = handle_url.strip().rstrip("/")
    full_url = base_url if "show=full" in base_url else f"{base_url}?show=full"

    slug_cache = re.sub(r"[^a-zA-Z0-9_-]", "_", base_url.split("handle/")[-1])
    cache_file = cache_dir / f"{slug_cache}.html"

    html = ""
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8", errors="ignore")
    else:
        try:
            resp = requests.get(
                full_url,
                timeout=20,
                verify=False,
                headers={"User-Agent": "Mozilla/5.0 (LEME-EPT Bibliometric Pipeline)"},
            )
            if resp.status_code == 200:
                html = resp.text
                cache_file.write_text(html, encoding="utf-8")
                time.sleep(0.6)
        except requests.RequestException as e:
            print(f"  [eduCAPES] Falha ao acessar {full_url}: {e}")

    meta = _extrair_metadados_html_educapes(html, base_url)
    tipo_regex, fonte_tipo = classificar_produto_com_fonte(
        titulo_produto_bruto=titulo_produto_bruto,
        sentenca_resumo=sentenca_resumo,
        sentenca_corpo=sentenca_corpo,
        titulo_capes=meta["titulo_capes"],
        dc_types=meta["dc_types"],
    )
    formato_regex, fonte_formato = classificar_formato_produto_com_fonte(
        resumo_pdf=resumo_pdf,
        descricao_produto_pdf=descricao_produto_pdf,
        titulo_produto_bruto=titulo_produto_bruto,
        titulo_capes=meta["titulo_capes"],
        dc_types=meta["dc_types"],
    )

    return EvidenciasEduCAPES(
        handle_url=base_url,
        titulo_produto=meta["titulo_capes"] or titulo_produto_bruto,
        titulo_produto_bruto=titulo_produto_bruto,
        data_publicacao=meta["data_pub"],
        autores_colaboradores=meta["autores_colab"],
        identificadores=meta["identificadores"],
        colecao_educapes=meta["colecao"],
        dc_type_educapes=meta["dc_types"],
        palavras_chave_educapes=meta["keywords"],
        tipo_produto_regex=tipo_regex,
        fonte_tipo_regex=fonte_tipo,
        formato_produto_regex=formato_regex,
        fonte_formato_regex=fonte_formato,
    )
