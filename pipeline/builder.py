import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from pipeline.data_model import (
    Defesa,
    Dissertacao,
    LinhaPesquisa,
    MacroProjeto,
    PainelV3,
    Pessoa,
    Produto,
    PublicoAlvo,
    TipoProduto,
)
from pipeline.product_classifier import classificar_tipo_produto

# Tabela institucional canônica do ProfEPT
LINHAS_JANONICAS = {
    "LP1": "Práticas Educativas em Educação Profissional e Tecnológica (EPT)",
    "LP2": "Organização e Memórias de Espaços Pedagógicos na Educação Profissional e Tecnológica (EPT)",
}

MAPEAMENTO_MP_LP = {
    "MP1": "LP1",
    "MP2": "LP1",
    "MP3": "LP1",
    "MP4": "LP2",
    "MP5": "LP2",
    "MP6": "LP2",
}

def inferir_linha_pesquisa(codigo_mp: str, raw_linha: Optional[str]) -> LinhaPesquisa:
    # 1. Se o Macroprojeto for conhecido, a amarração institucional é absoluta
    cod_lp = MAPEAMENTO_MP_LP.get(codigo_mp)
    
    # 2. Se o MP for indefinido, tenta inferir por texto da string legada
    if not cod_lp and raw_linha:
        txt = raw_linha.upper()
        if "LP1" in txt or "PRÁTICAS EDUCATIVAS" in txt:
            cod_lp = "LP1"
        elif "LP2" in txt or "ORGANIZAÇÃO E MEMÓRIAS" in txt:
            cod_lp = "LP2"

    if cod_lp and cod_lp in LINHAS_JANONICAS:
        return LinhaPesquisa(codigo=cod_lp, nome=LINHAS_JANONICAS[cod_lp])
    
    return LinhaPesquisa(codigo="LP_INDEFINIDA", nome="A revisar")

def normalizar_macroprojeto(raw_mp: Optional[str], raw_cod: Optional[str]) -> MacroProjeto:
    codigo = (raw_cod or "").strip()
    descricao = (raw_mp or "").strip()

    # Se a descrição tiver o prefixo "MP2 – Descrição...", limpa a redundância
    if "–" in descricao:
        partes = descricao.split("–", 1)
        if not codigo:
            codigo = partes[0].strip()
        descricao = partes[1].strip()
    elif "-" in descricao and not codigo:
        partes = descricao.split("-", 1)
        codigo = partes[0].strip()
        descricao = partes[1].strip()

    if not codigo:
        codigo = "MP_INDEFINIDO"
    if not descricao:
        descricao = "A revisar"

    return MacroProjeto(codigo=codigo, nome=descricao)


def mapear_publico_alvo(raw_publico: Optional[str]) -> List[PublicoAlvo]:
    if not raw_publico:
        return []

    texto = raw_publico.lower()
    publicos = []

    if re.search(r"\bestudantes?\b|\balunos?\b", texto):
        publicos.append(PublicoAlvo.ESTUDANTES)
    if re.search(r"\bdocentes?\b|\bprofessores?\b", texto):
        publicos.append(PublicoAlvo.DOCENTES)
    if re.search(r"\bdiscentes?\b", texto) and PublicoAlvo.ESTUDANTES not in publicos:
        publicos.append(PublicoAlvo.DISCENTES)
    if re.search(r"\bservidores?\b|\bprofissionais?\b|\btecnicos?\b", texto):
        publicos.append(PublicoAlvo.SERVIDORES_PROFISSIONAIS)
    if re.search(r"\bgest[ãa]o\b|\bequipes?\b", texto):
        publicos.append(PublicoAlvo.GESTAO_EQUIPES_INSTITUCIONAIS)

    return publicos


def transformar_registro_v1(v1: dict) -> Defesa:
    cod_defesa = v1.get("id", "").strip()

    # Tratamento de ano numérico
    ano_raw = v1.get("ano")
    ano_int = int(ano_raw) if str(ano_raw).strip().isdigit() else None

    # Pessoas
    autor = Pessoa(nome=v1.get("autor", "").strip())
    orientador = Pessoa(nome=v1.get("orientador", "").strip())

    # Estruturas institucionais
    macro = normalizar_macroprojeto(v1.get("macroprojeto"), v1.get("codigoMacroprojeto"))
    linha = inferir_linha_pesquisa(macro.codigo, v1.get("linhaPesquisa"))

    # Palavras-chave limpas
    raw_tags = v1.get("palavrasChave", [])
    palavras_chave = [p.strip() for p in raw_tags if isinstance(p, str) and p.strip()]

    # Dissertação
    dissertacao = Dissertacao(
        id=f"{cod_defesa}-DIS",
        titulo=v1.get("titulo", "").strip(),
        link=v1.get("linkPdf", "").strip() or None,
        resumo=v1.get("resumo", "").strip(),
        area_tematica=v1.get("area", "").strip() or None,
        palavras_chave=palavras_chave,
    )

    # Produto Educacional
    titulo_produto = v1.get("produto", "").strip()
    tipo_prod_classificado, score = classificar_tipo_produto(titulo_produto)
    publicos = mapear_publico_alvo(v1.get("publicoAlvo"))

    produto = Produto(
        id=f"{cod_defesa}-PRO",
        titulo=titulo_produto,
        link=v1.get("linkProduto", "").strip() or None,
        tipo_produto=tipo_prod_classificado,
        score_classificacao=score,
        nivel_aplicacao=v1.get("nivel", "").strip() or None,
        publico_alvo=publicos if publicos else None,
        palavras_chave=palavras_chave,
    )

    return Defesa(
        cod=cod_defesa,
        titulo=v1.get("titulo", "").strip(),
        ano=ano_int,
        campus=v1.get("instituicaoCampus", "IFC Blumenau").strip(),
        autor=autor,
        orientador=orientador,
        linha_pesquisa=linha,
        macroprojeto=macro,
        dissertacao=dissertacao,
        produto=produto,
    )


def construir_painel_v3(caminho_entrada: Path, caminho_saida: Path):
    if not caminho_entrada.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho_entrada}")

    with open(caminho_entrada, "r", encoding="utf-8") as f:
        dados_brutos = json.load(f)

    # Suporta se o JSON for uma lista ou um objeto encapsulador
    lista_v1 = dados_brutos if isinstance(dados_brutos, list) else dados_brutos.get("defesas", [])

    defesas_v3: List[Defesa] = []
    erros = []

    for item in lista_v1:
        try:
            defesa = transformar_registro_v1(item)
            defesas_v3.append(defesa)
        except Exception as e:
            erros.append((item.get("id", "SEM_ID"), str(e)))

    painel = PainelV3(
        versao="3.0",
        total_defesas=len(defesas_v3),
        defesas=defesas_v3,
    )

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(asdict(painel), f, ensure_ascii=False, indent=2)

    print(f"--- Pipeline Concluído ---")
    print(f"Total processado: {len(defesas_v3)} defesas")
    if erros:
        print(f"Atenção: {len(erros)} registros falharam:")
        for cod, err in erros:
            print(f"  [{cod}]: {err}")
    print(f"Arquivo gravado em: {caminho_saida}")


if __name__ == "__main__":
    # Ajuste para onde o JSON original está localizado
    ARQUIVO_ORIGINAL = Path("./painel-ept.json")
    ARQUIVO_DESTINO = Path("./painel-ept-v3.json")

    construir_painel_v3(ARQUIVO_ORIGINAL, ARQUIVO_DESTINO)
