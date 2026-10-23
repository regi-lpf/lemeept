import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .data_model import Registro


class GeradorPainel:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)

    def salvar(self, registros: Iterable[Dict[str, Any]]) -> Path:
        payload = [Registro.from_raw(r).to_dict() for r in registros]
        ids = [registro["id"] for registro in payload]
        if len(ids) != len(set(ids)):
            raise ValueError("Há IDs duplicados; o JSON final não foi atualizado.")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.output_path.with_suffix(self.output_path.suffix + ".tmp")
        with temporario.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        temporario.replace(self.output_path)
        return self.output_path
