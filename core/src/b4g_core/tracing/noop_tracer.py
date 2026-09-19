"""A Tracer that discards everything. Used by tests and offline CI runs
so `Agent` code never has to special-case "no observability backend
configured" — it just gets a NoopTracer instead."""

from __future__ import annotations

from .tracer import Tracer
from .types import Session, Span, Trace


class NoopTracer(Tracer):
    def _persist_session(self, session: Session) -> None:
        pass

    def _persist_trace_start(self, trace: Trace) -> None:
        pass

    def _persist_trace_end(self, trace: Trace) -> None:
        pass

    def _persist_span_start(self, span: Span) -> None:
        pass

    def _persist_span_end(self, span: Span) -> None:
        pass
