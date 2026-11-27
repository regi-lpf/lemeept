import copy
import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Type

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError as GeminiAPIError
from openai import APIError as OpenAIAPIError
from openai import OpenAI, RateLimitError
from pydantic import BaseModel

def _resolver_project_root() -> Path:
    candidatos = Path(__file__).resolve().parents
    if len(candidatos) > 2 and (candidatos[2] / "pyproject.toml").exists():
        return candidatos[2]
    return Path.cwd()


PROJECT_ROOT = _resolver_project_root()
_CWD_ENV = Path.cwd() / ".env"
if _CWD_ENV.exists():
    load_dotenv(dotenv_path=_CWD_ENV, override=False)
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)
logger = logging.getLogger("llm_provider")


def _parse_optional_int(valor: Optional[str]) -> Optional[int]:
    if valor is None or not valor.strip():
        return None
    return int(valor.strip())


def _parse_optional_bool(valor: Optional[str]) -> Optional[bool]:
    if valor is None or not valor.strip():
        return None
    norm = valor.strip().lower()
    if norm in ("false", "0", "no", "nao", "não"):
        return False
    if norm in ("true", "1", "yes", "sim"):
        return True
    raise ValueError(f"Valor booleano inválido em variável de ambiente: '{valor}'")


def _resolver_refs_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Expande $defs/$ref inline e adiciona 'additionalProperties': False para APIs OpenAI-compat."""
    schema_copia = copy.deepcopy(schema)
    defs = schema_copia.pop("$defs", {})

    def _expandir(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_name = node["$ref"].split("/")[-1]
                alvo = copy.deepcopy(defs.get(ref_name, {}))
                for k, v in node.items():
                    if k != "$ref":
                        alvo[k] = v
                return _expandir(alvo)

            if node.get("type") == "object" or "properties" in node:
                node["additionalProperties"] = False
                if "properties" in node:
                    node["required"] = list(node["properties"].keys())

            return {k: _expandir(v) for k, v in node.items()}

        if isinstance(node, list):
            return [_expandir(item) for item in node]

        return node

    return _expandir(schema_copia)


def _limpar_schema_gemini(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Remove chaves não suportadas pelo OpenAPI Schema do Gemini."""
    schema_copia = copy.deepcopy(schema)
    defs = schema_copia.pop("$defs", {})

    def _limpar(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_name = node["$ref"].split("/")[-1]
                alvo = copy.deepcopy(defs.get(ref_name, {}))
                for k, v in node.items():
                    if k != "$ref":
                        alvo[k] = v
                return _limpar(alvo)

            node.pop("additionalProperties", None)
            node.pop("title", None)
            return {k: _limpar(v) for k, v in node.items()}

        if isinstance(node, list):
            return [_limpar(item) for item in node]

        return node

    return _limpar(schema_copia)


def _erro_http_transiente(status_code: Optional[int]) -> bool:
    """Retorna True para erros transitórios (408, 429, 5xx ou sem código HTTP)."""
    if status_code is None:
        return True
    return status_code in (408, 429) or status_code >= 500


@lru_cache(maxsize=16)
def _obter_schema_openai_compat(response_model: Type[BaseModel]) -> Dict[str, Any]:
    return _resolver_refs_schema(response_model.model_json_schema())


@lru_cache(maxsize=16)
def _obter_schema_openai_json(response_model: Type[BaseModel]) -> str:
    return json.dumps(_obter_schema_openai_compat(response_model), ensure_ascii=False)


@lru_cache(maxsize=16)
def _obter_schema_gemini(response_model: Type[BaseModel]) -> Dict[str, Any]:
    return _limpar_schema_gemini(response_model.model_json_schema())


class LLMClient:
    """
    Cliente modular para inferência estruturada.
    Suporta: gemini, openrouter, ollama e llama.
    """

    OPENAI_COMPAT_PRESETS = {
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "env_key": "OPENROUTER_API_KEY",
            "default_model": "meta-llama/llama-3.3-70b-instruct:free",
            "default_delay": 4.5,
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "env_key": None,
            "default_model": "qwen2.5:7b-instruct",
            "default_delay": 0.0,
        },
        "llama": {
            "base_url": "http://localhost:8080/v1",
            "env_key": None,
            "default_model": "qwen3:8b",
            "default_delay": 0.0,
        },
    }

    def __init__(self):
        self.provider_name = (os.getenv("LLM_PROVIDER") or "openrouter").strip().lower()
        self.num_ctx = _parse_optional_int(os.getenv("LLM_NUM_CTX"))
        self.think = _parse_optional_bool(os.getenv("LLM_THINK"))
        self._ultimo_chamado: Optional[float] = None

        if self.provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
            if not api_key:
                raise EnvironmentError("Variável de ambiente GEMINI_API_KEY (ou LLM_API_KEY) não definida.")
            self.model = os.getenv("LLM_MODEL") or "gemini-2.5-flash"
            self.delay = float(os.getenv("LLM_DELAY") or "4.2")
            self.gemini_client = genai.Client(api_key=api_key)
            self.openai_client = None

        elif self.provider_name in self.OPENAI_COMPAT_PRESETS:
            preset = self.OPENAI_COMPAT_PRESETS[self.provider_name]
            base_url = os.getenv("LLM_BASE_URL") or preset["base_url"]
            self.model = os.getenv("LLM_MODEL") or preset["default_model"]
            self.delay = float(os.getenv("LLM_DELAY") or str(preset["default_delay"]))

            if preset["env_key"]:
                api_key = os.getenv(preset["env_key"]) or os.getenv("LLM_API_KEY")
                if not api_key:
                    raise EnvironmentError(
                        f"Variável de ambiente {preset['env_key']} (ou LLM_API_KEY) não definida."
                    )
            else:
                api_key = os.getenv("LLM_API_KEY") or "ollama"

            self.openai_client = OpenAI(base_url=base_url, api_key=api_key, max_retries=0, timeout=120.0)
            self.gemini_client = None

        else:
            validos = ["gemini", *self.OPENAI_COMPAT_PRESETS.keys()]
            raise ValueError(f"Provedor inválido '{self.provider_name}'. Opções: {validos}")

        logger.info(
            f"LLMClient inicializado | Provider: {self.provider_name} | "
            f"Modelo: {self.model} | Delay: {self.delay}s"
        )

    def _aguardar_rate_limit(self) -> None:
        if self.delay > 0 and self._ultimo_chamado is not None:
            restante = self.delay - (time.monotonic() - self._ultimo_chamado)
            if restante > 0:
                time.sleep(restante)

    def _chamar_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        max_retries: int,
    ) -> str:
        schema_limpo = _obter_schema_gemini(response_model)
        config_kwargs: Dict[str, Any] = {
            "system_instruction": system_prompt,
            "temperature": 0.0,
            "response_mime_type": "application/json",
            "response_schema": schema_limpo,
        }
        thinking_budget = _parse_optional_int(os.getenv("LLM_THINKING_BUDGET"))
        if thinking_budget is not None:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
        config = types.GenerateContentConfig(**config_kwargs)

        for tentativa in range(1, max_retries + 1):
            try:
                self._aguardar_rate_limit()
                response = self.gemini_client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=config,
                )
                self._ultimo_chamado = time.monotonic()
                texto = getattr(response, "text", None)
                if not texto or not texto.strip():
                    raise ValueError("Resposta vazia retornada pelo Gemini.")
                return texto
            except GeminiAPIError as e:
                status_code = getattr(e, "code", None)
                if tentativa == max_retries or not _erro_http_transiente(status_code):
                    raise
                espera = (2**tentativa) * 10 if status_code == 429 else 2**tentativa
                logger.warning(f"Erro Gemini (HTTP {status_code}). Aguardando {espera}s...")
                time.sleep(espera)

        raise RuntimeError("Falha no Gemini após múltiplas tentativas.")

    def _chamar_openai_compat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        max_retries: int,
    ) -> str:
        usar_strict = self.provider_name == "ollama"

        if usar_strict:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": _obter_schema_openai_compat(response_model),
                },
            }
            prompt_final = user_prompt
        else:
            response_format = {"type": "json_object"}
            schema_json = _obter_schema_openai_json(response_model)
            prompt_final = (
                f"{user_prompt}\n\n"
                f"OBRIGATÓRIO: Responda apenas com um objeto JSON válido aderente a este JSON Schema:\n"
                f"{schema_json}"
            )

        extra_body: Dict[str, Any] = {}
        if self.provider_name == "ollama":
            if self.num_ctx is not None:
                extra_body["options"] = {"num_ctx": self.num_ctx}
            if self.think is not None:
                extra_body["think"] = self.think

        for tentativa in range(1, max_retries + 1):
            try:
                request_kwargs: Dict[str, Any] = {
                    "model": self.model,
                    "temperature": 0.0,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_final},
                    ],
                    "response_format": response_format,
                }
                if extra_body:
                    request_kwargs["extra_body"] = extra_body

                self._aguardar_rate_limit()
                response = self.openai_client.chat.completions.create(**request_kwargs)
                self._ultimo_chamado = time.monotonic()
                choices = getattr(response, "choices", None) or []
                conteudo = (
                    getattr(choices[0].message, "content", None)
                    if choices and getattr(choices[0], "message", None) is not None
                    else None
                )
                if not conteudo or not conteudo.strip():
                    raise ValueError(f"Resposta vazia retornada por {self.provider_name}.")
                return conteudo

            except RateLimitError as e:
                if tentativa == max_retries:
                    raise
                espera = (2**tentativa) * 15
                logger.warning(f"Rate limit ({self.provider_name}). Aguardando {espera}s... ({e})")
                time.sleep(espera)
            except OpenAIAPIError as e:
                status_code = getattr(e, "status_code", None)
                if tentativa == max_retries or not _erro_http_transiente(status_code):
                    raise
                espera = 2**tentativa
                logger.warning(f"Erro API ({self.provider_name}): {e}. Tentando em {espera}s...")
                time.sleep(espera)

        raise RuntimeError(f"Falha em {self.provider_name} após múltiplas tentativas.")

    def gerar_estruturado(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        max_retries: int = 4,
    ) -> str:
        if self.provider_name == "gemini":
            return self._chamar_gemini(system_prompt, user_prompt, response_model, max_retries)
        return self._chamar_openai_compat(system_prompt, user_prompt, response_model, max_retries)
