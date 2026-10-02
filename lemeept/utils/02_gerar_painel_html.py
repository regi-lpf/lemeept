import pandas as pd
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

# ============================================================
# PROJETO LEME/EPT - SCRIPT 2
# Geração do painel HTML a partir da planilha revisada
#
# Este script NÃO recalcula Linha de Pesquisa nem Macroprojeto.
# Ele confia exatamente nos dados presentes na planilha revisada.
# ============================================================

ARQUIVO_ENTRADA = "dados_finais_painel_ept_linhas_macroprojetos.xlsx"
ARQUIVO_HTML_SAIDA = "painel_leme_ept.html"

COLUNAS_ESPERADAS = [
    "Ano",
    "Autor",
    "Orientador",
    "Título da Dissertação",
    "Produto Educacional",
    "Link do PDF",
    "Link do Produto",
    "Palavras-chave",
    "Tipo de Produto",
    "Resumo",
    "Base Epistemológica V2",
    "Nível de Aplicação V2",
    "Área Temática",
    "Finalidade do Produto",
    "Público-alvo",
    "Tipo de Produto V2",
    "Instituição/Campus",
    "Linha de Pesquisa",
    "Macroprojeto",
    "Código do Macroprojeto",
    "Confiança Linha/Macro",
    "Termos Detectados Linha/Macro",
    "Justificativa Linha/Macro",
    "Revisão Manual",
]


def limpar_valor(valor, padrao="---"):
    if pd.isna(valor):
        return padrao
    valor = str(valor).strip()
    if not valor or valor.lower() in ["nan", "none", "null"]:
        return padrao
    return valor


