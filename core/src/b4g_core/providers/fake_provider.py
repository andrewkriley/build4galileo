"""A scripted LLMProvider for tests — no network calls, no API keys.

Feed it a list of `ProviderResponse`s; each `complete()` call returns the
next one. Used by `core/tests` and `apps/chat-mvp/backend/tests` so the
agent/tool-loop/tracer machinery is fully exercised offline.
"""

from __future__ import annotations

from typing import Any

from .base import LLMProvider, ProviderResponse, ToolCall


class FakeProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, script: list[ProviderResponse]) -> None:
        self._script = list(script)
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    def initial_messages(self, user_message: str) -> list[dict]:
        return [{"role": "user", "content": user_message}]

    def to_provider_tools(self, mcp_tools: list[dict]) -> list[dict]:
        return mcp_tools

    def complete(self, messages: Any, tools: list[dict], system_prompt: str) -> ProviderResponse:
        if self._call_count >= len(self._script):
            raise AssertionError("FakeProvider script exhausted")
        response = self._script[self._call_count]
        self._call_count += 1
        return response

    def append_assistant_turn(
        self, messages: list[dict], response: ProviderResponse
    ) -> list[dict]:
        calls = [
            {"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls
        ]
        return [*messages, {"role": "assistant", "content": response.text, "tool_calls": calls}]

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
