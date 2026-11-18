import csv
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List

from pipeline.models_v4 import ContratoDefesaV4
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


def aplicar_curadoria_csv() -> int:
    """
    Lê dist/revisao_epistemologica_pendente.csv (se existir) e aplica aos JSONs
    individuais em data/records/ as revisões marcadas como APROVADO ou MANTER_NULO.
    """
    if not RELATORIO_REVISAO.exists():
        return 0

    atualizados = 0
    with open(RELATORIO_REVISAO, "r", encoding="utf-8-sig", newline="") as f:
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

            caminho_record = RECORDS_DIR / f"{cod}.json"
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
                if justificativa_editada:
                    base["justificativa"] = justificativa_editada
            elif status == StatusCuradoria.APROVADO:
                valor_final = valor_aprovado or (row.get("candidato_sugerido") or "").strip()
                if not valor_final:
                    logger.warning(f"[{cod}] Marcado como {StatusCuradoria.APROVADO.value}, mas sem valor definido. Ignorando.")
                    continue

                base["valor"] = valor_final
                base["candidato"] = None
                base["confianca"] = "alta"
                base["revisao_pendente"] = False
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


def compilar_pipeline_v4():
    # 1. Incorpora revisões humanas antes de compilar
    qtd_curados = aplicar_curadoria_csv()
    if qtd_curados:
        logger.info(f"Total de registros atualizados a partir da planilha de curadoria: {qtd_curados}")

    # 2. Lê e valida todos os registros individuais
    arquivos = sorted(RECORDS_DIR.glob("EPT-*.json"))
    if not arquivos:
        raise RuntimeError(f"Nenhum registro encontrado em {RECORDS_DIR}")

    defesas_validadas: List[dict] = []
    pendentes_revisao: List[dict] = []

    for arq in arquivos:
        with open(arq, "r", encoding="utf-8") as f:
            raw = json.load(f)

        registro = ContratoDefesaV4.model_validate(raw)
        dump = registro.model_dump(mode="json")
        defesas_validadas.append(dump)

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

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Gera artefato final
    artefato_final = {
        "schema_version": "4.0",
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total_defesas": len(defesas_validadas),
        "total_producoes": len(defesas_validadas) * 2,
        "defesas": defesas_validadas,
    }

    with open(ARQUIVO_FINAL, "w", encoding="utf-8") as f:
        json.dump(artefato_final, f, ensure_ascii=False, indent=2)

    # 4. Reescreve planilha apenas com o que ainda está pendente (ou remove se zerou)
    if pendentes_revisao:
        with open(RELATORIO_REVISAO, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(pendentes_revisao[0].keys()), delimiter=";")
            writer.writeheader()
            writer.writerows(pendentes_revisao)
    elif RELATORIO_REVISAO.exists():
        RELATORIO_REVISAO.unlink()

    logger.info(f"Artefato final compilado: {ARQUIVO_FINAL} ({len(defesas_validadas)} defesas)")
    logger.info(
        f"Status epistemológico: {len(defesas_validadas) - len(pendentes_revisao)} definidos | "
        f"{len(pendentes_revisao)} pendentes em {RELATORIO_REVISAO}"
    )


if __name__ == "__main__":
    compilar_pipeline_v4()