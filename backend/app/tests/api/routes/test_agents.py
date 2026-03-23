import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import create_test_agent


def test_create_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {"name": "Route Agent", "endpoint_url": "http://example.com/agent"}
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["name"] == "Route Agent"
    assert result["endpoint_url"] == "http://example.com/agent"
    assert "id" in result


def test_list_agents(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    create_test_agent(db)
    r = client.get(
        f"{settings.API_V1_STR}/agents/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["count"] >= 1
    assert len(result["data"]) >= 1


def test_get_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(agent.id)


def test_get_agent_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/agents/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"name": "Patched Agent"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Patched Agent"


def test_delete_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.delete(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    # Verify deleted
    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 404


def test_create_agent_unauthenticated(client: TestClient) -> None:
    data = {"name": "Unauth Agent", "endpoint_url": "http://example.com/agent"}
    r = client.post(f"{settings.API_V1_STR}/agents/", json=data)
    assert r.status_code in (401, 403)
