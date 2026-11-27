import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import ValidationError

from lemeept_extractor import catalogs
from lemeept_extractor.config import aplicar_config
from lemeept_extractor.io_utils import escrever_texto_atomico
from lemeept_extractor.llm_provider import LLMClient
from lemeept_extractor.models import (
    ContratoDefesaV4,
    ContratoExtracaoDeterministicaV4,
    RespostaInterpretativaDissertacaoLLM,
    RespostaInterpretativaLLM,
)
from lemeept_extractor.normalizers import (
    limpar_nome_pessoa,
    limpar_palavras_chave,
    limpar_resumo_publico,
    normalizar_base_epistemologica,
    normalizar_formato_produto,
    normalizar_nivel_aplicacao,
    normalizar_nome_orientador,
    normalizar_texto_busca,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("lemeept_extractor.stages.llm")

SKILL_PATH = Path(__file__).resolve().parent.parent / "SKILL.md"
STAGE2_DIR = Path("data/stage2_payloads")
RECORDS_DIR = Path("data/records")


def construir_indice_busca(registro: Dict[str, Any]) -> Dict[str, Any]:
    dis = registro.get("dissertacao") or {}
    pro = registro.get("produto") or {}
    base = dis.get("base_epistemologica") or {}

    tags_unificadas = limpar_palavras_chave(
        (dis.get("palavras_chave") or []) + (pro.get("palavras_chave") or [])
    )

    blocos = [
        registro.get("id", ""),
        str(registro.get("ano", "")),
        registro.get("autor", ""),
        registro.get("orientador", ""),
        " ".join(registro.get("coorientadores") or []),
        registro.get("instituicao", ""),
        registro.get("campus", ""),
        registro.get("linha_pesquisa", ""),
        registro.get("macroprojeto", ""),
        dis.get("titulo", ""),
        dis.get("resumo", ""),
        base.get("valor") or "",
        pro.get("titulo", ""),
        pro.get("tipo", ""),
        pro.get("formato") or "",
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


def montar_prompt_enxuto(
    payload: ContratoExtracaoDeterministicaV4,
    somente_dissertacoes: bool = False,
) -> str:
    """
    Filtra apenas os campos semanticamente relevantes e limita o volume textual
    para caber com folga em 8k de contexto na GPU local (~5k-6k tokens).
    """
    rec = payload.recortes_textuais
    edu = payload.evidencias_educapes
    modo_sem_produto = somente_dissertacoes or payload.metadados_resolvidos.sem_produto

    contexto_enxuto: Dict[str, Any] = {
        "id": payload.id,
        "titulo_dissertacao": payload.dissertacao_deterministica.titulo,
        "macroprojeto_pre_detectado": payload.metadados_resolvidos.macroprojeto,
        "linha_pesquisa_pre_detectada": payload.metadados_resolvidos.linha_pesquisa,
    }
    if not modo_sem_produto:
        contexto_enxuto["evidencias_produto"] = {
            "titulo_educapes": edu.titulo_produto,
            "colecao_educapes": edu.colecao_educapes,
            "dc_type_educapes": edu.dc_type_educapes,
            "tipo_sugerido_regex": edu.tipo_produto_regex,
            "formato_sugerido_regex": edu.formato_produto_regex,
            "descricao_na_dissertacao": rec.descricao_produto_na_dissertacao[:2500],
        }
    contexto_enxuto.update(
        {
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
    )

    instrucao_modo = (
        "Extraia apenas macroprojeto e base_epistemologica da dissertação (sem produto educacional)"
        if modo_sem_produto
        else "Extraia os campos interpretativos"
    )
    return (
        f"{instrucao_modo} do registro {payload.id}.\n"
        f"Seja conciso: justificativa em até 2 frases e trecho_curto com no máximo 180 caracteres.\n"
        f"{json.dumps(contexto_enxuto, ensure_ascii=False, separators=(',', ':'))}"
    )


def montar_registro_final(
    payload: ContratoExtracaoDeterministicaV4,
    resp: Union[RespostaInterpretativaLLM, RespostaInterpretativaDissertacaoLLM],
) -> ContratoDefesaV4:
    """Mescla os dados determinísticos da Etapa 2 com a saída enxuta da LLM."""
    meta = payload.metadados_resolvidos
    dis_det = payload.dissertacao_deterministica
    edu = payload.evidencias_educapes

    # 1. Vínculo rígido MP -> LP
    if meta.macroprojeto in catalogs.MP_PARA_LP:
        mp_final = meta.macroprojeto
    else:
        mp_final = resp.macroprojeto
        if meta.linha_pesquisa in ("LP1", "LP2") and catalogs.MP_PARA_LP[mp_final] != meta.linha_pesquisa:
            logger.warning(
                f"[{payload.id}] LLM escolheu {mp_final} ({catalogs.MP_PARA_LP[mp_final]}) "
                f"divergente da LP pré-detectada {meta.linha_pesquisa}."
            )
    lp_final = catalogs.MP_PARA_LP[mp_final]

    # 2. Normalização + Trava de confiança da Base Epistemológica
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

    valor_norm, eh_canonico = normalizar_base_epistemologica(base_llm.valor)
    cand_norm, _ = normalizar_base_epistemologica(base_llm.candidato)

    if base_llm.confianca == "alta" and evidencias_validas and valor_norm and eh_canonico:
        valor_final = valor_norm
        candidato_final = None
        revisao_pendente = False
        confianca_final = "alta"
    else:
        valor_final = None
        candidato_final = cand_norm or valor_norm
        revisao_pendente = True
        if base_llm.confianca == "alta":
            confianca_final = "media" if evidencias_validas else "baixa"
        else:
            confianca_final = base_llm.confianca

    tags_dis = limpar_palavras_chave(dis_det.palavras_chave)
    resumo_limpo = limpar_resumo_publico(payload.recortes_textuais.resumo)

    # 3. Produto Educacional e Proveniência (opcional em modo somente dissertações)
    if isinstance(resp, RespostaInterpretativaDissertacaoLLM) or meta.sem_produto:
        produto_dict: Optional[Dict[str, Any]] = None
    else:
        tipo_final = edu.tipo_produto_regex or resp.produto_tipo
        if edu.tipo_produto_regex:
            fonte_tipo = edu.fonte_tipo_regex or "dissertacao_ficha"
        else:
            fonte_tipo = "inferencia_llm"

        tags_pro = limpar_palavras_chave(edu.palavras_chave_educapes or tags_dis)
        nivel_aplicacao_norm = normalizar_nivel_aplicacao(resp.produto_nivel_aplicacao)
        formato_final = normalizar_formato_produto(edu.formato_produto_regex or resp.produto_formato)
        produto_dict = {
            "titulo": edu.titulo_produto or resp.produto_titulo,
            "tipo": tipo_final,
            "formato": formato_final,
            "link": edu.handle_url,
            "publico_alvo": list(resp.produto_publico_alvo),
            "nivel_aplicacao": nivel_aplicacao_norm,
            "palavras_chave": tags_pro,
            "data_publicacao": edu.data_publicacao,
            "autores_colaboradores": [a.model_dump() for a in edu.autores_colaboradores],
            "identificadores": [i.model_dump() for i in edu.identificadores],
            "proveniencia": {
                "fonte_tipo_escolhida": fonte_tipo,
                "rotulo_original_declarado": edu.titulo_produto_bruto or edu.titulo_produto,
                "colecao_educapes": edu.colecao_educapes,
                "dc_type_educapes": list(edu.dc_type_educapes),
            },
        }

    registro_dict: Dict[str, Any] = {
        "schema_version": "4.0",
        "id": payload.id,
        "ano": meta.ano,
        "autor": limpar_nome_pessoa(meta.autor),
        "orientador": normalizar_nome_orientador(meta.orientador),
        "coorientadores": [normalizar_nome_orientador(c) for c in meta.coorientadores],
        "instituicao": meta.instituicao,
        "campus": meta.campus,
        "linha_pesquisa": lp_final,
        "macroprojeto": mp_final,
        "dissertacao": {
            "titulo": dis_det.titulo,
            "link": dis_det.link,
            "resumo": resumo_limpo,
            "palavras_chave": tags_dis,
            "autores_referenciados": list(dis_det.autores_referenciados),
            "base_epistemologica": {
                "valor": valor_final,
                "candidato": candidato_final,
                "confianca": confianca_final,
                "revisao_pendente": revisao_pendente,
                "curado_humano": False,
                "justificativa": base_llm.justificativa.strip(),
                "evidencias": evidencias_validas,
            },
        },
        "produto": produto_dict,
    }

    registro_dict["indice_busca"] = construir_indice_busca(registro_dict)
    return ContratoDefesaV4.model_validate(registro_dict)


def processar_payload(
    caminho_payload: Path,
    system_prompt: str,
    llm: LLMClient,
    sobrescrever: bool = False,
    forcar_curados: bool = False,
    records_dir: Path = RECORDS_DIR,
    somente_dissertacoes: bool = False,
) -> Optional[ContratoDefesaV4]:
    with open(caminho_payload, "r", encoding="utf-8") as f:
        bruto = json.load(f)

    payload = ContratoExtracaoDeterministicaV4.model_validate(bruto)
    caminho_saida = records_dir / f"{payload.id}.json"

    if caminho_saida.exists():
        if not sobrescrever:
            logger.info(f"[{payload.id}] Já processado. Pulando.")
            return None
        if not forcar_curados:
            try:
                existente = json.loads(caminho_saida.read_text(encoding="utf-8"))
                if existente.get("dissertacao", {}).get("base_epistemologica", {}).get("curado_humano"):
                    logger.warning(
                        f"[{payload.id}] Registro possui curadoria humana (curado_humano=true). "
                        f"Pulando sobrescrita (use --forcar-curados para substituir)."
                    )
                    return None
            except (json.JSONDecodeError, OSError):
                pass

    modo_sem_produto = somente_dissertacoes or payload.metadados_resolvidos.sem_produto
    response_model = RespostaInterpretativaDissertacaoLLM if modo_sem_produto else RespostaInterpretativaLLM
    prompt_sistema = system_prompt
    if modo_sem_produto:
        prompt_sistema = (
            f"{system_prompt}\n\n"
            "## MODO SOMENTE DISSERTAÇÕES ATIVO\n"
            "Este acervo não possui produto educacional vinculado. Retorne estritamente o schema "
            "`RespostaInterpretativaDissertacaoLLM` (`macroprojeto` e `base_epistemologica`), omitindo todos os campos `produto_*`."
        )
    user_message = montar_prompt_enxuto(payload, somente_dissertacoes=modo_sem_produto)

    resp_llm = None
    ultimo_erro_validacao: Optional[Exception] = None
    for tentativa in range(2):
        try:
            conteudo = llm.gerar_estruturado(
                system_prompt=prompt_sistema,
                user_prompt=user_message,
                response_model=response_model,
            )
            resp_llm = response_model.model_validate_json(conteudo)
            break
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            ultimo_erro_validacao = e
            if tentativa == 0:
                logger.warning(f"[{payload.id}] Saída JSON inválida/vazia da LLM ({e}). Repetindo chamada...")
            else:
                raise

    if resp_llm is None and ultimo_erro_validacao is not None:
        raise ultimo_erro_validacao

    registro_validado = montar_registro_final(payload, resp_llm)

    escrever_texto_atomico(caminho_saida, registro_validado.model_dump_json(indent=2))

    tipo_log = registro_validado.produto.tipo if registro_validado.produto else "SEM_PRODUTO"
    logger.info(
        f"[{payload.id}] OK | MP={registro_validado.macroprojeto} "
        f"| Tipo={tipo_log} "
        f"| Base={registro_validado.dissertacao.base_epistemologica.valor or 'PENDENTE'}"
    )
    return registro_validado


def ressincronizar_registros_deterministico(
    stage2_dir: Path = STAGE2_DIR,
    records_dir: Path = RECORDS_DIR,
    ids: Optional[List[str]] = None,
) -> Dict[str, int]:
    """
    Atualiza campos determinísticos da Etapa 2 e normalizadores da Etapa 3 nos JSONs
    existentes em data/records/ sem chamar a LLM e preservando curadorias humanas.
    """
    arquivos_stage2 = sorted(stage2_dir.glob("EPT-*.json"))
    if ids:
        alvo = set(ids)
        arquivos_stage2 = [p for p in arquivos_stage2 if p.stem in alvo]

    stats = {
        "sincronizados": 0,
        "ignorados": 0,
        "rebaixados_nao_canonicos": 0,
        "erros": 0,
    }

    for caminho_s2 in arquivos_stage2:
        cod = caminho_s2.stem
        caminho_rec = records_dir / f"{cod}.json"
        if not caminho_rec.exists():
            stats["ignorados"] += 1
            continue

        try:
            payload = ContratoExtracaoDeterministicaV4.model_validate_json(
                caminho_s2.read_text(encoding="utf-8")
            )
            raw = json.loads(caminho_rec.read_text(encoding="utf-8"))

            meta = payload.metadados_resolvidos
            dis_det = payload.dissertacao_deterministica
            edu = payload.evidencias_educapes

            raw["ano"] = meta.ano
            raw["autor"] = limpar_nome_pessoa(meta.autor)
            raw["orientador"] = normalizar_nome_orientador(meta.orientador)
            raw["coorientadores"] = [normalizar_nome_orientador(c) for c in meta.coorientadores]
            raw["instituicao"] = meta.instituicao
            raw["campus"] = meta.campus

            if meta.macroprojeto in catalogs.MP_PARA_LP:
                raw["macroprojeto"] = meta.macroprojeto
                raw["linha_pesquisa"] = catalogs.MP_PARA_LP[meta.macroprojeto]
            else:
                if meta.linha_pesquisa in ("LP1", "LP2") and raw.get("linha_pesquisa") != meta.linha_pesquisa:
                    logger.warning(
                        f"[{cod}] Discrepância entre linha_pesquisa determinística ({meta.linha_pesquisa}) "
                        f"e registro atual ({raw.get('macroprojeto')}/{raw.get('linha_pesquisa')}); "
                        f"considere reprocessar via --id {cod} --sobrescrever."
                    )
                if raw.get("macroprojeto") in catalogs.MP_PARA_LP:
                    raw["linha_pesquisa"] = catalogs.MP_PARA_LP[raw["macroprojeto"]]

            dis = raw["dissertacao"]
            dis["titulo"] = dis_det.titulo
            dis["link"] = dis_det.link
            dis["resumo"] = limpar_resumo_publico(payload.recortes_textuais.resumo)
            tags_dis = limpar_palavras_chave(dis_det.palavras_chave)
            dis["palavras_chave"] = tags_dis
            dis["autores_referenciados"] = list(dis_det.autores_referenciados)

            base = dis["base_epistemologica"]
            base.setdefault("curado_humano", False)
            if base.get("curado_humano"):
                if base.get("valor"):
                    val_norm, eh_canon = normalizar_base_epistemologica(base["valor"])
                    if eh_canon and val_norm:
                        base["valor"] = val_norm
            else:
                if base.get("valor"):
                    val_norm, eh_canon = normalizar_base_epistemologica(base["valor"])
                    if eh_canon and val_norm:
                        base["valor"] = val_norm
                    else:
                        base["candidato"] = (
                            normalizar_base_epistemologica(base.get("candidato"))[0] or val_norm
                        )
                        base["valor"] = None
                        base["revisao_pendente"] = True
                        if base.get("confianca") == "alta":
                            base["confianca"] = "media" if base.get("evidencias") else "baixa"
                        stats["rebaixados_nao_canonicos"] += 1
                if base.get("candidato"):
                    base["candidato"] = normalizar_base_epistemologica(base["candidato"])[0]

            pro = raw.get("produto")
            if meta.sem_produto or pro is None:
                raw["produto"] = None
            else:
                pro["titulo"] = edu.titulo_produto or pro.get("titulo", "")
                pro["formato"] = normalizar_formato_produto(edu.formato_produto_regex or pro.get("formato"))
                pro["link"] = edu.handle_url
                pro["nivel_aplicacao"] = normalizar_nivel_aplicacao(pro.get("nivel_aplicacao"))
                pro["palavras_chave"] = limpar_palavras_chave(edu.palavras_chave_educapes or tags_dis)
                pro["data_publicacao"] = edu.data_publicacao
                pro["autores_colaboradores"] = [a.model_dump() for a in edu.autores_colaboradores]
                pro["identificadores"] = [i.model_dump() for i in edu.identificadores]

                prov = pro.setdefault("proveniencia", {})
                prov["rotulo_original_declarado"] = edu.titulo_produto_bruto or edu.titulo_produto
                prov["colecao_educapes"] = edu.colecao_educapes
                prov["dc_type_educapes"] = list(edu.dc_type_educapes)

                if edu.tipo_produto_regex:
                    pro["tipo"] = edu.tipo_produto_regex
                    prov["fonte_tipo_escolhida"] = edu.fonte_tipo_regex or "dissertacao_ficha"
                elif prov.get("fonte_tipo_escolhida") == "dissertacao_ficha":
                    logger.info(
                        f"[{cod}] tipo_produto_regex ficou ausente após atualização das regras; "
                        f"mantendo tipo atual '{pro.get('tipo')}' para revisão/inferência."
                    )

            raw["indice_busca"] = construir_indice_busca(raw)
            validado = ContratoDefesaV4.model_validate(raw)
            escrever_texto_atomico(caminho_rec, validado.model_dump_json(indent=2))
            stats["sincronizados"] += 1

        except Exception as e:
            logger.error(f"[{cod}] Erro na ressincronização determinística: {e}")
            stats["erros"] += 1

    logger.info(
        f"Ressincronização concluída | Sincronizados={stats['sincronizados']} "
        f"| Ignorados={stats['ignorados']} | Rebaixados={stats['rebaixados_nao_canonicos']} "
        f"| Erros={stats['erros']}"
    )
    return stats


def executar_etapa3(
    sobrescrever: bool = False,
    forcar_curados: bool = False,
    limite: Optional[int] = None,
    target_id: Optional[str] = None,
    skill_path: Path = SKILL_PATH,
    stage2_dir: Path = STAGE2_DIR,
    records_dir: Path = RECORDS_DIR,
    somente_dissertacoes: bool = False,
):
    if not skill_path.exists():
        raise FileNotFoundError(f"Arquivo de instruções não encontrado: {skill_path}")
    if forcar_curados and not sobrescrever:
        logger.warning("--forcar-curados não tem efeito sem --sobrescrever.")

    system_prompt = skill_path.read_text(encoding="utf-8")
    llm = LLMClient()

    arquivos = sorted(stage2_dir.glob("EPT-*.json"))
    if target_id:
        arquivos = [a for a in arquivos if a.stem == target_id]
    if limite and not sobrescrever:
        arquivos = [a for a in arquivos if not (records_dir / f"{a.stem}.json").exists()][:limite]
    elif limite:
        arquivos = arquivos[:limite]

    logger.info(f"Iniciando processamento de {len(arquivos)} payloads...")

    sucessos = 0
    falhas = []

    for arq in arquivos:
        try:
            res = processar_payload(
                arq,
                system_prompt,
                llm,
                sobrescrever=sobrescrever,
                forcar_curados=forcar_curados,
                records_dir=records_dir,
                somente_dissertacoes=somente_dissertacoes,
            )
            if res is not None:
                sucessos += 1
        except (ValidationError, json.JSONDecodeError, Exception) as e:
            logger.error(f"[{arq.stem}] Falha: {e}")
            falhas.append((arq.stem, str(e)))

    logger.info(f"Concluído | Novos: {sucessos} | Falhas: {len(falhas)}")
    for cod, erro in falhas:
        logger.error(f"  - {cod}: {erro}")
    return len(falhas)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Etapa 3: Inferência semântica LLM, hidratação e ressincronização determinística."
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        default=False,
        help="Reprocessa registros já existentes na LLM (preserva curados, salvo --forcar-curados).",
    )
    parser.add_argument(
        "--forcar-curados",
        action="store_true",
        default=False,
        help="Permite sobrescrever até registros com curado_humano=true (exige --sobrescrever).",
    )
    parser.add_argument("--limite", type=int, default=None, help="Limita quantidade de payloads.")
    parser.add_argument("--id", dest="target_id", default=None, help="Processa apenas um ID (ex: EPT-0001).")
    parser.add_argument(
        "--sync-deterministico",
        action="store_true",
        default=False,
        help="Ressincroniza campos da Etapa 2 e normalizadores nos registros atuais sem chamar a LLM.",
    )
    parser.add_argument(
        "--somente-dissertacoes",
        action="store_true",
        default=False,
        help="Extrai apenas macroprojeto e base epistemológica (sem produto educacional).",
    )
    parser.add_argument("--skill", type=Path, default=None, help="Caminho para o prompt SKILL.md.")
    parser.add_argument("--stage2-dir", type=Path, default=STAGE2_DIR, help="Diretório de payloads da Etapa 2.")
    parser.add_argument("--records-dir", type=Path, default=RECORDS_DIR, help="Diretório de saída dos registros v4.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Arquivo de configuração TOML da instância (padrão: ./lemeept.toml se existir).",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    cfg = aplicar_config(config_path=args.config)
    if args.sync_deterministico:
        ids_filtro = [args.target_id] if args.target_id else None
        stats = ressincronizar_registros_deterministico(
            stage2_dir=args.stage2_dir,
            records_dir=args.records_dir,
            ids=ids_filtro,
        )
        return 1 if stats["erros"] > 0 else 0
    skill_efetivo = args.skill or cfg.llm.skill_path or SKILL_PATH
    somente_diss = args.somente_dissertacoes or cfg.instituicao.somente_dissertacoes
    qtd_falhas = executar_etapa3(
        sobrescrever=args.sobrescrever,
        forcar_curados=args.forcar_curados,
        limite=args.limite,
        target_id=args.target_id,
        skill_path=skill_efetivo,
        stage2_dir=args.stage2_dir,
        records_dir=args.records_dir,
        somente_dissertacoes=somente_diss,
    )
    return 1 if qtd_falhas > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
