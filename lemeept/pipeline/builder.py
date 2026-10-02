import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .data_model import Registro


class GeradorPainel:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)

    def salvar(self, registros: Iterable[Dict[str, Any]]) -> Path:
        payload = [Registro.from_raw(r).to_dict() for r in registros]
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return self.output_path
