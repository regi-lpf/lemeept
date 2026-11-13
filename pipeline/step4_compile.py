import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from pipeline.models_v4 import ContratoDefesaV4

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("step4_compile")

RECORDS_DIR = Path("data/records")
DIST_DIR = Path("dist")
ARQUIVO_FINAL = DIST_DIR / "painel-ept-v4.json"
RELATORIO_REVISAO = DIST_DIR / "revisao_epistemologica_pendente.csv"


def compilar_pipeline_v4():
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
                    "justificativa_llm": base.justificativa,
                    "secao_evidencia": evidencia_principal.secao if evidencia_principal else "",
                    "pagina_evidencia": evidencia_principal.pagina if evidencia_principal else "",
                    "trecho_evidencia": evidencia_principal.trecho if evidencia_principal else "",
                    "link_pdf": str(registro.dissertacao.link),
                }
            )

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    artefato_final = {
        "schema_version": "4.0",
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total_defesas": len(defesas_validadas),
        "total_producoes": len(defesas_validadas) * 2,
        "defesas": defesas_validadas,
    }

    with open(ARQUIVO_FINAL, "w", encoding="utf-8") as f:
        json.dump(artefato_final, f, ensure_ascii=False, indent=2)

    if pendentes_revisao:
        with open(RELATORIO_REVISAO, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(pendentes_revisao[0].keys()), delimiter=";")
            writer.writeheader()
            writer.writerows(pendentes_revisao)

    logger.info(f"Artefato final compilado: {ARQUIVO_FINAL} ({len(defesas_validadas)} defesas)")
    logger.info(
        f"Curadoria epistemológica: {len(defesas_validadas) - len(pendentes_revisao)} aprovadas automaticamente | "
        f"{len(pendentes_revisao)} encaminhadas para {RELATORIO_REVISAO}"
    )


if __name__ == "__main__":
    compilar_pipeline_v4()