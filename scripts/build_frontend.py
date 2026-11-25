#!/usr/bin/env python3
"""Gera e valida o bundle autocontido Elementor-safe a partir dos fontes do frontend."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from lemeept_extractor.frontend_builder import (  # noqa: E402
    carregar_config_frontend,
    compactar_css,
    compactar_html,
    compactar_js_seguro,
    extrair_secao_raiz,
    gerar_bundle,
    gerar_site_completo,
    main,
    renderizar_index_template,
    renderizar_loader_template,
    validar_bundle,
)

__all__ = [
    "carregar_config_frontend",
    "compactar_css",
    "compactar_html",
    "compactar_js_seguro",
    "extrair_secao_raiz",
    "gerar_bundle",
    "gerar_site_completo",
    "main",
    "renderizar_index_template",
    "renderizar_loader_template",
    "validar_bundle",
]

if __name__ == "__main__":
    raise SystemExit(main(default_root=ROOT))
