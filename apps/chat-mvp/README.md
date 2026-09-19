# chat-mvp

The concrete consumer of [`b4g-core`](../../core/README.md): a FastAPI
backend running a supervisor→classifier→worker `Agent` tree against a demo
MCP server, and a Vite/React/TypeScript chat UI.

## Backend

```
cd apps/chat-mvp/backend
uv run uvicorn app.main:app --reload
```

- `POST /chat` — `{message, session_id, provider}` → `{answer}`. Runs one
  turn through `b4g_core.run_turn`.
- `GET /config` — `{available_providers, default_provider}`, so the
  frontend's dropdown only offers providers with a key actually set.

On startup, the app spawns `mcp_server/server.py` as a stdio subprocess
(not per-request — see `app/main.py`'s module docstring for why) and keeps
one `ClientSession` open for the app's lifetime.

### Layout

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI app, lifespan-managed MCP session |
| `app/agents.py` | Builds the supervisor/classifier/worker `Agent` tree for one turn |
| `app/classifier.py` | Keyword-heuristic classifier: `system` / `files` / `network` |
| `app/config.py` | Env config + which providers have keys set |
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

Themed from `andrewkriley/design-system`'s `business-venture` tokens
(`src/styles/tokens.css`, regenerated via `node scripts/sync-tokens.mjs`
from the repo root — see that script's docstring for why it's manual, not
build-time).

```
npm run lint       # eslint
npm run typecheck  # tsc -b --noEmit
npm run build      # production build
```
