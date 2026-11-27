"""CLI unificada do extrator bibliométrico universal (`lemeept-extractor`)."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from lemeept_extractor import __version__

SUBCOMMANDS: Dict[str, Tuple[str, str]] = {
    "ingest": (
        "lemeept_extractor.stages.ingest",
        "Etapa 1 universal: gera manifesto Stage 1 a partir de CSV ou pasta local de PDFs.",
    ),
    "extract": (
        "lemeept_extractor.stages.extract",
        "Etapa 2: extração determinística de PDFs (PyMuPDF), ABNT e metadados eduCAPES.",
    ),
    "llm": (
        "lemeept_extractor.stages.llm",
        "Etapa 3: inferência semântica estruturada (LLM), hidratação e --sync-deterministico.",
    ),
    "compile": (
        "lemeept_extractor.stages.compile",
        "Etapa 4: curadoria CSV, reconciliação global e compilação do painel JSON v4.",
    ),
    "build-frontend": (
        "lemeept_extractor.frontend_builder",
        "Empacota e valida public/widget-elementor.html a partir de index.html e frontend/ (ou template).",
    ),
}


def available_subcommands() -> Dict[str, Tuple[str, str]]:
    """Retorna os subcomandos disponíveis na CLI universal."""
    return dict(SUBCOMMANDS)


def _build_top_parser(comandos: Dict[str, Tuple[str, str]]) -> argparse.ArgumentParser:
    linhas_cmd = "\n".join(f"  {nome:<15} {desc}" for nome, (_, desc) in comandos.items())
    epilog = (
        f"subcomandos disponíveis:\n{linhas_cmd}\n\n"
        "Use `lemeept-extractor <subcomando> --help` para ver as opções de cada etapa."
    )
    parser = argparse.ArgumentParser(
        prog="lemeept-extractor",
        description="CLI universal da pipeline bibliométrica LEME / ProfEPT.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Arquivo de configuração TOML da instância (propaga via LEMEEPT_CONFIG).",
    )
    parser.add_argument(
        "subcomando",
        nargs="?",
        choices=list(comandos.keys()),
        help="Etapa da pipeline a executar.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    comandos = available_subcommands()

    config_cli: Optional[str] = None
    if args_list and args_list[0] == "--config":
        if len(args_list) < 2 or not args_list[1].strip():
            _build_top_parser(comandos).error("a opção `--config` exige um caminho de arquivo.")
        config_cli = str(Path(args_list[1]).resolve())
        args_list = args_list[2:]
    elif args_list and args_list[0].startswith("--config="):
        valor_cfg = args_list[0].split("=", 1)[1].strip()
        if not valor_cfg:
            _build_top_parser(comandos).error("a opção `--config=` exige um caminho não vazio.")
        config_cli = str(Path(valor_cfg).resolve())
        args_list = args_list[1:]

    env_anterior = os.environ.get("LEMEEPT_CONFIG")
    if config_cli is not None:
        os.environ["LEMEEPT_CONFIG"] = config_cli

    try:
        if not args_list:
            _build_top_parser(comandos).print_help()
            return 0
        if args_list[0] in ("-h", "--help", "--version"):
            _build_top_parser(comandos).parse_args(args_list[:1])
            return 0

        cmd = args_list[0]
        rest = args_list[1:]
        if cmd not in comandos:
            _build_top_parser(comandos).error(
                f"subcomando inválido: '{cmd}' (opções: {', '.join(comandos.keys())})"
            )

        modulo_nome, _ = comandos[cmd]
        modulo = importlib.import_module(modulo_nome)
        resultado = modulo.main(rest)
        return int(resultado) if isinstance(resultado, int) else 0
    finally:
        if config_cli is not None:
            if env_anterior is None:
                os.environ.pop("LEMEEPT_CONFIG", None)
            else:
                os.environ["LEMEEPT_CONFIG"] = env_anterior


if __name__ == "__main__":
    raise SystemExit(main())
