import json
from pathlib import Path

def explodir_painel(caminho_v3: Path, pasta_destino: Path):
    if not caminho_v3.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_v3}")

    with open(caminho_v3, "r", encoding="utf-8") as f:
        dados = json.load(f)

    defesas = dados.get("defesas", []) if isinstance(dados, dict) else dados
    pasta_destino.mkdir(parents=True, exist_ok=True)

    for d in defesas:
        cod = d.get("cod") or d.get("id")
        if not cod:
            continue
        caminho_item = pasta_destino / f"{cod}.json"
        with open(caminho_item, "w", encoding="utf-8") as out:
            json.dump(d, out, ensure_ascii=False, indent=2)

    print(f"Sucesso: {len(defesas)} registros individuais criados em '{pasta_destino}/'")

if __name__ == "__main__":
    explodir_painel(Path("painel-ept-v3.json"), Path("data/records"))