from __future__ import annotations

import json
import os
from typing import Any

from .base import LLMProvider, ProviderResponse, ToolCall

MODEL = "claude-sonnet-5"
# Multi-round tool-calling conversations grow fast; bounding what gets
# logged to the llm span keeps payload size sane regardless of how long
# the real conversation (sent to the API in full, unbounded) runs.
_MAX_LOGGED_TURNS = 6


def _content_to_log_text(blocks: Any) -> str:
    """Flatten Anthropic content blocks (text/tool_use/thinking) into
    readable text for the llm span's logged output — Galileo's add_llm_span
    only renders plain strings cleanly, not structured block lists."""
    parts = []
    for block in blocks:
        if block.type == "text":
            parts.append(block.text)
        elif block.type == "tool_use":
            parts.append(f"[tool_use: {block.name}({json.dumps(block.input)})]")
        elif block.type == "thinking" and block.thinking:
            parts.append(f"[thinking: {block.thinking}]")
    return "\n".join(parts)


def _log_safe_message(message: dict) -> dict:
    """`messages` re-submitted to the Anthropic API after a tool-calling
    round holds the SDK's own response content verbatim (a list of
    TextBlock/ToolUseBlock pydantic objects, per `append_assistant_turn`) —
    the API accepts that shape back, but it isn't JSON-serializable, and
    Galileo's add_llm_span silently drops the whole span if any logged
    message contains one. Flatten it the same way `logged_output` already
    is, so every round's llm span actually reaches Galileo."""
    content = message["content"]
    if isinstance(content, list) and content and hasattr(content[0], "type"):
        return {"role": message["role"], "content": _content_to_log_text(content)}
    return message


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    model = MODEL

    def __init__(self, api_key: str | None = None) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    def initial_messages(self, user_message: str) -> list[dict]:
        return [{"role": "user", "content": user_message}]

    def to_provider_tools(self, mcp_tools: list[dict]) -> list[dict]:
        return [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in mcp_tools
        ]

    def complete(
        self, messages: list[dict], tools: list[dict], system_prompt: str
    ) -> ProviderResponse:
        response = self._client.messages.create(
            model=self.model,
            # A demanding synthesis-style question can eat into a small
            # budget on Sonnet 5's own reasoning before any visible text is
            # emitted, coming back empty at 1024; 4096 gives real headroom.
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=tools or [],
        )
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]
        text = "".join(block.text for block in response.content if block.type == "text")

        return ProviderResponse(
            text=text,
            tool_calls=tool_calls,
            model=self.model,
            num_input_tokens=response.usage.input_tokens,
            num_output_tokens=response.usage.output_tokens,
            logged_input=[
                {"role": "system", "content": system_prompt},
                *(_log_safe_message(m) for m in messages[-_MAX_LOGGED_TURNS:]),
            ],
            logged_output=_content_to_log_text(response.content),
            raw=response,
        )

    def append_assistant_turn(self, messages: list[dict], response: ProviderResponse) -> list[dict]:
        return [*messages, {"role": "assistant", "content": response.raw.content}]

    def append_tool_results(
        self, messages: list[dict], tool_calls: list[ToolCall], results: list[str]
    ) -> list[dict]:
        tool_results = [
            {"type": "tool_result", "tool_use_id": tc.id, "content": result}
            for tc, result in zip(tool_calls, results, strict=True)
        ]
        return [*messages, {"role": "user", "content": tool_results}]
