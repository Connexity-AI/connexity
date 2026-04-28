import random
import string

import httpx
from fastapi import Response
from fastapi.responses import JSONResponse

from app.core.config import settings

AUTH_USER_EMAIL = "auth-user@example.com"
AUTH_USER_PASSWORD = "auth-password-changeme"


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def extract_token_as_cookie(
    response: "httpx._models.Response",
) -> dict[str, str]:
    """Extract access_token from JSON body and return it as an auth cookie dict."""
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise AssertionError("access_token not found in response body")
    return {settings.AUTH_COOKIE: token}


def extract_cookies(
    response: JSONResponse | httpx._models.Response | Response,
) -> dict[str, str]:
    cookie_prefix = f"{settings.AUTH_COOKIE}="
    if isinstance(response, httpx._models.Response):
        # Try Set-Cookie header first
        cookie_value = response.cookies.get(settings.AUTH_COOKIE)
        if cookie_value:
            return {settings.AUTH_COOKIE: cookie_value}
        # Fallback: extract access_token from JSON body
        try:
            data = response.json()
            token = data.get("access_token")
            if token:
                return {settings.AUTH_COOKIE: token}
        except Exception:
            pass
    else:
        # Handle Starlette Response
        cookie_header = response.headers.get("Set-Cookie")
        if cookie_header and cookie_prefix in cookie_header:
            cookie_value = cookie_header.split(cookie_prefix)[1].split(";")[0]
            if cookie_value:
                return {settings.AUTH_COOKIE: cookie_value}

    raise AssertionError("Cookie value not found")
