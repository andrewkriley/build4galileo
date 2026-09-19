"""Composable N-tier agents.

An `Agent` is either:

- a **router**: has `children` and a `route` function that picks one child
  by name from the user message, with no `provider` of its own. This keeps
  a classifier "a fast heuristic, no extra LLM call" a structural property
  of the primitive rather than an accident of how one example app used it.
  Routing gets its own nested "classifier" agent span, a sibling of the
  chosen child's span (not a wrapper around it) — matching cl-ai-builders'
  `supervisor -> [classifier, worker -> [llm, tool, ...]]` trace shape.
- a **leaf worker**: has a `provider` and `mcp_tools`, and runs a generic
  provider-agnostic tool-calling loop (round cap + repeated-call guard via
  `ToolLoopGuard`) against its scoped tool subset.

Nesting is unlimited — a router's child can itself be another router — and
span nesting always mirrors the actual call graph (see
`b4g_core.tracing.tracer`), so composing more tiers never needs extra
bookkeeping.

This intentionally supports single-child routing only: a router picks
exactly one child per turn. cl-ai-builders' fan-out-to-multiple-categories-
then-synthesize behavior is a natural extension of this primitive, not
implemented here — see core/README.md.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from ..providers.base import LLMProvider
from ..tracing.tracer import SpanHandle, TraceHandle
from .tool_loop import RepeatedToolCall, ToolLoopGuard, ToolLoopLimitExceeded

ToolCaller = Callable[[str, dict], Awaitable[str]]
Router = Callable[[str], str]
ParentSpan = TraceHandle | SpanHandle

_EMPTY_ANSWER_MESSAGE = (
    "The model finished without producing a final answer — this can happen on a demanding "
    "question if it runs out of response budget. Try asking again or narrowing the question."
)
_TURN_LIMIT_MESSAGE = "Reached the tool-call limit for this turn without a final answer."


def _repeated_call_message(tool_name: str) -> str:
    return (
        f"Stopped after detecting a repeated identical call to {tool_name} — the model may be "
        "stuck. Try rephrasing your question."
    )


@dataclass
class Agent:
    name: str
    system_prompt: str = ""
    agent_type: str = "default"  # forwarded to GalileoTracer's add_agent_span

    # Leaf-worker fields
    provider: LLMProvider | None = None
    mcp_tools: list[dict] = field(default_factory=list)
    call_tool: ToolCaller | None = None
    max_rounds: int = 8

    # Router fields
    children: dict[str, Agent] = field(default_factory=dict)
    route: Router | None = None
    classifier_name: str = "classifier"

    def is_router(self) -> bool:
        return self.route is not None

    def __post_init__(self) -> None:
        if self.is_router() and (self.provider is not None or self.mcp_tools):
            raise ValueError(f"agent {self.name!r}: a router cannot also have provider/mcp_tools")
        if not self.is_router() and self.provider is None:
            raise ValueError(f"agent {self.name!r}: a leaf agent needs a provider")

    async def run(self, user_message: str, parent: ParentSpan) -> str:
        with parent.span("agent", self.name, input=user_message) as agent_span:
            agent_span.set_metadata(agent_type=self.agent_type)
            if self.is_router():
                result = await self._run_router(user_message, agent_span)
            else:
                result = await self._run_worker(user_message, agent_span)
            agent_span.set_output(result)
            return result

    async def _run_router(self, user_message: str, agent_span: SpanHandle) -> str:
        assert self.route is not None
        with agent_span.span("agent", self.classifier_name, input=user_message) as cls_span:
            cls_span.set_metadata(agent_type="classifier")
            child_name = self.route(user_message)
            cls_span.set_output(child_name)

        child = self.children[child_name]
        return await child.run(user_message, agent_span)

    async def _run_worker(self, user_message: str, agent_span: SpanHandle) -> str:
        assert self.provider is not None
        guard = ToolLoopGuard(max_rounds=self.max_rounds)
        provider_tools = self.provider.to_provider_tools(self.mcp_tools)
        messages = self.provider.initial_messages(user_message)

        while True:
            try:
                guard.next_round()
            except ToolLoopLimitExceeded:
                return _TURN_LIMIT_MESSAGE

            with agent_span.span("llm", self.provider.name, input=user_message) as llm_span:
                response = self.provider.complete(messages, provider_tools, self.system_prompt)
                llm_span.set_output(response.logged_output or response.text)
                llm_span.set_metadata(
                    model=response.model,
                    tools=provider_tools,
                    num_input_tokens=response.num_input_tokens,
                    num_output_tokens=response.num_output_tokens,
                    logged_input=response.logged_input,
                )

            if not response.tool_calls:
                return response.text or _EMPTY_ANSWER_MESSAGE

            messages = self.provider.append_assistant_turn(messages, response)
            results: list[str] = []
            for tool_call in response.tool_calls:
                try:
                    guard.check(tool_call.name, tool_call.arguments)
                except RepeatedToolCall:
                    return _repeated_call_message(tool_call.name)

                assert self.call_tool is not None, f"{self.name!r} has tools but no call_tool"
                with agent_span.span(
                    "tool", tool_call.name, input=tool_call.arguments
                ) as tool_span:
                    result = await self.call_tool(tool_call.name, tool_call.arguments)
                    tool_span.set_output(result)
                results.append(result)

            messages = self.provider.append_tool_results(messages, response.tool_calls, results)
