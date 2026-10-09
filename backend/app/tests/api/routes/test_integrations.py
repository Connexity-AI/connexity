from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core import encryption
from app.core.config import settings
from app.models import IntegrationProvider
from app.services.n8n import N8nConnectionProblem, N8nConnectionResult
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


def test_integration_is_isolated_per_company(
    client: TestClient,
    auth_cookies: dict[str, str],
    normal_user_auth_cookies: dict[str, str],
) -> None:
    """Integrations are scoped per company — another company's user can't see, test, or delete them."""
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        create_r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("private"),
            cookies=auth_cookies,
        )
    assert create_r.status_code == 200
    integration_id = create_r.json()["id"]

    # ``normal_user_auth_cookies`` is in a different company → can't see it.
    other_list = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=normal_user_auth_cookies,
    )
    assert other_list.status_code == 200
    assert all(i["id"] != integration_id for i in other_list.json()["data"])

    # ...nor test it.
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        other_test = client.post(
            f"{settings.API_V1_STR}/integrations/{integration_id}/test",
            cookies=normal_user_auth_cookies,
        )
    assert other_test.status_code == 404

    # ...nor delete it.
    other_del = client.delete(
        f"{settings.API_V1_STR}/integrations/{integration_id}",
        cookies=normal_user_auth_cookies,
    )
    assert other_del.status_code == 404

    # The original owner still sees it.
    list_after = client.get(
        f"{settings.API_V1_STR}/integrations/",
        cookies=auth_cookies,
    )
    assert any(i["id"] == integration_id for i in list_after.json()["data"])


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


# ── n8n ────────────────────────────────────────────────────────────

N8N_URL = "https://n8n.example.com"


def _n8n_body(name: str = "n8n", base_url: str | None = N8N_URL) -> dict:
    body: dict = {"provider": "n8n", "name": name, "api_key": "n8n_api_invented_key"}
    if base_url is not None:
        body["base_url"] = base_url
    return body


def _n8n_ok(base_url: str = N8N_URL) -> AsyncMock:
    return AsyncMock(return_value=N8nConnectionResult(ok=True, base_url=base_url))


def test_create_n8n_stores_the_address_and_never_returns_the_key(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    checker = _n8n_ok()
    with patch("app.api.routes.integrations.check_n8n_connection", checker):
        r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_n8n_body(base_url=f"{N8N_URL}/"),
            cookies=auth_cookies,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "n8n"
    assert body["base_url"] == N8N_URL
    assert "api_key" not in body
    assert "n8n_api_invented_key" not in r.text
    checker.assert_awaited_once_with(N8N_URL, "n8n_api_invented_key")

    with patch("app.api.routes.integrations.check_n8n_connection", checker):
        test_r = client.post(
            f"{settings.API_V1_STR}/integrations/{body['id']}/test",
            cookies=auth_cookies,
        )
    assert test_r.status_code == 200
    assert checker.await_args is not None
    assert checker.await_args.args == (N8N_URL, "n8n_api_invented_key")

    listed = client.get(f"{settings.API_V1_STR}/integrations/", cookies=auth_cookies)
    assert any(i["id"] == body["id"] for i in listed.json()["data"])
    assert "n8n_api_invented_key" not in listed.text

    deleted = client.delete(
        f"{settings.API_V1_STR}/integrations/{body['id']}", cookies=auth_cookies
    )
    assert deleted.status_code == 200


@pytest.mark.parametrize("base_url", [None, "", "not a url", "ftp://n8n.example.com"])
def test_create_n8n_needs_a_usable_address(
    client: TestClient, auth_cookies: dict[str, str], base_url: str | None
) -> None:
    checker = _n8n_ok()
    with patch("app.api.routes.integrations.check_n8n_connection", checker):
        r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_n8n_body(base_url=base_url),
            cookies=auth_cookies,
        )
    assert r.status_code == 400
    assert "address" in r.json()["detail"]
    checker.assert_not_awaited()


def test_create_n8n_reports_what_went_wrong(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    failed = AsyncMock(
        return_value=N8nConnectionResult(
            ok=False,
            problem=N8nConnectionProblem.WRONG_KEY,
            message="n8n refused the API key",
        )
    )
    with patch("app.api.routes.integrations.check_n8n_connection", failed):
        r = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_n8n_body(),
            cookies=auth_cookies,
        )
    assert r.status_code == 400
    assert r.json()["detail"] == "n8n refused the API key"


def test_a_voice_provider_does_not_take_an_address(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    body = _create_body("with-address") | {"base_url": N8N_URL}
    r = client.post(
        f"{settings.API_V1_STR}/integrations/", json=body, cookies=auth_cookies
    )
    assert r.status_code == 400
    # An empty address is no address.
    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        empty = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_create_body("empty-address") | {"base_url": ""},
            cookies=auth_cookies,
        )
    assert empty.status_code == 200, empty.text
    assert empty.json()["base_url"] is None


def test_an_n8n_connection_has_no_agents_to_list(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    with patch("app.api.routes.integrations.check_n8n_connection", _n8n_ok()):
        created = client.post(
            f"{settings.API_V1_STR}/integrations/",
            json=_n8n_body(),
            cookies=auth_cookies,
        ).json()
    r = client.get(
        f"{settings.API_V1_STR}/integrations/{created['id']}/agents",
        cookies=auth_cookies,
    )
    assert r.status_code == 400
