"""The Retell webhook. Every payload here is invented."""

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app import crud
from app.api.routes.webhooks import retell_signature_is_valid
from app.core import encryption
from app.core.config import settings
from app.models import Agent, Call, IntegrationCreate, IntegrationProvider, Platform
from app.models.call import CallEvent
from app.models.integration import Integration
from app.tests.utils.eval import create_test_agent, get_test_company_id
from app.tests.utils.retell_payloads import invocation, retell_call, speech

API_KEY = "key_invented_webhook_badge"


@pytest.fixture(autouse=True)
def _encryption_key(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(
        encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    encryption._fernet.cache_clear()
    yield
    encryption._fernet.cache_clear()


def _integration(
    db: Session, provider: IntegrationProvider = IntegrationProvider.RETELL
) -> Integration:
    return crud.create_integration(
        session=db,
        data=IntegrationCreate(
            provider=provider, name=f"int-{uuid.uuid4().hex[:6]}", api_key=API_KEY
        ),
        company_id=get_test_company_id(db),
    )


def _retell_agent(db: Session) -> tuple[Agent, Integration, str]:
    integration = _integration(db)
    provider_agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    agent = create_test_agent(db)
    agent.platform = Platform.RETELL
    agent.integration_id = integration.id
    agent.platform_agent_id = provider_agent_id
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent, integration, provider_agent_id


def _sign(body: bytes, *, key: str = API_KEY, at_ms: int | None = None) -> str:
    timestamp = str(at_ms if at_ms is not None else int(time.time() * 1000))
    digest = hmac.new(
        key.encode(), body + timestamp.encode(), hashlib.sha256
    ).hexdigest()
    return f"v={timestamp},d={digest}"


def _post(
    client: TestClient,
    integration_id: uuid.UUID,
    body: dict[str, Any] | bytes,
    *,
    signature: str | None = "sign",
) -> Any:
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    headers = {"content-type": "application/json"}
    if signature == "sign":
        signature = _sign(raw)
    if signature is not None:
        headers["x-retell-signature"] = signature
    return client.post(
        f"{settings.API_V1_STR}/webhooks/retell/{integration_id}",
        content=raw,
        headers=headers,
    )


def _calls(db: Session, agent_id: uuid.UUID) -> int:
    return int(
        db.exec(select(func.count(col(Call.id))).where(Call.agent_id == agent_id)).one()
    )


def test_signed_call_ended_stores_a_trace(client: TestClient, db: Session) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    payload = retell_call("call_wh_1", agent_id=provider_agent_id)

    r = _post(client, integration.id, {"event": "call_ended", "call": payload})

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "stored"
    call = db.exec(select(Call).where(Call.agent_id == agent.id)).one()
    assert str(call.id) == r.json()["call_id"]
    assert call.external_id == "call_wh_1"
    assert call.company_id == agent.company_id
    assert call.integration_id == integration.id
    assert call.raw == payload
    assert call.outputs is None
    assert call.checked_at is not None
    events = db.exec(select(CallEvent).where(CallEvent.call_id == call.id)).all()
    assert len(events) == 2


def test_call_analyzed_replaces_the_trace_and_adds_outputs(
    client: TestClient, db: Session
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    ended = retell_call("call_wh_2", agent_id=provider_agent_id)
    analyzed = retell_call(
        "call_wh_2",
        agent_id=provider_agent_id,
        timeline=[
            speech("agent", "Hello", 0.5),
            speech("user", "Goodbye", 2.0),
            invocation("tc_end", "end_call", "", time_sec=3.0),
        ],
        call_analysis={"call_summary": "Invented summary", "call_successful": True},
    )

    assert (
        _post(client, integration.id, {"event": "call_ended", "call": ended}).json()[
            "status"
        ]
        == "stored"
    )
    r = _post(client, integration.id, {"event": "call_analyzed", "call": analyzed})

    assert r.json()["status"] == "stored"
    assert _calls(db, agent.id) == 1
    db.expire_all()
    call = db.exec(select(Call).where(Call.agent_id == agent.id)).one()
    assert call.outputs == {
        "call_summary": "Invented summary",
        "call_successful": True,
    }
    assert call.raw == analyzed
    events = db.exec(select(CallEvent).where(CallEvent.call_id == call.id)).all()
    assert len(events) == 3


@pytest.mark.parametrize(
    "signature",
    [
        None,
        "",
        "not-a-signature",
        "v=abc,d=00",
        _sign(b"{}"),  # signs a different body
    ],
)
def test_a_missing_or_wrong_signature_is_refused(
    client: TestClient, db: Session, signature: str | None
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    body = {"event": "call_ended", "call": retell_call(agent_id=provider_agent_id)}

    r = _post(client, integration.id, body, signature=signature)

    assert r.status_code == 401
    assert r.json()["detail"] == "Webhook could not be verified"
    assert _calls(db, agent.id) == 0


def test_a_signature_made_with_another_key_is_refused(
    client: TestClient, db: Session
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    raw = json.dumps(
        {"event": "call_ended", "call": retell_call(agent_id=provider_agent_id)}
    ).encode()

    r = _post(client, integration.id, raw, signature=_sign(raw, key="key_other"))

    assert r.status_code == 401
    assert _calls(db, agent.id) == 0


@pytest.mark.parametrize("offset_ms", [-6 * 60 * 1000, 6 * 60 * 1000])
def test_a_signature_outside_five_minutes_is_refused(
    client: TestClient, db: Session, offset_ms: int
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    raw = json.dumps(
        {"event": "call_ended", "call": retell_call(agent_id=provider_agent_id)}
    ).encode()
    stale = _sign(raw, at_ms=int(time.time() * 1000) + offset_ms)

    r = _post(client, integration.id, raw, signature=stale)

    assert r.status_code == 401
    assert _calls(db, agent.id) == 0


def test_signature_within_five_minutes_is_accepted() -> None:
    body = b'{"event":"call_ended"}'
    now = 1_750_000_000_000
    signature = _sign(body, at_ms=now - 4 * 60 * 1000)
    assert retell_signature_is_valid(
        raw_body=body, signature=signature, api_key=API_KEY, now_ms=now
    )
    assert not retell_signature_is_valid(
        raw_body=body + b" ", signature=signature, api_key=API_KEY, now_ms=now
    )


def test_an_unknown_integration_is_refused_like_a_bad_signature(
    client: TestClient,
) -> None:
    r = _post(client, uuid.uuid4(), {"event": "call_ended", "call": retell_call()})
    assert r.status_code == 401
    assert r.json()["detail"] == "Webhook could not be verified"


def test_an_integration_of_another_provider_is_refused(
    client: TestClient, db: Session
) -> None:
    integration = _integration(db, IntegrationProvider.VAPI)
    r = _post(client, integration.id, {"event": "call_ended", "call": retell_call()})
    assert r.status_code == 401


def test_a_call_for_an_unknown_agent_is_acknowledged_and_not_stored(
    client: TestClient, db: Session
) -> None:
    agent, integration, _provider_agent_id = _retell_agent(db)
    payload = retell_call("call_wh_unknown", agent_id="agent_nobody_connected")

    r = _post(client, integration.id, {"event": "call_ended", "call": payload})

    assert r.status_code == 200
    assert r.json() == {
        "status": "ignored",
        "reason": "agent not connected",
        "call_id": None,
    }
    assert _calls(db, agent.id) == 0


@pytest.mark.parametrize(
    "body",
    [
        {"event": "call_started", "call": {"call_id": "call_wh_started"}},
        {"event": "transcript_updated", "call": {"call_id": "call_wh_live"}},
        {"event": "call_ended"},
        ["not", "an", "object"],
    ],
)
def test_an_event_that_is_not_handled_is_acknowledged_and_not_stored(
    client: TestClient, db: Session, body: Any
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    if isinstance(body, dict) and isinstance(body.get("call"), dict):
        body["call"]["agent_id"] = provider_agent_id

    r = _post(client, integration.id, json.dumps(body).encode())

    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
    assert _calls(db, agent.id) == 0


def test_a_call_that_cannot_be_mapped_is_acknowledged_and_not_stored(
    client: TestClient, db: Session
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    payload = {"call_id": "call_wh_no_time", "agent_id": provider_agent_id}

    r = _post(client, integration.id, {"event": "call_ended", "call": payload})

    assert r.status_code == 200
    assert r.json()["reason"] == "call could not be mapped"
    assert _calls(db, agent.id) == 0


def test_a_signed_body_that_is_not_json_is_rejected(
    client: TestClient, db: Session
) -> None:
    _agent, integration, _provider_agent_id = _retell_agent(db)
    r = _post(client, integration.id, b"not json")
    assert r.status_code == 422


def test_a_stored_call_is_looked_up_for_executions_after_the_response(
    client: TestClient, db: Session
) -> None:
    agent, integration, provider_agent_id = _retell_agent(db)
    payload = retell_call("call_wh_exec", agent_id=provider_agent_id)
    with patch(
        "app.api.routes.webhooks.sync_call_executions_in_background", AsyncMock()
    ) as looked_up:
        r = _post(client, integration.id, {"event": "call_ended", "call": payload})
        ignored = _post(
            client, integration.id, {"event": "call_started", "call": payload}
        )
    assert r.status_code == 200
    assert ignored.json()["status"] == "ignored"
    assert looked_up.await_count == 1
    call = db.exec(select(Call).where(Call.agent_id == agent.id)).one()
    assert looked_up.await_args.args == (call.id,)
