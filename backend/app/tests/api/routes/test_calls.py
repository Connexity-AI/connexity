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
    IntegrationCreate,
    IntegrationProvider,
    Platform,
    User,
)
from app.services.elevenlabs import (
    ElevenLabsConversationDetails,
    ElevenLabsConversationSummary,
)
from app.services.retell import RetellCall
from app.tests.utils.eval import create_test_agent, get_test_company_id
from app.tests.utils.retell_payloads import retell_call
from app.tests.utils.utils import (
    AUTH_USER_EMAIL,
    extract_cookies,
    random_email,
    random_lower_string,
)


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


def _owned_retell_agent(db: Session, provider_agent_id: str = "ret_a1"):
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
        company_id=get_test_company_id(db),
    )
    agent.platform = Platform.RETELL
    agent.integration_id = integration.id
    agent.platform_agent_id = provider_agent_id
    agent.platform_agent_name = provider_agent_id
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent, integration, user


def _owned_elevenlabs_agent(db: Session, elevenlabs_agent_id: str = "el_a1"):
    user = _seed_user(db)
    agent = create_test_agent(db)
    agent.created_by = user.id
    db.add(agent)
    db.commit()
    db.refresh(agent)

    integration = crud.create_integration(
        session=db,
        data=IntegrationCreate(
            provider=IntegrationProvider.ELEVENLABS,
            name=f"int-{uuid.uuid4().hex[:6]}",
            api_key="sk_eleven_test_key",
        ),
        company_id=get_test_company_id(db),
    )
    agent.platform = Platform.ELEVENLABS
    agent.integration_id = integration.id
    agent.platform_agent_id = elevenlabs_agent_id
    agent.platform_agent_name = elevenlabs_agent_id
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent, integration, user


def _fake_retell_call(
    call_id: str,
    start_ms: int,
    end_ms: int | None = None,
    provider_agent_id: str = "ret_a1",
) -> RetellCall:
    return RetellCall(
        call_id=call_id,
        agent_id=provider_agent_id,
        start_timestamp=start_ms,
        end_timestamp=end_ms,
        call_status="ended",
        raw=retell_call(
            call_id,
            agent_id=provider_agent_id,
            start_ms=start_ms,
            duration_ms=(end_ms - start_ms) if end_ms else 60_000,
        ),
    )


def _fake_elevenlabs_summary(
    conversation_id: str, start_unix: int
) -> ElevenLabsConversationSummary:
    return ElevenLabsConversationSummary(
        conversation_id=conversation_id,
        agent_id="el_a1",
        start_time_unix_secs=start_unix,
        call_duration_secs=10,
        status="done",
        transcript_summary=None,
        raw={"conversation_id": conversation_id},
    )


