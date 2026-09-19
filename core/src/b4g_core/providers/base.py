"""Provider-agnostic LLM calling.

`LLMProvider` is one interface instead of branching on provider with a
separate hand-rolled loop function per provider, each with its own message
format, tool-call extraction, and Galileo logging: a single generic
tool-calling loop (see `b4g_core.agents.agent`) drives any provider through
the same four methods, and each adapter is the only place that still needs
to know its provider's native shapes.

A conversation's `messages` value is intentionally opaque to core code —
each provider keeps its own native message format (OpenAI's flat list with
`role="tool"` entries, Anthropic's content blocks, Gemini's `Content`
objects) and only the matching adapter's `initial_messages`/
`append_assistant_turn`/`append_tool_results` ever construct or read it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    num_input_tokens: int | None = None
    num_output_tokens: int | None = None
    # A Galileo-shaped (bounded, block-flattened) version of the request
    # this response answers, for the llm span — see each adapter's
    # `_logged_input`. Kept separate from `messages` so the real
    # conversation sent to the API is never truncated for logging's sake.
    logged_input: Any = None
    # Flattened text for the llm span's output, including markers for
    # tool_use/thinking/function_call blocks the tracer wouldn't otherwise
    # see (since `text` above is deliberately answer-only, used by the tool
    # loop to decide whether the turn is finished). Falls back to `text`.
    logged_output: str | None = None
    raw: Any = None


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def initial_messages(self, user_message: str) -> Any:
        """Build this provider's native message list from the first user turn."""

    @abstractmethod
    def to_provider_tools(self, mcp_tools: list[dict]) -> list[dict]:
        """Translate MCP tool definitions (name/description/input_schema) into
        this provider's native tool-definition format."""

    @abstractmethod
    def complete(self, messages: Any, tools: list[dict], system_prompt: str) -> ProviderResponse:
        """Call the provider once and normalize the result."""

    @abstractmethod
    def append_assistant_turn(self, messages: Any, response: ProviderResponse) -> Any:
        """Return a new message list with the assistant's (tool-calling) turn appended."""

    @abstractmethod
    def append_tool_results(
        self, messages: Any, tool_calls: list[ToolCall], results: list[str]
    ) -> Any:
        """Return a new message list with tool results appended, matched by position
        to `tool_calls`."""
