import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import encryption
from app.core.config import settings
from app.models import (
    EnvironmentCreate,
    IntegrationCreate,
    IntegrationProvider,
    Platform,
    User,
)
from app.tests.utils.eval import create_test_agent


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _superuser(db: Session) -> User:
    return db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()


def _make_owned_agent(db: Session, owner_email: str | None = None):
    user = (
        _superuser(db)
        if owner_email is None
        else db.exec(select(User).where(User.email == owner_email)).one()
    )
    agent = create_test_agent(db)
    agent.created_by = user.id
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent, user


def _make_integration(db: Session):
    return crud.create_integration(
        session=db,
        data=IntegrationCreate(
            provider=IntegrationProvider.RETELL,
            name=f"int-{uuid.uuid4().hex[:6]}",
            api_key="sk_test_env_routes",
        ),
    )


def _create_env_body(
    *, agent_id: uuid.UUID, integration_id: uuid.UUID, name: str = "prod"
) -> dict:
    return {
        "name": name,
        "platform": "retell",
        "agent_id": str(agent_id),
        "integration_id": str(integration_id),
        "platform_agent_id": "ret_agent_x",
        "platform_agent_name": "Retell Agent X",
    }


def test_environments_require_auth(client: TestClient) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/environments/", params={"agent_id": str(uuid.uuid4())}
    )
    assert r.status_code == 401


def test_create_environment_returns_404_when_integration_missing(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _ = _make_owned_agent(db)
    r = client.post(
        f"{settings.API_V1_STR}/environments/",
        json=_create_env_body(agent_id=agent.id, integration_id=uuid.uuid4()),
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_create_list_delete_environment_flow(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, user = _make_owned_agent(db)
    integration = _make_integration(db)

    create_r = client.post(
        f"{settings.API_V1_STR}/environments/",
        json=_create_env_body(
            agent_id=agent.id, integration_id=integration.id, name="prod"
        ),
        cookies=superuser_auth_cookies,
    )
    assert create_r.status_code == 200
    body = create_r.json()
    env_id = body["id"]
    assert body["name"] == "prod"
    assert body["platform"] == "retell"
    assert body["integration_id"] == str(integration.id)
    assert body["integration_name"] == integration.name

    list_r = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert list_r.status_code == 200
    listed = list_r.json()
    assert listed["count"] == 1
    assert listed["data"][0]["id"] == env_id
    assert listed["data"][0]["integration_name"] == integration.name

    del_r = client.delete(
        f"{settings.API_V1_STR}/environments/{env_id}",
        cookies=superuser_auth_cookies,
    )
    assert del_r.status_code == 200

    list_after = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert list_after.json()["count"] == 0


def test_list_environments_unknown_agent_returns_404(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(uuid.uuid4())},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_other_user_can_list_environment(
    client: TestClient,
    normal_user_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, user = _make_owned_agent(db)
    integration = _make_integration(db)
    env = crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name=f"env-{uuid.uuid4().hex[:6]}",
            platform=Platform.RETELL,
            agent_id=agent.id,
            integration_id=integration.id,
            platform_agent_id="ret_a_other",
            platform_agent_name="ret_a_other",
        ),
    )

    other_list = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=normal_user_auth_cookies,
    )
    assert other_list.status_code == 200
    assert any(item["id"] == str(env.id) for item in other_list.json()["data"])


def test_delete_integration_returns_409_when_environment_depends_on_it(
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, user = _make_owned_agent(db)
    integration = _make_integration(db)
    crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name=f"env-{uuid.uuid4().hex[:6]}",
            platform=Platform.RETELL,
            agent_id=agent.id,
            integration_id=integration.id,
            platform_agent_id="ret_a_409",
            platform_agent_name="ret_a_409",
        ),
    )

    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        del_r = client.delete(
            f"{settings.API_V1_STR}/integrations/{integration.id}",
            cookies=superuser_auth_cookies,
        )
    assert del_r.status_code == 409
    assert "environment" in del_r.json()["detail"].lower()
