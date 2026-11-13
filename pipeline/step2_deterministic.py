import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf
import requests
import urllib3
from bs4 import BeautifulSoup

from pipeline.models_v4 import (
    ContratoExtracaoDeterministicaV4,
    DissertacaoDeterministica,
    EvidenciasEduCAPES,
    MetadadosResolvidos,
    RecortesTextuais,
    TrechoEpistemologico,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- REGRAS CANÔNICAS PROFEPT ---
MAPEAMENTO_MP_LP = {
    "MP1": "LP1",
    "MP2": "LP1",
    "MP3": "LP1",
    "MP4": "LP2",
    "MP5": "LP2",
    "MP6": "LP2",
}

REGRAS_TIPO_PRODUTO: List[Tuple[str, str]] = [
    ("software_aplicativo", r"\b(software|aplicativo|app|plataforma\s+virtual|sistema\s+web|portal|website|ambiente\s+virtual|ava|moodle)\b"),
    ("manual_protocolo", r"\b(manual|protocolo|guia\s+de\s+instru[cç][oõ]es|procedimento\s+operacional)\b"),
    ("carta_mapa", r"\b(carta\s+pedag[oó]gica|mapa\s+conceitual|mapa\s+interativo|atlas)\b"),
    ("eventos_organizados", r"\b(exposi[cç][aã]o|mostra\s+cient[ií]fica|feira\s+de|olimp[ií]ada|semin[aá]rio|evento\s+cient[ií]fico)\b"),
    ("acervo", r"\b(acervo|curadoria|cole[cç][aã]o\s+digital|reposit[oó]rio|banco\s+de\s+dados)\b"),
    ("produto_comunicacao", r"\b(podcast|programa\s+de\s+r[aá]dio|programa\s+de\s+tv|campanha\s+publicit[aá]ria|boletim|jornal|revista\s+de\s+divulga[cç][aã]o)\b"),
    ("tecnologia_social", r"\b(tecnologia\s+social|dispositivo|equipamento|inova[cç][aã]o\s+social|prot[oó]tipo)\b"),
    ("material_didatico_instrucional", r"\b(material\s+did[aá]tico|sequ[eê]ncia\s+did[aá]tica|cartilha|e-?book|livro\s+digital|caderno|roteiro|proposta\s+pedag[oó]gica|proposta\s+de\s+interven[cç][aã]o|jogo|hist[oó]ria\s+em\s+quadrinhos|hq|gloss[aá]rio|v[ií]deo|videoaula|anima[cç][aã]o|guia|texto\s+de\s+apoio|objeto\s+de\s+aprendizagem)\b"),
    ("curso_oficina", r"\b(curso\s+de\s+forma[cç][aã]o|curso\s+livre|curso\s+fic|curso\s+online|curso\s+autoformativo|oficina|minicurso|workshop)\b"),
]

def normalizar_espacos(texto: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", texto)).strip()


def remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def extrair_sentenca_produto(texto: str) -> str:
    if not texto:
        return ""
    sentencas = re.split(r"(?<=[.!?])\s+", texto)
    relevantes = [s for s in sentencas if re.search(r"produto\s+educacional", s, flags=re.IGNORECASE)]
    return " ".join(relevantes)

def classificar_produto_regex(*fontes_texto: Optional[str]) -> Optional[str]:
    """Aplica regex em ordem de prioridade (dissertação/rótulo bruto primeiro, eduCAPES depois)."""
    for fonte in fontes_texto:
        if not fonte:
            continue
        limpo = fonte.strip().lower()
        for tipo_canonico, padrao in REGRAS_TIPO_PRODUTO:
            if re.search(padrao, limpo, flags=re.IGNORECASE):
                return tipo_canonico
    return None


def detectar_macroprojeto_e_linha(texto_completo_pdf: str) -> Tuple[str, str]:
    """
    Varre o texto completo do PDF buscando assinaturas explícitas de MP1..MP6
    (por número ou título) e aplica o vínculo rígido MP1-3 -> LP1 | MP4-6 -> LP2.
    """
    # Normaliza: remove acentos, quebras de linha e espaços múltiplos
    txt_limpo = re.sub(r"\s+", " ", remover_acentos(texto_completo_pdf)).lower()
    # Versão condensada sem espaços para capturar PDFs com fontes coladas (ex: EPT-0085)
    txt_colado = re.sub(r"[^a-z0-9]", "", txt_limpo)

    # 1. Padrão numérico explícito (evitando falso positivo de "mp4" formato de vídeo)
    padroes_num = [
        r"\bmacro\s*[-]?\s*projeto(?:\s+de\s+pesquisa(?:\s+e\s+desenvolvimento)?)?\s*[:\-–]?\s*([1-6]|i{1,3}|iv|v|vi)\b",
        r"\bmp\s*[-]?\s*([1-35-6])\b",       # MP1, MP2, MP3, MP5, MP6
        r"\bmp\s*[-]?\s*4(?!\s*(?:;|,|\)|\.|\b(?:video|formato|extensao|duracao|mb|audio)))\b",  # MP4 apenas se não for formato de vídeo
    ]
    romanos = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6"}

    for padrao in padroes_num:
        m = re.search(padrao, txt_limpo)
        if m:
            val = m.group(1).lower()
            num = romanos.get(val, val)
            mp = f"MP{num}"
            return mp, MAPEAMENTO_MP_LP[mp]

    # 2. Match pelos títulos canônicos dos Macroprojetos (tolerante a preposições e PDF sem espaço)
    assinaturas_mp = [
        ("MP1", r"propostas\s+metodologicas\s+e\s+recursos\s+didaticos", "propostasmetodologicase"),
        ("MP2", r"inclusao\s+e\s+diversidade\s+(?:em|nos)\s+espacos", "inclusaoediversidade"),
        ("MP3", r"praticas\s+educativas\s+no\s+curriculo\s+integrado", "praticaseducativasnocurriculointegrado"),
        ("MP4", r"historia\s+e\s+memorias?\s+no\s+contexto", "historiaememoriasnocontexto"),
        ("MP5", r"organizacao\s+do\s+curriculo\s+integrado", "organizacaodocurriculointegrado"),
        ("MP6", r"organizacao\s+(?:de|dos)\s+espacos\s+pedagogicos", "organizacaodeespacospedagogicos"),
    ]
    for mp, regex_espacado, slug_colado in assinaturas_mp:
        if re.search(regex_espacado, txt_limpo) or slug_colado in txt_colado:
            return mp, MAPEAMENTO_MP_LP[mp]

    # 3. Fallback apenas para Linha de Pesquisa (quando o autor declara a LP mas omite o MP)
    if re.search(r"praticas\s+(?:educativas|educacionais|pedagogicas)\s+(?:em|na)\s+(?:ept|educacao\s+profissional)", txt_limpo) or re.search(r"\blp\s*[-]?\s*1\b", txt_limpo):
        return "MP_INDEFINIDO", "LP1"

    if re.search(r"(?:organizac[aã]o\s+e\s+memorias?|memorias?\s+e\s+organizac[aã]o)\s+(?:de|dos)\s+espacos\s+pedagogicos", txt_limpo) or re.search(r"\blp\s*[-]?\s*2\b", txt_limpo):
        return "MP_INDEFINIDO", "LP2"

    return "MP_INDEFINIDO", "LP_INDEFINIDA"

def extrair_coorientador(texto_preliminar: str) -> List[str]:
    padrao = re.compile(
        r"Coorientador(?:a|\(a\))?\s*:\s*(?:Prof\.?\s*(?:Dr\.?|Me\.?|Ma\.?|Esp\.?)\s*)*([^\n\r]+)",
        flags=re.IGNORECASE,
    )
    encontrados = []
    for m in padrao.finditer(texto_preliminar):
        nome = re.sub(r"\s*\(.*?\)", "", m.group(1)).strip(" .;-")
        if 4 <= len(nome) <= 90 and nome not in encontrados:
            encontrados.append(nome)
    return encontrados


def extrair_palavras_chave_resumo(bloco_resumo: str) -> List[str]:
    match = re.search(
        r"Palavras-chave\s*:\s*(.+?)(?=\n\s*\n|Abstract|Keywords|$)",
        bloco_resumo,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []
    bruto = re.sub(r"\s+", " ", match.group(1)).strip().rstrip(".")
    # Suporta separadores por ponto, ponto-e-vírgula ou vírgula
    sep = ";" if ";" in bruto else ("." if "." in bruto else ",")
    tags = []
    for item in bruto.split(sep):
        limpa = item.strip(" .;-–—")
        if 2 <= len(limpa) <= 80:
            tags.append(limpa)
    return tags


# --- EXTRAÇÃO DE TEXTO E RECORTES DO PDF ---
def ler_paginas_pdf(pdf_path: Path) -> List[Tuple[int, str]]:
    """Retorna lista de tuplas (numero_pagina_1_based, texto_limpo)."""
    paginas = []
    with pymupdf.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            txt = page.get_text("text") or ""
            paginas.append((idx, normalizar_espacos(txt)))
    return paginas


def isolar_secoes_pdf(paginas: List[Tuple[int, str]]) -> RecortesTextuais:
    if not paginas:
        return RecortesTextuais()

    # 1. Pré-textuais (primeiras 14 páginas cobrem capa, folha de rosto, ficha, ata, resumo e sumário)
    pre_textuais = paginas[:14]
    capa = "\n\n".join(txt for _, txt in pre_textuais[:2])

    ficha = ""
    resumo = ""
    sumario = ""

    for num_pag, txt in pre_textuais:
        upper = txt.upper()
        if not ficha and ("FICHA CATALOGRÁFICA" in upper or "CDD" in upper or "CDU" in upper):
            ficha = f"[PÁG. {num_pag}]\n{txt}"
        if not resumo and re.search(r"(^|\n)\s*RESUMO\s*(\n|$)", upper):
            resumo = f"[PÁG. {num_pag}]\n{txt}"
        if not sumario and re.search(r"(^|\n)\s*SUM[ÁA]RIO\s*(\n|$)", upper):
            # Captura página do sumário e a seguinte caso seja longo
            prox = paginas[num_pag][1] if num_pag < len(paginas) else ""
            sumario = f"[PÁG. {num_pag}]\n{txt}\n{prox[:1500]}"

    # 2. Localizar início da Introdução e das Referências
    idx_intro = None
    idx_refs = None

    for i, (num_pag, txt) in enumerate(paginas):
        if num_pag <= 5:
            continue
        linhas_topo = "\n".join(txt.splitlines()[:8])
        if idx_intro is None and re.search(r"(^|\n)\s*(?:[1-3]\.?\s+)?INTRODU[ÇC][ÃA]O\s*$", linhas_topo, flags=re.IGNORECASE | re.MULTILINE):
            # Garante que não é a linha do Sumário (que contém pontos ".....")
            if "...." not in linhas_topo:
                idx_intro = i
        if re.search(r"(^|\n)\s*REFER[ÊE]NCIAS(?:\s+BIBLIOGR[ÁA]FICAS)?\s*$", linhas_topo, flags=re.IGNORECASE | re.MULTILINE):
            idx_refs = i

    introducao_paginas = paginas[idx_intro : idx_intro + 5] if idx_intro is not None else paginas[8:13]
    introducao = "\n\n".join(f"[PÁG. {p}]\n{t}" for p, t in introducao_paginas)[:8000]

    # 3. Seção de descrição do Produto Educacional (geralmente no capítulo metodológico ou capítulo final antes das referências)
    fim_corpo = idx_refs if idx_refs is not None else len(paginas)
    corpo_paginas = paginas[(idx_intro or 8) : fim_corpo]

    trechos_produto = []
    for p, t in corpo_paginas:
        if re.search(r"\bproduto\s+educacional\b", t, flags=re.IGNORECASE):
            # Extrai apenas parágrafos relevantes onde "produto educacional" aparece
            for paragrafo in t.split("\n\n"):
                if re.search(r"produto\s+educacional", paragrafo, flags=re.IGNORECASE) and len(paragrafo) > 80:
                    trechos_produto.append(f"[PÁG. {p}] {paragrafo.strip()}")
                    if len(trechos_produto) >= 6:
                        break
        if len(trechos_produto) >= 6:
            break

    descricao_produto = "\n\n".join(trechos_produto)[:3500]

    # 4. Evidências Epistemológicas (Introdução + Referencial/Metodologia) + Citações detectadas
    trechos_epist: List[TrechoEpistemologico] = []
    citacoes_unicas = set()

    marcadores_epist = re.compile(
        r"\b(epistemol[óo]g|ontol[óo]g|materialismo\s+hist[óo]rico|dial[ée]tic|freire|saviani|ciavatta|frigotto|ramos|gramsci|kosik|luk[áa]cs|vygotsky|vigotski|bakhtin|foucault|bourdieu|morin|positivis|fenomenolog|hermeneut|construtivis|omnilateral|politecnia|trabalho\s+como\s+princ[íi]pio\s+educativo|curr[íi]culo\s+integrado)\b",
        flags=re.IGNORECASE,
    )
    padrao_citacao = re.compile(r"\(([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s;&.-]+?,\s*\d{4}[a-z]?(?:,\s*p\.\s*\d+(?:-\d+)?)?)\)")

    for p, t in corpo_paginas:
        if len(trechos_epist) >= 12:
            break
        for paragrafo in t.split("\n\n"):
            if len(paragrafo) < 120:
                continue
            if marcadores_epist.search(paragrafo):
                cits = padrao_citacao.findall(paragrafo)
                for c in cits:
                    sobrenome = c.split(",")[0].strip().split()[0].upper()
                    if len(sobrenome) >= 3:
                        citacoes_unicas.add(sobrenome)
                trechos_epist.append(
                    TrechoEpistemologico(
                        secao="Introdução" if (idx_intro is not None and p <= paginas[idx_intro][0] + 4) else "Corpo/Fundamentação",
                        pagina=p,
                        texto=paragrafo.strip()[:1200],
                        citacoes_detectadas=cits[:8],
                    )
                )
                if len(trechos_epist) >= 12:
                    break

    # 5. Filtrar na seção de Referências apenas as obras correspondentes às citações detectadas
    referencias_filtradas = []
    if idx_refs is not None and citacoes_unicas:
        texto_refs = "\n".join(t for _, t in paginas[idx_refs : idx_refs + 15])
        # Divide entradas bibliográficas (linhas começando com SOBRENOME em caixa alta)
        entradas = re.split(r"\n(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}[,\s])", texto_refs)
        for entrada in entradas:
            entrada_limpa = re.sub(r"\s+", " ", entrada).strip()
            if len(entrada_limpa) < 25:
                continue
            primeiro_token = re.split(r"[,.\s]", entrada_limpa)[0].upper()
            if primeiro_token in citacoes_unicas:
                referencias_filtradas.append(entrada_limpa[:400])
                if len(referencias_filtradas) >= 25:
                    break

    return RecortesTextuais(
        capa=capa[:2500],
        ficha_catalografica=ficha[:2500],
        sumario=sumario[:3000],
        resumo=resumo[:3500],
        introducao=introducao,
        descricao_produto_na_dissertacao=descricao_produto,
        trechos_epistemologicos=trechos_epist,
        referencias_filtradas=referencias_filtradas,
    )


# --- SCRAPING RESILIENTE DO EDUCAPES ---
def coletar_evidencias_educapes(
    handle_url: Optional[str],
    titulo_produto_bruto: Optional[str],
    resumo_pdf: str,
    descricao_produto_pdf: str,
    cache_dir: Path,
) -> EvidenciasEduCAPES:
    if not handle_url:
        tipo_regex = classificar_produto_regex(titulo_produto_bruto, descricao_produto_pdf)
        return EvidenciasEduCAPES(
            titulo_produto=titulo_produto_bruto,
            tipo_produto_regex=tipo_regex,
        )

    # Normaliza URL para carregar a página completa (?show=full no DSpace revela todos os campos Dublin Core)
    base_url = handle_url.strip().rstrip("/")
    full_url = base_url if "show=full" in base_url else f"{base_url}?show=full"

    slug_cache = re.sub(r"[^a-zA-Z0-9_-]", "_", base_url.split("handle/")[-1])
    cache_file = cache_dir / f"{slug_cache}.html"

    html = ""
    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8", errors="ignore")
    else:
        try:
            resp = requests.get(
                full_url,
                timeout=20,
                verify=False,
                headers={"User-Agent": "Mozilla/5.0 (LEME-EPT Bibliometric Pipeline)"},
            )
            if resp.status_code == 200:
                html = resp.text
                cache_file.write_text(html, encoding="utf-8")
                time.sleep(0.6)  # Respeita rate-limit institucional
        except requests.RequestException as e:
            print(f"  [eduCAPES] Falha ao acessar {full_url}: {e}")

    titulo_capes = None
    data_pub = None
    dc_types: List[str] = []
    keywords: List[str] = []
    autores_colab: List[Dict[str, str]] = []
    identificadores: List[Dict[str, str]] = [{"esquema": "handle", "valor": base_url.split("handle/")[-1], "url": base_url}]
    colecao = None

    if html:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Tags <meta> Dublin Core no <head> (padrão universal DSpace/eduCAPES)
        for meta in soup.find_all("meta"):
            nome_meta = (meta.get("name") or "").lower().strip()
            conteudo = (meta.get("content") or "").strip()
            if not conteudo:
                continue

            if nome_meta == "dc.title" and not titulo_capes:
                titulo_capes = conteudo
            elif nome_meta in ("dcterms.issued", "dc.date.issued") and not data_pub:
                data_pub = conteudo[:10]
            elif nome_meta == "dc.type" and conteudo not in dc_types:
                dc_types.append(conteudo)
            elif nome_meta in ("dc.subject", "dcterms.subject") and conteudo not in keywords:
                keywords.append(conteudo)
            elif nome_meta in ("dc.contributor", "dc.creator"):
                papel = meta.get("scheme") or nome_meta.replace("dc.", "")
                autores_colab.append({"nome": conteudo, "papel": papel})
            elif nome_meta in ("dc.identifier", "dcterms.identifier") and "handle" not in conteudo:
                identificadores.append({"esquema": "identifier", "valor": conteudo, "url": ""})

        # 2. Tabela Dublin Core do DSpace (?show=full)
        for tr in soup.select("table tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            campo = tds[0].get_text(strip=True).lower()
            valor = tds[1].get_text(" ", strip=True)
            if not valor:
                continue

            if campo == "dc.title" and not titulo_capes:
                titulo_capes = valor
            elif campo == "dc.date.issued" and not data_pub:
                data_pub = valor[:10]
            elif campo == "dc.type":
                dc_types.append(valor)
            elif campo in ("dc.subject", "dc.subject.other"):
                if valor not in keywords:
                    keywords.append(valor)
            elif campo.startswith("dc.contributor"):
                papel = campo.replace("dc.contributor.", "") if "." in campo[14:] else "colaborador"
                autores_colab.append({"nome": valor, "papel": papel})
            elif campo.startswith("dc.identifier.") and campo != "dc.identifier.uri":
                identificadores.append({"esquema": campo.replace("dc.identifier.", ""), "valor": valor, "url": ""})

        # Coleção ("Aparece nas coleções:")
        for li in soup.select("ul.ds-referenceSet-list li a, .item-page-field-wrapper a[href*='/handle/']"):
            href = li.get("href", "")
            texto_link = li.get_text(strip=True)
            if texto_link and "capes" in href and href not in base_url:
                colecao = texto_link
                break

    # Hierarquia de fontes: Rótulo/dissertação primeiro, dc.type do eduCAPES apenas como evidência complementar
    sentenca_resumo = extrair_sentenca_produto(resumo_pdf)
    sentenca_corpo = extrair_sentenca_produto(descricao_produto_pdf)
    
    # Lembre-se de usar também na branch `if not handle_url:` no topo da função!
    tipo_regex = classificar_produto_regex(
        titulo_produto_bruto,
        sentenca_resumo,
        sentenca_corpo,
        titulo_capes,
        " ".join(dc_types),
    )

    return EvidenciasEduCAPES(
        handle_url=base_url,
        titulo_produto=titulo_capes or titulo_produto_bruto,
        data_publicacao=data_pub,
        autores_colaboradores=autores_colab,
        identificadores=identificadores,
        colecao_educapes=colecao,
        dc_type_educapes=dc_types,
        palavras_chave_educapes=keywords,
        tipo_produto_regex=tipo_regex,
    )


# --- ORQUESTRAÇÃO DA ETAPA 2 ---
def executar_etapa2(
    manifest_path: Path = Path("data/stage1_manifest.json"),
    output_dir: Path = Path("data/stage2_payloads"),
    cache_dir: Path = Path("data/cache_educapes"),
):
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifesto da Etapa 1 não encontrado: {manifest_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifesto = json.load(f)

    registros = manifesto if isinstance(manifesto, list) else manifesto.get("registros", manifesto.get("defesas", []))
    print(f"Iniciando Etapa 2 para {len(registros)} defesas...")

    processados = 0
    erros = []

    for item in registros:
        cod = item["id"]
        fonte = item["fonte_profept"]
        arquivos = item["arquivos"]
        pdf_path = Path(arquivos["pdf_dissertacao_path"])

        try:
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF ausente: {pdf_path}")

            paginas = ler_paginas_pdf(pdf_path)
            texto_full_pdf = "\n".join(txt for _, txt in paginas)
            recortes = isolar_secoes_pdf(paginas)

            bloco_preliminar = f"{recortes.capa}\n{recortes.ficha_catalografica}\n{recortes.resumo}"
            bloco_busca_mp = f"{recortes.capa}\n{recortes.ficha_catalografica}\n{recortes.resumo}\n{recortes.introducao}"
            mp, lp = detectar_macroprojeto_e_linha(texto_full_pdf)
            coorientadores = extrair_coorientador(bloco_preliminar)
            kw_dissertacao = extrair_palavras_chave_resumo(recortes.resumo)

            titulo_bruto_prod = fonte.get("titulo_produto_bruto")
            evidencias_capes = coletar_evidencias_educapes(
                handle_url=fonte.get("handle_educapes"),
                titulo_produto_bruto=titulo_bruto_prod,
                resumo_pdf=recortes.resumo,
                descricao_produto_pdf=recortes.descricao_produto_na_dissertacao,
                cache_dir=cache_dir,
            )

            payload = ContratoExtracaoDeterministicaV4(
                id=cod,
                metadados_resolvidos=MetadadosResolvidos(
                    ano=int(fonte["ano"]),
                    autor=fonte["autor_bruto"].strip(),
                    orientador=(fonte.get("orientador_bruto") or "").strip(),
                    coorientadores=coorientadores,
                    instituicao="Instituto Federal Catarinense (IFC)",
                    campus=fonte.get("campus") or "Blumenau",
                    linha_pesquisa=lp,
                    macroprojeto=mp,
                ),
                dissertacao_deterministica=DissertacaoDeterministica(
                    titulo=fonte["titulo_bruto"].strip(),
                    link=fonte["url_dissertacao"],
                    palavras_chave=kw_dissertacao,
                ),
                evidencias_educapes=evidencias_capes,
                recortes_textuais=recortes,
            )

            out_file = output_dir / f"{cod}.json"
            with open(out_file, "w", encoding="utf-8") as out:
                json.dump(payload.model_dump(), out, ensure_ascii=False, indent=2)

            processados += 1
            if processados % 15 == 0 or processados == len(registros):
                print(f"  [{processados}/{len(registros)}] {cod} -> MP:{mp} | LP:{lp} | TipoRegex:{evidencias_capes.tipo_produto_regex}")

        except Exception as e:
            erros.append((cod, str(e)))
            print(f"  [ERRO] {cod}: {e}")

    print("\n--- Resumo Etapa 2 ---")
    print(f"Payloads gerados com sucesso: {processados}/{len(registros)}")
    if erros:
        print(f"Falhas ({len(erros)}): {erros}")


if __name__ == "__main__":
    executar_etapa2()

