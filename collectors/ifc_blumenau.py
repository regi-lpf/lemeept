import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import requests
import urllib3
from bs4 import BeautifulSoup

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from lemeept_extractor.config import aplicar_config  # noqa: E402
from lemeept_extractor.io_utils import (  # noqa: E402
    DEFAULT_REF_IDS,
    baixar_pdf_com_validacao,
    calcular_sha256,
    carregar_mapeamento_ids_existentes,
)
from lemeept_extractor.models import (  # noqa: E402
    ArquivosDefesaV4,
    FonteProfeptV4,
    PreExtracaoItemV4,
    Stage1ManifestV4,
)
from lemeept_extractor.normalizers import (  # noqa: E402
    formatar_nome_proprio,
    limpar_prefixo_orientador,
    limpar_texto,
    normalizar_chave_busca,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
SSL_VERIFY = False

__all__ = [
    "DEFAULT_REF_IDS",
    "HEADERS",
    "SSL_VERIFY",
    "WP_API_URL",
    "baixar_pdf_com_validacao",
    "calcular_sha256",
    "carregar_mapeamento_ids_existentes",
    "executar_etapa1",
    "extrair_defesas_do_html",
    "main",
]

WP_API_URL = "https://profept.ifc.edu.br/wp-json/wp/v2/pages?slug=dissertacoes"
HEADERS = {
    "User-Agent": "LEME-EPT-Pipeline/4.0 (Pesquisa Bibliometrica Academica; IFC Blumenau)"
}

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
                        instituicao="Instituto Federal Catarinense (IFC)",
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


def executar_etapa1(
    caminho_manifesto_saida: Path = Path("data/stage1_manifest.json"),
    diretorio_pdfs: Path = Path("pdf/dissertacoes"),
    caminho_referencia_ids: Union[Optional[Path], Sequence[Path]] = DEFAULT_REF_IDS,
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
        cod_existente = mapa_ids.get(fonte.url_dissertacao.strip()) or mapa_ids.get(chave_autor)

        if cod_existente:
            cod_defesa = cod_existente
        else:
            max_id += 1
            cod_defesa = f"EPT-{max_id:04d}"
            print(f"  [+] Nova defesa descoberta: {cod_defesa} ({fonte.autor_bruto} - {fonte.ano})")

        nome_arquivo = f"{cod_defesa}.pdf"
        caminho_pdf = diretorio_pdfs / nome_arquivo

        sha256, status = baixar_pdf_com_validacao(
            fonte.url_dissertacao,
            caminho_pdf,
            headers=HEADERS,
            ssl_verify=SSL_VERIFY,
        )

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
    print("\n--- Etapa 1 Concluída ---")
    print(f"Manifesto gravado em: {caminho_manifesto_saida}")
    print(f"Total catalogado: {len(registros_v4)} | PDFs prontos (OK): {ok_count}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 1: Coleta ProfEPT e download de PDFs.")
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("data/stage1_manifest.json"),
        help="Caminho do manifesto JSON de saída.",
    )
    parser.add_argument(
        "--pdfs-dir",
        type=Path,
        default=Path("pdf/dissertacoes"),
        help="Diretório de destino dos PDFs baixados.",
    )
    parser.add_argument(
        "--ref-ids",
        type=Path,
        action="append",
        dest="ref_ids",
        default=None,
        help="Arquivo(s) de referência para preservação de IDs (pode repetir).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Arquivo de configuração TOML da instância (padrão: ./lemeept.toml se existir).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    aplicar_config(config_path=args.config)
    executar_etapa1(
        caminho_manifesto_saida=args.saida,
        diretorio_pdfs=args.pdfs_dir,
        caminho_referencia_ids=args.ref_ids if args.ref_ids is not None else DEFAULT_REF_IDS,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

