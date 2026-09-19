from __future__ import annotations

import json
import os

from .base import LLMProvider, ProviderResponse, ToolCall

MODEL = "gpt-4o"
_MAX_LOGGED_TURNS = 6


class OpenAIProvider(LLMProvider):
    name = "openai"
    model = MODEL

    def __init__(self, api_key: str | None = None) -> None:
        from openai import OpenAI

        # Plain client on purpose, not Galileo's `galileo.openai` import-swap
        # wrapper: that wrapper only patches the sync client's
        # `chat.completions.create`, and using it here would make this
        # provider log a differently-shaped llm span than Anthropic/Gemini
        # (Galileo's own auto-capture vs. our explicit add_llm_span) — the
        # entire point of this adapter is that all three providers emit
        # spans through the same path in `GalileoTracer`.
        self._client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])

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
