import random
import string

import httpx
from fastapi import Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.config import settings


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def get_superuser_auth_cookies(client: TestClient) -> dict[str, str]:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    return extract_cookies(r)


def extract_cookies(
    response: JSONResponse | httpx._models.Response | Response,
) -> dict[str, str]:
    cookie_prefix = f"{settings.AUTH_COOKIE}="
    if isinstance(response, httpx._models.Response):
        # Handle httpx Response
        cookie_value = response.cookies.get(settings.AUTH_COOKIE)
        if cookie_value:
            return {settings.AUTH_COOKIE: cookie_value}
    else:
        # Handle Starlette Response
        cookie_header = response.headers.get("Set-Cookie")
        if cookie_header and cookie_prefix in cookie_header:
            cookie_value = cookie_header.split(cookie_prefix)[1].split(";")[0]
            if cookie_value:
                return {settings.AUTH_COOKIE: cookie_value}

    raise AssertionError("Cookie value not found")
