import hashlib
import json
import re
import ssl
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False

from pipeline.models_v4 import (
    ArquivosDefesaV4,
    FonteProfeptV4,
    PreExtracaoItemV4,
    Stage1ManifestV4,
)

WP_API_URL = "https://profept.ifc.edu.br/wp-json/wp/v2/pages?slug=dissertacoes"
HEADERS = {
    "User-Agent": "LEME-EPT-Pipeline/4.0 (Pesquisa Bibliometrica Academica; IFC Blumenau)"
}


def normalizar_chave_busca(texto: str) -> str:
    """Gera chave limpa (sem acentos, minúscula) para cruzar registros existentes."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def limpar_texto(texto: str) -> str:
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def formatar_nome_proprio(nome: str) -> str:
    """Converte 'GEANDRO CHIARELLI' em 'Geandro Chiarelli' mantendo preposições."""
    preposicoes = {"da", "de", "do", "das", "dos", "e"}
    palavras = limpar_texto(nome).lower().split(" ")
    resultado = []
    for i, p in enumerate(palavras):
        if i > 0 and p in preposicoes:
            resultado.append(p)
        else:
            resultado.append(p.capitalize())
    return " ".join(resultado)


def limpar_prefixo_orientador(texto: str) -> str:
    """Remove 'Orientador:', 'Orientadora:', 'Dr.', 'Drª.', 'Prof.' etc."""
    txt = re.sub(r"^orientador[a]?\s*:\s*", "", texto, flags=re.IGNORECASE)
    txt = re.sub(r"^(prof[ªa]?\.?\s*)?(dr[ªa]?\.?\s*)", "", txt, flags=re.IGNORECASE)
    return formatar_nome_proprio(txt)


def carregar_mapeamento_ids_existentes(caminho_legado: Optional[Path]) -> Tuple[Dict[str, str], int]:
    """
    Lê um JSON anterior (v3 ou manifest v4) para manter os mesmos IDs (EPT-XXXX)
    para autores/URLs já catalogados. Retorna (mapa_chave_para_id, maior_numero_id).
    """
    mapa: Dict[str, str] = {}
    max_num = 0

    if not caminho_legado or not caminho_legado.exists():
        return mapa, max_num

    with open(caminho_legado, "r", encoding="utf-8") as f:
        dados = json.load(f)

    lista = dados.get("defesas") or dados.get("registros") or []
    for item in lista:
        cod = item.get("cod") or item.get("id") or ""
        match = re.match(r"^EPT-(\d{4})$", cod)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num

        # Mapeia tanto pela URL do PDF quanto pelo nome do autor
        url = (
            item.get("dissertacao", {}).get("link")
            or item.get("fonte_profept", {}).get("url_dissertacao")
            or ""
        )
        autor = (
            item.get("autor", {}).get("nome")
            if isinstance(item.get("autor"), dict)
            else (item.get("autor") or item.get("fonte_profept", {}).get("autor_bruto") or "")
        )

        if url:
            mapa[url.strip()] = cod
        if autor:
            mapa[normalizar_chave_busca(autor)] = cod

    return mapa, max_num

def extrair_defesas_do_html(html_content: str) -> List[FonteProfeptV4]:
    soup = BeautifulSoup(html_content, "html.parser")
    ano_atual: Optional[int] = None
    fontes: List[FonteProfeptV4] = []

    # Buffer da defesa em leitura sequencial
    atual: Dict[str, Optional[str]] = {}

    def flush_atual():
        nonlocal atual
        if atual.get("autor_raw") and atual.get("url_dis"):
            ano_final = ano_atual
            if not ano_final and atual["url_dis"]:
                m_url = re.search(r"/uploads/(?:sites/\d+/)?(20\d{2})/", atual["url_dis"])
                if m_url:
                    ano_final = int(m_url.group(1))
            if ano_final:
                fontes.append(
                    FonteProfeptV4(
                        titulo_bruto=atual.get("titulo_dis") or "",
                        autor_bruto=atual["autor_raw"],
                        orientador_bruto=atual.get("orientador_raw"),
                        ano=ano_final,
                        campus="IFC Blumenau",
                        url_dissertacao=atual["url_dis"],
                        titulo_produto_bruto=atual.get("titulo_prod"),
                        handle_educapes=atual.get("handle_prod"),
                    )
                )
        atual = {}

    # Percorre cabeçalhos (para ano) e todos os <li> sequencialmente (independe de <ul> quebrada)
    for elem in soup.find_all(["p", "h1", "h2", "h3", "h4", "div", "span", "strong", "li"]):
        if elem.name != "li":
            # Ignora containers que possuem filhos estruturais para não ler o bloco inteiro
            if elem.find(["ul", "li", "p"]):
                continue
            texto_bloco = limpar_texto(elem.get_text())
            match_ano = re.search(r"DEFESAS\s+(20\d{2})", texto_bloco, flags=re.IGNORECASE)
            if match_ano:
                flush_atual()
                ano_atual = int(match_ano.group(1))
            continue

        texto_li = limpar_texto(elem.get_text())
        link_tag = elem.find("a", href=True)

        # 1. Início de nova defesa (Acadêmico / Discente / Autor)
        if re.match(r"^(acad[êe]mic[oa]|discente|autor[a]?)\s*:", texto_li, flags=re.IGNORECASE):
            flush_atual()
            autor_bruto = re.sub(r"^(acad[êe]mic[oa]|discente|autor[a]?)\s*:\s*", "", texto_li, flags=re.IGNORECASE)
            atual["autor_raw"] = formatar_nome_proprio(autor_bruto)

        # 2. Orientador / Orientadora
        elif re.match(r"^orientador[a]?\s*:", texto_li, flags=re.IGNORECASE):
            atual["orientador_raw"] = limpar_prefixo_orientador(texto_li)

        # 3. Dissertação (aceita com ou sem ':', 'intitulada', 'artigo', etc.)
        elif re.match(r"^(disserta[çc][ãa]o|artigo|trabalho)(\s+intitulad[oa])?\s*:?\s*", texto_li, flags=re.IGNORECASE):
            if link_tag:
                atual["url_dis"] = link_tag["href"].strip()
                atual["titulo_dis"] = limpar_texto(link_tag.get_text())
            else:
                atual["titulo_dis"] = limpar_texto(
                    re.sub(r"^(disserta[çc][ãa]o|artigo|trabalho)(\s+intitulad[oa])?\s*:?\s*", "", texto_li, flags=re.IGNORECASE)
                )

        # 4. Produto Educacional (preserva prefixos como 'Podcast – ', 'Texto – ', 'Curso – ')
        elif re.match(r"^produto(\s+educacional)?\s*:?", texto_li, flags=re.IGNORECASE):
            texto_sem_label = re.sub(r"^produto(\s+educacional)?\s*:?\s*", "", texto_li, flags=re.IGNORECASE)
            atual["titulo_prod"] = limpar_texto(texto_sem_label)
            if link_tag:
                atual["handle_prod"] = link_tag["href"].strip()

    flush_atual()
    return fontes


def calcular_sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()

def baixar_pdf_com_validacao(url: str, destino: Path) -> Tuple[str, str]:
    """
    Baixa o PDF se não existir localmente. Valida a assinatura mágica '%PDF'.
    Retorna (sha256, status_download).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and destino.stat().st_size > 1024:
        with open(destino, "rb") as f:
            header = f.read(5)
        if header == b"%PDF-":
            return calcular_sha256(destino), "OK"

    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60, verify=SSL_VERIFY) as resp:
            if resp.status_code != 200:
                print(f"  [ERRO HTTP {resp.status_code}] {url}")
                return "", "ERRO_HTTP"

            with open(destino, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        with open(destino, "rb") as f:
            header = f.read(5)

        if header != b"%PDF-":
            print(f"  [CORROMPIDO] Arquivo baixado não é um PDF válido: {url}")
            destino.unlink(missing_ok=True)
            return "", "CORROMPIDO"

        return calcular_sha256(destino), "OK"

    except requests.RequestException as e:
        print(f"  [FALHA REDE] {url} -> {e}")
        return "", "ERRO_HTTP"


def executar_etapa1(
    caminho_manifesto_saida: Path,
    diretorio_pdfs: Path,
    caminho_referencia_ids: Optional[Path] = None,
):
    print("1. Consultando API do WordPress ProfEPT...")
    resp = requests.get(WP_API_URL, headers=HEADERS, timeout=30, verify=SSL_VERIFY)
    resp.raise_for_status()
    paginas = resp.json()

    if not paginas:
        raise RuntimeError("API do WordPress retornou lista vazia para slug='dissertacoes'.")

    html_bruto = paginas[0].get("content", {}).get("rendered", "")
    fontes = extrair_defesas_do_html(html_bruto)
    print(f"2. Encontradas {len(fontes)} defesas estruturadas na página.")

    mapa_ids, max_id = carregar_mapeamento_ids_existentes(caminho_referencia_ids)
    registros_v4: List[PreExtracaoItemV4] = []

    # Processa em ordem reversa (mais antigas para mais recentes) para manter numeração cronológica
    for fonte in reversed(fontes):
        chave_autor = normalizar_chave_busca(fonte.autor_bruto)
        cod_existente = mapa_ids.get(fonte.url_dissertacao) or mapa_ids.get(chave_autor)

        if cod_existente:
            cod_defesa = cod_existente
        else:
            max_id += 1
            cod_defesa = f"EPT-{max_id:04d}"
            print(f"  [+] Nova defesa descoberta: {cod_defesa} ({fonte.autor_bruto} - {fonte.ano})")

        nome_arquivo = f"{cod_defesa}.pdf"
        caminho_pdf = diretorio_pdfs / nome_arquivo

        sha256, status = baixar_pdf_com_validacao(fonte.url_dissertacao, caminho_pdf)

        registro = PreExtracaoItemV4(
            id=cod_defesa,
            fonte_profept=fonte,
            arquivos=ArquivosDefesaV4(
                pdf_dissertacao_path=str(caminho_pdf.as_posix()),
                sha256_dissertacao=sha256,
                pdf_produto_path=None,
                status_download=status,
            ),
        )
        registros_v4.append(registro)

    # Ordena o manifesto pelo ID canônico (EPT-0001 -> EPT-XXXX)
    registros_v4.sort(key=lambda r: r.id)

    manifesto = Stage1ManifestV4(
        total_registros=len(registros_v4),
        registros=registros_v4,
    )

    caminho_manifesto_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_manifesto_saida, "w", encoding="utf-8") as f:
        f.write(manifesto.model_dump_json(indent=2))

    ok_count = sum(1 for r in registros_v4 if r.arquivos.status_download == "OK")
    print(f"\n--- Etapa 1 Concluída ---")
    print(f"Manifesto gravado em: {caminho_manifesto_saida}")
    print(f"Total catalogado: {len(registros_v4)} | PDFs prontos (OK): {ok_count}")


if __name__ == "__main__":
    executar_etapa1(
        caminho_manifesto_saida=Path("data/stage1_manifest.json"),
        diretorio_pdfs=Path("pdf/dissertacoes"),
        caminho_referencia_ids=Path("painel-ept-v3.json"),  # Preserva os 110 IDs atuais
    )

