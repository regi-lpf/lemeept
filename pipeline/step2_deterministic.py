import argparse
import json
from pathlib import Path
from typing import Optional

from pipeline.extractors import (
    classificar_formato_produto_com_fonte,
    classificar_produto_com_fonte,
    classificar_produto_regex,
    coletar_evidencias_educapes,
    detectar_macroprojeto_e_linha,
    extrair_contexto_produto,
    extrair_coorientador,
    extrair_palavras_chave_resumo,
    extrair_sentenca_produto,
    isolar_secoes_pdf,
    ler_paginas_pdf,
)
from pipeline.models_v4 import (
    ContratoExtracaoDeterministicaV4,
    DissertacaoDeterministica,
    MetadadosResolvidos,
)
from pipeline.normalizers import limpar_nome_pessoa, normalizar_nome_orientador
from pipeline.references import extrair_autores_referencias

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
):
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
    erros = []

    for item in registros:
        cod = item["id"]
        fonte = item["fonte_profept"]
        pdf_path = Path(item["arquivos"]["pdf_dissertacao_path"])

        try:
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF ausente: {pdf_path}")

            paginas = ler_paginas_pdf(pdf_path)
            texto_full_pdf = "\n".join(txt for _, txt in paginas)
            recortes, texto_integral_referencias = isolar_secoes_pdf(paginas)

            paginas_prelim = "\n".join(txt for _, txt in paginas[:5])
            bloco_coorientador = f"{paginas_prelim}\n{recortes.ficha_catalografica}".strip()
            autor_limpo = limpar_nome_pessoa(fonte["autor_bruto"])
            orientador_limpo = normalizar_nome_orientador(fonte.get("orientador_bruto"))
            mp, lp = detectar_macroprojeto_e_linha(texto_full_pdf)
            coorientadores = extrair_coorientador(
                bloco_coorientador,
                orientador_principal=orientador_limpo,
            )
            kw_dissertacao = extrair_palavras_chave_resumo(recortes.resumo)

            evidencias_capes = coletar_evidencias_educapes(
                handle_url=fonte.get("handle_educapes"),
                titulo_produto_bruto=fonte.get("titulo_produto_bruto"),
                resumo_pdf=recortes.resumo,
                descricao_produto_pdf=recortes.descricao_produto_na_dissertacao,
                cache_dir=cache_dir,
            )

            payload = ContratoExtracaoDeterministicaV4(
                id=cod,
                metadados_resolvidos=MetadadosResolvidos(
                    ano=int(fonte["ano"]),
                    autor=autor_limpo,
                    orientador=orientador_limpo,
                    coorientadores=coorientadores,
                    instituicao="Instituto Federal Catarinense (IFC)",
                    campus=fonte.get("campus") or "Blumenau",
                    linha_pesquisa=lp,
                    macroprojeto=mp,
                ),
                dissertacao_deterministica=DissertacaoDeterministica(
                    titulo=fonte["titulo_bruto"].strip(),
                    link=fonte["url_dissertacao"],
                    palavras_chave=kw_dissertacao,
                    autores_referenciados=extrair_autores_referencias(texto_integral_referencias),
                ),
                evidencias_educapes=evidencias_capes,
                recortes_textuais=recortes,
            )

            out_file = output_dir / f"{cod}.json"
            with open(out_file, "w", encoding="utf-8") as out:
                json.dump(payload.model_dump(), out, ensure_ascii=False, indent=2)

            processados += 1
            if processados % 15 == 0 or processados == len(registros):
                print(f"  [{processados}/{len(registros)}] {cod} -> MP:{mp} | LP:{lp} | TipoRegex:{evidencias_capes.tipo_produto_regex}")

        except Exception as e:
            erros.append((cod, str(e)))
            print(f"  [ERRO] {cod}: {e}")

    print("\n--- Resumo Etapa 2 ---")
    print(f"Payloads gerados com sucesso: {processados}/{len(registros)}")
    if erros:
        print(f"Falhas ({len(erros)}): {erros}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 2: Extração determinística de PDFs e eduCAPES.")
    parser.add_argument("--manifesto", type=Path, default=Path("data/stage1_manifest.json"))
    parser.add_argument("--saida-dir", type=Path, default=Path("data/stage2_payloads"))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache_educapes"))
    parser.add_argument("--id", dest="target_id", default=None, help="Processar apenas um ID específico (ex: EPT-0001).")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    executar_etapa2(
        manifest_path=args.manifesto,
        output_dir=args.saida_dir,
        cache_dir=args.cache_dir,
        target_id=args.target_id,
    )
