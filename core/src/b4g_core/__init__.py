"""b4g-core: reusable session/trace/span + provider-agnostic agent composition.

See core/README.md for the design pattern this package extracts from
cl-ai-builders' Splunk workshop app.
"""

from .agents import Agent, run_turn
from .providers import PROVIDERS, LLMProvider, ProviderResponse, ToolCall
from .tracing import GalileoTracer, NoopTracer, Session, Tracer

__all__ = [
    "PROVIDERS",
    "Agent",
    "GalileoTracer",
    "LLMProvider",
    "NoopTracer",
    "ProviderResponse",
    "Session",
    "ToolCall",
    "Tracer",
    "run_turn",
]
