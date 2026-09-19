"""A Tracer that records every persisted event, for asserting on span
nesting/ordering in tests without touching Galileo or any other backend."""

from __future__ import annotations

from b4g_core.tracing.tracer import Tracer
from b4g_core.tracing.types import Session, Span, Trace


class RecordingTracer(Tracer):
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def _persist_session(self, session: Session) -> None:
        self.events.append(("session", session))

    def _persist_trace_start(self, trace: Trace) -> None:
        self.events.append(("trace_start", trace))

    def _persist_trace_end(self, trace: Trace) -> None:
        self.events.append(("trace_end", trace))

    def _persist_span_start(self, span: Span) -> None:
        self.events.append(("span_start", span))

    def _persist_span_end(self, span: Span) -> None:
        self.events.append(("span_end", span))

    def span_starts(self) -> list[Span]:
        return [event for kind, event in self.events if kind == "span_start"]
