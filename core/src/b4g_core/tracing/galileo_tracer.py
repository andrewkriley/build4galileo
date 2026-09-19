"""Tracer implementation backed by the real Galileo SDK.

Bridges our generic start/end span model onto Galileo's own stack-based
span API (`add_agent_span(...)` ... `conclude(...)`, plus atomic
`add_llm_span(...)`/`add_tool_span(...)` calls). This works because our
`SpanHandle` context managers already nest LIFO via Python's `with` block
nesting — exactly the discipline Galileo's implicit span stack expects: a
child span's `__exit__` always fires before its parent's, so `conclude()`
always closes the span that was most recently opened.

Two span kinds are logged differently, matching what cl-ai-builders'
`app/observability.py` found necessary in practice:

- "agent" spans are containers with children: `add_agent_span(...)` opens
  them in `_persist_span_start`, `conclude(...)` closes them in
  `_persist_span_end`.
- "llm" and "tool" spans are leaves with no children, logged in one atomic
  call once both input and output are known — so they're a no-op at
  `_persist_span_start` and fully logged in `_persist_span_end`. This is
  also what keeps every provider's `llm` span shaped identically: unlike
  cl-ai-builders (which used Galileo's OpenAI-only `galileo.openai` native
  wrapper for one provider and hand-built spans for the other two), every
  `LLMProvider` adapter here funnels through this same `add_llm_span` call.

`llm` spans expect richer metadata (model name, token counts, a
Galileo-shaped message list) than the generic `Span` record carries by
default — provider adapters attach that via `span_handle.set_metadata(...)`
before the span closes; see `b4g_core.providers`.
"""

from __future__ import annotations

import os
from typing import Any

from galileo import galileo_context, start_session

from .tracer import Tracer
from .types import Session, Span, Trace


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    import json

    return json.dumps(value, default=str)


def _status_code(status: str) -> int:
    return 0 if status == "ok" else 1


def _duration_ns(started_at: float, ended_at: float | None) -> int | None:
    if ended_at is None:
        return None
    return int((ended_at - started_at) * 1e9)


class GalileoTracer(Tracer):
    def __init__(self, project: str | None = None, log_stream: str | None = None) -> None:
        self._project = project or os.environ["GALILEO_PROJECT"]
        self._log_stream = log_stream or os.environ.get("GALILEO_LOG_STREAM", "default")
        self._galileo_session_ids: dict[str, str] = {}
        self._active_contexts: dict[str, Any] = {}

    def _persist_session(self, session: Session) -> None:
        # `session.id` is our caller's stable key (the chat MVP's
        # frontend-generated conversation id); Galileo mints its own
        # session id the first time we see it, then every later trace in
        # the same conversation reuses it — so a full multi-turn browser
        # conversation lands in one Galileo session containing many traces.
        if session.id not in self._galileo_session_ids:
            name = f"build4galileo-{session.id}"
            self._galileo_session_ids[session.id] = start_session(name=name)

    def _persist_trace_start(self, trace: Trace) -> None:
        context = galileo_context(
            project=self._project,
            log_stream=self._log_stream,
            session_id=self._galileo_session_ids[trace.session_id],
        )
        context.__enter__()
        self._active_contexts[trace.id] = context

        logger = galileo_context.get_logger_instance()
        logger.start_trace(input=_to_text(trace.input))

    def _persist_trace_end(self, trace: Trace) -> None:
        logger = galileo_context.get_logger_instance()
        logger.conclude(
            output=_to_text(trace.output),
            status_code=_status_code(trace.status),
            duration_ns=_duration_ns(trace.started_at, trace.ended_at),
        )
        galileo_context.flush()

        context = self._active_contexts.pop(trace.id, None)
        if context is not None:
            context.__exit__(None, None, None)

    def _persist_span_start(self, span: Span) -> None:
        if span.span_type != "agent":
            return  # llm/tool spans are atomic — logged entirely on end
        logger = galileo_context.get_logger_instance()
        logger.add_agent_span(
            input=_to_text(span.input),
            name=span.name,
            agent_type=span.metadata.get("agent_type", "default"),
        )

    def _persist_span_end(self, span: Span) -> None:
        logger = galileo_context.get_logger_instance()
        duration_ns = _duration_ns(span.started_at, span.ended_at)

        if span.span_type == "agent":
            logger.conclude(
                output=_to_text(span.output),
                status_code=_status_code(span.status),
                duration_ns=duration_ns,
            )
        elif span.span_type == "llm":
            meta = span.metadata
            logger.add_llm_span(
                input=meta.get("logged_input", span.input),
                output=_to_text(span.output),
                model=meta.get("model"),
                name=span.name,
                tools=meta.get("tools"),
                num_input_tokens=meta.get("num_input_tokens"),
                num_output_tokens=meta.get("num_output_tokens"),
                status_code=_status_code(span.status),
                duration_ns=duration_ns,
            )
        elif span.span_type == "tool":
            logger.add_tool_span(
                input=_to_text(span.input),
                output=_to_text(span.output),
                name=span.name,
                status_code=_status_code(span.status),
                duration_ns=duration_ns,
            )
