"""http_ping MCP tool — checks whether a URL responds, with SSRF guards.

An agentic tool that fetches arbitrary caller-supplied URLs is a classic
SSRF vector (cloud metadata endpoints, internal services) — this repo means
to model good agentic-tool practice, not skip its own advice. Restricted to
http/https; the hostname is resolved and every returned address is checked
against private/loopback/link-local/reserved/multicast ranges before any
request is made. Redirects are not followed, so a public URL that 302s to
an internal address can't be used to bypass the check either.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx2 as httpx

_ALLOWED_SCHEMES = {"http", "https"}


class BlockedURL(Exception):
    pass


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise BlockedURL(f"scheme {parsed.scheme!r} is not allowed")
    if not parsed.hostname:
        raise BlockedURL("URL has no hostname")

    try:
        addrs = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise BlockedURL(f"could not resolve host: {exc}") from exc

    for _family, _type, _proto, _canonname, sockaddr in addrs:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise BlockedURL(f"{parsed.hostname} resolves to a non-public address ({ip})")


async def http_ping(url: str, timeout_seconds: float = 5.0) -> str:
    try:
        _check_url(url)
    except BlockedURL as exc:
        return f"Refused: {exc}"

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        try:
            response = await client.head(url)
            if response.status_code == 405:  # some servers reject HEAD outright
                response = await client.get(url)
        except httpx.HTTPError as exc:
            return f"Request failed: {exc}"

    return f"{url} -> HTTP {response.status_code}"
