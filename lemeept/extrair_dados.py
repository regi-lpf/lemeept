from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

from lemeept.atualizar_dados import (
    ARQUIVO_PLANILHA,
    ARQUIVO_SAIDA,
    enriquecer_registro if False else extrair_campos,
)