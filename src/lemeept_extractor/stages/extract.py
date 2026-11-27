import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from lemeept_extractor.config import LemeConfig, aplicar_config
from lemeept_extractor.io_utils import calcular_sha256, escrever_json_atomico
from lemeept_extractor.extractors import (
    classificar_formato_produto_com_fonte,
    classificar_produto_com_fonte,
    classificar_produto_regex,
    coletar_evidencias_educapes,
    detectar_macroprojeto_e_linha,
    extrair_contexto_produto,
    extrair_coorientador,
    extrair_metadados_preliminares_pdf,
    extrair_palavras_chave_resumo,
    extrair_sentenca_produto,
    isolar_secoes_pdf,
    ler_paginas_pdf,
)
from lemeept_extractor.models import (
    ContratoExtracaoDeterministicaV4,
    DissertacaoDeterministica,
    EvidenciasEduCAPES,
    MetadadosResolvidos,
)
from lemeept_extractor.normalizers import limpar_nome_pessoa, normalizar_nome_orientador
from lemeept_extractor.references import extrair_autores_referencias

__all__ = [
    "classificar_formato_produto_com_fonte",
    "classificar_produto_com_fonte",
    "classificar_produto_regex",
    "coletar_evidencias_educapes",
    "detectar_macroprojeto_e_linha",
    "executar_etapa2",
    "extrair_autores_referencias",
    "extrair_contexto_produto",
    "extrair_coorientador",
    "extrair_metadados_preliminares_pdf",
    "extrair_palavras_chave_resumo",
    "extrair_sentenca_produto",
    "isolar_secoes_pdf",
    "ler_paginas_pdf",
]


