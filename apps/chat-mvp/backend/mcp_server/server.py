"""Demo MCP server: system_info, file_search, http_ping — stdio transport.

Run directly (`python -m mcp_server.server`) or spawned as a subprocess by
the chat MVP backend via `b4g_core.mcp.stdio_mcp_session` — see
`app/main.py`. Running as a separate subprocess (rather than calling these
functions in-process) is deliberate: it's what keeps "the agent talks to
tools as a swappable, standard-protocol service" part of the demonstrated
pattern, the same way a remote MCP server over the network would be.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from .tools.file_search import file_search as _file_search
from .tools.http_ping import http_ping as _http_ping
from .tools.system_info import system_info as _system_info

mcp = MCPServer(name="build4galileo-demo-tools")

_SYSTEM_INFO_DESC = (
    "Report basic host/platform info (OS, release, machine, Python version, CPU count)."
)
_FILE_SEARCH_DESC = (
    "Search filenames under a sandboxed demo directory. `path` is a subdirectory "
    "within the sandbox (default: its root); `query` matches filenames case-insensitively."
)
_HTTP_PING_DESC = (
    "Check whether a public http(s) URL responds. Refuses private/loopback/internal addresses."
)


@mcp.tool(description=_SYSTEM_INFO_DESC)
def system_info() -> str:
    return _system_info()


@mcp.tool(description=_FILE_SEARCH_DESC)
def file_search(query: str, path: str = ".", max_results: int = 20) -> str:
    return _file_search(query, path=path, max_results=max_results)


@mcp.tool(description=_HTTP_PING_DESC)
async def http_ping(url: str, timeout_seconds: float = 5.0) -> str:
    return await _http_ping(url, timeout_seconds=timeout_seconds)


if __name__ == "__main__":
    mcp.run(transport="stdio")
