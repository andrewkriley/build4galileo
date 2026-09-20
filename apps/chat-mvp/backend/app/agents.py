"""Builds the supervisor -> classifier -> {system,files,network} worker
Agent tree for one chat turn, scoped to the demo MCP server's tools.

This is the chat MVP's concrete configuration of `b4g_core.Agent` — the
3-tier shape and per-category system prompts live here, in application
code, not in the reusable core.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from b4g_core import Agent
from b4g_core.providers import PROVIDERS

from .classifier import classify

BASE_SYSTEM_PROMPT = (
    "You are an AI assistant helping a build4galileo user explore a small demo "
    "environment through MCP tools. Be concise and cite concrete facts from the "
    "tool results in your answer."
)

CATEGORY_PROMPTS = {
    "system": BASE_SYSTEM_PROMPT
    + "\n\nYou specialize in host/platform facts, answered via the system_info tool.",
    "files": BASE_SYSTEM_PROMPT
    + "\n\nYou specialize in searching the sandboxed demo file tree via the file_search tool.",
    "network": BASE_SYSTEM_PROMPT
    + "\n\nYou specialize in checking URL reachability via the http_ping tool.",
}

# 1:1 category -> tool scoping: each worker can only call the one tool
# matching its category, so the classifier is real access control, not
# just a persona picker.
CATEGORY_TOOL_NAMES = {"system": "system_info", "files": "file_search", "network": "http_ping"}

ToolCaller = Callable[[str, dict], Awaitable[str]]


def build_supervisor(
    provider_name: str, model: str | None, mcp_tools: list[dict], call_tool: ToolCaller
) -> Agent:
    provider = PROVIDERS[provider_name](model=model) if model else PROVIDERS[provider_name]()

    workers = {
        category: Agent(
            name=f"{category}_worker",
            agent_type="react",
            system_prompt=CATEGORY_PROMPTS[category],
            provider=provider,
            mcp_tools=[t for t in mcp_tools if t["name"] == tool_name],
            call_tool=call_tool,
        )
        for category, tool_name in CATEGORY_TOOL_NAMES.items()
    }

    return Agent(name="supervisor", agent_type="supervisor", route=classify, children=workers)
