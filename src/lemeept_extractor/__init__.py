"""Pacote universal de extração, inferência e compilação bibliométrica (`lemeept-extractor`)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("lemeept-extractor")
except PackageNotFoundError:
    __version__ = "0.4.1b0"

__all__ = ["__version__"]
