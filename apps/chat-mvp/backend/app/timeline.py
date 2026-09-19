"""Turns the generic trace/span events emitted by `b4g_core`'s Tracer into
a small, human-readable timeline for the chat MVP's own UI — a "here's what
just happened in Galileo" explainer shown alongside the answer. This is not
a Galileo API client; it only describes the same session/trace/span shapes
GalileoTracer is, separately, sending there (see b4g_core.tracing).

It knows this app's own agent tree (supervisor -> classifier ->
{system,files,network}_worker -> llm/tool) to write specific commentary —
that shape lives in `app/agents.py`, deliberately not in b4g_core, which
stays generic.
"""

from __future__ import annotations

import json
from typing import Any


def _preview(value: Any, limit: int = 160) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _describe(event: dict[str, Any]) -> str:
    metadata = event.get("metadata") or {}

    if event["kind"] == "trace":
        return (
            f'One chat message became one Galileo trace: "{_preview(event["input"], 60)}" '
            f'→ "{_preview(event["output"], 60)}".'
        )

    span_type = event.get("span_type")
    name = event.get("name") or ""

    if span_type == "agent":
        agent_type = metadata.get("agent_type")
        if agent_type == "supervisor":
            return "Supervisor agent received the message and routed it through a classifier."
        if agent_type == "classifier":
            return (
                f'Classifier picked the "{event.get("output")}" worker — '
                "a keyword heuristic, no LLM call spent on routing."
            )
        return f'"{name}" worker ran its reasoning + tool-calling loop and answered.'

    if span_type == "llm":
        model = metadata.get("model") or "the model"
        tokens_in = metadata.get("num_input_tokens")
        tokens_out = metadata.get("num_output_tokens")
        token_note = f" — {tokens_in} in / {tokens_out} out tokens" if tokens_in is not None else ""
        return f"Called {model}{token_note}."

    if span_type == "tool":
        return f'Called tool "{name}" with {_preview(event.get("input"), 80)}.'

    return f'"{name}" ran.'


def _icon(event: dict[str, Any]) -> str:
    if event["kind"] == "trace":
        return "trace"
    return event.get("span_type") or "span"


def build_timeline(events: list[dict[str, Any]], turn_started_at: float) -> list[dict[str, Any]]:
    """Order a turn's finished trace/span events chronologically — they
    arrive in *completion* order, since a span only reports in once it's
    done and a parent can't finish before its children — and attach
    display fields: how deep to indent it, when it started relative to the
    turn, and a plain-English line describing what it represents.
    """
    ordered = sorted(events, key=lambda e: e["started_at"])
    by_id = {e["id"]: e for e in ordered}

    def depth(event: dict[str, Any]) -> int:
        d = 1  # nested directly under the trace
        parent_id = event.get("parent_id")
        while parent_id is not None:
            d += 1
            parent = by_id.get(parent_id)
            parent_id = parent.get("parent_id") if parent else None
        return d

    timeline = []
    for event in ordered:
        duration_ms = event.get("duration_ms")
        timeline.append(
            {
                "kind": event["kind"],
                "span_type": event.get("span_type"),
                "icon": _icon(event),
                "name": event.get("name"),
                "status": event.get("status"),
                "depth": 0 if event["kind"] == "trace" else depth(event),
                "offset_ms": round((event["started_at"] - turn_started_at) * 1000),
                "duration_ms": None if duration_ms is None else round(duration_ms),
                "commentary": _describe(event),
                "input_preview": _preview(event.get("input")),
                "output_preview": _preview(event.get("output")),
            }
        )
    return timeline
