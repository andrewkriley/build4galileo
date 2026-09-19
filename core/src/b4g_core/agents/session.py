"""One turn of a conversation: session + trace lifecycle glue.

Resolves/creates the observability Session for this conversation, opens one
Trace for this turn, runs the given root `Agent` inside it, and records the
trace's own input/output explicitly (the user's question and the agent's
final answer). Without this, a trace left to be created lazily by whichever
span logs first would end up with an arbitrary tool call or LLM message
list as its own input/output instead of the real turn.
"""

from __future__ import annotations

from ..tracing.tracer import Tracer
from .agent import Agent


async def run_turn(tracer: Tracer, session_id: str, root_agent: Agent, user_message: str) -> str:
    # Only consulted on this conversation's first turn (see
    # GalileoTracer._persist_session) — a backend that wants to name the
    # session after the opening question reads it from here.
    session = tracer.start_session(session_id, metadata={"first_message": user_message})
    with tracer.trace(session, name=root_agent.name, input=user_message) as trace:
        result = await root_agent.run(user_message, trace)
        trace.set_output(result)
        return result
