import pytest

from app.core.oauth_redirects import is_loopback, matches_registered, may_register

ALLOWED = {"https://claude.ai/api/mcp/auth_callback"}


@pytest.mark.parametrize(
    "uri",
    [
        "https://claude.ai/api/mcp/auth_callback",
        "http://localhost/callback",
        "http://localhost:3118/callback",
        "http://127.0.0.1:53122/callback",
        "http://[::1]:8080/callback",
        "https://chatgpt.com/connector_platform_oauth_redirect",
        "https://chatgpt.com/connector/oauth/abc_DEF-123",
        "https://chatgpt.com/connector/oauth/conn.abc~1",
    ],
)
def test_callbacks_a_client_may_register(uri: str) -> None:
    assert may_register(uri, ALLOWED)


@pytest.mark.parametrize(
    "uri",
    [
        "http://evil.example.com/callback",
        "https://localhost:3118/callback",
        "http://localhost.evil.com/callback",
        "http://user@localhost/callback",
        "http://localhost/callback#fragment",
        "http://localhost:notaport/callback",
        "https://chatgpt.com/other",
        "https://chatgpt.com/connector/oauth/abc/extra",
        "https://chatgpt.com.evil.com/connector_platform_oauth_redirect",
        "http://chatgpt.com/connector_platform_oauth_redirect",
    ],
)
def test_callbacks_that_are_refused(uri: str) -> None:
    assert not may_register(uri, ALLOWED)


def test_a_loopback_callback_matches_on_any_port() -> None:
    registered = ["http://localhost/callback", "http://127.0.0.1/callback"]

    assert matches_registered("http://localhost:3118/callback", registered)
    assert matches_registered("http://127.0.0.1:53122/callback", registered)
    assert matches_registered("http://localhost/callback", registered)


def test_a_loopback_callback_needs_the_same_host_and_path() -> None:
    registered = ["http://localhost:3118/callback"]

    assert matches_registered("http://localhost:9999/callback", registered)
    assert not matches_registered("http://127.0.0.1:3118/callback", registered)
    assert not matches_registered("http://localhost:3118/other", registered)
    assert not matches_registered("https://localhost:3118/callback", registered)


def test_other_callbacks_match_exactly() -> None:
    registered = ["https://chatgpt.com/connector_platform_oauth_redirect"]

    assert matches_registered(registered[0], registered)
    assert not matches_registered("https://chatgpt.com/connector/oauth/abc", registered)


def test_is_loopback() -> None:
    assert is_loopback("http://[::1]/callback")
    assert not is_loopback("ftp://localhost/callback")
