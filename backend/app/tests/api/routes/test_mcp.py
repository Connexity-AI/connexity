import base64
import uuid
from datetime import timedelta

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import User, UserCreate
from app.models.company import workspace_name_from_email
from app.tests.utils.eval import create_test_agent
from app.tests.utils.utils import random_lower_string

MCP_PREFIX = f"{settings.API_V1_STR}/mcp"
RESOURCE = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"
CLIENT_ID = "claude-client"


def _new_user(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(
            email=f"{random_lower_string()[:12]}@acme-{random_lower_string()[:6]}.com",
            password=random_lower_string(),
        ),
    )


def _token_for(
    user: User,
    monkeypatch,
    *,
    audience: str = RESOURCE,
    scope: str = "mcp:access",
) -> dict[str, str]:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", RESOURCE)
    access_token, _ = security.create_oauth_access_token(
        subject=user.id,
        audience=audience,
        issuer=ISSUER,
        client_id=CLIENT_ID,
        scope=scope,
        expires_delta=timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {access_token}"}


def _assert_answer_shape(body: dict) -> None:
    assert set(body) == {"data", "rules", "next_steps", "guide", "next_cursor"}
    assert body["rules"], "every answer states the rules that apply"
    assert body["guide"].startswith("connexity://guides/")


# ── Auth ──


def test_mcp_requires_oauth_user_token(client: TestClient) -> None:
    response = client.get(f"{MCP_PREFIX}/workspaces")

    assert response.status_code == 401


def test_mcp_rejects_wrong_audience(
    client: TestClient, db: Session, monkeypatch
) -> None:
    headers = _token_for(
        _new_user(db), monkeypatch, audience="https://another-resource.example.com/mcp"
    )

    response = client.get(f"{MCP_PREFIX}/workspaces", headers=headers)

    assert response.status_code == 401


def test_every_mcp_route_is_scoped_to_a_workspace() -> None:
    """A route without a workspace in its path would reach across workspaces."""
    unscoped = {f"{MCP_PREFIX}/workspaces"}
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith(MCP_PREFIX):
            continue
        if route.path in unscoped:
            continue
        scoped = f"{MCP_PREFIX}/workspaces/{{workspace_id}}"
        assert route.path == scoped or route.path.startswith(
            f"{scoped}/"
        ), f"{route.path} is not scoped to a workspace"


# ── list_workspaces ──


def test_list_workspaces_returns_the_persons_workspace(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)

    response = client.get(
        f"{MCP_PREFIX}/workspaces", headers=_token_for(user, monkeypatch)
    )

    assert response.status_code == 200
    body = response.json()
    _assert_answer_shape(body)
    assert body["data"] == [
        {"id": str(user.company_id), "name": workspace_name_from_email(user.email)}
    ]
    assert body["next_cursor"] is None
    assert any("list_agents" in step for step in body["next_steps"])


def test_workspace_name_comes_from_the_email_domain() -> None:
    assert workspace_name_from_email("Ann@bright-dental.com") == "Bright Dental"
    assert workspace_name_from_email("bob@kestrel_plumbing.co.uk") == "Kestrel Plumbing"
    assert workspace_name_from_email("no-at-sign") == "My workspace"
    assert workspace_name_from_email("trailing@") == "My workspace"


# ── list_agents ──


def test_list_agents_in_the_persons_workspace(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)
    agent = create_test_agent(db, company_id=user.company_id)

    response = client.get(
        f"{MCP_PREFIX}/workspaces/{user.company_id}/agents",
        headers=_token_for(user, monkeypatch),
    )

    assert response.status_code == 200
    body = response.json()
    _assert_answer_shape(body)
    assert [item["id"] for item in body["data"]] == [str(agent.id)]
    assert body["next_cursor"] is None


def test_list_agents_in_another_workspace_is_not_found(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)
    other = _new_user(db)
    create_test_agent(db, company_id=other.company_id)
    headers = _token_for(user, monkeypatch)

    for workspace_id in (other.company_id, uuid.uuid4()):
        response = client.get(
            f"{MCP_PREFIX}/workspaces/{workspace_id}/agents", headers=headers
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error"] == "Workspace not found"
        assert any("list_workspaces" in step for step in detail["next_steps"])
        assert detail["guide"] == "connexity://guides/workspaces"


def test_list_agents_pages_to_the_last_page(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)
    created = {
        str(create_test_agent(db, company_id=user.company_id).id) for _ in range(5)
    }
    headers = _token_for(user, monkeypatch)

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, str | int] = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        response = client.get(
            f"{MCP_PREFIX}/workspaces/{user.company_id}/agents",
            headers=headers,
            params=params,
        )
        assert response.status_code == 200
        body = response.json()
        seen.extend(item["id"] for item in body["data"])
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
        assert any("next_cursor" in step for step in body["next_steps"])

    assert pages == 3
    assert len(seen) == len(set(seen)) == 5
    assert set(seen) == created


def test_list_agents_rejects_a_bad_cursor(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)

    response = client.get(
        f"{MCP_PREFIX}/workspaces/{user.company_id}/agents",
        headers=_token_for(user, monkeypatch),
        params={"cursor": "not-a-cursor"},
    )

    assert response.status_code == 400
    huge = base64.urlsafe_b64encode(b"o:99999999999999999999").decode()
    too_far = client.get(
        f"{MCP_PREFIX}/workspaces/{user.company_id}/agents",
        headers=_token_for(user, monkeypatch),
        params={"cursor": huge},
    )
    assert too_far.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "This cursor is not valid"
    assert detail["next_steps"]


def test_list_agents_searches_by_name(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)
    booking = create_test_agent(
        db, company_id=user.company_id, name="Car service booking"
    )
    create_test_agent(db, company_id=user.company_id, name="Dental reception")
    headers = _token_for(user, monkeypatch)
    url = f"{MCP_PREFIX}/workspaces/{user.company_id}/agents"

    response = client.get(url, headers=headers, params={"query": "SERVICE"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [str(booking.id)]

    none = client.get(url, headers=headers, params={"query": "100%_"}).json()
    assert none["data"] == []
    assert any("without `query`" in step for step in none["next_steps"])


# ── create_workspace ──


def test_create_workspace_adds_one_the_person_can_reach(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _new_user(db)
    headers = _token_for(user, monkeypatch)

    created = client.post(
        f"{MCP_PREFIX}/workspaces", headers=headers, json={"name": " Kestrel Plumbing "}
    )

    assert created.status_code == 200, created.text
    body = created.json()
    _assert_answer_shape(body)
    assert body["data"]["name"] == "Kestrel Plumbing"
    listed = client.get(f"{MCP_PREFIX}/workspaces", headers=headers).json()["data"]
    assert {w["id"] for w in listed} == {str(user.company_id), body["data"]["id"]}
    agents = client.get(
        f"{MCP_PREFIX}/workspaces/{body['data']['id']}/agents", headers=headers
    )
    assert agents.status_code == 200
    assert agents.json()["data"] == []
    # Creating through MCP does not change the workspace open on the web.
    db.refresh(user)
    assert str(user.company_id) != body["data"]["id"]


def test_create_workspace_refuses_a_blank_name(
    client: TestClient, db: Session, monkeypatch
) -> None:
    headers = _token_for(_new_user(db), monkeypatch)

    response = client.post(
        f"{MCP_PREFIX}/workspaces", headers=headers, json={"name": "  "}
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "A workspace needs a name"
