"""Backend-agnostic Session/Trace/Span tracer.

`Tracer` provides the context-manager ergonomics (nesting, timing, status,
error capture) that every backend gets for free. A concrete backend only
implements the five `_persist_*` hooks — everything about *how spans nest*
lives here, once, so agent code never needs to know which backend (Galileo,
a no-op for tests, or something added later) is receiving its spans.

Nesting is structural, not manual: calling `.span(...)` on a handle makes
the new span a child of that handle. An `Agent`'s call graph (see
`b4g_core.agents.agent`) maps directly onto this without any parent-id
plumbing in application code.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .types import Session, Span, SpanType, Trace, new_id


class SpanHandle:
    def __init__(self, tracer: Tracer, span: Span) -> None:
        self._tracer = tracer
        self.span_record = span

    @property
    def id(self) -> str:
        return self.span_record.id

    def set_output(self, output: Any) -> None:
        self.span_record.output = output

    def set_metadata(self, **kwargs: Any) -> None:
        """Attach backend-specific fields (e.g. model, token counts, a
        Galileo-shaped logged_input) a Tracer implementation may need to
        emit this span correctly. Core code never reads these back — only
        the Tracer backend does, in its own `_persist_span_end`."""
        self.span_record.metadata.update(kwargs)

    @contextmanager
    def span(self, span_type: SpanType, name: str, input: Any = None) -> Iterator[SpanHandle]:
        child = Span(
            id=new_id(),
            trace_id=self.span_record.trace_id,
            parent_span_id=self.span_record.id,
            span_type=span_type,
            name=name,
            input=input,
        )
        handle = SpanHandle(self._tracer, child)
        yield from _run_span(self._tracer, handle)


class TraceHandle:
    def __init__(self, tracer: Tracer, trace: Trace) -> None:
        self._tracer = tracer
        self.trace_record = trace

    @property
    def id(self) -> str:
        return self.trace_record.id

    def set_output(self, output: Any) -> None:
        self.trace_record.output = output

    @contextmanager
    def span(self, span_type: SpanType, name: str, input: Any = None) -> Iterator[SpanHandle]:
        child = Span(
            id=new_id(),
            trace_id=self.trace_record.id,
            parent_span_id=None,
            span_type=span_type,
            name=name,
            input=input,
        )
        handle = SpanHandle(self._tracer, child)
        yield from _run_span(self._tracer, handle)


def _run_span(tracer: Tracer, handle: SpanHandle) -> Iterator[SpanHandle]:
    span = handle.span_record
    tracer._persist_span_start(span)
    try:
        yield handle
    except Exception as exc:  # noqa: BLE001 - re-raised after recording
        span.status = "error"
        span.error = repr(exc)
        raise
    finally:
        span.ended_at = time.time()
        tracer._persist_span_end(span)


class Tracer(ABC):
    """Base class for a Session/Trace/Span backend."""

    def start_session(self, session_id: str, metadata: dict[str, Any] | None = None) -> Session:
        session = Session(id=session_id, metadata=metadata or {})
        self._persist_session(session)
        return session

    @contextmanager
    def trace(self, session: Session, name: str, input: Any = None) -> Iterator[TraceHandle]:
        trace = Trace(id=new_id(), session_id=session.id, input=input)
        self._persist_trace_start(trace)
        handle = TraceHandle(self, trace)
        try:
            yield handle
        except Exception as exc:  # noqa: BLE001 - re-raised after recording
            trace.status = "error"
            trace.error = repr(exc)
            raise
        finally:
            trace.ended_at = time.time()
            self._persist_trace_end(trace)

    @abstractmethod
    def _persist_session(self, session: Session) -> None: ...

    @abstractmethod
    def _persist_trace_start(self, trace: Trace) -> None: ...

    @abstractmethod
    def _persist_trace_end(self, trace: Trace) -> None: ...

    @abstractmethod
    def _persist_span_start(self, span: Span) -> None: ...

    @abstractmethod
    def _persist_span_end(self, span: Span) -> None: ...
