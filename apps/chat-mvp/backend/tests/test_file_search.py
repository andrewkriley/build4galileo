from mcp_server.tools.file_search import file_search


def test_finds_seeded_sample_file() -> None:
    result = file_search("notes")
    assert "notes/project-notes.md" in result or "notes\\project-notes.md" in result


def test_no_match_reports_clearly() -> None:
    result = file_search("definitely-not-a-real-file-xyz")
    assert "No files matching" in result


def test_path_traversal_is_refused_not_silently_empty() -> None:
    result = file_search("passwd", path="../../../../../../etc")
    assert result.startswith("Refused:")