def normalizar_texto(texto):
    texto = limpar_valor(texto, "")
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def formatar_nome_orientador(valor):
    nome = limpar_valor(valor, "")
    if not nome or nome == "---":
        return "---"
    nome = re.sub(r"[:;]+", "", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome if nome else "---"


def chave_orientador(valor):
    nome = formatar_nome_orientador(valor)
    if nome == "---":
        return ""
    nome = nome.lower()
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    nome = re.sub(r"\bdr[aª]?\b\.?,?", "", nome, flags=re.IGNORECASE)
    nome = re.sub(r"\bprof[aª]?\b\.?,?", "", nome, flags=re.IGNORECASE)
    nome = re.sub(r"[^a-z0-9\s]", " ", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome


def ano_limpo(valor):
    texto = limpar_valor(valor, "")
    m = re.search(r"(20\d{2})", texto)
    return m.group(1) if m else "---"


def dividir_tags(texto):
    texto = limpar_valor(texto, "")
    if not texto:
        return []
    partes = re.split(r"[;,|\n]+", texto)
    tags = []
    vistos = set()
    for parte in partes:
        tag = re.sub(r"\s+", " ", parte).strip(" .;,-")
        if not tag or tag == "---":
            continue
        chave = normalizar_texto(tag)
        if chave not in vistos:
            vistos.add(chave)
            tags.append(tag)
    return tags


def limitar_texto(texto, limite=280):
    texto = limpar_valor(texto, "")
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "..."


def link_valido(link):
    link = limpar_valor(link, "")
    return link.startswith("http://") or link.startswith("https://")


def primeiro_valor(row, *colunas, padrao="---"):
    for coluna in colunas:
        if coluna in row:
            valor = limpar_valor(row.get(coluna), "")
            if valor and valor != "---":
                return valor
    return padrao


def carregar_planilha(arquivo=ARQUIVO_ENTRADA):
    caminho = Path(arquivo)
    if not caminho.exists():
        raise FileNotFoundError(
            f"Planilha de entrada não encontrada: {arquivo}\n"
            "Rode primeiro: python 01_classificar_linhas_macroprojetos.py\n"
            "Depois revise e salve a planilha antes de gerar o HTML."
        )

    df = pd.read_excel(caminho)

    faltantes = [col for col in COLUNAS_ESPERADAS if col not in df.columns]
    if faltantes:
        print("ATENÇÃO: estas colunas esperadas não foram encontradas na planilha e serão preenchidas com '---':")
        for col in faltantes:
            print(f"- {col}")
            df[col] = "---"

    return df.fillna("---")


def preparar_dados_para_html(df):
    registros = []

    for _, row_series in df.iterrows():
        row = row_series.to_dict()

        ano = primeiro_valor(row, "Ano Limpo", "Ano")
        orientador = formatar_nome_orientador(row.get("Orientador", ""))
        orientador_chave = chave_orientador(row.get("Orientador", ""))
        link_pdf = primeiro_valor(row, "Link do PDF", padrao="")
        link_produto = primeiro_valor(row, "Link do Produto", padrao="")

        registro = {
            "ano": ano_limpo(ano),
            "autor": primeiro_valor(row, "Autor"),
            "orientador": orientador,
            "orientadorChave": orientador_chave,
            "titulo": primeiro_valor(row, "Título da Dissertação"),
            "produto": primeiro_valor(row, "Produto Educacional"),
            "linkPdf": link_pdf if link_valido(link_pdf) else "",
            "linkProduto": link_produto if link_valido(link_produto) else "",
            "palavrasChave": dividir_tags(row.get("Palavras-chave", "")),
            "tipoProdutoOriginal": primeiro_valor(row, "Tipo de Produto"),
            "tipoProduto": primeiro_valor(row, "Tipo de Produto V2", "Tipo de Produto"),
            "resumo": primeiro_valor(row, "Resumo"),
            "resumoCurto": limitar_texto(row.get("Resumo", ""), 280),
            "nivel": primeiro_valor(row, "Nível de Aplicação V2", "Nível de Aplicação"),
            "base": primeiro_valor(row, "Base Epistemológica V2", "Base Epistemológica"),
            "confiancaBase": primeiro_valor(row, "Confiança da Base"),
            "termosBase": primeiro_valor(row, "Termos Detectados da Base"),
            "area": primeiro_valor(row, "Área Temática"),
            "finalidade": primeiro_valor(row, "Finalidade do Produto"),
            "publicoAlvo": primeiro_valor(row, "Público-alvo"),
            "instituicaoCampus": primeiro_valor(row, "Instituição/Campus"),
            "linhaPesquisa": primeiro_valor(row, "Linha de Pesquisa"),
            "macroprojeto": primeiro_valor(row, "Macroprojeto"),
            "codigoMacroprojeto": primeiro_valor(row, "Código do Macroprojeto"),
            "confiancaLinhaMacro": primeiro_valor(row, "Confiança Linha/Macro"),
            "termosLinhaMacro": primeiro_valor(row, "Termos Detectados Linha/Macro"),
            "justificativaLinhaMacro": primeiro_valor(row, "Justificativa Linha/Macro"),
            "revisaoManual": primeiro_valor(row, "Revisão Manual"),
        }

        registros.append(registro)

    return registros



def gerar_html(registros):
    dados_json = json.dumps(registros, ensure_ascii=False).replace("</", "<\\/")

    total = len(registros)
    total_orientadores = len({
        r.get("orientadorChave", "")
        for r in registros
        if r.get("orientadorChave", "")
    })
    total_bases = len({r["base"] for r in registros if r["base"] != "---"})
    total_produtos = sum(1 for r in registros if r["linkProduto"])

    anos_validos = sorted([r["ano"] for r in registros if r["ano"] != "---"])
    periodo = f"{anos_validos[0]}–{anos_validos[-1]}" if anos_validos else "---"
    atualizado_em = datetime.now().strftime("%d/%m/%Y")

    html = r'''<!-- =========================================================
PAINEL LEME EPT V5
Gerado automaticamente por Python
Cole TODO este bloco no Elementor > Editor de Texto ou HTML
Inclui Chart.js via CDN, busca, filtros, exportação e paginação
========================================================= -->

<section id="leme-painel-ept" class="leme-painel-ept">
  <style>
    #leme-painel-ept {
      --leme-primary: #4f46e5;
      --leme-primary-dark: #3730a3;
      --leme-primary-soft: #eef2ff;
      --leme-cyan: #06b6d4;
      --leme-pink: #ec4899;
      --leme-green: #16a34a;
      --leme-green-soft: #dcfce7;
      --leme-orange: #f97316;
      --leme-red: #e11d48;
      --leme-bg: #f8fafc;
      --leme-card: rgba(255,255,255,.92);
      --leme-border: #e5e7eb;
      --leme-border-strong: #d7dcff;
      --leme-text: #111827;
      --leme-muted: #64748b;
      --leme-shadow: 0 18px 50px rgba(15, 23, 42, .10);
      --leme-shadow-soft: 0 10px 28px rgba(15, 23, 42, .07);
      font-family: "Inter", "Segoe UI", Arial, sans-serif;
      color: var(--leme-text);
      background:
        radial-gradient(circle at top left, rgba(79,70,229,.16), transparent 34%),
        radial-gradient(circle at top right, rgba(6,182,212,.12), transparent 30%),
        linear-gradient(180deg, #ffffff, var(--leme-bg));
      border: 1px solid var(--leme-border);
      border-radius: 28px;
      padding: 26px;
      box-sizing: border-box;
      overflow: hidden;
    }

    #leme-painel-ept * { box-sizing: border-box; }

    #leme-painel-ept .leme-header {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: start;
      margin-bottom: 22px;
    }

    #leme-painel-ept .leme-eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 12px;
      border-radius: 999px;
      background: var(--leme-primary-soft);
      color: var(--leme-primary-dark);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .02em;
      margin-bottom: 10px;
    }

    #leme-painel-ept h2 {
      margin: 0;
      color: var(--leme-primary-dark);
      font-size: clamp(25px, 3vw, 38px);
      line-height: 1.08;
      font-weight: 900;
      letter-spacing: -.04em;
    }

    #leme-painel-ept .leme-subtitle {
      margin: 10px 0 0;
      color: var(--leme-muted);
      font-size: 15px;
      line-height: 1.6;
      max-width: 920px;
    }

    #leme-painel-ept .leme-update {
      background: rgba(255,255,255,.82);
      border: 1px solid var(--leme-border-strong);
      border-radius: 18px;
      padding: 13px 15px;
      font-size: 12px;
      color: var(--leme-muted);
      white-space: nowrap;
      box-shadow: var(--leme-shadow-soft);
      backdrop-filter: blur(10px);
    }

    #leme-painel-ept .leme-stats {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }

    #leme-painel-ept .leme-stat {
      background: var(--leme-card);
      border: 1px solid var(--leme-border);
      border-radius: 22px;
      padding: 18px;
      box-shadow: var(--leme-shadow-soft);
      position: relative;
      overflow: hidden;
    }

    #leme-painel-ept .leme-stat::after {
      content: "";
      position: absolute;
      inset: auto -30px -42px auto;
      width: 105px;
      height: 105px;
      border-radius: 999px;
      background: rgba(79,70,229,.09);
    }

    #leme-painel-ept .leme-stat strong {
      display: block;
      color: var(--leme-primary-dark);
      font-size: 29px;
      line-height: 1;
      margin-bottom: 7px;
      letter-spacing: -.03em;
    }

    #leme-painel-ept .leme-stat span {
      color: var(--leme-muted);
      font-size: 12px;
      font-weight: 750;
    }

    #leme-painel-ept .leme-analytics {
      margin: 0 0 20px;
      background: rgba(255,255,255,.94);
      border: 1px solid var(--leme-border);
      border-radius: 26px;
      padding: 20px;
      box-shadow: var(--leme-shadow);
      backdrop-filter: blur(12px);
    }

    #leme-painel-ept .leme-analytics-head {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }

    #leme-painel-ept .leme-analytics-head h3 {
      margin: 0;
      color: var(--leme-primary-dark);
      font-size: 23px;
      line-height: 1.2;
      font-weight: 900;
      letter-spacing: -.025em;
    }

    #leme-painel-ept .leme-analytics-head p {
      margin: 6px 0 0;
      color: var(--leme-muted);
      font-size: 13px;
      line-height: 1.55;
      max-width: 800px;
    }

    #leme-painel-ept .leme-analytics-note {
      background: var(--leme-primary-soft);
      color: var(--leme-primary-dark);
      border: 1px solid #d9ddff;
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 12px;
      font-weight: 850;
      white-space: nowrap;
    }

    #leme-painel-ept .leme-charts-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    #leme-painel-ept .leme-chart-card {
      border: 1px solid var(--leme-border);
      border-radius: 22px;
      padding: 16px;
      background: linear-gradient(180deg, #ffffff, #fbfdff);
      min-height: 330px;
      box-shadow: 0 8px 20px rgba(15, 23, 42, .045);
    }

    #leme-painel-ept .leme-chart-card.is-wide { grid-column: 1 / -1; }

    #leme-painel-ept .leme-chart-title {
      margin: 0 0 4px;
      color: var(--leme-text);
      font-size: 15px;
      font-weight: 900;
    }

    #leme-painel-ept .leme-chart-subtitle {
      margin: 0 0 12px;
      color: var(--leme-muted);
      font-size: 12px;
      line-height: 1.45;
    }

    #leme-painel-ept .leme-chart-wrap {
      position: relative;
      height: 260px;
      width: 100%;
    }

    #leme-painel-ept .leme-chart-card.is-wide .leme-chart-wrap { height: 300px; }
    #leme-painel-ept .leme-chart-card.is-wide .leme-chart-wrap.is-tall { height: 390px; }

    #leme-painel-ept .leme-controls {
      background: rgba(255,255,255,.95);
      border: 1px solid var(--leme-border);
      border-radius: 24px;
      padding: 17px;
      margin-bottom: 18px;
      box-shadow: var(--leme-shadow);
      backdrop-filter: blur(12px);
    }

    #leme-painel-ept .leme-section-label {
      margin: 0 0 12px;
      color: var(--leme-primary-dark);
      font-size: 18px;
      font-weight: 900;
      letter-spacing: -.02em;
    }

    #leme-painel-ept .leme-search-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      margin-bottom: 14px;
    }

    #leme-painel-ept .leme-search {
      width: 100%;
      border: 1px solid var(--leme-border-strong);
      border-radius: 18px;
      padding: 15px 16px;
      font-size: 15px;
      color: var(--leme-text);
      outline: none;
      background: #fff;
      transition: border-color .2s ease, box-shadow .2s ease;
    }

    #leme-painel-ept .leme-search:focus {
      border-color: var(--leme-primary);
      box-shadow: 0 0 0 4px rgba(79, 70, 229, .12);
    }

    #leme-painel-ept .leme-clear {
      border: none;
      border-radius: 18px;
      padding: 0 17px;
      background: linear-gradient(135deg, var(--leme-primary), var(--leme-cyan));
      color: #fff;
      font-weight: 850;
      cursor: pointer;
      box-shadow: 0 12px 22px rgba(79, 70, 229, .16);
    }

    #leme-painel-ept .leme-clear:hover { filter: brightness(.96); }

    #leme-painel-ept .leme-filters {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 11px;
    }

    #leme-painel-ept .leme-field label {
      display: block;
      font-size: 11px;
      font-weight: 850;
      color: var(--leme-muted);
      margin: 0 0 6px;
      text-transform: uppercase;
      letter-spacing: .045em;
    }

    #leme-painel-ept .leme-field select {
      width: 100%;
      border: 1px solid var(--leme-border);
      border-radius: 15px;
      padding: 11px 12px;
      background: #fff;
      color: var(--leme-text);
      font-size: 13px;
      outline: none;
    }

    #leme-painel-ept .leme-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin: 16px 0;
      flex-wrap: wrap;
    }

    #leme-painel-ept .leme-count {
      font-size: 14px;
      color: var(--leme-muted);
      font-weight: 750;
    }

    #leme-painel-ept .leme-count strong { color: var(--leme-primary-dark); }

    #leme-painel-ept .leme-actions-toolbar {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }

    #leme-painel-ept .leme-export-btn,
    #leme-painel-ept .leme-view button,
    #leme-painel-ept .leme-page-btn {
      border: 1px solid var(--leme-border);
      border-radius: 999px;
      background: #fff;
      color: var(--leme-primary-dark);
      padding: 9px 13px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 850;
      transition: background .16s ease, border-color .16s ease, transform .16s ease, color .16s ease;
    }

    #leme-painel-ept .leme-export-btn:hover,
    #leme-painel-ept .leme-view button:hover,
    #leme-painel-ept .leme-page-btn:hover {
      background: var(--leme-primary-soft);
      border-color: #cfd4ff;
      transform: translateY(-1px);
    }

    #leme-painel-ept .leme-view { display: inline-flex; gap: 8px; align-items: center; }

    #leme-painel-ept .leme-view button.is-active,
    #leme-painel-ept .leme-page-btn.is-active {
      background: var(--leme-primary);
      border-color: var(--leme-primary);
      color: #fff;
    }

    #leme-painel-ept .leme-page-btn:disabled {
      opacity: .45;
      cursor: not-allowed;
      transform: none;
    }

    #leme-painel-ept .leme-results {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    #leme-painel-ept .leme-results.is-table {
      display: block;
      overflow-x: auto;
      background: #fff;
      border: 1px solid var(--leme-border);
      border-radius: 22px;
      box-shadow: var(--leme-shadow-soft);
    }

    #leme-painel-ept .leme-card {
      background: var(--leme-card);
      border: 1px solid var(--leme-border);
      border-radius: 24px;
      padding: 20px;
      box-shadow: var(--leme-shadow-soft);
      transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
    }

    #leme-painel-ept .leme-card:hover {
      transform: translateY(-3px);
      box-shadow: 0 20px 44px rgba(15, 23, 42, .12);
      border-color: rgba(79, 70, 229, .34);
    }

    #leme-painel-ept .leme-card-title {
      margin: 0 0 12px;
      color: var(--leme-primary-dark);
      font-size: 16px;
      line-height: 1.35;
      font-weight: 900;
      letter-spacing: -.01em;
    }

    #leme-painel-ept .leme-meta {
      display: grid;
      gap: 7px;
      margin: 0 0 12px;
      color: var(--leme-muted);
      font-size: 13px;
      line-height: 1.35;
    }

    #leme-painel-ept .leme-meta b { color: var(--leme-text); }

    #leme-painel-ept .leme-badges,
    #leme-painel-ept .leme-tags,
    #leme-painel-ept .leme-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    #leme-painel-ept .leme-badges { margin: 12px 0; }
    #leme-painel-ept .leme-tags { margin-top: 10px; }
    #leme-painel-ept .leme-actions { margin-top: 15px; }

    #leme-painel-ept .leme-badge,
    #leme-painel-ept .leme-tag {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 11px;
      font-weight: 850;
      background: var(--leme-primary-soft);
      color: var(--leme-primary-dark);
      border: 1px solid #d9ddff;
    }

    #leme-painel-ept .leme-badge.green { background: var(--leme-green-soft); color: #166534; border-color: #bbf7d0; }
    #leme-painel-ept .leme-badge.red { background: #fff1f2; color: var(--leme-red); border-color: #fecdd3; }
    #leme-painel-ept .leme-tag { background: #f8fafc; border-color: #e2e8f0; color: #475569; font-weight: 750; }

    #leme-painel-ept .leme-summary {
      color: #475569;
      font-size: 13px;
      line-height: 1.6;
      margin: 13px 0;
    }

    #leme-painel-ept details {
      margin-top: 11px;
      border-top: 1px solid var(--leme-border);
      padding-top: 11px;
    }

    #leme-painel-ept summary {
      cursor: pointer;
      color: var(--leme-primary-dark);
      font-weight: 900;
      font-size: 13px;
      list-style: none;
    }

    #leme-painel-ept summary::-webkit-details-marker { display: none; }

    #leme-painel-ept .leme-detail {
      margin-top: 12px;
      color: #374151;
      font-size: 13px;
      line-height: 1.58;
    }

    #leme-painel-ept .leme-link {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      border-radius: 999px;
      padding: 9px 12px;
      text-decoration: none !important;
      font-size: 12px;
      font-weight: 900;
      border: 1px solid transparent;
    }

    #leme-painel-ept .leme-link.pdf { color: #fff !important; background: var(--leme-red); }
    #leme-painel-ept .leme-link.produto { color: #fff !important; background: var(--leme-green); }

    #leme-painel-ept .leme-empty {
      grid-column: 1 / -1;
      background: #fff;
      border: 1px dashed var(--leme-border-strong);
      border-radius: 22px;
      padding: 32px;
      text-align: center;
      color: var(--leme-muted);
      font-weight: 800;
    }

    #leme-painel-ept table.leme-table {
      width: 100%;
      min-width: 1150px;
      border-collapse: collapse;
      font-size: 13px;
    }

    #leme-painel-ept .leme-table th {
      background: var(--leme-primary);
      color: #fff;
      text-align: left;
      padding: 14px;
      position: sticky;
      top: 0;
      z-index: 2;
      white-space: nowrap;
    }

    #leme-painel-ept .leme-table td {
      padding: 14px;
      border-bottom: 1px solid var(--leme-border);
      vertical-align: top;
    }

    #leme-painel-ept .leme-table-title { color: var(--leme-primary-dark); font-weight: 900; line-height: 1.35; }

    #leme-painel-ept .leme-pagination {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 7px;
      flex-wrap: wrap;
      margin: 20px 0 4px;
    }

    #leme-painel-ept .leme-pagination-info {
      width: 100%;
      text-align: center;
      color: var(--leme-muted);
      font-size: 12px;
      font-weight: 750;
      margin-top: 4px;
    }

    #leme-painel-ept mark.leme-highlight {
      background: #fef08a;
      color: inherit;
      border-radius: 5px;
      padding: 0 2px;
      box-decoration-break: clone;
      -webkit-box-decoration-break: clone;
    }

    @media (max-width: 1024px) {
      #leme-painel-ept .leme-stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      #leme-painel-ept .leme-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      #leme-painel-ept .leme-results { grid-template-columns: 1fr; }
      #leme-painel-ept .leme-charts-grid { grid-template-columns: 1fr; }
      #leme-painel-ept .leme-chart-card.is-wide { grid-column: auto; }
    }

    @media (max-width: 720px) {
      #leme-painel-ept { padding: 16px; border-radius: 20px; }
      #leme-painel-ept .leme-header { grid-template-columns: 1fr; }
      #leme-painel-ept .leme-update { white-space: normal; }
      #leme-painel-ept .leme-stats { grid-template-columns: 1fr; }
      #leme-painel-ept .leme-search-row { grid-template-columns: 1fr; }
      #leme-painel-ept .leme-clear { padding: 13px 16px; }
      #leme-painel-ept .leme-filters { grid-template-columns: 1fr; }
      #leme-painel-ept .leme-view { display: none; }
      #leme-painel-ept .leme-actions-toolbar { width: 100%; }
      #leme-painel-ept .leme-export-btn { flex: 1; }
      #leme-painel-ept .leme-chart-wrap { height: 245px; }
      #leme-painel-ept .leme-chart-wrap.is-tall { height: 315px; }
      #leme-painel-ept .leme-results { display: grid !important; grid-template-columns: 1fr; overflow: visible !important; border: 0 !important; background: transparent !important; }
    }
  </style>

  <div class="leme-header">
    <div>
      <div class="leme-eyebrow">📊 Painel bibliométrico · EPT</div>
      <h2>Repositório Digital da Produção ProfEPT</h2>
      <p class="leme-subtitle">
        Consulte trabalhos por tema, autor, orientador, instituição, base epistemológica,
        nível de aplicação, finalidade do produto educacional e palavras-chave.
      </p>
    </div>
    <div class="leme-update">
      Atualizado em <strong>__ATUALIZADO_EM__</strong><br>
      Período analisado: <strong>__PERIODO__</strong>
    </div>
  </div>

  <div class="leme-stats" aria-label="Indicadores gerais do painel">
    <div class="leme-stat"><strong>__TOTAL__</strong><span>trabalhos analisados</span></div>
    <div class="leme-stat"><strong>__TOTAL_PRODUTOS__</strong><span>produtos com link</span></div>
    <div class="leme-stat"><strong>__TOTAL_ORIENTADORES__</strong><span>orientadores</span></div>
    <div class="leme-stat"><strong>__TOTAL_BASES__</strong><span>bases identificadas</span></div>
  </div>

  <section class="leme-analytics" aria-label="Visualizações bibliométricas">
    <div class="leme-analytics-head">
      <div>
        <h3>Visão geral da produção</h3>
        <p>
          Os gráficos aparecem antes da busca para dar uma leitura rápida do acervo. Ao pesquisar ou filtrar,
          os gráficos e os resultados mudam em tempo real usando apenas os registros filtrados.
        </p>
      </div>
      <div id="leme-graficos-nota" class="leme-analytics-note">Todos os trabalhos</div>
    </div>

    <div class="leme-charts-grid">
      <div class="leme-chart-card is-wide">
        <h4 class="leme-chart-title">Trabalhos por ano</h4>
        <p class="leme-chart-subtitle">Evolução temporal da produção cadastrada no repositório.</p>
        <div class="leme-chart-wrap"><canvas id="leme-chart-ano"></canvas></div>
      </div>

      <div class="leme-chart-card is-wide">
        <h4 class="leme-chart-title">Orientadores</h4>
        <p class="leme-chart-subtitle">Top 15 orientadores com mais trabalhos no conjunto filtrado.</p>
        <div class="leme-chart-wrap is-tall"><canvas id="leme-chart-orientador"></canvas></div>
      </div>

      <div class="leme-chart-card">
        <h4 class="leme-chart-title">Base epistemológica</h4>
        <p class="leme-chart-subtitle">Distribuição dos trabalhos pela base identificada automaticamente.</p>
        <div class="leme-chart-wrap"><canvas id="leme-chart-base"></canvas></div>
      </div>

      <div class="leme-chart-card">
        <h4 class="leme-chart-title">Nível de aplicação</h4>
        <p class="leme-chart-subtitle">Onde os produtos e pesquisas mais se concentram.</p>
        <div class="leme-chart-wrap"><canvas id="leme-chart-nivel"></canvas></div>
      </div>

      <div class="leme-chart-card">
        <h4 class="leme-chart-title">Linha de pesquisa</h4>
        <p class="leme-chart-subtitle">Distribuição dos trabalhos pelas linhas acadêmicas definidas.</p>
        <div class="leme-chart-wrap"><canvas id="leme-chart-linha"></canvas></div>
      </div>

      <div class="leme-chart-card">
        <h4 class="leme-chart-title">Macroprojeto</h4>
        <p class="leme-chart-subtitle">Distribuição dos seis macroprojetos oficiais do ProfEPT.</p>
        <div class="leme-chart-wrap"><canvas id="leme-chart-macro"></canvas></div>
      </div>
    </div>
  </section>

  <div class="leme-controls">
    <h3 class="leme-section-label">Pesquisa e resultados</h3>
    <div class="leme-search-row">
      <input id="leme-busca" class="leme-search" type="search"
        placeholder="Busque por tema, título, autor, orientador, resumo, palavra-chave, campus..."
        aria-label="Busca no painel EPT">
      <button id="leme-limpar" class="leme-clear" type="button">Limpar filtros</button>
    </div>

    <div class="leme-filters">
      <div class="leme-field"><label for="leme-filtro-ano">Ano</label><select id="leme-filtro-ano" data-campo="ano"><option value="">Todos</option></select></div>
      <div class="leme-field"><label for="leme-filtro-nivel">Nível</label><select id="leme-filtro-nivel" data-campo="nivel"><option value="">Todos</option></select></div>
      <div class="leme-field"><label for="leme-filtro-base">Base epistemológica</label><select id="leme-filtro-base" data-campo="base"><option value="">Todas</option></select></div>
      <div class="leme-field"><label for="leme-filtro-linha">Linha de pesquisa</label><select id="leme-filtro-linha" data-campo="linhaPesquisa"><option value="">Todas</option></select></div>
      <div class="leme-field"><label for="leme-filtro-macro">Macroprojeto</label><select id="leme-filtro-macro" data-campo="macroprojeto"><option value="">Todos</option></select></div>
      <div class="leme-field"><label for="leme-filtro-area">Área temática</label><select id="leme-filtro-area" data-campo="area"><option value="">Todas</option></select></div>
      <div class="leme-field"><label for="leme-filtro-orientador">Orientador</label><select id="leme-filtro-orientador" data-campo="orientador"><option value="">Todos</option></select></div>
      <div class="leme-field"><label for="leme-filtro-tipo">Tipo de produto</label><select id="leme-filtro-tipo" data-campo="tipoProduto"><option value="">Todos</option></select></div>
      <div class="leme-field"><label for="leme-filtro-finalidade">Finalidade</label><select id="leme-filtro-finalidade" data-campo="finalidade"><option value="">Todas</option></select></div>
      <div class="leme-field"><label for="leme-filtro-publico">Público-alvo</label><select id="leme-filtro-publico" data-campo="publicoAlvo"><option value="">Todos</option></select></div>
    </div>
  </div>

  <div class="leme-toolbar">
    <div id="leme-contador" class="leme-count">Carregando resultados...</div>

    <div class="leme-actions-toolbar">
      <button id="leme-exportar-csv" class="leme-export-btn" type="button">⬇️ Exportar filtrados</button>
      <button id="leme-copiar-resultados" class="leme-export-btn" type="button">📋 Copiar resultados</button>
      <div class="leme-view" aria-label="Alternar visualização">
        <button id="leme-view-cards" type="button" class="is-active">Cards</button>
        <button id="leme-view-table" type="button">Tabela</button>
      </div>
    </div>
  </div>

  <div id="leme-resultados" class="leme-results"></div>
  <nav id="leme-paginacao" class="leme-pagination" aria-label="Paginação de resultados"></nav>

  <script type="application/json" id="leme-dados-json">__DADOS_JSON__</script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

  <script>
    (function() {
      const raiz = document.getElementById("leme-painel-ept");
      if (!raiz) return;

      const dadosEl = raiz.querySelector("#leme-dados-json");
      const dados = JSON.parse(dadosEl.textContent || "[]");

      const busca = raiz.querySelector("#leme-busca");
      const limpar = raiz.querySelector("#leme-limpar");
      const resultados = raiz.querySelector("#leme-resultados");
      const paginacao = raiz.querySelector("#leme-paginacao");
      const contador = raiz.querySelector("#leme-contador");
      const filtros = Array.from(raiz.querySelectorAll("select[data-campo]"));
      const graficosNota = raiz.querySelector("#leme-graficos-nota");
      const exportarCsv = raiz.querySelector("#leme-exportar-csv");
      const copiarResultados = raiz.querySelector("#leme-copiar-resultados");
      const btnCards = raiz.querySelector("#leme-view-cards");
      const btnTable = raiz.querySelector("#leme-view-table");

      let resultadosAtuais = [];
      let modo = "cards";
      let paginaAtual = 1;
      const itensPorPagina = 12;
      const graficos = {};

      const palette = [
        "#4f46e5", "#06b6d4", "#16a34a", "#f97316", "#ec4899",
        "#8b5cf6", "#14b8a6", "#e11d48", "#f59e0b", "#0ea5e9"
      ];

      const macroprojetosOficiais = [
        "Macroprojeto 1 – Propostas metodológicas e recursos didáticos em espaços formais e não formais de ensino na EPT",
        "Macroprojeto 2 – Inclusão e diversidade em espaços formais e não formais de ensino na EPT",
        "Macroprojeto 3 – Práticas Educativas no Currículo Integrado",
        "Macroprojeto 4 – História e memórias no contexto da EPT",
        "Macroprojeto 5 – Organização do currículo integrado na EPT",
        "Macroprojeto 6 – Organização de espaços pedagógicos na EPT"
      ];

      const linhasOficiais = [
        "Práticas Educativas em Educação Profissional e Tecnológica (EPT)",
        "Organização e Memórias de Espaços Pedagógicos na Educação Profissional e Tecnológica (EPT)"
      ];

      function carregarChartJs(callback) {
        if (window.Chart) {
          callback();
          return;
        }

        const existente = document.querySelector('script[data-leme-chartjs="true"]');
        if (existente) {
          existente.addEventListener("load", callback, { once: true });
          return;
        }

        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/chart.js";
        script.dataset.lemeChartjs = "true";
        script.onload = callback;
        document.head.appendChild(script);
      }

      function normalizarBusca(valor) {
        return String(valor || "")
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .replace(/\s+/g, " ")
          .trim();
      }

      function textoBusca(item) {
        return normalizarBusca([
          item.ano, item.autor, item.orientador, item.orientadorChave, item.titulo, item.produto,
          item.resumo, item.nivel, item.base, item.area, item.finalidade,
          item.publicoAlvo, item.tipoProduto, item.instituicaoCampus,
          item.linhaPesquisa, item.macroprojeto, item.codigoMacroprojeto, item.confiancaLinhaMacro,
          item.termosLinhaMacro, item.justificativaLinhaMacro, item.revisaoManual,
          (item.palavrasChave || []).join(" ")
        ].join(" "));
      }

      function termosBusca() {
        const termo = normalizarBusca(busca.value || "");
        return termo ? termo.split(" ").filter(Boolean) : [];
      }

      function escapeHtml(valor) {
        return String(valor || "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }

      function highlightText(valor) {
        const textoOriginal = String(valor || "");
        const termos = termosBusca();
        if (!termos.length || !textoOriginal) return escapeHtml(textoOriginal);

        const textoNormalizado = normalizarBusca(textoOriginal);
        const ranges = [];

        termos.forEach(termo => {
          let inicio = 0;
          while (inicio < textoNormalizado.length) {
            const idx = textoNormalizado.indexOf(termo, inicio);
            if (idx === -1) break;
            ranges.push([idx, idx + termo.length]);
            inicio = idx + termo.length;
          }
        });

        if (!ranges.length) return escapeHtml(textoOriginal);
        ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1]);

        const mesclados = [];
        ranges.forEach(range => {
          const ultimo = mesclados[mesclados.length - 1];
          if (!ultimo || range[0] > ultimo[1]) mesclados.push(range);
          else ultimo[1] = Math.max(ultimo[1], range[1]);
        });

        let saida = "";
        let cursor = 0;
        mesclados.forEach(([ini, fim]) => {
          saida += escapeHtml(textoOriginal.slice(cursor, ini));
          saida += '<mark class="leme-highlight">' + escapeHtml(textoOriginal.slice(ini, fim)) + '</mark>';
          cursor = fim;
        });
        saida += escapeHtml(textoOriginal.slice(cursor));
        return saida;
      }

      function optionHtml(valor) {
        return '<option value="' + escapeHtml(valor) + '">' + escapeHtml(valor) + '</option>';
      }

      function popularFiltros() {
        filtros.forEach(select => {
          const campo = select.dataset.campo;
          const valores = [...new Set(dados.map(item => item[campo]).filter(v => v && v !== "---"))].sort((a, b) => String(a).localeCompare(String(b)));
          valores.forEach(valor => select.insertAdjacentHTML("beforeend", optionHtml(valor)));
        });
      }

      function passaFiltros(item) {
        const termos = termosBusca();
        const texto = textoBusca(item);
        if (termos.length && !termos.every(t => texto.includes(t))) return false;

        for (const filtro of filtros) {
          const campo = filtro.dataset.campo;
          const valor = filtro.value;
          if (valor && item[campo] !== valor) return false;
        }
        return true;
      }

      function renderBadges(item) {
        const badges = [
          '<span class="leme-badge">' + escapeHtml(item.ano) + '</span>',
          '<span class="leme-badge green">' + escapeHtml(item.nivel) + '</span>',
          '<span class="leme-badge">' + escapeHtml(item.base) + '</span>'
        ];
        if (item.tipoProduto && item.tipoProduto !== "---") badges.push('<span class="leme-badge red">' + escapeHtml(item.tipoProduto) + '</span>');
        return badges.join("");
      }

      function renderTags(tags) {
        if (!tags || !tags.length) return "";
        return '<div class="leme-tags">' + tags.slice(0, 10).map(t => '<span class="leme-tag">' + highlightText(t) + '</span>').join("") + '</div>';
      }

      function renderActions(item) {
        const links = [];
        if (item.linkPdf) links.push('<a class="leme-link pdf" href="' + escapeHtml(item.linkPdf) + '" target="_blank" rel="noopener">📄 PDF</a>');
        if (item.linkProduto) links.push('<a class="leme-link produto" href="' + escapeHtml(item.linkProduto) + '" target="_blank" rel="noopener">📦 Produto</a>');
        return links.length ? '<div class="leme-actions">' + links.join("") + '</div>' : "";
      }

      function renderCards(lista) {
        if (!lista.length) {
          resultados.innerHTML = '<div class="leme-empty">Nenhum trabalho encontrado com os filtros selecionados.</div>';
          return;
        }

        resultados.innerHTML = lista.map(item => `
          <article class="leme-card">
            <h3 class="leme-card-title">${highlightText(item.titulo)}</h3>
            <div class="leme-meta">
              <div><b>Autor:</b> ${highlightText(item.autor)}</div>
              <div><b>Orientador:</b> ${highlightText(item.orientador)}</div>
              <div><b>Instituição/Campus:</b> ${highlightText(item.instituicaoCampus)}</div>
            </div>
            <div class="leme-badges">${renderBadges(item)}</div>
            <p class="leme-summary">${highlightText(item.resumoCurto || "Resumo não disponível.")}</p>
            <details>
              <summary>Ver detalhes da classificação e do trabalho</summary>
              <div class="leme-detail">
                <p><b>Produto educacional:</b> ${highlightText(item.produto)}</p>
                <p><b>Área temática:</b> ${highlightText(item.area)}</p>
                <p><b>Finalidade:</b> ${highlightText(item.finalidade)}</p>
                <p><b>Público-alvo:</b> ${highlightText(item.publicoAlvo)}</p>
                <p><b>Base epistemológica:</b> ${highlightText(item.base)}</p>
                <p><b>Linha de pesquisa:</b> ${highlightText(item.linhaPesquisa || "Não classificado")}</p>
                <p><b>Macroprojeto:</b> ${highlightText(item.macroprojeto || "Não classificado")}</p>
                <p><b>Código do macroprojeto:</b> ${highlightText(item.codigoMacroprojeto || "Não classificado")}</p>
                <p><b>Confiança Linha/Macro:</b> ${highlightText(item.confiancaLinhaMacro || "Baixa")} · <b>Revisão manual:</b> ${highlightText(item.revisaoManual || "Sim")}</p>
                <p><b>Justificativa Linha/Macro:</b> ${highlightText(item.justificativaLinhaMacro || "")}</p>
                <p><b>Resumo:</b> ${highlightText(item.resumo || "Resumo não disponível.")}</p>
                ${renderTags(item.palavrasChave)}
              </div>
            </details>
            ${renderActions(item)}
          </article>
        `).join("");
      }

      function renderTable(lista) {
        if (!lista.length) {
          resultados.innerHTML = '<div class="leme-empty">Nenhum trabalho encontrado com os filtros selecionados.</div>';
          return;
        }

        resultados.innerHTML = `
          <table class="leme-table">
            <thead>
              <tr>
                <th>Título</th><th>Autor</th><th>Orientador</th><th>Ano</th>
                <th>Nível</th><th>Base</th><th>Linha</th><th>Macroprojeto</th><th>Código</th><th>Área</th><th>Links</th>
              </tr>
            </thead>
            <tbody>
              ${lista.map(item => `
                <tr>
                  <td><div class="leme-table-title">${highlightText(item.titulo)}</div></td>
                  <td>${highlightText(item.autor)}</td>
                  <td>${highlightText(item.orientador)}</td>
                  <td>${escapeHtml(item.ano)}</td>
                  <td>${escapeHtml(item.nivel)}</td>
                  <td>${escapeHtml(item.base)}</td>
                  <td>${escapeHtml(item.linhaPesquisa || "Não classificado")}</td>
                  <td>${escapeHtml(item.macroprojeto || "Não classificado")}</td>
                  <td>${escapeHtml(item.codigoMacroprojeto || "Não classificado")}</td>
                  <td>${escapeHtml(item.area)}</td>
                  <td>${renderActions(item)}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        `;
      }

      function contarPorCampo(lista, campo) {
        const mapa = new Map();
        lista.forEach(item => {
          const valor = item[campo] && item[campo] !== "---" ? item[campo] : "Não identificado";
          mapa.set(valor, (mapa.get(valor) || 0) + 1);
        });
        return Array.from(mapa.entries())
          .map(([label, valor]) => ({ label, valor }))
          .sort((a, b) => b.valor - a.valor || String(a.label).localeCompare(String(b.label)));
      }

      function contarPorAno(lista) {
        const mapa = new Map();
        lista.forEach(item => {
          const valor = item.ano && item.ano !== "---" ? item.ano : "S/A";
          mapa.set(valor, (mapa.get(valor) || 0) + 1);
        });
        return Array.from(mapa.entries())
          .map(([label, valor]) => ({ label, valor }))
          .sort((a, b) => String(a.label).localeCompare(String(b.label)));
      }

      function destruirGrafico(nome) {
        if (graficos[nome]) {
          graficos[nome].destroy();
          graficos[nome] = null;
        }
      }

      function dadosLimitados(lista, limite) {
        return lista.slice(0, limite || 10);
      }

      function contarComListaFixa(lista, campo, valoresFixos) {
        const mapa = new Map();
        valoresFixos.forEach(valor => mapa.set(valor, 0));

        lista.forEach(item => {
          const valor = item[campo];
          if (!valor || valor === "---" || valor === "Não classificado") return;
          mapa.set(valor, (mapa.get(valor) || 0) + 1);
        });

        return Array.from(mapa.entries())
          .map(([label, valor]) => ({ label, valor }))
          .sort((a, b) => {
            if (b.valor !== a.valor) return b.valor - a.valor;
            return valoresFixos.indexOf(a.label) - valoresFixos.indexOf(b.label);
          });
      }

      function normalizarChaveOrientador(valor) {
        let texto = String(valor || "").trim();
        if (!texto || texto === "---") return "";

        texto = texto
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .toLowerCase()
          .replace(/\bdr[aª]?\b\.?/gi, " ")
          .replace(/\bprof[aª]?\b\.?/gi, " ")
          .replace(/[^a-z0-9\s]/g, " ")
          .replace(/\s+/g, " ")
          .trim();

        return texto;
      }

      function nomeExibicaoOrientador(valor) {
        const texto = String(valor || "").replace(/\s+/g, " ").trim();
        if (!texto || texto === "---") return "";
        return texto;
      }

      function contarOrientadores(lista, limite) {
        const mapa = new Map();

        lista.forEach(item => {
          const nomeBruto = item.orientador || "";
          const chave = item.orientadorChave || normalizarChaveOrientador(nomeBruto);
          const nomeExibicao = nomeExibicaoOrientador(nomeBruto);

          if (!chave || !nomeExibicao) return;

          if (!mapa.has(chave)) {
            mapa.set(chave, { label: nomeExibicao, valor: 0 });
          }

          mapa.get(chave).valor += 1;
        });

        return Array.from(mapa.values())
          .sort((a, b) => {
            if (b.valor !== a.valor) return b.valor - a.valor;
            return String(a.label).localeCompare(String(b.label), "pt-BR");
          })
          .slice(0, limite || 15);
      }

      function valorTooltip(ctx) {
        if (typeof ctx.parsed === "number") return Number(ctx.parsed || 0);
        if (ctx.chart && ctx.chart.options && ctx.chart.options.indexAxis === "y") {
          return Number(ctx.parsed.x || 0);
        }
        return Number(ctx.parsed.y || 0);
      }

      function criarOuAtualizarGrafico(nome, canvasId, config) {
        if (!window.Chart) return;
        const canvas = raiz.querySelector(canvasId);
        if (!canvas) return;
        destruirGrafico(nome);
        graficos[nome] = new Chart(canvas.getContext("2d"), config);
      }

      function atualizarGraficos(lista) {
        if (!window.Chart) return;

        const porAno = contarPorAno(lista);
        const porOrientador = contarOrientadores(lista, 15);
        const porBase = dadosLimitados(contarPorCampo(lista, "base"), 8);
        const porNivel = dadosLimitados(contarPorCampo(lista, "nivel"), 8);
        const porLinha = contarComListaFixa(lista, "linhaPesquisa", linhasOficiais);
        const porMacro = contarComListaFixa(lista, "macroprojeto", macroprojetosOficiais);

        const tooltip = {
          backgroundColor: "rgba(15, 23, 42, .94)",
          titleColor: "#fff",
          bodyColor: "#fff",
          borderColor: "rgba(255,255,255,.15)",
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            label: function(ctx) {
              const valor = valorTooltip(ctx);
              let total = ctx.dataset.data.reduce((soma, n) => soma + Number(n || 0), 0);

              if (ctx.chart.config.type === "doughnut") {
                total = ctx.dataset.data.reduce((soma, n, index) => {
                  return soma + (ctx.chart.getDataVisibility(index) ? Number(n || 0) : 0);
                }, 0);
              }

              const pct = total ? Math.round((Number(valor) / total) * 100) : 0;
              return " " + valor + " trabalho(s) · " + pct + "%";
            }
          }
        };

        const legendaRoscaRecalculada = {
          position: "bottom",
          labels: {
            boxWidth: 12,
            color: "#334155",
            font: { size: 11, weight: "700" },
            generateLabels: function(chart) {
              const baseLabels = Chart.overrides.doughnut.plugins.legend.labels.generateLabels(chart);
              const valores = chart.data.datasets[0].data || [];
              const totalVisivel = valores.reduce((soma, valor, index) => {
                return soma + (chart.getDataVisibility(index) ? Number(valor || 0) : 0);
              }, 0);

              return baseLabels.map(item => {
                const valor = Number(valores[item.index] || 0);
                const pct = chart.getDataVisibility(item.index) && totalVisivel
                  ? Math.round((valor / totalVisivel) * 100)
                  : 0;
                item.text = chart.data.labels[item.index] + " — " + valor + " (" + pct + "%)";
                return item;
              });
            }
          },
          onClick: function(event, legendItem, legend) {
            const chart = legend.chart;
            chart.toggleDataVisibility(legendItem.index);
            chart.update();
          }
        };

        const valueLabelPlugin = {
          id: "lemeValueLabel",
          afterDatasetsDraw(chart) {
            const tipo = chart.config.type;
            if (tipo === "doughnut") return;
            const ctx = chart.ctx;
            ctx.save();
            ctx.fillStyle = "#334155";
            ctx.font = "700 11px Segoe UI, Arial";
            ctx.textAlign = "center";
            chart.data.datasets.forEach((dataset, datasetIndex) => {
              const meta = chart.getDatasetMeta(datasetIndex);
              meta.data.forEach((element, index) => {
                const valor = dataset.data[index];
                if (!valor) return;
                const pos = element.tooltipPosition();
                if (chart.options.indexAxis === "y") {
                  ctx.textAlign = "left";
                  ctx.fillText(valor, pos.x + 8, pos.y + 4);
                } else {
                  ctx.textAlign = "center";
                  ctx.fillText(valor, pos.x, pos.y - 8);
                }
              });
            });
            ctx.restore();
          }
        };

        criarOuAtualizarGrafico("ano", "#leme-chart-ano", {
          type: "bar",
          data: {
            labels: porAno.map(d => d.label),
            datasets: [{
              label: "Trabalhos",
              data: porAno.map(d => d.valor),
              backgroundColor: "rgba(79, 70, 229, .82)",
              borderColor: "#3730a3",
              borderWidth: 1,
              borderRadius: 12,
              maxBarThickness: 44
            }]
          },
          plugins: [valueLabelPlugin],
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            plugins: { legend: { display: false }, tooltip },
            scales: {
              x: { grid: { display: false }, ticks: { color: "#64748b", font: { weight: "700" } } },
              y: { beginAtZero: true, ticks: { precision: 0, color: "#64748b" }, grid: { color: "rgba(148,163,184,.18)" } }
            }
          }
        });

        criarOuAtualizarGrafico("orientador", "#leme-chart-orientador", {
          type: "bar",
          data: {
            labels: porOrientador.map(d => d.label),
            datasets: [{
              label: "Trabalhos",
              data: porOrientador.map(d => d.valor),
              backgroundColor: porOrientador.map((_, i) => palette[i % palette.length]),
              borderRadius: 10,
              maxBarThickness: 28
            }]
          },
          plugins: [valueLabelPlugin],
          options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            plugins: { legend: { display: false }, tooltip },
            scales: {
              x: { beginAtZero: true, ticks: { precision: 0, color: "#64748b" }, grid: { color: "rgba(148,163,184,.18)" } },
              y: { grid: { display: false }, ticks: { color: "#334155", font: { size: 11, weight: "700" } } }
            }
          }
        });

        criarOuAtualizarGrafico("base", "#leme-chart-base", {
          type: "doughnut",
          data: {
            labels: porBase.map(d => d.label),
            datasets: [{
              data: porBase.map(d => d.valor),
              backgroundColor: porBase.map((_, i) => palette[i % palette.length]),
              borderColor: "#fff",
              borderWidth: 3,
              hoverOffset: 8
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "62%",
            plugins: {
              legend: legendaRoscaRecalculada,
              tooltip
            }
          }
        });

        criarOuAtualizarGrafico("nivel", "#leme-chart-nivel", {
          type: "bar",
          data: {
            labels: porNivel.map(d => d.label),
            datasets: [{
              label: "Trabalhos",
              data: porNivel.map(d => d.valor),
              backgroundColor: porNivel.map((_, i) => palette[(i + 2) % palette.length]),
              borderRadius: 12,
              maxBarThickness: 42
            }]
          },
          plugins: [valueLabelPlugin],
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            plugins: { legend: { display: false }, tooltip },
            scales: {
              x: { grid: { display: false }, ticks: { color: "#64748b", font: { size: 11, weight: "700" } } },
              y: { beginAtZero: true, ticks: { precision: 0, color: "#64748b" }, grid: { color: "rgba(148,163,184,.18)" } }
            }
          }
        });

        criarOuAtualizarGrafico("linha", "#leme-chart-linha", {
          type: "doughnut",
          data: {
            labels: porLinha.map(d => d.label),
            datasets: [{
              data: porLinha.map(d => d.valor),
              backgroundColor: porLinha.map((_, i) => palette[(i + 4) % palette.length]),
              borderColor: "#fff",
              borderWidth: 3,
              hoverOffset: 8
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "58%",
            plugins: { legend: legendaRoscaRecalculada, tooltip }
          }
        });

        criarOuAtualizarGrafico("macro", "#leme-chart-macro", {
          type: "bar",
          data: {
            labels: porMacro.map(d => d.label),
            datasets: [{
              label: "Trabalhos",
              data: porMacro.map(d => d.valor),
              backgroundColor: porMacro.map((_, i) => palette[(i + 1) % palette.length]),
              borderRadius: 10,
              maxBarThickness: 28
            }]
          },
          plugins: [valueLabelPlugin],
          options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 450 },
            plugins: { legend: { display: false }, tooltip },
            scales: {
              x: { beginAtZero: true, ticks: { precision: 0, color: "#64748b" }, grid: { color: "rgba(148,163,184,.18)" } },
              y: { grid: { display: false }, ticks: { color: "#334155", font: { size: 10, weight: "700" }, callback: function(value) { const label = this.getLabelForValue(value); return label.length > 42 ? label.slice(0, 42) + "..." : label; } } }
            }
          }
        });

        if (graficosNota) {
          graficosNota.textContent = lista.length === dados.length
            ? "Todos os trabalhos"
            : lista.length + " de " + dados.length + " trabalhos filtrados";
        }
      }

      function paginaLista(lista) {
        const totalPaginas = Math.max(1, Math.ceil(lista.length / itensPorPagina));
        if (paginaAtual > totalPaginas) paginaAtual = totalPaginas;
        const inicio = (paginaAtual - 1) * itensPorPagina;
        return lista.slice(inicio, inicio + itensPorPagina);
      }

      function paginasVisiveis(totalPaginas) {
        const paginas = new Set([1, totalPaginas, paginaAtual - 1, paginaAtual, paginaAtual + 1]);
        if (paginaAtual <= 3) [1,2,3,4].forEach(p => paginas.add(p));
        if (paginaAtual >= totalPaginas - 2) [totalPaginas - 3, totalPaginas - 2, totalPaginas - 1, totalPaginas].forEach(p => paginas.add(p));
        return [...paginas].filter(p => p >= 1 && p <= totalPaginas).sort((a, b) => a - b);
      }

      function botaoPagina(rotulo, pagina, extraClasse, disabled) {
        return '<button type="button" class="leme-page-btn ' + (extraClasse || "") + '" data-pagina="' + pagina + '" ' + (disabled ? "disabled" : "") + '>' + rotulo + '</button>';
      }

      function renderPaginacao(totalItens) {
        const totalPaginas = Math.max(1, Math.ceil(totalItens / itensPorPagina));
        if (!totalItens || totalPaginas <= 1) {
          paginacao.innerHTML = "";
          return;
        }

        let html = botaoPagina("Anterior", Math.max(1, paginaAtual - 1), "", paginaAtual === 1);
        const visiveis = paginasVisiveis(totalPaginas);
        let anterior = 0;

        visiveis.forEach(p => {
          if (anterior && p - anterior > 1) html += '<span class="leme-pagination-info" style="width:auto;margin:0;">...</span>';
          html += botaoPagina(String(p), p, p === paginaAtual ? "is-active" : "", false);
          anterior = p;
        });

        html += botaoPagina("Próximo", Math.min(totalPaginas, paginaAtual + 1), "", paginaAtual === totalPaginas);

        const inicio = (paginaAtual - 1) * itensPorPagina + 1;
        const fim = Math.min(paginaAtual * itensPorPagina, totalItens);
        html += '<div class="leme-pagination-info">Exibindo ' + inicio + '–' + fim + ' de ' + totalItens + ' resultados</div>';
        paginacao.innerHTML = html;
      }

      function renderResultadosPaginados() {
        const pagina = paginaLista(resultadosAtuais);
        resultados.classList.toggle("is-table", modo === "table");
        if (modo === "table") renderTable(pagina);
        else renderCards(pagina);
        renderPaginacao(resultadosAtuais.length);
      }

      function aplicarFiltros(resetPagina) {
        if (resetPagina) paginaAtual = 1;
        const filtrados = dados.filter(passaFiltros);
        resultadosAtuais = filtrados;
        contador.innerHTML = '<strong>' + filtrados.length + '</strong> trabalhos encontrados de <strong>' + dados.length + '</strong> analisados';
        atualizarGraficos(filtrados);
        renderResultadosPaginados();
      }

      function valorExportavel(valor) {
        if (Array.isArray(valor)) return valor.join("; ");
        return String(valor || "").replace(/\s+/g, " ").trim();
      }

      function linhasExportacao(lista) {
        const colunas = [
          ["ano", "Ano"], ["autor", "Autor"], ["orientador", "Orientador"],
          ["titulo", "Título"], ["produto", "Produto"], ["tipoProduto", "Tipo de produto"],
          ["nivel", "Nível"], ["base", "Base epistemológica"],
          ["linhaPesquisa", "Linha de Pesquisa"], ["macroprojeto", "Macroprojeto"],
          ["codigoMacroprojeto", "Código do Macroprojeto"],
          ["confiancaLinhaMacro", "Confiança Linha/Macro"], ["termosLinhaMacro", "Termos Detectados Linha/Macro"],
          ["justificativaLinhaMacro", "Justificativa Linha/Macro"], ["revisaoManual", "Revisão Manual"],
          ["area", "Área temática"],
          ["finalidade", "Finalidade"], ["publicoAlvo", "Público-alvo"],
          ["instituicaoCampus", "Instituição/Campus"], ["palavrasChave", "Palavras-chave"],
          ["linkPdf", "Link do PDF"], ["linkProduto", "Link do produto"]
        ];
        const linhas = [colunas.map(c => c[1])];
        lista.forEach(item => linhas.push(colunas.map(([campo]) => valorExportavel(item[campo]))));
        return linhas;
      }

      function csvEscape(valor) {
        const texto = String(valor || "");
        return '"' + texto.replace(/"/g, '""') + '"';
      }

      function exportarResultadosCsv() {
        const linhas = linhasExportacao(resultadosAtuais);
        const csv = linhas.map(linha => linha.map(csvEscape).join(";")).join("\r\n");
        const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const data = new Date().toISOString().slice(0, 10);
        const a = document.createElement("a");
        a.href = url;
        a.download = "resultados_filtrados_leme_ept_" + data + ".csv";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      function copiarResultadosTabela() {
        const texto = linhasExportacao(resultadosAtuais)
          .map(linha => linha.map(valor => String(valor || "").replace(/\t/g, " ").replace(/\n/g, " ")).join("\t"))
          .join("\n");

        const confirmar = () => {
          const original = copiarResultados.textContent;
          copiarResultados.textContent = "✅ Copiado";
          setTimeout(() => { copiarResultados.textContent = original; }, 1600);
        };

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(texto).then(confirmar).catch(() => copiarFallback(texto, confirmar));
        } else {
          copiarFallback(texto, confirmar);
        }
      }

      function copiarFallback(texto, callback) {
        const area = document.createElement("textarea");
        area.value = texto;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.left = "-9999px";
        document.body.appendChild(area);
        area.select();
        try { document.execCommand("copy"); callback(); }
        finally { document.body.removeChild(area); }
      }

      function limparFiltros() {
        busca.value = "";
        filtros.forEach(f => f.value = "");
        aplicarFiltros(true);
        busca.focus();
      }

      busca.addEventListener("input", () => aplicarFiltros(true));
      limpar.addEventListener("click", limparFiltros);
      filtros.forEach(f => f.addEventListener("change", () => aplicarFiltros(true)));
      if (exportarCsv) exportarCsv.addEventListener("click", exportarResultadosCsv);
      if (copiarResultados) copiarResultados.addEventListener("click", copiarResultadosTabela);

      paginacao.addEventListener("click", function(e) {
        const botao = e.target.closest("button[data-pagina]");
        if (!botao || botao.disabled) return;
        paginaAtual = Number(botao.dataset.pagina) || 1;
        renderResultadosPaginados();
        resultados.scrollIntoView({ behavior: "smooth", block: "start" });
      });

      btnCards.addEventListener("click", function() {
        modo = "cards";
        btnCards.classList.add("is-active");
        btnTable.classList.remove("is-active");
        paginaAtual = 1;
        renderResultadosPaginados();
      });

      btnTable.addEventListener("click", function() {
        modo = "table";
        btnTable.classList.add("is-active");
        btnCards.classList.remove("is-active");
        paginaAtual = 1;
        renderResultadosPaginados();
      });

      popularFiltros();
      carregarChartJs(() => aplicarFiltros(true));
      aplicarFiltros(true);
    })();
  </script>
</section>
'''

    html = html.replace("__ATUALIZADO_EM__", atualizado_em)
    html = html.replace("__PERIODO__", periodo)
    html = html.replace("__TOTAL__", str(total))
    html = html.replace("__TOTAL_PRODUTOS__", str(total_produtos))
    html = html.replace("__TOTAL_ORIENTADORES__", str(total_orientadores))
    html = html.replace("__TOTAL_BASES__", str(total_bases))
    html = html.replace("__DADOS_JSON__", dados_json)

    return html


def salvar_html(html, arquivo=ARQUIVO_HTML_SAIDA):
    Path(arquivo).write_text(html, encoding="utf-8")


def main():
    print(f"Lendo planilha revisada: {ARQUIVO_ENTRADA}")
    df = carregar_planilha(ARQUIVO_ENTRADA)

    print("Preparando dados para o HTML sem recalcular classificações...")
    registros = preparar_dados_para_html(df)

    print("Gerando painel HTML...")
    html = gerar_html(registros)
    salvar_html(html, ARQUIVO_HTML_SAIDA)

    print("Painel gerado com sucesso!")
    print(f"Arquivo HTML: {ARQUIVO_HTML_SAIDA}")
    print(f"Total de trabalhos no painel: {len(registros)}")


if __name__ == "__main__":
    main()
