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
    ]

    texto_normalizado = normalizar_texto_busca(" ".join(filter(None, blocos)))

    return {
        "texto_busca_normalizado": texto_normalizado,
        "termos_unificados": tags_unificadas,
        "tem_produto_vinculado": bool(pro.get("link")),
        "tem_resumo": bool(dis.get("resumo") and len(dis.get("resumo", "").strip()) > 30),
    }


def aplicar_governanca_pos_llm(
    payload: ContratoExtracaoDeterministicaV4,
    saida_llm: Dict[str, Any],
) -> Dict[str, Any]:
    meta = payload.metadados_resolvidos
    dis_det = payload.dissertacao_deterministica
    edu = payload.evidencias_educapes

    saida_llm["schema_version"] = "4.0"
    saida_llm["id"] = payload.id
    saida_llm["ano"] = meta.ano
    saida_llm["autor"] = meta.autor
    saida_llm["orientador"] = meta.orientador
    saida_llm["coorientadores"] = list(meta.coorientadores)
    saida_llm["instituicao"] = meta.instituicao
    saida_llm["campus"] = meta.campus

    # 1. Preservação e vínculo rígido MP -> LP
    mp_final = (
        meta.macroprojeto
        if meta.macroprojeto != "MP_INDEFINIDO"
        else saida_llm.get("macroprojeto", "MP1")
    )
    if mp_final not in MP_PARA_LP:
        mp_final = "MP1"
    saida_llm["macroprojeto"] = mp_final
    saida_llm["linha_pesquisa"] = MP_PARA_LP[mp_final]

    # 2. Dissertação e Trava Epistemológica
    dis_out = saida_llm.setdefault("dissertacao", {})
    dis_out["titulo"] = dis_det.titulo
    dis_out["link"] = dis_det.link
    dis_out["palavras_chave"] = limpar_palavras_chave(
        dis_det.palavras_chave or dis_out.get("palavras_chave") or []
    )
    if not dis_out.get("resumo") and payload.recortes_textuais.resumo:
        dis_out["resumo"] = payload.recortes_textuais.resumo.strip()

    base = dis_out.setdefault("base_epistemologica", {})
    confianca = base.get("confianca", "abstencao")
    evidencias = base.get("evidencias") or []

    evidencias_validas = [
        ev
        for ev in evidencias
        if isinstance(ev, dict) and ev.get("trecho") and isinstance(ev.get("pagina"), int)
    ]
    base["evidencias"] = evidencias_validas

    if confianca != "alta" or not evidencias_validas or not base.get("valor"):
        if base.get("valor") and not base.get("candidato"):
            base["candidato"] = base["valor"]
        base["valor"] = None
        base["revisao_pendente"] = True
        if confianca == "alta":
            base["confianca"] = "media" if evidencias_validas else "baixa"
    else:
        base["revisao_pendente"] = False

    # 3. Produto Educacional e Proveniência (com serialização explícita dos submodelos)
    pro_out = saida_llm.setdefault("produto", {})
    if edu.titulo_produto and not pro_out.get("titulo"):
        pro_out["titulo"] = edu.titulo_produto
    pro_out["link"] = edu.handle_url or pro_out.get("link")
    pro_out["data_publicacao"] = edu.data_publicacao
    pro_out["autores_colaboradores"] = [a.model_dump() for a in edu.autores_colaboradores]
    pro_out["identificadores"] = [i.model_dump() for i in edu.identificadores]

    tags_pro = (
        (edu.palavras_chave_educapes or [])
        or (pro_out.get("palavras_chave") or [])
        or dis_out["palavras_chave"]
    )
    pro_out["palavras_chave"] = limpar_palavras_chave(tags_pro)

    prov = pro_out.setdefault("proveniencia", {})
    if edu.tipo_produto_regex:
        pro_out["tipo"] = edu.tipo_produto_regex
        prov["fonte_tipo_escolhida"] = "dissertacao_ficha"
    else:
        prov.setdefault("fonte_tipo_escolhida", "inferencia_llm")

    prov["colecao_educapes"] = edu.colecao_educapes
    prov["dc_type_educapes"] = list(edu.dc_type_educapes)
    prov.setdefault("rotulo_original_declarado", edu.titulo_produto)

    # 4. Índice de busca determinístico
    saida_llm["indice_busca"] = construir_indice_busca(saida_llm)

    return saida_llm


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

    logger.info(f"[{payload.id}] Processando via {llm.provider_name} ({llm.model})...")

    user_message = (
        f"Processe o registro {payload.id} abaixo e retorne estritamente o JSON conforme o schema.\n\n"
        f"{payload.model_dump_json(indent=2)}"
    )

    conteudo = llm.gerar_estruturado(
        system_prompt=system_prompt,
        user_prompt=user_message,
        response_model=ContratoDefesaV4,
    )

    dados_brutos_llm = json.loads(conteudo)
    dados_governados = aplicar_governanca_pos_llm(payload, dados_brutos_llm)
    registro_validado = ContratoDefesaV4.model_validate(dados_governados)

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
    executar_etapa3(sobrescrever=False, limite=6)