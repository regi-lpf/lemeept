import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List

from pipeline.models_v4 import ContratoDefesaV4, PainelEptV4Output
from pipeline.normalizers import normalizar_base_epistemologica
from pipeline.references import reconciliar_autores_referenciados
from pipeline.step3_llm_extract import construir_indice_busca

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("step4_compile")

RECORDS_DIR = Path("data/records")
DIST_DIR = Path("dist")
ARQUIVO_FINAL = DIST_DIR / "painel-ept-v4.json"
RELATORIO_REVISAO = DIST_DIR / "revisao_epistemologica_pendente.csv"


class StatusCuradoria(str, Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    MANTER_NULO = "MANTER_NULO"


def aplicar_curadoria_csv(
    records_dir: Path = RECORDS_DIR,
    relatorio_revisao: Path = RELATORIO_REVISAO,
) -> int:
    """
    Lê dist/revisao_epistemologica_pendente.csv (se existir) e aplica aos JSONs
    individuais em data/records/ as revisões marcadas como APROVADO ou MANTER_NULO.
    """
    if not relatorio_revisao.exists():
        return 0

    atualizados = 0
    with open(relatorio_revisao, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            cod = (row.get("id") or "").strip()
            if not cod:
                continue

            status_bruto = (row.get("status_curadoria") or StatusCuradoria.PENDENTE.value).strip().upper()
            valor_aprovado = (row.get("base_epistemologica_aprovada") or "").strip()
            justificativa_editada = (row.get("justificativa_llm") or "").strip()

            # Infere APROVADO se o curador preencheu o termo final mas esqueceu de mudar o status
            if valor_aprovado and status_bruto == StatusCuradoria.PENDENTE.value:
                status = StatusCuradoria.APROVADO
            else:
                try:
                    status = StatusCuradoria(status_bruto)
                except ValueError:
                    validos = [s.value for s in StatusCuradoria]
                    logger.warning(
                        f"[{cod}] Status inválido '{status_bruto}' no CSV (esperado: {validos}). Ignorando."
                    )
                    continue

            if status == StatusCuradoria.PENDENTE:
                continue

            caminho_record = records_dir / f"{cod}.json"
            if not caminho_record.exists():
                logger.warning(f"[{cod}] Registro não encontrado em {caminho_record} durante importação do CSV.")
                continue

            with open(caminho_record, "r", encoding="utf-8") as rf:
                raw = json.load(rf)

            base = raw["dissertacao"]["base_epistemologica"]

            if status == StatusCuradoria.MANTER_NULO:
                base["valor"] = None
                base["candidato"] = None
                base["revisao_pendente"] = False
                base["curado_humano"] = True
                if justificativa_editada:
                    base["justificativa"] = justificativa_editada
            elif status == StatusCuradoria.APROVADO:
                valor_final = valor_aprovado or (row.get("candidato_sugerido") or "").strip()
                if not valor_final:
                    logger.warning(f"[{cod}] Marcado como {StatusCuradoria.APROVADO.value}, mas sem valor definido. Ignorando.")
                    continue

                valor_norm, _ = normalizar_base_epistemologica(valor_final)
                base["valor"] = valor_norm
                base["candidato"] = None
                base["confianca"] = "alta"
                base["revisao_pendente"] = False
                base["curado_humano"] = True
                if justificativa_editada:
                    base["justificativa"] = justificativa_editada

            # Atualiza índice de busca e valida contrato completo
            raw["indice_busca"] = construir_indice_busca(raw)
            registro_validado = ContratoDefesaV4.model_validate(raw)

            with open(caminho_record, "w", encoding="utf-8") as wf:
                wf.write(registro_validado.model_dump_json(indent=2))

            atualizados += 1
            logger.info(f"[{cod}] Curadoria aplicada ({status.value}) -> Base: {base['valor'] or 'NULA (Confirmada)'}")

    return atualizados


def compilar_pipeline_v4(
    records_dir: Path = RECORDS_DIR,
    dist_dir: Path = DIST_DIR,
) -> PainelEptV4Output:
    arquivo_final = dist_dir / "painel-ept-v4.json"
    relatorio_revisao = dist_dir / "revisao_epistemologica_pendente.csv"

    # 1. Incorpora revisões humanas antes de compilar
    qtd_curados = aplicar_curadoria_csv(records_dir=records_dir, relatorio_revisao=relatorio_revisao)
    if qtd_curados:
        logger.info(f"Total de registros atualizados a partir da planilha de curadoria: {qtd_curados}")

    # 2. Lê e valida todos os registros individuais
    arquivos = sorted(records_dir.glob("EPT-*.json"))
    if not arquivos:
        raise RuntimeError(f"Nenhum registro encontrado em {records_dir}")

    registros_validados: List[ContratoDefesaV4] = []
    raw_por_id: Dict[str, tuple[Path, dict]] = {}
    pendentes_revisao: List[dict] = []

    for arq in arquivos:
        with open(arq, "r", encoding="utf-8") as f:
            raw = json.load(f)

        registro = ContratoDefesaV4.model_validate(raw)
        registros_validados.append(registro)
        raw_por_id[registro.id] = (arq, raw)

    # 2b. Reconciliação determinística global de autores referenciados no acervo
    mapa_autores = {
        reg.id: list(reg.dissertacao.autores_referenciados)
        for reg in registros_validados
    }
    autores_reconciliados = reconciliar_autores_referenciados(mapa_autores)
    qtd_reconciliados = 0
    for idx, registro in enumerate(registros_validados):
        novos_autores = autores_reconciliados.get(registro.id, [])
        if novos_autores != registro.dissertacao.autores_referenciados:
            arq, raw = raw_por_id[registro.id]
            raw["dissertacao"]["autores_referenciados"] = novos_autores
            raw["indice_busca"] = construir_indice_busca(raw)
            registro_atualizado = ContratoDefesaV4.model_validate(raw)
            arq.write_text(registro_atualizado.model_dump_json(indent=2), encoding="utf-8")
            registros_validados[idx] = registro_atualizado
            qtd_reconciliados += 1

    if qtd_reconciliados:
        logger.info(
            f"Autores referenciados reconciliados em {qtd_reconciliados} registro(s) de {records_dir}."
        )

    for registro in registros_validados:
        base = registro.dissertacao.base_epistemologica
        if base.revisao_pendente:
            evidencia_principal = base.evidencias[0] if base.evidencias else None
            pendentes_revisao.append(
                {
                    "id": registro.id,
                    "ano": registro.ano,
                    "autor": registro.autor,
                    "orientador": registro.orientador,
                    "titulo_dissertacao": registro.dissertacao.titulo,
                    "confianca_llm": base.confianca,
                    "candidato_sugerido": base.candidato or "",
                    "base_epistemologica_aprovada": "",
                    "status_curadoria": StatusCuradoria.PENDENTE.value,
                    "justificativa_llm": base.justificativa,
                    "secao_evidencia": evidencia_principal.secao if evidencia_principal else "",
                    "pagina_evidencia": evidencia_principal.pagina if evidencia_principal else "",
                    "trecho_evidencia": evidencia_principal.trecho if evidencia_principal else "",
                    "link_pdf": str(registro.dissertacao.link),
                }
            )

    dist_dir.mkdir(parents=True, exist_ok=True)

    # 3. Gera e valida artefato final via PainelEptV4Output
    artefato_final = PainelEptV4Output(
        schema_version="4.0",
        gerado_em=datetime.now(timezone.utc).isoformat(),
        total_defesas=len(registros_validados),
        total_producoes=len(registros_validados) * 2,
        defesas=registros_validados,
    )

    arquivo_final.write_text(artefato_final.model_dump_json(indent=2), encoding="utf-8")

    # 4. Reescreve planilha apenas com o que ainda está pendente (ou remove se zerou)
    if pendentes_revisao:
        with open(relatorio_revisao, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(pendentes_revisao[0].keys()), delimiter=";")
            writer.writeheader()
            writer.writerows(pendentes_revisao)
    elif relatorio_revisao.exists():
        relatorio_revisao.unlink()

    logger.info(f"Artefato final compilado: {arquivo_final} ({len(registros_validados)} defesas)")
    logger.info(
        f"Status epistemológico: {len(registros_validados) - len(pendentes_revisao)} definidos | "
        f"{len(pendentes_revisao)} pendentes em {relatorio_revisao}"
    )
    return artefato_final


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Etapa 4: Curadoria CSV e compilação do artefato final v4.")
    parser.add_argument("--records-dir", type=Path, default=RECORDS_DIR)
    parser.add_argument("--dist-dir", type=Path, default=DIST_DIR)
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    compilar_pipeline_v4(records_dir=args.records_dir, dist_dir=args.dist_dir)
