"""FastAPI app for the build4galileo chat MVP.

`POST /chat` runs one turn through the core session/trace/agent pattern
(see `b4g_core` and this app's `agents.py`); `GET /config` reports which
LLM providers have a key configured, over HTTP, so the frontend's provider
dropdown only offers ones that'll actually work.

The demo MCP server is spawned once, as a subprocess, at startup (not
per-request) and its `ClientSession` is reused for the app's lifetime —
cheaper than paying subprocess-startup cost on every chat turn. One shared
session across concurrent requests is a known simplification (this is a
single-user demo, not a multi-tenant service) — provider calls are
synchronous and block the event loop for their duration, which naturally
serializes most of a turn anyway.
"""

from __future__ import annotations

import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from b4g_core import GalileoTracer, run_turn
from b4g_core.mcp import call_tool as mcp_call_tool
from b4g_core.mcp import list_tools, stdio_mcp_session
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config
from .agents import build_supervisor
from .timeline import build_timeline

_MCP_SERVER_ARGS = ["-m", "mcp_server.server"]


class AppState:
    tracer: GalileoTracer
    mcp_session: object
    mcp_tools: list[dict]


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    state.tracer = GalileoTracer(
        project=config.GALILEO_PROJECT, log_stream=config.GALILEO_LOG_STREAM
    )
    async with stdio_mcp_session(sys.executable, _MCP_SERVER_ARGS) as session:
        state.mcp_session = session
        state.mcp_tools = await list_tools(session)
        yield


app = FastAPI(title="build4galileo chat MVP", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str
    provider: str = config.DEFAULT_LLM_PROVIDER


class ChatResponse(BaseModel):
    answer: str
    # This turn's Galileo trace, as a flat ordered list the frontend renders
    # as a nested timeline — see `app/timeline.py` and
    # `b4g_core.tracing.tracer`'s `on_event` hook for where it comes from.
    timeline: list[dict[str, Any]] = []


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if req.provider not in config.available_providers():
        raise HTTPException(400, f"no API key configured for provider {req.provider!r}")

    async def call_tool(name: str, arguments: dict) -> str:
        return await mcp_call_tool(state.mcp_session, name, arguments)

    supervisor = build_supervisor(req.provider, state.mcp_tools, call_tool)

    events: list[dict[str, Any]] = []
    turn_started_at = time.time()
    # `state.tracer` is one shared instance for the app's lifetime (see this
    # module's docstring on the single-user demo simplification), so this is
    # only safe because a turn's provider calls are synchronous and block
    # the event loop — no other request's events can interleave here.
    state.tracer.on_event = events.append
    try:
        answer = await run_turn(state.tracer, req.session_id, supervisor, req.message)
    finally:
        state.tracer.on_event = None

    return ChatResponse(answer=answer, timeline=build_timeline(events, turn_started_at))


@app.get("/config")
async def get_config() -> dict:
    return {
        "available_providers": config.available_providers(),
        "default_provider": config.DEFAULT_LLM_PROVIDER,
    }
