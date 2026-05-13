from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core import encryption
from app.core.config import settings
from app.models import IntegrationProvider
from app.services.retell import RetellAgentSummary


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
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/integrations/",
        json={"provider": "unknown", "name": "x", "api_key": "k"},
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_create_returns_400_when_connection_fails(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=False)},
        clear=False,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("bad-key"),
            cookies=auth_cookies,
        )
    assert r.status_code == 400


def test_create_list_get_test_delete_flow(
    client: TestClient, auth_cookies: dict[str, str]
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
            cookies=auth_cookies,
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
        cookies=auth_cookies,
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
            cookies=auth_cookies,
        )
    assert test_r.status_code == 200

    del_r = client.delete(
        f"{settings.API_V1_STR}/integrations/{integration_id}",
        cookies=auth_cookies,
    )
    assert del_r.status_code == 200

    list_after = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=auth_cookies,
    )
    assert all(i["id"] != integration_id for i in list_after.json()["data"])


def test_integration_visible_to_all_authenticated_users(
    client: TestClient,
    auth_cookies: dict[str, str],
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
            cookies=auth_cookies,
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
        cookies=auth_cookies,
    )
    assert all(i["id"] != integration_id for i in list_after.json()["data"])


def test_list_integration_agents_deduplicates_by_agent_id(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        create_r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("retell-dedupe"),
            cookies=auth_cookies,
        )
    assert create_r.status_code == 200
    integration_id = create_r.json()["id"]

    mock_agents = [
        RetellAgentSummary(
            agent_id="agent-1",
            agent_name="Agent One Draft",
            is_published=False,
            version=6,
        ),
        RetellAgentSummary(
            agent_id="agent-1",
            agent_name="Agent One Published",
            is_published=True,
            version=5,
        ),
        RetellAgentSummary(
            agent_id="agent-2",
            agent_name="Agent Two v1",
            is_published=True,
            version=1,
        ),
        RetellAgentSummary(
            agent_id="agent-2",
            agent_name="Agent Two v2",
            is_published=True,
            version=2,
        ),
    ]

    with patch(
        "app.api.routes.integrations.list_retell_agents",
        AsyncMock(return_value=mock_agents),
    ):
        list_agents_r = client.get(
            f"{settings.API_V1_STR}/integrations/{integration_id}/agents",
            cookies=auth_cookies,
        )

    assert list_agents_r.status_code == 200
    body = list_agents_r.json()
    assert len(body) == 2
    by_id = {row["agent_id"]: row for row in body}
    assert by_id["agent-1"]["agent_name"] == "Agent One Published"
    assert by_id["agent-1"]["version"] == 5
    assert by_id["agent-1"]["is_published"] is True
    assert by_id["agent-2"]["agent_name"] == "Agent Two v2"
    assert by_id["agent-2"]["version"] == 2
