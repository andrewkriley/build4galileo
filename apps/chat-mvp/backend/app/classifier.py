"""Fast keyword-heuristic classifier — no extra LLM call.

A plain keyword match, not a model call, so routing stays deterministic
and free of extra API cost/latency. Categories map 1:1 to the demo MCP
server's tools (see `app/agents.py`) — classification is real
access-scoping (which tool the matched worker can call), not just persona
selection.
"""

from __future__ import annotations

NETWORK_KEYWORDS = [
    "ping", "url", "http", "network", "connect", "reachable", "website", "endpoint", "down", "up",
]
FILES_KEYWORDS = [
    "file", "files", "directory", "folder", "search", "find", "notes", "document", "readme",
]
SYSTEM_KEYWORDS = [
    "system", "host", "cpu", "platform", "os version", "operating system", "machine", "hardware",
]


def classify(user_message: str) -> str:
    text = user_message.lower()
    if any(keyword in text for keyword in NETWORK_KEYWORDS):
        return "network"
    if any(keyword in text for keyword in FILES_KEYWORDS):
        return "files"
    if any(keyword in text for keyword in SYSTEM_KEYWORDS):
        return "system"
    return "system"  # default category when nothing matches
