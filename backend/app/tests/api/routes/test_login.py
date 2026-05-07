import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.tests.utils.utils import (
    AUTH_USER_EMAIL,
    AUTH_USER_PASSWORD,
)


@pytest.mark.usefixtures("auth_cookies")
def test_get_auth_cookie(client: TestClient) -> None:
    # auth_cookies fixture ensures AUTH_USER_EMAIL exists with AUTH_USER_PASSWORD
    login_data = {
        "username": AUTH_USER_EMAIL,
        "password": AUTH_USER_PASSWORD,
    }

    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "expires" in data


@pytest.mark.usefixtures("auth_cookies")
def test_get_auth_cookie_incorrect_password(client: TestClient) -> None:
    login_data = {
        "username": AUTH_USER_EMAIL,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert r.status_code == 400


def test_use_auth_cookie(client: TestClient, auth_cookies: dict[str, str]) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        cookies=auth_cookies,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


@pytest.mark.usefixtures("auth_cookies")
def test_use_bearer_token(client: TestClient) -> None:
    login_data = {
        "username": AUTH_USER_EMAIL,
        "password": AUTH_USER_PASSWORD,
    }
    login = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    assert login.status_code == 200
    token = login.json()["access_token"]
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "email" in r.json()
