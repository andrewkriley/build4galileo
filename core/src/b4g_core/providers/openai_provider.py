from __future__ import annotations

import os

from .openai_compatible import OpenAICompatibleProvider

MODEL = "gpt-4o"


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    model = MODEL

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        from openai import OpenAI

        # Plain client on purpose, not Galileo's `galileo.openai` import-swap
        # wrapper: that wrapper only patches the sync client's
        # `chat.completions.create`, and using it here would make this
        # provider log a differently-shaped llm span than Anthropic/Gemini
        # (Galileo's own auto-capture vs. our explicit add_llm_span) — the
        # entire point of this adapter is that all three providers emit
        # spans through the same path in `GalileoTracer`.
        self.model = model or MODEL
        self._client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
