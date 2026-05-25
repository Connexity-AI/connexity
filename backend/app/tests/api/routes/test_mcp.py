from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.tests.utils.eval import create_test_agent
from app.tests.utils.user import create_random_user

MCP_PREFIX = f"{settings.API_V1_STR}/mcp"
RESOURCE = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
CLIENT_ID = "claude-client"


def _issue_mcp_oauth_token(
    db: Session,
    monkeypatch,
    *,
    audience: str = RESOURCE,
    scope: str = "mcp:access",
) -> tuple[str, str]:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", RESOURCE)
    user = create_random_user(db)
    access_token, _ = security.create_oauth_access_token(
        subject=user.id,
        audience=audience,
        issuer=ISSUER,
        client_id=CLIENT_ID,
        scope=scope,
        expires_delta=timedelta(minutes=60),
    )
    return access_token, str(user.id)


def test_mcp_list_agents_requires_oauth_user_token(client: TestClient) -> None:
    response = client.get(f"{MCP_PREFIX}/agents")

    assert response.status_code == 401


def test_mcp_list_agents_rejects_wrong_audience(
    client: TestClient, db: Session, monkeypatch
) -> None:
    access_token, _ = _issue_mcp_oauth_token(
        db,
        monkeypatch,
        audience="https://another-resource.example.com/mcp",
    )

    response = client.get(
        f"{MCP_PREFIX}/agents",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401


def test_mcp_list_agents_with_oauth_user_token(
    client: TestClient, db: Session, monkeypatch
) -> None:
    access_token, _ = _issue_mcp_oauth_token(db, monkeypatch)
    agent = create_test_agent(db)

    response = client.get(
        f"{MCP_PREFIX}/agents",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert any(item["id"] == str(agent.id) for item in body["data"])


def test_mcp_update_draft_with_oauth_user_token(
    client: TestClient, db: Session, monkeypatch
) -> None:
    access_token, user_id = _issue_mcp_oauth_token(db, monkeypatch)
    agent = create_test_agent(db)

    response = client.put(
        f"{MCP_PREFIX}/agents/{agent.id}/draft",
        json={"system_prompt": "MCP draft prompt"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["system_prompt"] == "MCP draft prompt"
    assert body["created_by"] == user_id
