"""Configuração declarativa de instância (`lemeept.toml`) e overlays de catálogos."""

from __future__ import annotations

import json
import os
import tomllib
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

from pydantic import BaseModel, Field

from lemeept_extractor import catalogs
from lemeept_extractor.frontend_builder import (
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_FRONTEND_CONFIG,
    ENV_CONFIG_VAR,
)


class InstituicaoConfig(BaseModel):
    nome: str = ""
    campus: str = ""
    sigla: str = ""
    somente_dissertacoes: bool = False


class CatalogosConfig(BaseModel):
    overlay_json: Optional[Path] = None
    aliases_docentes: Dict[str, str] = Field(default_factory=dict)
    aliases_autores_referencia: Dict[str, str] = Field(default_factory=dict)
    stopwords_continuacao_nome: List[str] = Field(default_factory=list)
    stopwords_entidade: List[str] = Field(default_factory=list)
    stopwords_token_nao_pessoa: List[str] = Field(default_factory=list)
    prefixos_nao_pessoa: List[str] = Field(default_factory=list)
    bases_epistemologicas_canonicas: List[str] = Field(default_factory=list)
    aliases_base_epistemologica: Dict[str, str] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    skill_path: Optional[Path] = None


class FrontendConfig(BaseModel):
    titulo: str = DEFAULT_FRONTEND_CONFIG["titulo"]
    titulo_pagina: str = DEFAULT_FRONTEND_CONFIG["titulo_pagina"]
    subtitulo: str = DEFAULT_FRONTEND_CONFIG["subtitulo"]
    eyebrow: str = DEFAULT_FRONTEND_CONFIG["eyebrow"]
    titulo_graficos: str = DEFAULT_FRONTEND_CONFIG["titulo_graficos"]
    json_url: str = DEFAULT_FRONTEND_CONFIG["json_url"]
    json_url_local: str = DEFAULT_FRONTEND_CONFIG["json_url_local"]
    widget_url: str = DEFAULT_FRONTEND_CONFIG["widget_url"]
    loader_texto: str = DEFAULT_FRONTEND_CONFIG["loader_texto"]
    loader_erro_log: str = DEFAULT_FRONTEND_CONFIG["loader_erro_log"]


class LemeConfig(BaseModel):
    instituicao: InstituicaoConfig = Field(default_factory=InstituicaoConfig)
    catalogos: CatalogosConfig = Field(default_factory=CatalogosConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    frontend: FrontendConfig = Field(default_factory=FrontendConfig)
    origem_path: Optional[Path] = None


def _unir_listas(base: List[str], extra: List[str]) -> List[str]:
    vistas = set(base)
    resultado = list(base)
    for item in extra:
        if item not in vistas:
            resultado.append(item)
            vistas.add(item)
    return resultado


def _carregar_overlay_json(caminho: Path) -> Dict[str, Any]:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de overlay de catálogos não encontrado: {caminho}")
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError(f"Overlay JSON deve ser um objeto: {caminho}")
    return dados


def _resolver_caminho(valor: Optional[Path], base_dir: Path) -> Optional[Path]:
    if valor is None:
        return None
    return valor if valor.is_absolute() else (base_dir / valor).resolve()


def _resolver_caminho_config(
    config_path: Optional[Path],
    *,
    auto_detect: bool,
) -> Optional[Path]:
    if config_path is not None:
        caminho = Path(config_path)
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho}")
        return caminho.resolve()

    env_val = (os.getenv(ENV_CONFIG_VAR) or "").strip()
    if env_val:
        caminho_env = Path(env_val)
        if not caminho_env.exists():
            raise FileNotFoundError(
                f"Arquivo configurado em {ENV_CONFIG_VAR} não encontrado: {caminho_env}"
            )
        return caminho_env.resolve()

    if auto_detect:
        candidato = Path.cwd() / DEFAULT_CONFIG_FILENAME
        if candidato.exists():
            return candidato.resolve()

    return None


