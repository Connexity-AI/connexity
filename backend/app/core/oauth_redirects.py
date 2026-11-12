"""Which callback addresses (redirect URIs) an assistant may register and use.

- Exact addresses: Claude.ai's callbacks and any in `OAUTH_ALLOWED_REDIRECT_URIS`.
- Loopback callbacks for apps on the person's machine, such as Claude Code (RFC 8252,
  section 7.3): `http://localhost`, `http://127.0.0.1` or `http://[::1]`, on any port.
  A registered loopback callback matches a request with the same host, path and query on
  any port, because the port changes every session.
- ChatGPT's two documented callbacks: `https://chatgpt.com/connector_platform_oauth_redirect`
  and `https://chatgpt.com/connector/oauth/{callback_id}`.
"""

import re
from urllib.parse import urlsplit

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
CHATGPT_STABLE = "https://chatgpt.com/connector_platform_oauth_redirect"
# One path segment of unreserved characters (RFC 3986); the docs do not say more.
CHATGPT_PER_CONNECTION = re.compile(
    r"https://chatgpt\.com/connector/oauth/[A-Za-z0-9._~-]{1,256}"
)


def is_loopback(uri: str) -> bool:
    try:
        parts = urlsplit(uri)
        parts.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        return False
    return (
        parts.scheme == "http"
        and parts.hostname in LOOPBACK_HOSTS
        and not parts.username
        and not parts.password
        and not parts.fragment
    )


def may_register(uri: str, allowed: set[str]) -> bool:
    """Whether a client may register this callback."""
    return (
        uri in allowed
        or is_loopback(uri)
        or uri == CHATGPT_STABLE
        or CHATGPT_PER_CONNECTION.fullmatch(uri) is not None
    )


def matches_registered(requested: str, registered: list[str]) -> bool:
    """Whether an authorization request's callback is one the client registered."""
    if requested in registered:
        return True
    if not is_loopback(requested):
        return False
    asked = urlsplit(requested)
    for uri in registered:
        if not is_loopback(uri):
            continue
        known = urlsplit(uri)
        if (
            known.hostname == asked.hostname
            and (known.path or "/") == (asked.path or "/")
            and known.query == asked.query
        ):
            return True
    return False
