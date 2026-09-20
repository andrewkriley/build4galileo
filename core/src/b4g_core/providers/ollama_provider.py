from __future__ import annotations

import os

from .openai_compatible import OpenAICompatibleProvider

# Ollama's OpenAI-compatible endpoint; like vLLM, the actual model is
# whatever the user has pulled locally, so this default only matters if
# neither an explicit `model` nor `OLLAMA_MODEL` is given.
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.1"


class OllamaProvider(OpenAICompatibleProvider):
    """OpenAI-compatible provider for a local Ollama server.

    Ollama serves an OpenAI-compatible `/v1/chat/completions` (and
    `/v1/models`) endpoint, so this reuses
    `OpenAICompatibleProvider`'s request/response handling and only swaps
    the client's `base_url`, auth (Ollama doesn't check the API key at
    all), and which locally-pulled model to send.
    """

    name = "ollama"
    model = DEFAULT_MODEL

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
        self._client = OpenAI(
            base_url=base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL),
            api_key=api_key or "ollama",
        )
