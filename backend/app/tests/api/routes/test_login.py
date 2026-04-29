from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.core.security import verify_password
from app.crud import create_user
from app.models import UserCreate
from app.tests.utils.user import user_authentication_headers
from app.tests.utils.utils import (
    AUTH_USER_EMAIL,
    AUTH_USER_PASSWORD,
    random_email,
    random_lower_string,
)
from app.utils import generate_password_reset_token


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


def test_recovery_password(
    client: TestClient, normal_user_auth_cookies: dict[str, str]
) -> None:
    with (
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
        patch("app.core.config.settings.EMAILS_FROM_EMAIL", "info@example.com"),
    ):
        email = "test@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            cookies=normal_user_auth_cookies,
        )
        assert r.status_code == 200
        assert r.json() == {"message": "Password recovery email sent"}


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_auth_cookies: dict[str, str]
) -> None:
    email = "jVgQr@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        cookies=normal_user_auth_cookies,
    )
    assert r.status_code == 404


# Todo: ??
def test_reset_password(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        full_name="Test User",
        password=password,
        is_active=True,
    )
    user = create_user(session=db, user_create=user_create)
    token = generate_password_reset_token(email=email)
    headers = user_authentication_headers(client=client, email=email, password=password)
    data = {"new_password": new_password, "token": token}

    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        cookies=headers,
        json=data,
    )

    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    db.refresh(user)
    assert user.hashed_password is not None
    assert verify_password(new_password, user.hashed_password)


def test_reset_password_invalid_token(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        cookies=auth_cookies,
        json=data,
    )
    response = r.json()

    assert "detail" in response
    assert r.status_code == 400
    assert response["detail"] == "Invalid token"
