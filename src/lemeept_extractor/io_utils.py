import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Literal, Optional, Sequence, Tuple, Union

import requests
import urllib3

from lemeept_extractor.normalizers import normalizar_chave_busca

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "lemeept-extractor/0.4.0b0 (Pesquisa Bibliometrica Academica)"
}

DEFAULT_REF_IDS: Tuple[Path, ...] = (
    Path("data/stage1_manifest.json"),
    Path("public/painel-ept-v4.json"),
    Path("painel-ept-v3.json"),
)

_ID_PATTERN = re.compile(r"^EPT-(\d{4})$")


def calcular_sha256(caminho: Path) -> str:
    """Calcula o digest SHA-256 de um arquivo em streaming."""
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def validar_cabecalho_pdf(caminho: Path, tamanho_minimo: int = 5) -> bool:
    """Verifica se o caminho existe, é arquivo regular, atende ao tamanho mínimo e inicia com %PDF-."""
    if not caminho.exists() or not caminho.is_file():
        return False
    if caminho.stat().st_size < tamanho_minimo:
        return False
    try:
        with open(caminho, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def baixar_pdf_com_validacao(
    url: str,
    destino: Path,
    *,
    headers: Optional[Dict[str, str]] = None,
    ssl_verify: bool = False,
) -> Tuple[str, Literal["OK", "ERRO_HTTP", "CORROMPIDO"]]:
    """
    Baixa o PDF se não existir localmente. Valida a assinatura mágica '%PDF-'.
    Retorna (sha256, status_download).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)

    if validar_cabecalho_pdf(destino, tamanho_minimo=1025):
        return calcular_sha256(destino), "OK"

    try:
        with requests.get(
            url,
            headers=headers or DEFAULT_HEADERS,
            stream=True,
            timeout=60,
            verify=ssl_verify,
        ) as resp:
            if resp.status_code != 200:
                print(f"  [ERRO HTTP {resp.status_code}] {url}")
                return "", "ERRO_HTTP"

            with open(destino, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        if not validar_cabecalho_pdf(destino, tamanho_minimo=5):
            print(f"  [CORROMPIDO] Arquivo baixado não é um PDF válido: {url}")
            destino.unlink(missing_ok=True)
            return "", "CORROMPIDO"

        return calcular_sha256(destino), "OK"

    except requests.RequestException as e:
        print(f"  [FALHA REDE] {url} -> {e}")
        return "", "ERRO_HTTP"


def validar_ou_copiar_pdf_local(
    origem: Path,
    destino: Optional[Path] = None,
) -> Tuple[str, Literal["OK", "CORROMPIDO"], Path]:
    """
    Valida um arquivo PDF local (%PDF-) e opcionalmente copia para `destino`.
    Retorna (sha256, status_download, caminho_final).
    """
    alvo_retorno = destino if destino is not None else origem
    if not validar_cabecalho_pdf(origem, tamanho_minimo=5):
        return "", "CORROMPIDO", alvo_retorno

    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if origem.resolve() != destino.resolve():
            shutil.copy2(origem, destino)
        alvo = destino
    else:
        alvo = origem

    return calcular_sha256(alvo), "OK", alvo


def carregar_mapeamento_ids_existentes(
    caminho_legado: Union[Optional[Path], Sequence[Path]],
) -> Tuple[Dict[str, str], int]:
    """
    Lê JSONs anteriores (manifesto v4, dist v4 ou legado v3) em ordem de prioridade
    para preservar os mesmos IDs (EPT-XXXX) de autores/URLs/arquivos já catalogados.
    Retorna (mapa_chave_para_id, maior_numero_id).
    """
    mapa: Dict[str, str] = {}
    max_num = 0

    if caminho_legado is None:
        return mapa, max_num

    caminhos = [caminho_legado] if isinstance(caminho_legado, Path) else list(caminho_legado)

    for caminho in caminhos:
        if not caminho or not caminho.exists():
            continue

        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)

        lista = dados.get("defesas") or dados.get("registros") or []
        for item in lista:
            cod = item.get("cod") or item.get("id") or ""
            match = _ID_PATTERN.match(cod)
            if not match:
                continue

            num = int(match.group(1))
            if num > max_num:
                max_num = num

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
            pdf_path = item.get("arquivos", {}).get("pdf_dissertacao_path") or ""

            if url:
                mapa.setdefault(url.strip(), cod)
            if autor:
                mapa.setdefault(normalizar_chave_busca(autor), cod)
            if pdf_path:
                mapa.setdefault(pdf_path.strip(), cod)
                mapa.setdefault(Path(pdf_path).name, cod)

    return mapa, max_num


def resolver_id_estavel(
    mapa_ids: Dict[str, str],
    max_id: int,
    *,
    id_explicito: Optional[str] = None,
    url: str = "",
    autor: str = "",
    chave_arquivo: str = "",
) -> Tuple[str, int, bool]:
    """
    Resolve ou gera um identificador estável EPT-XXXX.
    Retorna (id_resolvido, novo_max_id, eh_novo).
    """
    if id_explicito:
        id_norm = id_explicito.strip().upper()
        match = _ID_PATTERN.match(id_norm)
        if match:
            return id_norm, max(max_id, int(match.group(1))), False

    chaves_busca = [
        url.strip() if url else "",
        chave_arquivo.strip() if chave_arquivo else "",
        Path(chave_arquivo).name if chave_arquivo else "",
        normalizar_chave_busca(autor) if autor else "",
    ]
    for chave in chaves_busca:
        if chave and chave in mapa_ids:
            return mapa_ids[chave], max_id, False

    novo_max = max_id + 1
    return f"EPT-{novo_max:04d}", novo_max, True
