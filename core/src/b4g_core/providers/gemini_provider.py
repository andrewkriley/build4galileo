from __future__ import annotations

import json
import os
from typing import Any

from .base import LLMProvider, ProviderResponse, ToolCall

MODEL = "gemini-3.6-flash"
_MAX_LOGGED_TURNS = 6


def _part_to_log_text(part: Any) -> str:
    if part.text is not None:
        return part.text
    if part.function_call is not None:
        args = json.dumps(dict(part.function_call.args or {}))
        return f"[function_call: {part.function_call.name}({args})]"
    if part.function_response is not None:
        name = part.function_response.name
        payload = json.dumps(dict(part.function_response.response or {}))
        return f"[function_response: {name} -> {payload}]"
    return f"[{type(part).__name__}]"


def _content_to_log_text(content: Any) -> str:
    if content is None:
        return ""
    return "\n".join(_part_to_log_text(part) for part in content.parts)


class GeminiProvider(LLMProvider):
    name = "gemini"
    model = MODEL

    def __init__(self, api_key: str | None = None) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])

    def initial_messages(self, user_message: str) -> list[Any]:
        from google.genai import types

        return [types.Content(role="user", parts=[types.Part.from_text(text=user_message)])]

    def to_provider_tools(self, mcp_tools: list[dict]) -> list[dict]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters_json_schema": t["input_schema"],
            }
            for t in mcp_tools
        ]

    def complete(
        self, messages: list[Any], tools: list[dict], system_prompt: str
    ) -> ProviderResponse:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(function_declarations=tools)] if tools else None,
        )
        response = self._client.models.generate_content(
            model=self.model, contents=messages, config=config
        )

        calls = response.function_calls or []
        tool_calls = [
            ToolCall(id=call.id or call.name, name=call.name, arguments=dict(call.args or {}))
            for call in calls
        ]
        usage = response.usage_metadata
        response_content = response.candidates[0].content if response.candidates else None

        logged_input = [
            {"role": "system", "content": system_prompt},
            *[
                {
                    "role": "assistant" if c.role == "model" else c.role,
                    "content": _content_to_log_text(c),
                }
                for c in messages[-_MAX_LOGGED_TURNS:]
            ],
        ]

        return ProviderResponse(
            text=response.text or "",
            tool_calls=tool_calls,
            model=self.model,
            num_input_tokens=usage.prompt_token_count if usage else None,
            num_output_tokens=usage.candidates_token_count if usage else None,
            logged_input=logged_input,
            logged_output=_content_to_log_text(response_content),
            raw=response,
        )

    def append_assistant_turn(self, messages: list[Any], response: ProviderResponse) -> list[Any]:
        content = response.raw.candidates[0].content if response.raw.candidates else None
        return [*messages, content] if content is not None else list(messages)

    def append_tool_results(
        self, messages: list[Any], tool_calls: list[ToolCall], results: list[str]
    ) -> list[Any]:
        from google.genai import types

        parts = [
            types.Part.from_function_response(name=tc.name, response={"result": result})
            for tc, result in zip(tool_calls, results, strict=True)
        ]
        return [*messages, types.Content(role="user", parts=parts)]
