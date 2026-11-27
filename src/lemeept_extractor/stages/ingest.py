import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Set, Tuple, Union

import pymupdf

from lemeept_extractor.config import LemeConfig, aplicar_config
from lemeept_extractor.extractors import (
    extrair_capa_e_ficha,
    extrair_metadados_preliminares_pdf,
)
from lemeept_extractor.io_utils import (
    DEFAULT_REF_IDS,
    baixar_pdf_com_validacao,
    carregar_mapeamento_ids_existentes,
    escrever_texto_atomico,
    resolver_id_estavel,
    validar_cabecalho_pdf,
    validar_ou_copiar_pdf_local,
)
from lemeept_extractor.models import (
    ArquivosDefesaV4,
    FonteProfeptV4,
    PreExtracaoItemV4,
    Stage1ManifestV4,
)
from lemeept_extractor.normalizers import (
    formatar_nome_proprio,
    limpar_prefixo_orientador,
    limpar_texto,
    normalizar_espacos,
    remover_acentos,
)

_COLUNAS_ALIASES: Dict[str, str] = {
    "id": "id",
    "cod": "id",
    "codigo": "id",
    "titulo": "titulo",
    "titulo_dissertacao": "titulo",
    "titulo_bruto": "titulo",
    "dissertacao": "titulo",
    "autor": "autor",
    "autor_bruto": "autor",
    "discente": "autor",
    "academico": "autor",
    "academica": "autor",
    "orientador": "orientador",
    "orientador_bruto": "orientador",
    "ano": "ano",
    "ano_defesa": "ano",
    "pdf": "pdf",
    "arquivo_pdf": "pdf",
    "caminho_pdf": "pdf",
    "pdf_path": "pdf",
    "url_pdf": "pdf",
    "link_pdf": "pdf",
    "url_dissertacao": "url_dissertacao",
    "link_dissertacao": "url_dissertacao",
    "url": "url_dissertacao",
    "instituicao": "instituicao",
    "campus": "campus",
    "titulo_produto": "titulo_produto",
    "titulo_produto_bruto": "titulo_produto",
    "produto": "titulo_produto",
    "handle_educapes": "handle_educapes",
    "url_produto": "handle_educapes",
    "link_produto": "handle_educapes",
    "sem_produto": "sem_produto",
    "somente_dissertacao": "sem_produto",
}

_ID_STEM_RE = re.compile(r"^(EPT-\d{4})$", flags=re.IGNORECASE)


def _normalizar_cabecalho_csv(nome: str) -> str:
    chave = remover_acentos(nome or "").strip().lower()
    chave = re.sub(r"[\s\-/]+", "_", chave)
    chave = re.sub(r"_+", "_", chave).strip("_")
    return _COLUNAS_ALIASES.get(chave, chave)


def _detectar_delimitador(amostra: str) -> str:
    primeira_linha = amostra.splitlines()[0] if amostra else ""
    if primeira_linha.count(";") > primeira_linha.count(","):
        return ";"
    if primeira_linha.count(",") > 0:
        return ","
    try:
        dialect = csv.Sniffer().sniff(amostra, delimiters=";,\t")
        return dialect.delimiter
    except csv.Error:
        return ";" if ";" in amostra else ","


def _parse_bool_csv(valor: Optional[str]) -> bool:
    return (valor or "").strip().lower() in ("1", "true", "sim", "s", "yes", "y")


def _eh_url_http(valor: str) -> bool:
    return valor.strip().lower().startswith(("http://", "https://"))


def _ler_primeiras_paginas_pdf(pdf_path: Path, max_paginas: int = 8) -> List[Tuple[int, str]]:
    paginas: List[Tuple[int, str]] = []
    with pymupdf.open(pdf_path) as doc:
        limite = min(len(doc), max_paginas)
        for idx in range(limite):
            txt = doc[idx].get_text("text") or ""
            paginas.append((idx + 1, normalizar_espacos(txt)))
    return paginas


def _gravar_manifesto(
    registros: List[PreExtracaoItemV4],
    caminho_manifesto_saida: Path,
) -> Stage1ManifestV4:
    registros.sort(key=lambda r: r.id)
    manifesto = Stage1ManifestV4(
        total_registros=len(registros),
        registros=registros,
    )
    escrever_texto_atomico(caminho_manifesto_saida, manifesto.model_dump_json(indent=2))
    return manifesto


