from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core import encryption
from app.core.config import settings
from app.models import IntegrationProvider


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _create_body(name: str, api_key: str = "sk_test_1234567890ABCDEF") -> dict:
    return {"provider": "retell", "name": name, "api_key": api_key}


def test_integrations_require_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/integrations/")
    assert r.status_code == 401


def test_create_rejects_invalid_provider(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/integrations/",
        json={"provider": "unknown", "name": "x", "api_key": "k"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 422


def test_create_returns_400_when_connection_fails(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=False)},
        clear=False,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("bad-key"),
            cookies=superuser_auth_cookies,
        )
    assert r.status_code == 400


def test_create_list_get_test_delete_flow(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    api_key = "sk_test_super_secret_value_xyz"
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        create_r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("retell-prod", api_key=api_key),
            cookies=superuser_auth_cookies,
        )
    assert create_r.status_code == 200
    body = create_r.json()
    integration_id = body["id"]
    assert body["provider"] == "retell"
    assert body["name"] == "retell-prod"
    assert body["masked_api_key"].startswith("sk_t")
    assert body["masked_api_key"].endswith("_xyz")
    assert api_key not in body["masked_api_key"]
    assert "encrypted_api_key" not in body
    assert "api_key" not in body

    list_r = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=superuser_auth_cookies,
    )
    assert list_r.status_code == 200
    listed = list_r.json()
    assert listed["count"] >= 1
    assert any(i["id"] == integration_id for i in listed["data"])
    for item in listed["data"]:
        assert "encrypted_api_key" not in item

    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        test_r = client.post(
            f"{settings.API_V1_STR}/integrations/{integration_id}/test",
            cookies=superuser_auth_cookies,
        )
    assert test_r.status_code == 200

    del_r = client.delete(
        f"{settings.API_V1_STR}/integrations/{integration_id}",
        cookies=superuser_auth_cookies,
    )
    assert del_r.status_code == 200

    list_after = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=superuser_auth_cookies,
    )
    assert all(i["id"] != integration_id for i in list_after.json()["data"])


def test_integration_visible_to_all_authenticated_users(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    normal_user_auth_cookies: dict[str, str],
) -> None:
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        create_r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("shared"),
            cookies=superuser_auth_cookies,
        )
    assert create_r.status_code == 200
    integration_id = create_r.json()["id"]

    other_list = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=normal_user_auth_cookies,
    )
    assert other_list.status_code == 200
    assert any(i["id"] == integration_id for i in other_list.json()["data"])

    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        other_test = client.post(
            f"{settings.API_V1_STR}/integrations/{integration_id}/test",
            cookies=normal_user_auth_cookies,
        )
    assert other_test.status_code == 200

    other_del = client.delete(
        f"{settings.API_V1_STR}/integrations/{integration_id}",
        cookies=normal_user_auth_cookies,
    )
    assert other_del.status_code == 200

    list_after = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=superuser_auth_cookies,
    )
    assert all(i["id"] != integration_id for i in list_after.json()["data"])
