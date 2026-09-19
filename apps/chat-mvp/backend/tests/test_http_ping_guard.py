import pytest
from mcp_server.tools.http_ping import BlockedURL, _check_url


def test_allows_a_public_looking_address() -> None:
    _check_url("https://1.1.1.1/")  # literal public IP, no DNS needed — just shouldn't raise


def test_blocks_non_http_scheme() -> None:
    with pytest.raises(BlockedURL):
        _check_url("ftp://example.com/")


def test_blocks_loopback() -> None:
    with pytest.raises(BlockedURL):
        _check_url("http://127.0.0.1:8080/admin")


def test_blocks_link_local_cloud_metadata_address() -> None:
    with pytest.raises(BlockedURL):
        _check_url("http://169.254.169.254/latest/meta-data/")


def test_blocks_private_range() -> None:
    with pytest.raises(BlockedURL):
        _check_url("http://10.0.0.5/")