def _normalizar_linha_csv(
    linha_bruta: Dict[str, Optional[str]],
    mapa_colunas: Dict[str, str],
) -> Dict[str, str]:
    linha: Dict[str, str] = {}
    for orig, norm in mapa_colunas.items():
        val = (linha_bruta.get(orig) or "").strip()
        if val and not linha.get(norm):
            linha[norm] = val
    return linha


def _parse_ano_csv(valor: str) -> int:
    texto = (valor or "").strip()
    return int(texto) if texto.isdigit() else 0


def _resolver_pdf_csv(
    fonte_pdf: str,
    csv_dir: Path,
    destino_pdf: Path,
    copiar_pdfs: bool,
) -> Tuple[str, Literal["OK", "ERRO_HTTP", "CORROMPIDO"], Path]:
    if not fonte_pdf:
        return "", "CORROMPIDO", destino_pdf
    if _eh_url_http(fonte_pdf):
        sha256, status = baixar_pdf_com_validacao(fonte_pdf, destino_pdf)
        return sha256, status, destino_pdf

    origem_local = Path(fonte_pdf)
    if not origem_local.is_absolute() and not origem_local.exists():
        cand_rel = csv_dir / origem_local
        if cand_rel.exists():
            origem_local = cand_rel
    return validar_ou_copiar_pdf_local(
        origem_local,
        destino=destino_pdf if copiar_pdfs else None,
    )


def _extrair_preliminares_pdf_local(pdf_path: Path) -> Dict[str, object]:
    if not validar_cabecalho_pdf(pdf_path, tamanho_minimo=5):
        return {}
    try:
        paginas = _ler_primeiras_paginas_pdf(pdf_path, max_paginas=8)
        capa, ficha = extrair_capa_e_ficha(paginas)
        return extrair_metadados_preliminares_pdf(capa, ficha, pdf_path.stem)
    except Exception:
        return {}


def ingerir_de_csv(
    csv_path: Path,
    caminho_manifesto_saida: Path = Path("data/stage1_manifest.json"),
    diretorio_pdfs: Path = Path("pdf/dissertacoes"),
    caminho_referencia_ids: Union[Optional[Path], Sequence[Path]] = DEFAULT_REF_IDS,
    instituicao_padrao: Optional[str] = None,
    campus_padrao: str = "",
    somente_dissertacoes: bool = False,
    copiar_pdfs: bool = True,
    config: Optional[LemeConfig] = None,
) -> Stage1ManifestV4:
    """Gera Stage1ManifestV4 a partir de um arquivo CSV com links HTTP ou caminhos locais de PDFs."""
    if config is not None:
        aplicar_config(config)
        instituicao_padrao = instituicao_padrao or (config.instituicao.nome or None)
        campus_padrao = campus_padrao or config.instituicao.campus
        somente_dissertacoes = somente_dissertacoes or config.instituicao.somente_dissertacoes
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")

    conteudo = csv_path.read_text(encoding="utf-8-sig")
    if not conteudo.strip():
        raise ValueError(f"Arquivo CSV vazio: {csv_path}")

    delimitador = _detectar_delimitador(conteudo[:4096])
    mapa_ids, max_id = carregar_mapeamento_ids_existentes(caminho_referencia_ids)
    ids_usados: Set[str] = set()

    registros: List[PreExtracaoItemV4] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimitador)
        if not reader.fieldnames:
            raise ValueError(f"Cabeçalho ausente no CSV: {csv_path}")

        mapa_colunas = {col: _normalizar_cabecalho_csv(col) for col in reader.fieldnames}
        for linha_bruta in reader:
            linha = _normalizar_linha_csv(linha_bruta, mapa_colunas)
            if not any(linha.values()):
                continue

            autor_bruto = formatar_nome_proprio(linha["autor"]) if linha.get("autor") else ""
            orientador_bruto = (
                limpar_prefixo_orientador(linha["orientador"]) if linha.get("orientador") else None
            )
            fonte_pdf = linha.get("pdf", "") or linha.get("url_dissertacao", "")
            url_dissertacao = linha.get("url_dissertacao", "")
            if not url_dissertacao and _eh_url_http(fonte_pdf):
                url_dissertacao = fonte_pdf

            cod_defesa, max_id, _ = resolver_id_estavel(
                mapa_ids,
                max_id,
                id_explicito=linha.get("id") or None,
                url=url_dissertacao or fonte_pdf,
                autor=autor_bruto,
                chave_arquivo="" if _eh_url_http(fonte_pdf) else fonte_pdf,
                ids_usados=ids_usados,
            )

            sha256, status, caminho_final = _resolver_pdf_csv(
                fonte_pdf,
                csv_path.parent,
                diretorio_pdfs / f"{cod_defesa}.pdf",
                copiar_pdfs,
            )

            registros.append(
                PreExtracaoItemV4(
                    id=cod_defesa,
                    fonte_profept=FonteProfeptV4(
                        titulo_bruto=limpar_texto(linha.get("titulo", "")),
                        autor_bruto=autor_bruto,
                        orientador_bruto=orientador_bruto,
                        ano=_parse_ano_csv(linha.get("ano", "")),
                        instituicao=linha.get("instituicao") or instituicao_padrao,
                        campus=linha.get("campus") or campus_padrao,
                        url_dissertacao=url_dissertacao,
                        titulo_produto_bruto=linha.get("titulo_produto") or None,
                        handle_educapes=linha.get("handle_educapes") or None,
                        sem_produto=somente_dissertacoes or _parse_bool_csv(linha.get("sem_produto")),
                    ),
                    arquivos=ArquivosDefesaV4(
                        pdf_dissertacao_path=str(caminho_final.as_posix()),
                        sha256_dissertacao=sha256,
                        pdf_produto_path=None,
                        status_download=status,
                    ),
                )
            )

    return _gravar_manifesto(registros, caminho_manifesto_saida)


