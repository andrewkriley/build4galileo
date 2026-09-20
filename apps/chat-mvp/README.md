# chat-mvp

The concrete consumer of [`b4g-core`](../../core/README.md): a FastAPI
backend running a supervisor→classifier→worker `Agent` tree against a demo
MCP server, and a Vite/React/TypeScript chat UI.

## Backend

```
cd apps/chat-mvp/backend
uv run uvicorn app.main:app --reload
```

- `POST /chat` — `{message, session_id, provider, model}` → `{answer, timeline}`.
  Runs one turn through `b4g_core.run_turn`; `timeline` is that turn's
  session/trace/span structure, formatted for the frontend's own "Galileo
  trace" display (see `app/timeline.py` — it mirrors what gets sent to
  Galileo, it isn't read back from Galileo's API).
- `GET /config` — `{available_providers, default_provider, models}`, so the
  frontend's provider dropdown only offers providers that are actually
  configured (a key for a cloud provider, a base URL for a local one), and
  its model dropdown only offers models `models[provider]` reports for the
  currently selected provider.

Providers: `anthropic`, `openai`, `gemini` (cloud, gated by an API key) and
`vllm`, `ollama` (self-hosted, gated by a base URL — see `.env.example`).
The two local providers report their model list live from the server's own
OpenAI-compatible `/v1/models` endpoint, since it's whatever's actually
loaded there, not a fixed catalog.

On startup, the app spawns `mcp_server/server.py` as a stdio subprocess
(not per-request — see `app/main.py`'s module docstring for why) and keeps
one `ClientSession` open for the app's lifetime.

### Layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app, lifespan-managed MCP session |
| `app/agents.py` | Builds the supervisor/classifier/worker `Agent` tree for one turn |
| `app/classifier.py` | Keyword-heuristic classifier: `system` / `files` / `network` |
| `app/config.py` | Env config + which providers/models are available |
| `app/timeline.py` | Turns one turn's trace/span events into the frontend's "Galileo trace" display |
| `mcp_server/server.py` | Demo MCP server: `system_info`, `file_search`, `http_ping` |
| `mcp_server/sandbox.py` | Path-containment guard for `file_search` |
| `mcp_server/sandbox_root/` | Sample files `file_search` can find |

### Tests

```
uv run pytest apps/chat-mvp/backend/tests
```

Fully offline: the demo MCP server tests exercise real path-traversal and
SSRF-guard attempts, and the app-boot test spawns the real MCP subprocess
but never calls an LLM.

## Frontend

```
cd apps/chat-mvp/frontend
npm install
npm run dev
```

Themed from `andrewkriley/design-system`'s `therileys-team` pattern — a
self-contained, dark-only token set, not merged with `shared.json`
(`src/styles/tokens.css`, regenerated via `node scripts/sync-tokens.mjs`
from the repo root — see that script's docstring for why it's manual, not
build-time). Each assistant reply also renders its own turn's trace as a
collapsible "Galileo trace" (`src/components/TraceTimeline.tsx`).

```
npm run lint       # eslint
npm run typecheck  # tsc -b --noEmit
npm run build      # production build
```
