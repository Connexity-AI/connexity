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
    Agent,
    EnvironmentCreate,
    IntegrationCreate,
    IntegrationProvider,
    Platform,
    User,
)
from app.tests.utils.eval import create_test_agent, get_test_company_id
from app.tests.utils.utils import AUTH_USER_EMAIL


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _seed_user(db: Session) -> User:
    return db.exec(select(User).where(User.email == AUTH_USER_EMAIL)).one()


def _make_owned_agent(db: Session, owner_email: str | None = None):
    user = (
        _seed_user(db)
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
        company_id=get_test_company_id(db),
    )


def _make_elevenlabs_integration(db: Session):
    return crud.create_integration(
        session=db,
        data=IntegrationCreate(
            provider=IntegrationProvider.ELEVENLABS,
            name=f"int-{uuid.uuid4().hex[:6]}",
            api_key="sk_test_eleven_env_routes",
        ),
        company_id=get_test_company_id(db),
    )


def _create_env_body(
    *,
    agent_id: uuid.UUID,
    name: str = "prod",
    platform: str = "retell",
) -> dict:
    body: dict[str, str] = {
        "name": name,
        "platform": platform,
        "agent_id": str(agent_id),
    }
    if platform == "webhook":
        body["endpoint_url"] = "https://example.com/hooks/deploy"
    return body


def _bind_agent_provider_target(
    db: Session,
    *,
    agent: Agent,
    platform: Platform,
    integration_id: uuid.UUID,
    platform_agent_id: str,
    platform_agent_name: str,
) -> None:
    agent.platform = platform
    agent.integration_id = integration_id
    agent.platform_agent_id = platform_agent_id
    agent.platform_agent_name = platform_agent_name
    db.add(agent)
    db.commit()
    db.refresh(agent)


def test_create_list_delete_elevenlabs_environment_flow(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _user = _make_owned_agent(db)
    integration = _make_elevenlabs_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.ELEVENLABS,
        integration_id=integration.id,
        platform_agent_id="el_agent_x",
        platform_agent_name="ElevenLabs Agent X",
    )

    create_r = client.post(
        f"{settings.API_V1_STR}/environments/",
        json=_create_env_body(
            agent_id=agent.id,
            name="prod",
            platform="elevenlabs",
        ),
        cookies=auth_cookies,
    )
    assert create_r.status_code == 200
    body = create_r.json()
    env_id = body["id"]
    assert body["platform"] == "elevenlabs"
    assert body["integration_name"] == integration.name

    list_r = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=auth_cookies,
    )
    assert list_r.status_code == 200
    assert any(item["id"] == env_id for item in list_r.json()["data"])

    del_r = client.delete(
        f"{settings.API_V1_STR}/environments/{env_id}",
        cookies=auth_cookies,
    )
    assert del_r.status_code == 200


def test_environments_require_auth(client: TestClient) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/environments/", params={"agent_id": str(uuid.uuid4())}
    )
    assert r.status_code == 401


def test_create_environment_returns_404_when_integration_missing(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _ = _make_owned_agent(db)
    integration = _make_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.RETELL,
        integration_id=integration.id,
        platform_agent_id="ret_agent_x",
        platform_agent_name="Retell Agent X",
    )
    with patch(
        "app.api.routes.environments.crud.get_integration",
        return_value=None,
    ):
        r = client.post(
            f"{settings.API_V1_STR}/environments/",
            json=_create_env_body(agent_id=agent.id),
            cookies=auth_cookies,
        )
    assert r.status_code == 404


def test_create_list_delete_environment_flow(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, user = _make_owned_agent(db)
    integration = _make_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.RETELL,
        integration_id=integration.id,
        platform_agent_id="ret_agent_x",
        platform_agent_name="Retell Agent X",
    )

    create_r = client.post(
        f"{settings.API_V1_STR}/environments/",
        json=_create_env_body(agent_id=agent.id, name="prod"),
        cookies=auth_cookies,
    )
    assert create_r.status_code == 200
    body = create_r.json()
    env_id = body["id"]
    assert body["name"] == "prod"
    assert body["platform"] == "retell"
    assert body["integration_name"] == integration.name

    list_r = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=auth_cookies,
    )
    assert list_r.status_code == 200
    listed = list_r.json()
    assert listed["count"] == 1
    assert listed["data"][0]["id"] == env_id
    assert listed["data"][0]["integration_name"] == integration.name

    del_r = client.delete(
        f"{settings.API_V1_STR}/environments/{env_id}",
        cookies=auth_cookies,
    )
    assert del_r.status_code == 200

    list_after = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=auth_cookies,
    )
    assert list_after.json()["count"] == 0


