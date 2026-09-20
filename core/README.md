# b4g-core

A small, reusable pattern for building agentic AI workers/workflows/apps
with well-structured sessions, traces, and spans. `apps/chat-mvp` in this
repo is one concrete consumer of it.

## Design decisions

**Provider abstraction.** `providers.LLMProvider` is one interface
(`initial_messages`/`to_provider_tools`/`complete`/`append_assistant_turn`/
`append_tool_results`); `agents.Agent` drives any provider through the same
generic loop, and `tracing.GalileoTracer` logs every provider's `llm` span
through the identical `add_llm_span` call — no separate per-provider loop
function, and no provider gets a structurally different span shape or a
different Galileo logging path than the others.

**A real tracer abstraction.** `tracing.Tracer` defines backend-agnostic
`Session`/`Trace`/`Span` primitives as context managers
(`trace.span(type, name, input) -> SpanHandle`). Nesting is structural —
calling `.span()` on a handle makes the new span its child — so it always
matches Python's own `with`-block nesting, which is also exactly the
implicit stack Galileo's `add_agent_span()`/`conclude()` API expects (see
`tracing/galileo_tracer.py`'s module docstring for how that bridge works).
Application code never imports anything Galileo-specific; only
`GalileoTracer` does. Swapping to a different observability backend later
means writing one new `Tracer` subclass, not touching agent code.

**N-tier `Agent` composition instead of a hardcoded shape.** An `Agent` is
either a **router** (`children` + a `route` function, no `provider` — this
is what keeps a classifier "a fast heuristic, no extra LLM call" a
structural property, not an accident) or a **leaf worker** (a `provider` +
scoped `mcp_tools`). Routers can nest arbitrarily deep; span nesting always
mirrors the actual call graph. `apps/chat-mvp` builds a 3-tier
supervisor→classifier→worker for its MVP, but that's one particular
composition of the primitive, not the primitive's structure.

> Scope note: routing is single-child only — a router picks exactly one
> child per turn. Fanning out to multiple categories and synthesizing
> across them (for a question that spans more than one) is a natural
> extension of this primitive, deliberately not implemented here.

**A reusable tool-loop guard.** The round cap + repeated-identical-tool-call
guard (`agents.ToolLoopGuard`) is one utility any worker's loop uses, not
reimplemented per provider.

**Tracer backend: Galileo only, synchronous.** A local durable trace store
(to harden against Galileo's own `flush()`/ingest path occasionally
failing to log a span on multi-round conversations — see
`tracing/galileo_tracer.py` and the root README's "Known limitations") was
considered and explicitly decided against for this repo, in favor of
simplicity. The `Tracer` interface stays backend-agnostic by design even
though only `GalileoTracer` ships today — that's a stated non-goal-for-now,
not an oversight.

## Layout

```
src/b4g_core/
├── tracing/    Session/Trace/Span + the Tracer protocol, GalileoTracer, NoopTracer
├── providers/  LLMProvider + Anthropic/OpenAI/Gemini/vLLM/Ollama adapters + FakeProvider (tests)
├── agents/     Agent (router/leaf composition), ToolLoopGuard, run_turn (session+trace glue)
└── mcp/        thin MCP client wrapper (stdio transport)
```

## Minimal usage

```python
from b4g_core import Agent, GalileoTracer, run_turn
from b4g_core.providers import AnthropicProvider

worker = Agent(
    name="files_worker",
    agent_type="react",
    system_prompt="...",
    provider=AnthropicProvider(),
    mcp_tools=mcp_tool_list,       # from b4g_core.mcp.list_tools(session)
    call_tool=my_call_tool,        # async (name, args) -> str
)
supervisor = Agent(
    name="supervisor",
    agent_type="supervisor",
    route=classify,                # (user_message: str) -> str, a key into `children`
    children={"files": worker},
)

tracer = GalileoTracer()  # or NoopTracer() for tests/offline
answer = await run_turn(tracer, session_id, supervisor, user_message)
```

Every turn in the same `session_id` lands in one Galileo session containing
one trace per turn, each shaped `agent(supervisor) -> [agent(classifier),
agent(worker) -> [llm, tool, ...]]`.

## Testing

`core/tests` runs fully offline against `FakeProvider` (a scripted
`LLMProvider`) and a `RecordingTracer` test double — no network calls, no
API keys, no Galileo dependency. Run from the repo root:

```
uv run pytest core/tests
```
