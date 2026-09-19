"""Environment configuration for the chat MVP backend."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

GALILEO_PROJECT = os.environ.get("GALILEO_PROJECT", "build4galileo")
GALILEO_LOG_STREAM = os.environ.get("GALILEO_LOG_STREAM", "default")
DEFAULT_LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")

_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def available_providers() -> list[str]:
    """Providers the chat UI's dropdown may actually offer — only ones with
    a key set, mirroring cl-ai-builders' `/config` readiness check."""
    return [name for name, env_var in _KEY_ENV_VARS.items() if os.environ.get(env_var)]
