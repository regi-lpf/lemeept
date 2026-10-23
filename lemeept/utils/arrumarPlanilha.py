import pandas as pd
import re
import unicodedata
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO = "dados_finais_painel_ept.xlsx"

# Caso algum nome seja identificado errado, corrija aqui manualmente.
# Use o primeiro nome SEM acento e em minúsculo.
#
# Exemplo:
# GENERO_MANUAL = {
#     "reginaldo": "M",
#     "maria": "F",
# }
GENERO_MANUAL = {
    "reginaldo": "M",
    "joao": "M",
    "jose": "M",
    "carlos": "M",
    "paulo": "M",
    "marcos": "M",
    "ricardo": "M",
    "roberto": "M",
    "fernando": "M",
    "antonio": "M",
    "luiz": "M",
    "luis": "M",
    "pedro": "M",
    "rafael": "M",
    "daniel": "M",
    "fabio": "M",
    "cassio": "M",
    "william": "M",

    "maria": "F",
    "ana": "F",
    "julia": "F",
    "juliana": "F",
    "patricia": "F",
    "claudia": "F",
    "cristina": "F",
    "fernanda": "F",
    "marcia": "F",
    "luciana": "F",
    "carla": "F",
    "camila": "F",
    "aline": "F",
    "eliane": "F",
    "renata": "F",
    "sandra": "F",
    "silvia": "F",
    "simone": "F",
    "leticia": "F",
    "vanessa": "F",
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def remover_acentos(texto):
    """
    Remove acentos para unificar nomes como:
    João / Joao
    Cássio / Cassio
    """
    if pd.isna(texto):
        return texto

    texto = str(texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")

    return texto


def limpar_espacos(texto):
    """
    Remove espaços extras no começo, no fim e no meio do texto.
    """
    if pd.isna(texto):
        return texto

    texto = str(texto).strip()
    texto = re.sub(r"\s+", " ", texto)

    return texto


def remover_titulos(nome):
    """
    Remove títulos acadêmicos e profissionais do início do nome.

    Exemplos removidos:
    Dr.
    Dra.
    DR
    DRA
    Prof.
    Profa.
    Professor
    Professora
    Me.
    MSc
    PhD
    """
    if pd.isna(nome):
        return nome

    nome = str(nome)

    # Remove quebras de linha
    nome = re.sub(r"[\n\r]+", " ", nome)

    # Remove espaços extras
    nome = limpar_espacos(nome)

    # Remove caracteres estranhos comuns em raspagem
    nome = nome.replace(":", "").replace(".:", "").strip()

    # Remove títulos repetidos no início
    padrao_titulos = (
        r"^(?:"
        r"dr|dra|drª|prof|profa|profª|professor|professora|"
        r"me|ma|msc|ms|mestre|mestra|phd"
        r")\.?\s+"
    )

    while re.match(padrao_titulos, nome, flags=re.IGNORECASE):
        nome = re.sub(padrao_titulos, "", nome, flags=re.IGNORECASE).strip()

    return nome


def formatar_nome(nome):
    """
    Formata o nome no padrão:
    Nome Sobrenome

    Mantém preposições em minúsculo:
    de, da, do, dos, das, e
    """
    if pd.isna(nome):
        return nome

    nome = str(nome).lower().strip()

    partes = nome.split()

    preposicoes = {"de", "da", "do", "dos", "das", "e"}

    partes_formatadas = []

    for parte in partes:
        if parte in preposicoes:
            partes_formatadas.append(parte)
        else:
            partes_formatadas.append(parte.capitalize())

    return " ".join(partes_formatadas)


def identificar_genero(nome_base):
    """
    Identifica o gênero pelo primeiro nome.

    Primeiro tenta usar a lista manual.
    Depois usa uma lógica simples por terminação.
    """
    if pd.isna(nome_base) or str(nome_base).strip() == "":
        return "M"

    nome_sem_acento = remover_acentos(nome_base).lower().strip()
    primeiro_nome = nome_sem_acento.split()[0]

    # 1. Verifica lista manual
    if primeiro_nome in GENERO_MANUAL:
        return GENERO_MANUAL[primeiro_nome]

    # 2. Heurística simples:
    # muitos nomes femininos em português terminam com "a"
    if primeiro_nome.endswith("a"):
        return "F"

    # 3. Caso não saiba, assume masculino por padrão
    return "M"


def padronizar_orientador(nome):
    """
    Padroniza o nome do orientador.

    Fluxo:
    1. Remove títulos existentes.
    2. Remove acentos.
    3. Remove espaços extras.
    4. Identifica gênero pelo primeiro nome.
    5. Formata capitalização.
    6. Aplica Dr. ou Dra. obrigatoriamente.
    """
    if pd.isna(nome):
        return nome

    nome = str(nome).strip()

    if nome == "" or nome == "---":
        return "---"

    # Remove títulos existentes
    nome_base = remover_titulos(nome)

    # Remove acentos para unificar duplicidades
    nome_base = remover_acentos(nome_base)

    # Remove qualquer pontuação solta no início/fim
    nome_base = nome_base.strip(" .,-;:")

    # Remove espaços extras
    nome_base = limpar_espacos(nome_base)

    if nome_base == "":
        return "---"

    # Identifica gênero
    genero = identificar_genero(nome_base)

    # Formata nome
    nome_formatado = formatar_nome(nome_base)

    # Aplica título correto
    if genero == "F":
        return f"Dra. {nome_formatado}"
    else:
        return f"Dr. {nome_formatado}"


def limpar_texto_longo(texto):
    """
    Limpa Título da Dissertação e Resumo:
    - remove quebras de linha;
    - remove espaços duplicados;
    - remove espaços no início e fim.
    """
    if pd.isna(texto):
        return texto

    texto = str(texto)

    texto = re.sub(r"[\n\r]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip()

    return texto


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():
    caminho = Path(ARQUIVO)

    try:
        if not caminho.exists():
            raise FileNotFoundError(f"O arquivo '{ARQUIVO}' não foi encontrado.")

        print(f"Lendo arquivo: {ARQUIVO}")

        df = pd.read_excel(caminho)

        if "Orientador" in df.columns:
            df["Orientador"] = df["Orientador"].apply(padronizar_orientador)
            print("Coluna 'Orientador' padronizada com Dr./Dra.")
        else:
            print("Aviso: coluna 'Orientador' não encontrada.")

        if "Título da Dissertação" in df.columns:
            df["Título da Dissertação"] = df["Título da Dissertação"].apply(limpar_texto_longo)
            print("Coluna 'Título da Dissertação' limpa.")
        else:
            print("Aviso: coluna 'Título da Dissertação' não encontrada.")

        if "Resumo" in df.columns:
            df["Resumo"] = df["Resumo"].apply(limpar_texto_longo)
            print("Coluna 'Resumo' limpa.")
        else:
            print("Aviso: coluna 'Resumo' não encontrada.")

        # Sobrescreve o próprio arquivo
        df.to_excel(caminho, index=False)

        print("\nLimpeza concluída com sucesso!")
        print(f"Arquivo sobrescrito: {ARQUIVO}")

    except FileNotFoundError as erro:
        print("\nErro: arquivo não encontrado.")
        print(erro)

    except PermissionError:
        print("\nErro: não foi possível salvar o arquivo.")
        print("Feche a planilha no Excel antes de rodar o script.")

    except Exception as erro:
        print("\nOcorreu um erro durante a leitura ou limpeza da planilha.")
        print(f"Detalhes do erro: {erro}")


if __name__ == "__main__":
    main()