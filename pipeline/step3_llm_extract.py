import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from pipeline.llm_provider import LLMClient
from pipeline.models_v4 import (
    ContratoDefesaV4,
    ContratoExtracaoDeterministicaV4,
    RespostaInterpretativaLLM,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("step3_llm_extract")

SKILL_PATH = Path("pipeline/SKILL.md")
STAGE2_DIR = Path("data/stage2_payloads")
RECORDS_DIR = Path("data/records")

MP_PARA_LP = {
    "MP1": "LP1",
    "MP2": "LP1",
    "MP3": "LP1",
    "MP4": "LP2",
    "MP5": "LP2",
    "MP6": "LP2",
}


def normalizar_texto_busca(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    sem_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-z0-9\s]", " ", sem_acentos)
    return re.sub(r"\s+", " ", limpo).strip()


def limpar_palavras_chave(tags: List[str]) -> List[str]:
    vistas: Dict[str, str] = {}
    for tag in tags:
        if not isinstance(tag, str):
            continue
        limpa = re.sub(r"^[\s\-–—.;:]+|[\s\-–—.;:]+$", "", tag).strip()
        if len(limpa) < 2:
            continue
        chave = normalizar_texto_busca(limpa)
        if chave and chave not in vistas:
            vistas[chave] = limpa[0].upper() + limpa[1:]
    return list(vistas.values())


def construir_indice_busca(registro: Dict[str, Any]) -> Dict[str, Any]:
    dis = registro.get("dissertacao", {})
    pro = registro.get("produto", {})

    tags_unificadas = limpar_palavras_chave(
        (dis.get("palavras_chave") or []) + (pro.get("palavras_chave") or [])
    )

    blocos = [
        registro.get("id", ""),
        str(registro.get("ano", "")),
        registro.get("autor", ""),
        registro.get("orientador", ""),
        " ".join(registro.get("coorientadores") or []),
        registro.get("campus", ""),
        registro.get("linha_pesquisa", ""),
        registro.get("macroprojeto", ""),
        dis.get("titulo", ""),
        dis.get("resumo", ""),
        pro.get("titulo", ""),
        pro.get("tipo", ""),
        pro.get("nivel_aplicacao", ""),
        " ".join(tags_unificadas),
        " ".join(dis.get("autores_referenciados") or []),
    ]

    return {
        "texto_busca_normalizado": normalizar_texto_busca(" ".join(filter(None, blocos))),
        "termos_unificados": tags_unificadas,
        "tem_produto_vinculado": bool(pro.get("link")),
        "tem_resumo": bool(dis.get("resumo") and len(dis.get("resumo", "").strip()) > 30),
    }


def montar_prompt_enxuto(payload: ContratoExtracaoDeterministicaV4) -> str:
    """
    Filtra apenas os campos semanticamente relevantes e limita o volume textual
    para caber com folga em 8k de contexto na GPU local (~5k-6k tokens).
    """
    rec = payload.recortes_textuais
    edu = payload.evidencias_educapes

    contexto_enxuto = {
        "id": payload.id,
        "titulo_dissertacao": payload.dissertacao_deterministica.titulo,
        "macroprojeto_pre_detectado": payload.metadados_resolvidos.macroprojeto,
        "evidencias_produto": {
            "titulo_educapes": edu.titulo_produto,
            "colecao_educapes": edu.colecao_educapes,
            "dc_type_educapes": edu.dc_type_educapes,
            "tipo_sugerido_regex": edu.tipo_produto_regex,
            "descricao_na_dissertacao": rec.descricao_produto_na_dissertacao[:2500],
        },
        "resumo": rec.resumo[:3000],
        "introducao_recorte": rec.introducao[:5500],
        "trechos_epistemologicos": [
            {
                "secao": t.secao,
                "pagina": t.pagina,
                "texto": t.texto[:900],
                "citacoes": t.citacoes_detectadas,
            }
            for t in rec.trechos_epistemologicos[:8]
        ],
        "referencias_filtradas": rec.referencias_filtradas[:25],
    }

    return (
        f"Extraia os campos interpretativos do registro {payload.id}.\n"
        f"Seja conciso: justificativa em até 2 frases e trecho_curto com no máximo 180 caracteres.\n"
        f"{json.dumps(contexto_enxuto, ensure_ascii=False, separators=(',', ':'))}"
    )


def montar_registro_final(
    payload: ContratoExtracaoDeterministicaV4,
    resp: RespostaInterpretativaLLM,
) -> ContratoDefesaV4:
    """Mescla os dados determinísticos da Etapa 2 com a saída enxuta da LLM."""
    meta = payload.metadados_resolvidos
    dis_det = payload.dissertacao_deterministica
    edu = payload.evidencias_educapes

    # 1. Vínculo rígido MP -> LP
    mp_final = (
        meta.macroprojeto
        if meta.macroprojeto in MP_PARA_LP
        else resp.macroprojeto
    )
    lp_final = MP_PARA_LP[mp_final]

    # 2. Trava de confiança da Base Epistemológica
    base_llm = resp.base_epistemologica
    evidencias_validas = [
        {
            "secao": ev.secao,
            "pagina": ev.pagina,
            "trecho": ev.trecho_curto[:220],
            "referencia_correspondente": ev.referencia_correspondente,
        }
        for ev in base_llm.evidencias
        if ev.trecho_curto.strip() and isinstance(ev.pagina, int)
    ]

    if base_llm.confianca != "alta" or not evidencias_validas or not base_llm.valor:
        valor_final = None
        candidato_final = base_llm.candidato or base_llm.valor
        revisao_pendente = True
        confianca_final = (
            "media"
            if (base_llm.confianca == "alta" and evidencias_validas)
            else ("baixa" if base_llm.confianca == "alta" else base_llm.confianca)
        )
    else:
        valor_final = base_llm.valor
        candidato_final = None
        revisao_pendente = False
        confianca_final = "alta"

    # 3. Produto Educacional e Proveniência
    tipo_final = edu.tipo_produto_regex or resp.produto_tipo
    fonte_tipo = "dissertacao_ficha" if edu.tipo_produto_regex else "inferencia_llm"

    tags_dis = limpar_palavras_chave(dis_det.palavras_chave)
    tags_pro = limpar_palavras_chave(edu.palavras_chave_educapes or tags_dis)

    registro_dict: Dict[str, Any] = {
        "schema_version": "4.0",
        "id": payload.id,
        "ano": meta.ano,
        "autor": meta.autor,
        "orientador": meta.orientador,
        "coorientadores": list(meta.coorientadores),
        "instituicao": meta.instituicao,
        "campus": meta.campus,
        "linha_pesquisa": lp_final,
        "macroprojeto": mp_final,
        "dissertacao": {
            "titulo": dis_det.titulo,
            "link": dis_det.link,
            "resumo": payload.recortes_textuais.resumo.strip(),
            "palavras_chave": tags_dis,
            "autores_referenciados": list(dis_det.autores_referenciados),
            "base_epistemologica": {
                "valor": valor_final,
                "candidato": candidato_final,
                "confianca": confianca_final,
                "revisao_pendente": revisao_pendente,
                "justificativa": base_llm.justificativa.strip(),
                "evidencias": evidencias_validas,
            },
        },
        "produto": {
            "titulo": edu.titulo_produto or resp.produto_titulo,
            "tipo": tipo_final,
            "link": edu.handle_url,
            "publico_alvo": list(resp.produto_publico_alvo),
            "nivel_aplicacao": resp.produto_nivel_aplicacao.strip(),
            "palavras_chave": tags_pro,
            "data_publicacao": edu.data_publicacao,
            "autores_colaboradores": [a.model_dump() for a in edu.autores_colaboradores],
            "identificadores": [i.model_dump() for i in edu.identificadores],
            "proveniencia": {
                "fonte_tipo_escolhida": fonte_tipo,
                "rotulo_original_declarado": edu.titulo_produto,
                "colecao_educapes": edu.colecao_educapes,
                "dc_type_educapes": list(edu.dc_type_educapes),
            },
        },
    }

    registro_dict["indice_busca"] = construir_indice_busca(registro_dict)
    return ContratoDefesaV4.model_validate(registro_dict)


def processar_payload(
    caminho_payload: Path,
    system_prompt: str,
    llm: LLMClient,
    sobrescrever: bool = False,
) -> Optional[ContratoDefesaV4]:
    with open(caminho_payload, "r", encoding="utf-8") as f:
        bruto = json.load(f)

    payload = ContratoExtracaoDeterministicaV4.model_validate(bruto)
    caminho_saida = RECORDS_DIR / f"{payload.id}.json"

    if caminho_saida.exists() and not sobrescrever:
        logger.info(f"[{payload.id}] Já processado. Pulando.")
        return None

    user_message = montar_prompt_enxuto(payload)

    conteudo = llm.gerar_estruturado(
        system_prompt=system_prompt,
        user_prompt=user_message,
        response_model=RespostaInterpretativaLLM,
    )

    resp_llm = RespostaInterpretativaLLM.model_validate_json(conteudo)
    registro_validado = montar_registro_final(payload, resp_llm)

    RECORDS_DIR.mkdir(parents=True, exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(registro_validado.model_dump_json(indent=2))

    logger.info(
        f"[{payload.id}] OK | MP={registro_validado.macroprojeto} "
        f"| Tipo={registro_validado.produto.tipo} "
        f"| Base={registro_validado.dissertacao.base_epistemologica.valor or 'PENDENTE'}"
    )
    return registro_validado


def executar_etapa3(sobrescrever: bool = False, limite: Optional[int] = None):
    if not SKILL_PATH.exists():
        raise FileNotFoundError(f"Arquivo de instruções não encontrado: {SKILL_PATH}")

    system_prompt = SKILL_PATH.read_text(encoding="utf-8")
    llm = LLMClient()

    arquivos = sorted(STAGE2_DIR.glob("EPT-*.json"))
    if limite:
        arquivos = arquivos[:limite]

    logger.info(f"Iniciando processamento de {len(arquivos)} payloads...")

    sucessos = 0
    falhas = []

    for arq in arquivos:
        try:
            res = processar_payload(arq, system_prompt, llm, sobrescrever=sobrescrever)
            if res is not None:
                sucessos += 1
        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"[{arq.stem}] Falha: {e}")
            falhas.append((arq.stem, str(e)))

    logger.info(f"Concluído | Novos: {sucessos} | Falhas: {len(falhas)}")
    for cod, erro in falhas:
        logger.error(f"  - {cod}: {erro}")


if __name__ == "__main__":
    executar_etapa3(sobrescrever=True, limite=None)