from __future__ import annotations

import os

from .openai_compatible import OpenAICompatibleProvider

# A self-hosted vLLM server's OpenAI-compatible endpoint; unlike the cloud
# providers there's no single "the" model — whatever's loaded on the server
# is whatever gets served, so this default only matters if neither an
# explicit `model` nor `VLLM_MODEL` is given.
DEFAULT_BASE_URL = "http://localhost:8000/v1"
DEFAULT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"


class VLLMProvider(OpenAICompatibleProvider):
    """OpenAI-compatible provider for a self-hosted vLLM server.

    vLLM serves the same `/v1/chat/completions` shape as OpenAI, so this
    reuses `OpenAICompatibleProvider`'s request/response handling and only
    swaps the client's `base_url`, auth (vLLM ignores the API key unless it
    was started with one configured), and which model name to send.
    """

    name = "vllm"
    model = DEFAULT_MODEL

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.model = model or os.environ.get("VLLM_MODEL", DEFAULT_MODEL)
        self._client = OpenAI(
            base_url=base_url or os.environ.get("VLLM_BASE_URL", DEFAULT_BASE_URL),
            api_key=api_key or os.environ.get("VLLM_API_KEY", "not-needed"),
        )