def _mesclar_catalogos_overlay(
    overlay_cfg: CatalogosConfig,
    inline_cfg: CatalogosConfig,
    overlay_path: Path,
) -> CatalogosConfig:
    return CatalogosConfig(
        overlay_json=overlay_path,
        aliases_docentes={**overlay_cfg.aliases_docentes, **inline_cfg.aliases_docentes},
        aliases_autores_referencia={
            **overlay_cfg.aliases_autores_referencia,
            **inline_cfg.aliases_autores_referencia,
        },
        stopwords_continuacao_nome=_unir_listas(
            overlay_cfg.stopwords_continuacao_nome, inline_cfg.stopwords_continuacao_nome
        ),
        stopwords_entidade=_unir_listas(
            overlay_cfg.stopwords_entidade, inline_cfg.stopwords_entidade
        ),
        stopwords_token_nao_pessoa=_unir_listas(
            overlay_cfg.stopwords_token_nao_pessoa, inline_cfg.stopwords_token_nao_pessoa
        ),
        prefixos_nao_pessoa=_unir_listas(
            overlay_cfg.prefixos_nao_pessoa, inline_cfg.prefixos_nao_pessoa
        ),
        bases_epistemologicas_canonicas=_unir_listas(
            overlay_cfg.bases_epistemologicas_canonicas,
            inline_cfg.bases_epistemologicas_canonicas,
        ),
        aliases_base_epistemologica={
            **overlay_cfg.aliases_base_epistemologica,
            **inline_cfg.aliases_base_epistemologica,
        },
    )


def carregar_config(
    config_path: Optional[Path] = None,
    *,
    auto_detect: bool = True,
) -> LemeConfig:
    """Carrega `LemeConfig` de `config_path`, `LEMEEPT_CONFIG` ou `./lemeept.toml`."""
    caminho = _resolver_caminho_config(config_path, auto_detect=auto_detect)
    if caminho is None:
        return LemeConfig()

    bruto = tomllib.loads(caminho.read_text(encoding="utf-8"))
    cfg = LemeConfig.model_validate({**bruto, "origem_path": caminho})
    base_dir = caminho.parent

    if cfg.llm.skill_path is not None:
        cfg.llm.skill_path = _resolver_caminho(cfg.llm.skill_path, base_dir)

    if cfg.catalogos.overlay_json is not None:
        overlay_path = _resolver_caminho(cfg.catalogos.overlay_json, base_dir)
        cfg.catalogos.overlay_json = overlay_path
        overlay_cfg = CatalogosConfig.model_validate(_carregar_overlay_json(overlay_path))
        cfg.catalogos = _mesclar_catalogos_overlay(overlay_cfg, cfg.catalogos, overlay_path)

    return cfg


def aplicar_config(
    config: Optional[LemeConfig] = None,
    *,
    config_path: Optional[Path] = None,
    auto_detect: bool = True,
) -> LemeConfig:
    """Reseta os catálogos base e aplica os overlays definidos na configuração."""
    cfg = config if config is not None else carregar_config(config_path, auto_detect=auto_detect)
    catalogs.resetar_catalogos()
    cat = cfg.catalogos
    if any(
        (
            cat.aliases_docentes,
            cat.aliases_autores_referencia,
            cat.stopwords_continuacao_nome,
            cat.stopwords_entidade,
            cat.stopwords_token_nao_pessoa,
            cat.prefixos_nao_pessoa,
            cat.bases_epistemologicas_canonicas,
            cat.aliases_base_epistemologica,
        )
    ):
        catalogs.aplicar_overlay(
            aliases_docentes=cat.aliases_docentes or None,
            aliases_autores_referencia=cat.aliases_autores_referencia or None,
            stopwords_continuacao_nome=cat.stopwords_continuacao_nome or None,
            stopwords_entidade=cat.stopwords_entidade or None,
            stopwords_token_nao_pessoa=cat.stopwords_token_nao_pessoa or None,
            prefixos_nao_pessoa=cat.prefixos_nao_pessoa or None,
            bases_epistemologicas_canonicas=cat.bases_epistemologicas_canonicas or None,
            aliases_base_epistemologica=cat.aliases_base_epistemologica or None,
        )
    return cfg


@contextmanager
def usar_config(
    config_or_path: Union[LemeConfig, Path, None] = None,
    *,
    auto_detect: bool = False,
) -> Iterator[LemeConfig]:
    """Context manager que aplica uma configuração e restaura os catálogos base ao sair."""
    if isinstance(config_or_path, LemeConfig):
        cfg = aplicar_config(config_or_path)
    else:
        cfg = aplicar_config(config_path=config_or_path, auto_detect=auto_detect)
    try:
        yield cfg
    finally:
        catalogs.resetar_catalogos()
