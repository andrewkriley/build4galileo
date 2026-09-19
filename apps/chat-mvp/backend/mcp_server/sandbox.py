"""Path containment for the file_search tool.

Every result must stay under SANDBOX_ROOT. `resolve_within_sandbox` is the
one place that decides whether a caller-supplied path is allowed — it
resolves symlinks and rejects anything (`..`, an absolute path, a symlink
escape) that would land outside the sandbox, so untrusted input can only
ever name files build4galileo ships as sample data.
"""

from __future__ import annotations

from pathlib import Path

SANDBOX_ROOT = (Path(__file__).parent / "sandbox_root").resolve()


class PathEscapesSandbox(Exception):
    def __init__(self, attempted: str) -> None:
        super().__init__(f"path escapes the sandbox: {attempted!r}")
        self.attempted = attempted


def resolve_within_sandbox(relative_path: str) -> Path:
    candidate = (SANDBOX_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(SANDBOX_ROOT)
    except ValueError:
        raise PathEscapesSandbox(relative_path) from None
    return candidate
