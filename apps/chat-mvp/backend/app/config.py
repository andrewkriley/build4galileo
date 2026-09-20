"""Environment configuration for the chat MVP backend."""

from __future__ import annotations

import os

import httpx2 as httpx
from b4g_core.providers import PROVIDERS
from dotenv import load_dotenv

load_dotenv()

GALILEO_PROJECT = os.environ.get("GALILEO_PROJECT", "build4galileo")
GALILEO_LOG_STREAM = os.environ.get("GALILEO_LOG_STREAM", "default")
DEFAULT_LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")

# Cloud providers: gated by an API key env var, one fixed model each.
_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

# Local, self-hosted providers: gated by a base-url env var instead of a
# key — there's nothing to authenticate, so "configured" means "the user
# pointed us at a server". Model choice for these isn't fixed like the
# cloud providers above; it's whatever's actually loaded there right now
# (see `available_models`).
_LOCAL_BASE_URL_ENV_VARS = {
    "vllm": "VLLM_BASE_URL",
    "ollama": "OLLAMA_BASE_URL",
}


def available_providers() -> list[str]:
    """Providers the chat UI's dropdown may actually offer — cloud
    providers with a key actually set, plus local providers pointed at a
    server."""
    cloud = [name for name, env_var in _KEY_ENV_VARS.items() if os.environ.get(env_var)]
    local = [name for name, env_var in _LOCAL_BASE_URL_ENV_VARS.items() if os.environ.get(env_var)]
    return cloud + local


def available_models(provider: str) -> list[str]:
    """Model choices to offer for `provider`, so the chat UI's model
    dropdown can be populated once a provider is picked.

    Cloud providers each support exactly one fixed model today; local
    providers (vLLM, Ollama) report whatever's actually loaded on the
    server right now via its OpenAI-compatible `/v1/models` endpoint —
    hardcoding a model catalog for those would just go stale."""
    if provider in _KEY_ENV_VARS:
        return [PROVIDERS[provider].model]

    if provider in _LOCAL_BASE_URL_ENV_VARS:
        base_url = os.environ.get(_LOCAL_BASE_URL_ENV_VARS[provider])
        if not base_url:
            return []
        try:
            response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=2.0)
            response.raise_for_status()
            return sorted(m["id"] for m in response.json().get("data", []))
        except httpx.HTTPError:
            return []

    return []
