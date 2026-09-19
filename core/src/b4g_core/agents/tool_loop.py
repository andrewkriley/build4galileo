"""Reusable round-cap + repeated-identical-tool-call guard.

cl-ai-builders reimplemented this by hand in each of its three per-provider
loop functions (`_openai_loop`/`_anthropic_loop`/`_gemini_loop`), each with
its own `seen_calls: set[...]` and `for _ in range(MAX_TURNS)`. One
`ToolLoopGuard` instance does this once, for any provider's loop.
"""

from __future__ import annotations

import json


class ToolLoopLimitExceeded(Exception):
    """Raised when the round cap is hit without a final answer."""

    def __init__(self, max_rounds: int) -> None:
        super().__init__(f"exceeded {max_rounds} rounds without a final answer")
        self.max_rounds = max_rounds


class RepeatedToolCall(Exception):
    """Raised when the exact same tool name + arguments is called twice in one turn —
    a common stuck-agent failure mode, cheaper to catch than waiting for the round cap."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"repeated identical call to {tool_name!r}")
        self.tool_name = tool_name


class ToolLoopGuard:
    def __init__(self, max_rounds: int = 8) -> None:
        self.max_rounds = max_rounds
        self._seen: set[tuple[str, str]] = set()
        self._round = 0

    def next_round(self) -> int:
        self._round += 1
        if self._round > self.max_rounds:
            raise ToolLoopLimitExceeded(self.max_rounds)
        return self._round

    def check(self, tool_name: str, arguments: dict) -> None:
        key = (tool_name, json.dumps(arguments, sort_keys=True))
        if key in self._seen:
            raise RepeatedToolCall(tool_name)
        self._seen.add(key)
