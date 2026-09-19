"""file_search MCP tool — filename search under a fixed sandbox directory.

`path` is a caller-supplied subdirectory to search within, which is exactly
the kind of input a tool-calling loop should never trust blindly — it goes
through `resolve_within_sandbox` so `path=".."` or an absolute path can't
walk the search outside `sandbox_root/`.
"""

from __future__ import annotations

from ..sandbox import SANDBOX_ROOT, PathEscapesSandbox, resolve_within_sandbox


def file_search(query: str, path: str = ".", max_results: int = 20) -> str:
    try:
        search_root = resolve_within_sandbox(path)
    except PathEscapesSandbox as exc:
        return f"Refused: {exc}"

    if not search_root.is_dir():
        return f"Refused: {path!r} is not a directory in the sandbox."

    query_lower = query.lower()
    matches = [
        str(candidate.relative_to(SANDBOX_ROOT))
        for candidate in sorted(search_root.rglob("*"))
        if candidate.is_file() and query_lower in candidate.name.lower()
    ]
    if not matches:
        return f"No files matching {query!r} found under {path!r}."
    return "\n".join(matches[:max_results])