def executar_etapa2(
    manifest_path: Path = Path("data/stage1_manifest.json"),
    output_dir: Path = Path("data/stage2_payloads"),
    cache_dir: Path = Path("data/cache_educapes"),
    target_id: Optional[str] = None,
    somente_dissertacoes: bool = False,
    config: Optional[LemeConfig] = None,
    forcar: bool = False,
):
    if config is not None:
        aplicar_config(config)

    cfg_instituicao = config.instituicao.nome if config is not None else ""
    cfg_campus = config.instituicao.campus if config is not None else ""
    cfg_sem_produto = config.instituicao.somente_dissertacoes if config is not None else False

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifesto da Etapa 1 não encontrado: {manifest_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifesto = json.load(f)

    registros = manifesto if isinstance(manifesto, list) else manifesto.get("registros", manifesto.get("defesas", []))
    if target_id:
        registros = [r for r in registros if r.get("id") == target_id]
    print(f"Iniciando Etapa 2 para {len(registros)} defesas...")

    processados = 0
    pulados = 0
    erros = []

    for item in registros:
        cod = str(item.get("id", "<sem-id>")) if isinstance(item, dict) else "<invalido>"

        try:
            cod = item["id"]
            fonte = item["fonte_profept"]
            pdf_path = Path(item["arquivos"]["pdf_dissertacao_path"])
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF ausente: {pdf_path}")

            sem_produto = somente_dissertacoes or cfg_sem_produto or bool(fonte.get("sem_produto", False))
            sha_pdf = calcular_sha256(pdf_path)
            out_file = output_dir / f"{cod}.json"
            if not forcar and out_file.exists():
                try:
                    dados_exist = json.loads(out_file.read_text(encoding="utf-8"))
                except (OSError, ValueError, TypeError):
                    dados_exist = None
                if (
                    isinstance(dados_exist, dict)
                    and dados_exist.get("sha256_dissertacao") == sha_pdf
                    and bool((dados_exist.get("metadados_resolvidos") or {}).get("sem_produto", False)) == sem_produto
                ):
                    pulados += 1
                    continue

            paginas = ler_paginas_pdf(pdf_path)
            texto_full_pdf = "\n".join(txt for _, txt in paginas)
            recortes, texto_integral_referencias = isolar_secoes_pdf(paginas)

            paginas_prelim = "\n".join(txt for _, txt in paginas[:5])
            bloco_coorientador = f"{paginas_prelim}\n{recortes.ficha_catalografica}".strip()

            titulo_bruto = (fonte.get("titulo_bruto") or "").strip()
            autor_bruto = (fonte.get("autor_bruto") or "").strip()
            orientador_bruto = (fonte.get("orientador_bruto") or "").strip()
            ano_bruto = int(fonte.get("ano") or 0)

            prelim = {}
            if (
                not titulo_bruto
                or not autor_bruto
                or not orientador_bruto
                or ano_bruto == 0
                or not fonte.get("instituicao")
                or not fonte.get("campus")
            ):
                prelim = extrair_metadados_preliminares_pdf(
                    recortes.capa,
                    recortes.ficha_catalografica,
                    pdf_path.stem,
                )

            autor_limpo = limpar_nome_pessoa(autor_bruto or str(prelim.get("autor") or ""))
            orientador_limpo = normalizar_nome_orientador(
                orientador_bruto or str(prelim.get("orientador") or "")
            )
            ano_final = ano_bruto or int(prelim.get("ano") or 0)
            titulo_final = titulo_bruto or str(prelim.get("titulo") or pdf_path.stem)
            instituicao_final = (
                fonte.get("instituicao")
                or str(prelim.get("instituicao") or "")
                or cfg_instituicao
            )
            campus_bruto = fonte.get("campus")
            campus_final = (
                campus_bruto
                if campus_bruto
                else (str(prelim.get("campus") or "") or cfg_campus)
            )

            mp, lp = detectar_macroprojeto_e_linha(texto_full_pdf)
            coorientadores = extrair_coorientador(
                bloco_coorientador,
                orientador_principal=orientador_limpo,
            )
            kw_dissertacao = extrair_palavras_chave_resumo(recortes.resumo)

            if sem_produto:
                evidencias_capes = EvidenciasEduCAPES()
            else:
                evidencias_capes = coletar_evidencias_educapes(
                    handle_url=fonte.get("handle_educapes"),
                    titulo_produto_bruto=fonte.get("titulo_produto_bruto"),
                    resumo_pdf=recortes.resumo,
                    descricao_produto_pdf=recortes.descricao_produto_na_dissertacao,
                    cache_dir=cache_dir,
                )

            payload = ContratoExtracaoDeterministicaV4(
                id=cod,
                sha256_dissertacao=sha_pdf,
                metadados_resolvidos=MetadadosResolvidos(
                    ano=ano_final,
                    autor=autor_limpo,
                    orientador=orientador_limpo,
                    coorientadores=coorientadores,
                    instituicao=instituicao_final,
                    campus=campus_final,
                    linha_pesquisa=lp,
                    macroprojeto=mp,
                    sem_produto=sem_produto,
                ),
                dissertacao_deterministica=DissertacaoDeterministica(
                    titulo=titulo_final,
                    link=fonte.get("url_dissertacao") or "",
                    palavras_chave=kw_dissertacao,
                    autores_referenciados=extrair_autores_referencias(texto_integral_referencias),
                ),
                evidencias_educapes=evidencias_capes,
                recortes_textuais=recortes,
            )

            escrever_json_atomico(out_file, payload.model_dump())

            processados += 1
            if processados % 15 == 0 or processados == len(registros):
                print(f"  [{processados}/{len(registros)}] {cod} -> MP:{mp} | LP:{lp} | TipoRegex:{evidencias_capes.tipo_produto_regex}")

        except Exception as e:
            erros.append((cod, str(e)))
            print(f"  [ERRO] {cod}: {e}")

    print("\n--- Resumo Etapa 2 ---")
    extra_cache = f" (pulados em cache: {pulados})" if pulados else ""
    print(f"Payloads gerados com sucesso: {processados}/{len(registros)}{extra_cache}")
    if erros:
        print(f"Falhas ({len(erros)}): {erros}")
    return len(erros)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 2: Extração determinística de PDFs e eduCAPES.")
    parser.add_argument("--manifesto", type=Path, default=Path("data/stage1_manifest.json"))
    parser.add_argument("--saida-dir", type=Path, default=Path("data/stage2_payloads"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache_educapes"))
    parser.add_argument("--id", dest="target_id", default=None, help="Processar apenas um ID específico (ex: EPT-0001).")
    parser.add_argument(
        "--somente-dissertacoes",
        action="store_true",
        default=False,
        help="Ignora coleta de evidências de produto educacional (modo somente dissertações).",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        default=False,
        help="Reprocessa todos os PDFs mesmo quando o payload em cache possui o mesmo SHA-256.",
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
    qtd_erros = executar_etapa2(
        manifest_path=args.manifesto,
        output_dir=args.saida_dir,
        cache_dir=args.cache_dir,
        target_id=args.target_id,
        somente_dissertacoes=args.somente_dissertacoes,
        config=cfg,
        forcar=args.forcar,
    )
    return 1 if qtd_erros > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
