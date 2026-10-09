"""Guard for addresses a user supplies and the server then fetches.

A hosted, multi-tenant server must not be talked into calling its own network. An
address is accepted only when it is ``https`` and every address its host resolves to is
public. ``ALLOW_PRIVATE_INTEGRATION_URLS`` relaxes both rules for a self-hosted
Connexity and for local development.

The check runs when a connection is saved and again before each request. The request is
then sent to the very address that was checked (``OutboundTarget``), so a host cannot
answer one address for the check and another for the request.
"""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from app.core.config import settings

MAX_URL_LENGTH = 2048


class OutboundUrlError(ValueError):
    """The address is not one the server may call. The message says why."""


def normalize_base_url(url: str) -> str:
    """Scheme, host, optional port and path, with no trailing slash, query or fragment.

    Raises:
        OutboundUrlError: The text is not an http(s) address.
    """
    text = url.strip()
    if not text or len(text) > MAX_URL_LENGTH:
        msg = "The address is empty or too long"
        raise OutboundUrlError(msg)
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        msg = "The address must start with https:// and name a host"
        raise OutboundUrlError(msg)
    if parts.username or parts.password:
        msg = "The address must not contain a username or password"
        raise OutboundUrlError(msg)
    return urlunsplit(
        (parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", "")
    )


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def _resolve(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


@dataclass(frozen=True)
class OutboundTarget:
    """Where to send a request so that it reaches the address that was checked."""

    # The address as the user gave it, normalized. Stored and shown.
    base_url: str
    # The same address with the host replaced by the checked IP. Requests go here.
    connect_url: str
    headers: dict[str, str] = field(default_factory=dict)
    # httpx request extensions: the name to present and verify in the TLS handshake.
    extensions: dict[str, str] = field(default_factory=dict)


async def resolve_outbound_target(url: str) -> OutboundTarget:
    """Check the address and return where to send requests for it.

    Raises:
        OutboundUrlError: Not https, the host does not resolve, or it resolves to a
            private, local or otherwise non-public address.
    """
    normalized = normalize_base_url(url)
    if settings.ALLOW_PRIVATE_INTEGRATION_URLS:
        return OutboundTarget(base_url=normalized, connect_url=normalized)

    parts = urlsplit(normalized)
    if parts.scheme != "https":
        msg = "The address must use https"
        raise OutboundUrlError(msg)
    host = parts.hostname or ""
    try:
        addresses = await _resolve(host, parts.port or 443)
    except OSError as exc:
        msg = f"The host {host} could not be found"
        raise OutboundUrlError(msg) from exc
    if not addresses or not all(_is_public(address) for address in addresses):
        msg = "The address points to a private or local network, which is not allowed"
        raise OutboundUrlError(msg)

    address = addresses[0]
    literal = f"[{address}]" if ":" in address else address
    netloc = f"{literal}:{parts.port}" if parts.port else literal
    return OutboundTarget(
        base_url=normalized,
        connect_url=urlunsplit((parts.scheme, netloc, parts.path, "", "")),
        headers={"Host": parts.netloc},
        extensions={"sni_hostname": host},
    )


async def ensure_outbound_url_allowed(url: str) -> str:
    """Return the normalized address if the server may call it.

    Raises:
        OutboundUrlError: As ``resolve_outbound_target``.
    """
    return (await resolve_outbound_target(url)).base_url
