import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session

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
from app.services.retell import RetellCall
from app.tests.utils.eval import create_test_agent
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
    from sqlmodel import select

    user = db.exec(select(User).where(User.email == AUTH_USER_EMAIL)).one()
    return user


def _owned_agent_with_environment(db: Session, retell_agent_id: str = "ret_a1"):
    user = _seed_user(db)
    agent = create_test_agent(db)
    agent.created_by = user.id
    db.add(agent)
    db.commit()
    db.refresh(agent)

    integration = crud.create_integration(
        session=db,
        data=IntegrationCreate(
            provider=IntegrationProvider.RETELL,
            name=f"int-{uuid.uuid4().hex[:6]}",
            api_key="sk_test_key_abcdef",
        ),
    )
    crud.create_environment(
        session=db,
        data=EnvironmentCreate(
            name=f"env-{uuid.uuid4().hex[:6]}",
            platform=Platform.RETELL,
            agent_id=agent.id,
            integration_id=integration.id,
            platform_agent_id=retell_agent_id,
            platform_agent_name=retell_agent_id,
        ),
    )
    return agent, integration, user


def _fake_retell_call(
    call_id: str, start_ms: int, end_ms: int | None = None
) -> RetellCall:
    return RetellCall(
        call_id=call_id,
        agent_id="ret_a1",
        start_timestamp=start_ms,
        end_timestamp=end_ms,
        call_status="ended",
        transcript_object=[{"role": "agent", "content": "Hello"}],
        raw={"call_id": call_id},
    )


def test_list_calls_requires_auth(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/agents/{uuid.uuid4()}/calls")
    assert r.status_code == 401


def test_list_calls_unknown_agent(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/agents/{uuid.uuid4()}/calls",
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_list_calls_empty_when_no_integration(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    user = _seed_user(db)
    agent = create_test_agent(db)
    agent.created_by = user.id
    db.add(agent)
    db.commit()
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/calls",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0
    assert body["data"] == []


def test_list_calls_fetches_from_retell_and_marks_new(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _integration, _user = _owned_agent_with_environment(db)
    fake_calls = [
        _fake_retell_call("ret_call_1", 1_700_000_000_000, 1_700_000_060_000),
        _fake_retell_call("ret_call_2", 1_700_000_100_000, 1_700_000_200_000),
    ]
    mocked = AsyncMock(return_value=fake_calls)
    with patch("app.api.routes.calls.list_retell_calls", mocked):
        # Stale-while-revalidate: first GET serves an empty response and kicks
        # off a background sync. TestClient awaits ASGI background tasks before
        # returning, so by the second GET the DB is populated. The TTL gate
        # keeps the second GET from queueing another sync.
        first = client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )
        assert first.status_code == 200
        r = client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert len(body["data"]) == 2
    for item in body["data"]:
        assert item["is_new"] is True
        assert item["test_case_count"] == 0
    assert mocked.await_count == 1


def test_seen_endpoint_clears_new_badge(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _integration, _user = _owned_agent_with_environment(
        db, retell_agent_id="ret_a_seen"
    )
    fake_calls = [_fake_retell_call("ret_call_seen_1", 1_700_001_000_000)]
    with patch(
        "app.api.routes.calls.list_retell_calls",
        AsyncMock(return_value=fake_calls),
    ):
        # Prime: kicks off the background sync.
        client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )
        # Read populated state on the next call (TTL gate prevents a second sync).
        r = client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    call_id = r.json()["data"][0]["id"]

    seen_r = client.post(
        f"{settings.API_V1_STR}/calls/{call_id}/seen",
        cookies=auth_cookies,
    )
    assert seen_r.status_code == 200

    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/calls",
        cookies=auth_cookies,
    )
    assert r2.status_code == 200
    target = next(c for c in r2.json()["data"] if c["id"] == call_id)
    assert target["is_new"] is False


def test_refresh_uses_incremental_fetch(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _integration, _user = _owned_agent_with_environment(
        db, retell_agent_id="ret_a_refresh"
    )
    initial = [
        _fake_retell_call("ret_call_refresh_1", 1_700_002_000_000, 1_700_002_050_000),
    ]
    with patch(
        "app.api.routes.calls.list_retell_calls",
        AsyncMock(return_value=initial),
    ):
        client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )

    second_batch = [
        _fake_retell_call("ret_call_refresh_2", 1_700_003_000_000, 1_700_003_050_000),
    ]
    mocked = AsyncMock(return_value=second_batch)
    with patch("app.api.routes.calls.list_retell_calls", mocked):
        r = client.post(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls/refresh",
            cookies=auth_cookies,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 1
    assert body["total"] == 2

    # Verify list_retell_calls was called with a non-None start_after on refresh
    assert mocked.await_args is not None
    _args, kwargs = mocked.await_args
    assert kwargs.get("start_after") is not None


def test_refresh_requires_integration_configured(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    user = _seed_user(db)
    agent = create_test_agent(db)
    agent.created_by = user.id
    db.add(agent)
    db.commit()
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/calls/refresh",
        cookies=auth_cookies,
    )
    assert r.status_code == 400
