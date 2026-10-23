from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__:
    from .pipeline.production_builder import build_production_dataset
else:
    sys.path.insert(0, str(ROOT))
    from lemeept.pipeline.production_builder import build_production_dataset


DEFAULT_INPUT = ROOT / "lemeept" / "painel-ept.json"
DEFAULT_OUTPUT = ROOT / "lemeept" / "painel-ept-v2.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte o JSON legado em defesas e produções independentes.")
    parser.add_argument("--entrada", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--extracoes", type=Path, help="JSON opcional com campos PDF e evidências por ID de defesa.")
    args = parser.parse_args()
    legacy = json.loads(args.entrada.read_text(encoding="utf-8"))
    extractions = {}
    if args.extracoes:
        report = json.loads(args.extracoes.read_text(encoding="utf-8"))
        rows = report.get("registros", []) if isinstance(report, dict) else report
        extractions = {row["id"]: row for row in rows if isinstance(row, dict) and row.get("id")}
    dataset = build_production_dataset(legacy, extractions=extractions)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.saida.with_suffix(args.saida.suffix + ".tmp")
    temporary.write_text(json.dumps(dataset, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(args.saida)
    print(f"JSON v2 atualizado: {args.saida}")
    print(f"Defesas: {len(dataset['defesas'])}; produções: {len(dataset['producoes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
