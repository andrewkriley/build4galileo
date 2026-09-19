# build4galileo

A reusable, provider-agnostic pattern for building agentic AI workers,
workflows, and applications with well-structured sessions, traces, and
spans — plus a chat MVP that's the first thing built on it.

This repo extracts the agent and observability logic from
[cl-ai-builders](https://github.com/andrewkriley/cl-ai-builders) (a
Splunk-specific workshop app) into `core/`, a small standalone library,
generalizing what was three hardcoded per-provider loops and a fixed
3-tier agent shape into one composable pattern. See
[`core/README.md`](core/README.md) for exactly what changed and why.

## What you'll build

A chat app whose agent:

1. Takes a user's question in a React chat UI.
2. Classifies it (`system` / `files` / `network` — a fast keyword
   heuristic, no extra LLM call) and hands it to a worker scoped to a
   matching system prompt and a **single** tool — classification is real
   access control, not just persona selection.
3. Calls an LLM (Anthropic, OpenAI, or Gemini — your own key; a dropdown in
   the chat UI switches between whichever you have keys for, per message)
   through a provider-agnostic interface.
4. Lets the LLM call a demo MCP server's tools — `system_info`,
   `file_search` (sandboxed, path-traversal guarded), `http_ping`
   (SSRF-guarded) — with the same round-cap and repeated-call safety nets
   cl-ai-builders used against Splunk MCP.
5. Traces each turn to Galileo, structured as `session -> trace ->
   agent(supervisor) -> [agent(classifier), agent(worker) -> [llm, tool,
   ...]]` — every turn in one browser conversation is grouped under one
   Galileo session.

```
 Browser (React chat UI)
       │
       ▼
   FastAPI app ──► supervisor Agent ──► classifier (keyword heuristic)
       │                 │
       │                 ▼
       │           worker Agent ──► LLMProvider (Anthropic / OpenAI / Gemini)
       │                 │                     │
       │                 │                     ▼ (tool calls)
       │                 └──────────► demo MCP server (stdio subprocess)
       │
       ▼
     Galileo (nested trace: supervisor → classifier + worker → llm/tool spans)
```

## Repo layout

| Path | Purpose |
|---|---|
| [`core/`](core/README.md) | Reusable `b4g-core` library: Session/Trace/Span tracer, `LLMProvider` + 3 adapters, composable `Agent`, `ToolLoopGuard` |
| `apps/chat-mvp/backend/` | FastAPI app (`/chat`, `/config`) + the demo MCP server, wiring `core` into a concrete supervisor→classifier→worker tree |
| `apps/chat-mvp/frontend/` | Vite + React + TypeScript chat UI, themed from `andrewkriley/design-system`'s `business-venture` tokens |
| `scripts/sync-tokens.mjs` | Pulls and resolves design tokens from `design-system` into `apps/chat-mvp/frontend/src/styles/tokens.css` (committed, manually re-run) |

## Prerequisites

- **Python 3.11+** and [uv](https://docs.astral.sh/uv/)
- **Node.js 20+** and npm
- Your own Anthropic, OpenAI, or Gemini API key (a billed API key, not a
  Claude.ai/ChatGPT subscription — the app calls the API directly)
- A [Galileo](https://app.galileo.ai/sign-up) account + API key

## Getting started

```
cp .env.example .env   # fill in your Galileo + at least one LLM provider key
uv sync --all-packages
```

Run the backend (spawns the demo MCP server as a subprocess on startup):

```
cd apps/chat-mvp/backend
uv run uvicorn app.main:app --reload
```

Run the frontend, in a second terminal:

```
cd apps/chat-mvp/frontend
npm install
npm run dev
```

Open the frontend's local URL, pick a provider in the header dropdown, and
ask something like "what CPU does this host have?", "find the readme in
the sandbox", or "is 1.1.1.1 reachable?" — then check the Galileo dashboard
for the resulting session/trace/span structure.

## Testing

```
uv run pytest          # core + backend — fully offline, no API keys needed
cd apps/chat-mvp/frontend && npm run lint && npm run typecheck && npm run build
```

## Known limitations

cl-ai-builders documented an unresolved, Galileo-backend-side bug: in a
real multi-round tool-calling conversation, some `llm` spans can silently
fail to reach Galileo (every `tool` span and the trace's own input/output
are unaffected). Several mitigations were tried upstream (bounding payload
size, async clients, per-span flush, `mode="distributed"`) and none fixed
it. This repo carries the same risk — a local durable trace store was
considered as a hardening measure and deliberately left out of this MVP for
simplicity; see `core/README.md`. It's an observability gap only; the
chat app's answers are correct regardless.

## License

MIT — see [`LICENSE`](LICENSE).
