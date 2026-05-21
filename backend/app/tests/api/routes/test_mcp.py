from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import create_test_agent

MCP_PREFIX = f"{settings.API_V1_STR}/mcp"
TOKEN_PREFIX = f"{settings.API_V1_STR}/internal"
CLIENT_ID = "mcp-server"
CUSTOM_CLIENT_ID = "custom-mcp-client"
CLIENT_SECRET = "very-long-random-string"


def _issue_service_token(
    client: TestClient,
    monkeypatch,
    *,
    client_id: str = CLIENT_ID,
    configured_client_id: str | None = None,
) -> str:
    monkeypatch.setattr(settings, "MCP_CLIENT_ID", configured_client_id or CLIENT_ID)
    monkeypatch.setattr(settings, "MCP_CLIENT_SECRET", CLIENT_SECRET)
    response = client.post(
        f"{TOKEN_PREFIX}/token",
        json={"client_id": client_id, "client_secret": CLIENT_SECRET},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 300
    return body["access_token"]


def test_mcp_token_exchange_rejects_bad_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "MCP_CLIENT_SECRET", CLIENT_SECRET)

    response = client.post(
        f"{TOKEN_PREFIX}/token",
        json={"client_id": CLIENT_ID, "client_secret": "wrong-secret"},
    )

    assert response.status_code == 401


def test_mcp_token_exchange_uses_default_client_id_when_env_unset(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "MCP_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(settings, "MCP_CLIENT_SECRET", CLIENT_SECRET)

    response = client.post(
        f"{TOKEN_PREFIX}/token",
        json={"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
    )

    assert response.status_code == 200


def test_mcp_token_exchange_accepts_custom_client_id_override(
    client: TestClient, monkeypatch
) -> None:
    access_token = _issue_service_token(
        client,
        monkeypatch,
        client_id=CUSTOM_CLIENT_ID,
        configured_client_id=CUSTOM_CLIENT_ID,
    )

    response = client.get(
        f"{MCP_PREFIX}/agents",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200


def test_mcp_list_agents_with_service_jwt(
    client: TestClient, db: Session, monkeypatch
) -> None:
    access_token = _issue_service_token(client, monkeypatch)
    agent = create_test_agent(db)

    response = client.get(
        f"{MCP_PREFIX}/agents",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert any(item["id"] == str(agent.id) for item in body["data"])


def test_mcp_list_agents_rejects_raw_client_secret(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "MCP_CLIENT_SECRET", CLIENT_SECRET)

    response = client.get(
        f"{MCP_PREFIX}/agents",
        headers={"Authorization": f"Bearer {CLIENT_SECRET}"},
    )

    assert response.status_code == 401


def test_mcp_update_draft_with_service_jwt(
    client: TestClient, db: Session, monkeypatch
) -> None:
    access_token = _issue_service_token(client, monkeypatch)
    agent = create_test_agent(db)

    response = client.put(
        f"{MCP_PREFIX}/agents/{agent.id}/draft",
        json={"system_prompt": "MCP draft prompt"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["system_prompt"] == "MCP draft prompt"
