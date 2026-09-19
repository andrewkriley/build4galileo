"""Thin MCP client wrapper.

An `Agent`'s `call_tool` only needs `list_tools()` + `call_tool(name,
arguments)`. Connecting over stdio to a local subprocess MCP server (the
chat MVP's demo server) keeps "the agent talks to tools as a separate,
swappable, standard-protocol service" part of the pattern — cl-ai-builders
made the same call talking to a remote Splunk MCP server over
streamable-http instead. Swapping transports later is a different
`*_client` call here, not a rewrite of anything that calls this module.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@asynccontextmanager
async def stdio_mcp_session(
    command: str, args: list[str], env: dict[str, str] | None = None
) -> AsyncIterator[ClientSession]:
    params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def list_tools(session: ClientSession) -> list[dict]:
    result = await session.list_tools()
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
        for t in result.tools
    ]


async def call_tool(session: ClientSession, name: str, arguments: dict) -> str:
    result = await session.call_tool(name, arguments)
    return "\n".join(block.text for block in result.content if hasattr(block, "text"))
