"""Backend-agnostic Session/Trace/Span data shapes.

These are plain data holders. A Tracer implementation (e.g. GalileoTracer)
is responsible for turning them into whatever its backend expects.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

SpanType = Literal["agent", "llm", "tool"]
Status = Literal["ok", "error"]


def new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Session:
    id: str
    started_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    id: str
    session_id: str
    input: Any = None
    output: Any = None
    status: Status = "ok"
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None


@dataclass
class Span:
    id: str
    trace_id: str
    parent_span_id: str | None
    span_type: SpanType
    name: str
    input: Any = None
    output: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: Status = "ok"
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
