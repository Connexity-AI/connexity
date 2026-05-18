import httpx
import pytest
from fastapi import Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.tests.utils.utils import extract_cookies, extract_token_as_cookie


def test_extract_token_as_cookie_returns_auth_cookie() -> None:
    response = httpx.Response(200, json={"access_token": "token-123"})

    assert extract_token_as_cookie(response) == {settings.AUTH_COOKIE: "token-123"}


def test_extract_token_as_cookie_raises_when_token_missing() -> None:
    response = httpx.Response(200, json={"message": "missing token"})

    with pytest.raises(AssertionError, match="access_token not found"):
        extract_token_as_cookie(response)


def test_extract_cookies_reads_httpx_cookie_header() -> None:
    request = httpx.Request("POST", "https://example.com/login")
    response = httpx.Response(
        200,
        request=request,
        headers={"set-cookie": f"{settings.AUTH_COOKIE}=cookie-123; Path=/"},
    )

    assert extract_cookies(response) == {settings.AUTH_COOKIE: "cookie-123"}


def test_extract_cookies_reads_httpx_json_fallback() -> None:
    request = httpx.Request("POST", "https://example.com/login")
    response = httpx.Response(200, request=request, json={"access_token": "token-123"})

    assert extract_cookies(response) == {settings.AUTH_COOKIE: "token-123"}


def test_extract_cookies_reads_starlette_response_cookie() -> None:
    response = JSONResponse({"ok": True})
    response.headers["Set-Cookie"] = f"{settings.AUTH_COOKIE}=cookie-xyz; Path=/"

    assert extract_cookies(response) == {settings.AUTH_COOKIE: "cookie-xyz"}


def test_extract_cookies_raises_when_no_cookie_found() -> None:
    response = Response("ok")

    with pytest.raises(AssertionError, match="Cookie value not found"):
        extract_cookies(response)