def _fake_elevenlabs_details(
    conversation_id: str, start_unix: int
) -> ElevenLabsConversationDetails:
    return ElevenLabsConversationDetails(
        conversation_id=conversation_id,
        agent_id="el_a1",
        start_time_unix_secs=start_unix,
        call_duration_secs=10,
        status="done",
        transcript=[{"role": "agent", "time_in_call_secs": 1, "message": "Hello"}],
        raw={"conversation_id": conversation_id, "transcript": [{"message": "Hello"}]},
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
    agent, _integration, _user = _owned_retell_agent(db)
    fake_calls = [
        _fake_retell_call("ret_call_1", 1_700_000_000_000, 1_700_000_060_000),
        _fake_retell_call("ret_call_2", 1_700_000_100_000, 1_700_000_200_000),
    ]
    mocked = AsyncMock(return_value=fake_calls)
    with patch("app.services.call_sync.list_retell_calls", mocked):
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
    agent, _integration, _user = _owned_retell_agent(db, provider_agent_id="ret_a_seen")
    fake_calls = [_fake_retell_call("ret_call_seen_1", 1_700_001_000_000)]
    with patch(
        "app.services.call_sync.list_retell_calls",
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
    agent, _integration, _user = _owned_retell_agent(
        db, provider_agent_id="ret_a_refresh"
    )
    initial = [
        _fake_retell_call(
            "ret_call_refresh_1",
            1_700_002_000_000,
            1_700_002_050_000,
            provider_agent_id="ret_a_refresh",
        ),
    ]
    with patch(
        "app.services.call_sync.list_retell_calls",
        AsyncMock(return_value=initial),
    ):
        client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )

    second_batch = [
        _fake_retell_call(
            "ret_call_refresh_2",
            1_700_003_000_000,
            1_700_003_050_000,
            provider_agent_id="ret_a_refresh",
        ),
    ]
    mocked = AsyncMock(return_value=second_batch)
    with patch("app.services.call_sync.list_retell_calls", mocked):
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


def test_list_calls_fetches_from_elevenlabs(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, _integration, _user = _owned_elevenlabs_agent(db)
    summaries = [_fake_elevenlabs_summary("conv_1", 1_700_000_000)]
    details = _fake_elevenlabs_details("conv_1", 1_700_000_000)

    with (
        patch(
            "app.services.call_sync.list_elevenlabs_conversations",
            AsyncMock(return_value=summaries),
        ) as mock_list,
        patch(
            "app.services.call_sync.get_elevenlabs_conversation",
            AsyncMock(return_value=details),
        ) as mock_get,
    ):
        client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )
        r = client.get(
            f"{settings.API_V1_STR}/agents/{agent.id}/calls",
            cookies=auth_cookies,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["data"][0]["external_id"] == "conv_1"
    assert mock_list.await_count >= 1
    assert mock_get.await_count == 1


def _sync(client: TestClient, cookies: dict[str, str], agent_id: uuid.UUID) -> dict:
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent_id}/calls/refresh", cookies=cookies
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_refresh_stores_retell_calls_as_traces_with_the_original_payload(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent, integration, _user = _owned_retell_agent(db, provider_agent_id="ret_a_tr")
    fake = _fake_retell_call(
        "ret_call_tr_1", 1_700_010_000_000, 1_700_010_090_000, "ret_a_tr"
    )
    with patch(
        "app.services.call_sync.list_retell_calls", AsyncMock(return_value=[fake])
    ):
        assert _sync(client, auth_cookies, agent.id)["created"] == 1

    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/calls", cookies=auth_cookies
    )
    (item,) = r.json()["data"]
    assert item["provider"] == "retell"
    assert item["has_trace"] is True
    assert item["duration_seconds"] == 90
    assert item["end_reason"] == "caller_hangup"
    assert item["provider_agent_id"] == "ret_a_tr"
    assert "transcript" not in item
    assert "status" not in item

    call = crud.get_call(
        session=db, call_id=uuid.UUID(item["id"]), company_id=agent.company_id
    )
    assert call is not None
    assert call.raw == fake.raw
    assert call.integration_id == integration.id

    trace_r = client.get(
        f"{settings.API_V1_STR}/calls/{item['id']}/trace", cookies=auth_cookies
    )
    assert trace_r.status_code == 200, trace_r.text
    body = trace_r.json()
    assert body["trace"]["external_id"] == "ret_call_tr_1"
    assert [e["type"] for e in body["trace"]["events"]] == ["utterance", "utterance"]
    assert "timing" in body["capabilities"]
    assert "tool_calls" in body["capabilities"]


def test_refreshing_the_same_calls_again_creates_no_duplicates(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent, _integration, _user = _owned_retell_agent(db, provider_agent_id="ret_a_dup")
    fake = _fake_retell_call("ret_call_dup_1", 1_700_020_000_000, None, "ret_a_dup")
    with patch(
        "app.services.call_sync.list_retell_calls", AsyncMock(return_value=[fake])
    ):
        first = _sync(client, auth_cookies, agent.id)
        second = _sync(client, auth_cookies, agent.id)
    assert (first["created"], first["total"]) == (1, 1)
    assert (second["created"], second["total"]) == (0, 1)


def test_a_retell_call_that_cannot_be_mapped_is_skipped(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent, _integration, _user = _owned_retell_agent(db, provider_agent_id="ret_a_bad")
    good = _fake_retell_call("ret_call_ok", 1_700_030_000_000, None, "ret_a_bad")
    no_time = RetellCall(call_id="ret_call_bad", raw={"call_id": "ret_call_bad"})
    no_payload = RetellCall(call_id="ret_call_empty")
    with patch(
        "app.services.call_sync.list_retell_calls",
        AsyncMock(return_value=[no_time, good, no_payload]),
    ):
        result = _sync(client, auth_cookies, agent.id)
    assert (result["created"], result["total"]) == (1, 1)


def test_trace_of_a_call_that_was_not_converted_is_not_found(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent, _integration, _user = _owned_elevenlabs_agent(db, "el_a_nt")
    with (
        patch(
            "app.services.call_sync.list_elevenlabs_conversations",
            AsyncMock(
                return_value=[_fake_elevenlabs_summary("conv_nt", 1_700_040_000)]
            ),
        ),
        patch(
            "app.services.call_sync.get_elevenlabs_conversation",
            AsyncMock(return_value=_fake_elevenlabs_details("conv_nt", 1_700_040_000)),
        ),
    ):
        _sync(client, auth_cookies, agent.id)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/calls", cookies=auth_cookies
    )
    (item,) = r.json()["data"]
    assert item["has_trace"] is False

    trace_r = client.get(
        f"{settings.API_V1_STR}/calls/{item['id']}/trace", cookies=auth_cookies
    )
    assert trace_r.status_code == 404
    assert "not been converted" in trace_r.json()["detail"]


def test_trace_of_another_companys_call_is_not_found(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent, _integration, _user = _owned_retell_agent(db, provider_agent_id="ret_a_oc")
    fake = _fake_retell_call("ret_call_oc", 1_700_050_000_000, None, "ret_a_oc")
    with patch(
        "app.services.call_sync.list_retell_calls", AsyncMock(return_value=[fake])
    ):
        _sync(client, auth_cookies, agent.id)
    call_id = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/calls", cookies=auth_cookies
    ).json()["data"][0]["id"]

    email, password = random_email(), random_lower_string()
    client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": email, "password": password},
    )
    login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    other = extract_cookies(login)
    for path in (f"calls/{call_id}/trace", f"calls/{call_id}"):
        r = client.get(f"{settings.API_V1_STR}/{path}", cookies=other)
        assert r.status_code == 404
    assert (
        client.get(f"{settings.API_V1_STR}/calls/{uuid.uuid4()}/trace").status_code
        == 401
    )
