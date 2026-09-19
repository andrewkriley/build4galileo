import pytest
from mcp_server.sandbox import SANDBOX_ROOT, PathEscapesSandbox, resolve_within_sandbox


def test_resolves_paths_inside_the_sandbox() -> None:
    resolved = resolve_within_sandbox("notes")
    assert resolved == SANDBOX_ROOT / "notes"


def test_rejects_parent_traversal() -> None:
    with pytest.raises(PathEscapesSandbox):
        resolve_within_sandbox("../../../../etc")


def test_rejects_absolute_path_escape() -> None:
    with pytest.raises(PathEscapesSandbox):
        resolve_within_sandbox("/etc/passwd")