def test_list_environments_unknown_agent_returns_404(
    client: TestClient,
    auth_cookies: dict[str, str],
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(uuid.uuid4())},
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_environment_is_isolated_per_company(
    client: TestClient,
    normal_user_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    """An environment created in one company isn't visible to a user in another."""
    agent, user = _make_owned_agent(db)
    integration = _make_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.RETELL,
        integration_id=integration.id,
        platform_agent_id="ret_a_other",
        platform_agent_name="ret_a_other",
    )
    crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name=f"env-{uuid.uuid4().hex[:6]}",
            platform=Platform.RETELL,
            agent_id=agent.id,
        ),
        company_id=get_test_company_id(db),
    )

    # ``normal_user_auth_cookies`` is in a different company, so the agent
    # itself is hidden — listing environments via that agent_id returns 404.
    other_list = client.get(
        f"{settings.API_V1_STR}/environments/",
        params={"agent_id": str(agent.id)},
        cookies=normal_user_auth_cookies,
    )
    assert other_list.status_code == 404


def test_create_webhook_environment_without_integration(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _ = _make_owned_agent(db)
    create_r = client.post(
        f"{settings.API_V1_STR}/environments/",
        json=_create_env_body(
            agent_id=agent.id,
            name="internal webhook",
            platform="webhook",
        ),
        cookies=auth_cookies,
    )
    assert create_r.status_code == 200
    body = create_r.json()
    assert body["platform"] == "webhook"
    assert body["integration_name"] is None
    assert body["endpoint_url"] == "https://example.com/hooks/deploy"


def test_update_environment_changes_configuration_fields(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _ = _make_owned_agent(db)
    integration = _make_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.RETELL,
        integration_id=integration.id,
        platform_agent_id="ret_a_old",
        platform_agent_name="Old Retell Agent",
    )
    env = crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name="prod",
            platform=Platform.RETELL,
            agent_id=agent.id,
        ),
        company_id=get_test_company_id(db),
    )
    r = client.patch(
        f"{settings.API_V1_STR}/environments/{env.id}",
        json={
            "name": "Internal Webhook",
            "platform": "webhook",
            "endpoint_url": "https://example.com/hooks/new-deploy",
        },
        cookies=auth_cookies,
    )

    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Internal Webhook"
    assert body["platform"] == "retell"
    assert body["integration_name"] == integration.name
    assert body["endpoint_url"] is None


def test_update_environment_rejects_null_required_fields(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _ = _make_owned_agent(db)
    integration = _make_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.RETELL,
        integration_id=integration.id,
        platform_agent_id="ret_a_old",
        platform_agent_name="Old Retell Agent",
    )
    env = crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name="prod",
            platform=Platform.RETELL,
            agent_id=agent.id,
        ),
        company_id=get_test_company_id(db),
    )

    r = client.patch(
        f"{settings.API_V1_STR}/environments/{env.id}",
        json={"name": None},
        cookies=auth_cookies,
    )

    assert r.status_code == 422


def test_delete_integration_returns_409_when_environment_depends_on_it(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, user = _make_owned_agent(db)
    integration = _make_integration(db)
    _bind_agent_provider_target(
        db,
        agent=agent,
        platform=Platform.RETELL,
        integration_id=integration.id,
        platform_agent_id="ret_a_409",
        platform_agent_name="ret_a_409",
    )
    crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name=f"env-{uuid.uuid4().hex[:6]}",
            platform=Platform.RETELL,
            agent_id=agent.id,
        ),
        company_id=get_test_company_id(db),
    )

    with patch.dict(
        "app.api.routes.integrations._CONNECTION_TESTERS",
        {IntegrationProvider.RETELL: AsyncMock(return_value=True)},
        clear=False,
    ):
        del_r = client.delete(
            f"{settings.API_V1_STR}/integrations/{integration.id}",
            cookies=auth_cookies,
        )
    assert del_r.status_code == 409
    assert "environment" in del_r.json()["detail"].lower()


def test_environment_create_derives_platform_from_retell_agent(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _user = _make_owned_agent(db)
    integration = _make_integration(db)
    agent.platform = Platform.RETELL
    agent.integration_id = integration.id
    agent.platform_agent_id = "retell-bound-1"
    agent.platform_agent_name = "Bound Retell"
    db.add(agent)
    db.commit()

    create_r = client.post(
        f"{settings.API_V1_STR}/environments/",
        json={
            "name": "prod",
            "platform": "webhook",
            "agent_id": str(agent.id),
            "endpoint_url": "https://example.com/ignored-for-retell-agent",
        },
        cookies=auth_cookies,
    )
    assert create_r.status_code == 200
    body = create_r.json()
    assert body["platform"] == "retell"
    assert body["integration_name"] == integration.name
    assert body["endpoint_url"] is None
