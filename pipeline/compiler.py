import json
import re
from pathlib import Path

SINONIMOS_TAGS = {
    "ept": "Educação Profissional e Tecnológica",
    "educação profissional e tecnológica (ept)": "Educação Profissional e Tecnológica",
    "educacao profissional e tecnologica": "Educação Profissional e Tecnológica",
    "ensino médio integrado": "Ensino Médio Integrado",
    "emi": "Ensino Médio Integrado",
    "proeja": "PROEJA",
    "ifsc": "Institutos Federais",
    "ifc": "Institutos Federais",
}

def normalizar_palavra_chave(raw: str) -> str:
    limpa = re.sub(r"^[-–—.\s]+|[-–—.\s]+$", "", raw.strip())
    if len(limpa) < 2:
        return ""
    chave_busca = limpa.lower()
    if chave_busca in SINONIMOS_TAGS:
        return SINONIMOS_TAGS[chave_busca]
    return limpa[0].upper() + limpa[1:]

def extrair_lista_tags(campo) -> list[str]:
    if not campo:
        return []
    if isinstance(campo, list):
        return [str(x) for x in campo if x]
    if isinstance(campo, str):
        # Caso alguma tag tenha vindo como string única separada por ; ou .
        return [x.strip() for x in re.split(r"[;.]", campo) if x.strip()]
    return []

def compilar_registros(pasta_records: Path, arquivo_saida: Path):
    arquivos = sorted(pasta_records.glob("EPT-*.json"))
    defesas = []

    for arq in arquivos:
        with open(arq, "r", encoding="utf-8") as f:
            reg = json.load(f)

        dis = reg.get("dissertacao") or {}
        pro = reg.get("produto") or {}

        # Coleta tags de todos os lugares possíveis sem perder nada
        tags_brutas = (
            extrair_lista_tags(reg.get("palavras_chave"))
            + extrair_lista_tags(reg.get("palavrasChave"))
            + extrair_lista_tags(dis.get("palavras_chave"))
            + extrair_lista_tags(pro.get("palavras_chave"))
        )

        tags_limpas = []
        vistos = set()
        for t in tags_brutas:
            norm = normalizar_palavra_chave(t)
            if norm and norm.lower() not in vistos:
                vistos.add(norm.lower())
                tags_limpas.append(norm)

        # Salva na raiz e preserva nos objetos filhos
        reg["palavras_chave"] = tags_limpas
        if isinstance(dis, dict) and "palavras_chave" in dis:
            dis["palavras_chave"] = tags_limpas
        if isinstance(pro, dict):
            pro["palavras_chave"] = tags_limpas

        defesas.append(reg)

    painel = {
        "versao": "3.0",
        "total_defesas": len(defesas),
        "defesas": defesas,
    }

    with open(arquivo_saida, "w", encoding="utf-8") as out:
        json.dump(painel, out, ensure_ascii=False, indent=2)

    print(f"Compilado com sucesso: {len(defesas)} defesas -> {arquivo_saida}")

if __name__ == "__main__":
    compilar_registros(Path("data/records"), Path("painel-ept-v3.json"))
