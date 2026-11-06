import json
import re
import unicodedata
from pathlib import Path

def norm(texto: str) -> str:
    if not texto:
        return ""
    s = "".join(
        c for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return s

# Ordem de prioridade estrita (do mais específico para o mais amplo)
REGRAS_REGEX = [
    ("software_aplicativo", r"\b(software|aplicativo|app|portal|site|website|pagina web|jogo|quiz|gamif|ferramenta de avaliacao|socrative|ambiente virtual)\b"),
    ("produto_comunicacao", r"\b(video|videos|audiovisual|podcast|animacao|documentario|redes sociais|cinema|curta-metragem|oralitura|multimidia)\b"),
    ("curso_oficina", r"\b(curso|oficina|capacitacao|formacao continuada|minicurso|workshop|roda de conversa|acao educativa|letramento)\b"),
    ("eventos_organizados", r"\b(feira|mostra|seminario|evento|coloquio|encontro|jornada)\b"),
    ("manual_protocolo", r"\b(minuta|relatorio tecnico|prontuario|protocolo|diretrizes|orientacoes gerais|manual|guia de orientacao|implementacao da comissao)\b"),
    ("acervo", r"\b(acervo|memorial|repositorio|catalogo|inventario|memorias|historia do|origens do)\b"),
    ("carta_mapa", r"\b(infografico|cartilha|mapa|folder|folheto|guia|roteiro|trilha|tour)\b"),
    ("material_didatico_instrucional", r"\b(livro digital|e-book|ebook|caderno|material didatico|sequencia didatica|apostila|glossario|tutorial|apresentacao|aprestacao|portifolio|portfolio|proposta pedagogica|propostas de praticas|tres momentos pedagogicos|material de apoio|texto|textos)\b"),
]

# Padrão que captura a frase onde o autor declara o produto dentro do resumo
REGEX_CONTEXTO_RESUMO = re.compile(
    r"(?:produto educacional|como produto|resultou em|elaborou-se|desenvolveu-se|construiu-se|propomos|produziu-se)[^.]{0,140}",
    re.IGNORECASE
)

def classificar_item(titulo_pro: str, resumo_dis: str) -> tuple[str, float]:
    t_norm = norm(titulo_pro)
    
    # Camada 1: Match direto no Título do Produto (Score 1.0)
    for categoria, padrao in REGRAS_REGEX:
        if re.search(padrao, t_norm):
            return categoria, 1.0

    # Camada 2: Match na frase declaratória do Resumo da Dissertação (Score 0.85)
    r_norm = norm(resumo_dis)
    trechos_produto = REGEX_CONTEXTO_RESUMO.findall(r_norm)
    texto_foco = " ".join(trechos_produto) if trechos_produto else r_norm

    for categoria, padrao in REGRAS_REGEX:
        if re.search(padrao, texto_foco):
            return categoria, 0.85

    return "pendente_revisao", 0.0

def processar_records(pasta: Path):
    arquivos = sorted(pasta.glob("EPT-*.json"))
    resolvidos = 0
    restantes = []

    for arq in arquivos:
        with open(arq, "r", encoding="utf-8") as f:
            d = json.load(f)

        pro = d.get("produto") or {}
        dis = d.get("dissertacao") or {}
        atual = pro.get("tipo_produto")

        if atual in (None, "", "pendente_revisao"):
            novo_tipo, score = classificar_item(
                pro.get("titulo", ""),
                dis.get("resumo", "")
            )
            if novo_tipo != "pendente_revisao":
                pro["tipo_produto"] = novo_tipo
                pro["score_classificacao"] = score
                d["produto"] = pro
                with open(arq, "w", encoding="utf-8") as out:
                    json.dump(d, out, ensure_ascii=False, indent=2)
                resolvidos += 1
            else:
                restantes.append((d.get("cod"), pro.get("titulo")))

    print(f"Classificados automaticamente agora: {resolvidos}")
    print(f"Ainda pendentes ({len(restantes)}):")
    for cod, tit in restantes:
        print(f"  {cod} : {tit}")

if __name__ == "__main__":
    processar_records(Path("data/records"))