def ingerir_de_diretorio_pdfs(
    origem_pdfs_dir: Path,
    caminho_manifesto_saida: Path = Path("data/stage1_manifest.json"),
    diretorio_pdfs: Optional[Path] = None,
    caminho_referencia_ids: Union[Optional[Path], Sequence[Path]] = DEFAULT_REF_IDS,
    instituicao_padrao: Optional[str] = None,
    campus_padrao: str = "",
    ano_padrao: Optional[int] = None,
    somente_dissertacoes: bool = False,
    copiar_pdfs: bool = False,
    config: Optional[LemeConfig] = None,
) -> Stage1ManifestV4:
    """Gera Stage1ManifestV4 varrendo PDFs locais e extraindo metadados preliminares da capa/ficha."""
    if config is not None:
        aplicar_config(config)
        instituicao_padrao = instituicao_padrao or (config.instituicao.nome or None)
        campus_padrao = campus_padrao or config.instituicao.campus
        somente_dissertacoes = somente_dissertacoes or config.instituicao.somente_dissertacoes
    if not origem_pdfs_dir.exists() or not origem_pdfs_dir.is_dir():
        raise FileNotFoundError(f"Diretório de PDFs não encontrado: {origem_pdfs_dir}")

    arquivos_pdf = sorted(
        p for p in origem_pdfs_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )
    mapa_ids, max_id = carregar_mapeamento_ids_existentes(caminho_referencia_ids)
    ids_usados: Set[str] = set()
    destino_base = diretorio_pdfs or Path("pdf/dissertacoes")
    registros: List[PreExtracaoItemV4] = []

    for arq in arquivos_pdf:
        m_stem = _ID_STEM_RE.match(arq.stem)
        id_explicito = m_stem.group(1).upper() if m_stem else None
        prelim = _extrair_preliminares_pdf_local(arq)
        autor_prelim = str(prelim.get("autor") or "")

        cod_defesa, max_id, _ = resolver_id_estavel(
            mapa_ids,
            max_id,
            id_explicito=id_explicito,
            autor=autor_prelim,
            chave_arquivo=str(arq.as_posix()),
            ids_usados=ids_usados,
        )

        destino_copia = (destino_base / f"{cod_defesa}.pdf") if copiar_pdfs else None
        sha256, status, caminho_final = validar_ou_copiar_pdf_local(arq, destino=destino_copia)

        ano_final = int(prelim.get("ano") or 0) or (ano_padrao or 0)
        registros.append(
            PreExtracaoItemV4(
                id=cod_defesa,
                fonte_profept=FonteProfeptV4(
                    titulo_bruto=str(prelim.get("titulo") or ""),
                    autor_bruto=autor_prelim,
                    orientador_bruto=str(prelim.get("orientador") or "") or None,
                    ano=ano_final,
                    instituicao=instituicao_padrao or (str(prelim.get("instituicao") or "") or None),
                    campus=campus_padrao or str(prelim.get("campus") or ""),
                    url_dissertacao="",
                    titulo_produto_bruto=None,
                    handle_educapes=None,
                    sem_produto=somente_dissertacoes,
                ),
                arquivos=ArquivosDefesaV4(
                    pdf_dissertacao_path=str(caminho_final.as_posix()),
                    sha256_dissertacao=sha256,
                    pdf_produto_path=None,
                    status_download=status,
                ),
            )
        )

    return _gravar_manifesto(registros, caminho_manifesto_saida)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Etapa 1 (Universal): Ingestão de acervos via CSV ou pasta local de PDFs."
    )
    fonte = parser.add_mutually_exclusive_group(required=True)
    fonte.add_argument(
        "--csv",
        type=Path,
        dest="csv_path",
        help="Arquivo CSV com metadados e links/caminhos locais de PDFs.",
    )
    fonte.add_argument(
        "--pdfs-dir",
        type=Path,
        dest="pdfs_dir",
        help="Diretório contendo arquivos PDF locais para ingestão direta.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("data/stage1_manifest.json"),
        help="Caminho do manifesto JSON de saída.",
    )
    parser.add_argument(
        "--pdfs-destino",
        type=Path,
        default=Path("pdf/dissertacoes"),
        help="Diretório de destino para PDFs baixados ou copiados.",
    )
    copia = parser.add_mutually_exclusive_group()
    copia.add_argument(
        "--copiar-pdfs",
        action="store_true",
        default=None,
        help="Copia PDFs locais para --pdfs-destino (padrão em --csv).",
    )
    copia.add_argument(
        "--nao-copiar-pdfs",
        action="store_false",
        dest="copiar_pdfs",
        help="Referencia PDFs locais diretamente sem copiar para --pdfs-destino (padrão em --pdfs-dir).",
    )
    parser.add_argument(
        "--ref-ids",
        type=Path,
        action="append",
        dest="ref_ids",
        default=None,
        help="Arquivo(s) de referência para preservação de IDs (pode repetir).",
    )
    parser.add_argument("--instituicao", default=None, help="Instituição padrão para registros sem esse campo.")
    parser.add_argument("--campus", default="", help="Campus padrão para registros sem esse campo.")
    parser.add_argument("--ano-padrao", type=int, default=None, help="Ano fallback quando ausente no PDF (--pdfs-dir).")
    parser.add_argument(
        "--somente-dissertacoes",
        action="store_true",
        default=False,
        help="Marca registros sem produto educacional vinculado (modo somente dissertações).",
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
    cfg = aplicar_config(config_path=args.config)
    ref_ids = args.ref_ids if args.ref_ids is not None else DEFAULT_REF_IDS
    instituicao_efetiva = args.instituicao or (cfg.instituicao.nome or None)
    campus_efetivo = args.campus or cfg.instituicao.campus
    somente_diss = args.somente_dissertacoes or cfg.instituicao.somente_dissertacoes

    if args.csv_path is not None:
        copiar = True if args.copiar_pdfs is None else args.copiar_pdfs
        manifesto = ingerir_de_csv(
            csv_path=args.csv_path,
            caminho_manifesto_saida=args.saida,
            diretorio_pdfs=args.pdfs_destino,
            caminho_referencia_ids=ref_ids,
            instituicao_padrao=instituicao_efetiva,
            campus_padrao=campus_efetivo,
            somente_dissertacoes=somente_diss,
            copiar_pdfs=copiar,
        )
    else:
        copiar = False if args.copiar_pdfs is None else args.copiar_pdfs
        manifesto = ingerir_de_diretorio_pdfs(
            origem_pdfs_dir=args.pdfs_dir,
            caminho_manifesto_saida=args.saida,
            diretorio_pdfs=args.pdfs_destino,
            caminho_referencia_ids=ref_ids,
            instituicao_padrao=instituicao_efetiva,
            campus_padrao=campus_efetivo,
            ano_padrao=args.ano_padrao,
            somente_dissertacoes=somente_diss,
            copiar_pdfs=copiar,
        )

    ok_count = sum(1 for r in manifesto.registros if r.arquivos.status_download == "OK")
    print(f"Manifesto gravado em: {args.saida}")
    print(f"Total catalogado: {manifesto.total_registros} | PDFs prontos (OK): {ok_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
