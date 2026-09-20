"""Shared request/response handling for any server that speaks OpenAI's
`/v1/chat/completions` wire format — the real OpenAI API, and self-hosted
vLLM/Ollama servers that mimic it closely enough to reuse the same client.

Subclasses only need to set up `self._client` (an `openai.OpenAI` pointed at
the right `base_url`/`api_key`) and `self.model`; everything below is
provider-agnostic OpenAI wire format, not OpenAI-the-company-specific.
"""

from __future__ import annotations

import json
from typing import Any

from .base import LLMProvider, ProviderResponse, ToolCall

# Multi-round tool-calling conversations grow fast; bounding what gets
# logged to the llm span keeps payload size sane regardless of how long
# the real conversation (sent to the API in full, unbounded) runs.
_MAX_LOGGED_TURNS = 6


class OpenAICompatibleProvider(LLMProvider):
    _client: Any

    def initial_messages(self, user_message: str) -> list[dict]:
        return [{"role": "user", "content": user_message}]

    def to_provider_tools(self, mcp_tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in mcp_tools
        ]

    def complete(
        self, messages: list[dict], tools: list[dict], system_prompt: str
    ) -> ProviderResponse:
        full_messages = [{"role": "system", "content": system_prompt}, *messages]
        response = self._client.chat.completions.create(
            model=self.model, messages=full_messages, tools=tools or None
        )
        message = response.choices[0].message
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments or "{}"),
            )
            for tc in (message.tool_calls or [])
        ]
        usage = response.usage

        return ProviderResponse(
            text=message.content or "",
            tool_calls=tool_calls,
            model=self.model,
            num_input_tokens=usage.prompt_tokens if usage else None,
            num_output_tokens=usage.completion_tokens if usage else None,
            logged_input=[
                {"role": "system", "content": system_prompt},
                *messages[-_MAX_LOGGED_TURNS:],
            ],
            raw=response,
        )

    def append_assistant_turn(self, messages: list[dict], response: ProviderResponse) -> list[dict]:
        return [*messages, response.raw.choices[0].message.model_dump(exclude_unset=True)]

    def append_tool_results(
        self, messages: list[dict], tool_calls: list[ToolCall], results: list[str]
    ) -> list[dict]:
        return [
            *messages,
            *(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
                for tc, result in zip(tool_calls, results, strict=True)
            ),
        ]
