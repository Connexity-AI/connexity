"""The scheduled call pull and its route. Every Retell answer here is invented."""

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
import pytest
import respx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlmodel import Session, select

from app import crud
from app.api.routes import internal
from app.core import encryption
from app.core.config import settings
from app.core.encryption import encrypt, key_fingerprint, mask_key
from app.models import Agent, Call, UserCreate
from app.models.call_pull import CallPullAccount, CallPullLease
from app.models.enums import IntegrationProvider, Platform
from app.models.integration import Integration
from app.services import call_pull
from app.services.call_pull import run_pull
from app.tests.utils.retell_payloads import retell_call
from app.tests.utils.utils import random_email, random_lower_string

LIST_CALLS = "https://api.retellai.com/v3/list-calls"
GET_CALL = r"https://api.retellai.com/v2/get-call/(?P<call_id>[^/]+)"
GET_AGENT = r"https://api.retellai.com/get-agent/.+"
MINUTE_MS = 60_000


@pytest.fixture(autouse=True)
def _isolated(db: Session) -> Generator[None, None, None]:
    # Keys stored by other tests were encrypted under other keys: the pull skips them.
    encryption_key = Fernet.generate_key().decode()
    original = encryption.settings.ENCRYPTION_KEY
    encryption.settings.ENCRYPTION_KEY = encryption_key
    encryption._fernet.cache_clear()
    db.execute(delete(CallPullLease))
    db.commit()
    yield
    encryption.settings.ENCRYPTION_KEY = original
    encryption._fernet.cache_clear()


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


class Retell:
    """Invented Retell accounts, told apart by key: their calls and full records."""

    def __init__(self) -> None:
        self.calls: dict[str, list[dict[str, Any]]] = {}
        self.lists: list[str] = []
        self.reads: list[str] = []
        self.rate_limited: dict[str, httpx.Response] = {}
        self.broken: set[str] = set()
        self.failing: set[str] = set()

    def add(self, key: str, call: dict[str, Any]) -> None:
        self.calls.setdefault(key, []).append(call)

    def _key(self, request: httpx.Request) -> str:
        return request.headers["Authorization"].removeprefix("Bearer ")

    def list_calls(self, request: httpx.Request) -> httpx.Response:
        key = self._key(request)
        self.lists.append(key)
        if key in self.rate_limited:
            return self.rate_limited[key]
        body = json.loads(request.content)
        after = body["filter_criteria"]["start_timestamp"]["value"]
        agents = {a["agent_id"] for a in body["filter_criteria"]["agent"]}
        items = sorted(
            (
                {k: v for k, v in c.items() if k != "transcript_with_tool_calls"}
                for c in self.calls.get(key, [])
                if c["start_timestamp"] > after and c["agent_id"] in agents
            ),
            key=lambda c: c["start_timestamp"],
        )
        return httpx.Response(200, json={"items": items[: body["limit"]]})

    def get_call(self, request: httpx.Request, call_id: str) -> httpx.Response:
        key = self._key(request)
        self.reads.append(call_id)
        if call_id in self.broken:
            return httpx.Response(200, text="<html>")
        if call_id in self.failing:
            return httpx.Response(500, json={})
        found = next(
            (c for c in self.calls.get(key, []) if c["call_id"] == call_id), None
        )
        return (
            httpx.Response(200, json=found) if found else httpx.Response(404, json={})
        )

    def mock(self) -> None:
        respx.post(LIST_CALLS).mock(side_effect=self.list_calls)
        respx.get(url__regex=GET_CALL).mock(side_effect=self.get_call)
        respx.get(url__regex=GET_AGENT).mock(return_value=httpx.Response(404, json={}))


def _ended(
    call_id: str, agent_id: str, minutes_ago: float, **extra: Any
) -> dict[str, Any]:
    return retell_call(
        call_id,
        agent_id=agent_id,
        start_ms=_now_ms() - int(minutes_ago * MINUTE_MS),
        duration_ms=30_000,
        **extra,
    )


def _ongoing(call_id: str, agent_id: str, minutes_ago: float) -> dict[str, Any]:
    call = _ended(call_id, agent_id, minutes_ago, call_status="ongoing")
    call.pop("end_timestamp")
    return call


def _workspace(db: Session) -> uuid.UUID:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    return user.company_id


def _connect(db: Session, company_id: uuid.UUID, key: str) -> Integration:
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Retell",
        company_id=company_id,
        encrypted_api_key=encrypt(key),
        masked_api_key=mask_key(key),
        key_fingerprint=key_fingerprint(key),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def _add(db: Session, integration: Integration, platform_agent_id: str) -> Agent:
    agent, _ = crud.add_platform_agent(
        session=db,
        company_id=integration.company_id,
        integration=integration,
        platform=Platform.RETELL,
        platform_agent_id=platform_agent_id,
        name=platform_agent_id,
        platform_agent_name=None,
        created_by=_owner(db, integration.company_id),
    )
    return agent


def _owner(db: Session, company_id: uuid.UUID) -> uuid.UUID:
    from app.models import User

    user = db.exec(select(User).where(User.company_id == company_id)).first()
    assert user is not None
    return user.id


def _account(db: Session, key: str, agent_ids: list[str]) -> list[Agent]:
    integration = _connect(db, _workspace(db), key)
    return [_add(db, integration, a) for a in agent_ids]


def _start_from(db: Session, key: str, minutes_ago: float) -> None:
    db.add(
        CallPullAccount(
            key_fingerprint=key_fingerprint(key),
            cursor=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        )
    )
    db.commit()


def _stored(db: Session, agent: Agent) -> list[str]:
    db.expire_all()
    return sorted(
        db.exec(select(Call.external_id).where(Call.agent_id == agent.id)).all()
    )


def _state(db: Session, key: str) -> CallPullAccount:
    db.expire_all()
    state = db.get(CallPullAccount, key_fingerprint(key))
    assert state is not None
    return state


def _key() -> str:
    return f"key_invented_{uuid.uuid4().hex[:8]}"


def _agent_id() -> str:
    return f"agent_{uuid.uuid4().hex[:8]}"


@respx.mock
async def test_a_run_stores_new_calls_per_account_and_in_every_workspace(
    db: Session,
) -> None:
    key_a, key_b = _key(), _key()
    shared, other = _agent_id(), _agent_id()
    [first] = _account(db, key_a, [shared])
    [second] = _account(db, key_a, [shared])  # the same account in another workspace
    [elsewhere] = _account(db, key_b, [other])
    _start_from(db, key_a, 60)
    _start_from(db, key_b, 60)
    retell = Retell()
    retell.add(key_a, _ended("call_a1", shared, 30))
    retell.add(key_a, _ended("call_a2", shared, 20))
    retell.add(key_b, _ended("call_b1", other, 10))
    retell.mock()

    run = await run_pull(session=db)

    assert run.status == "ok"
    assert _stored(db, first) == ["call_a1", "call_a2"]
    assert _stored(db, second) == ["call_a1", "call_a2"]
    assert _stored(db, elsewhere) == ["call_b1"]
    # One list per account, and each call read once even when stored twice.
    assert retell.lists.count(key_a) == 1
    assert retell.lists.count(key_b) == 1
    assert sorted(retell.reads) == ["call_a1", "call_a2", "call_b1"]
    assert _state(db, key_a).last_pulled_at is not None
    # Checked as they arrived.
    for agent in (first, second, elsewhere):
        for call in db.exec(select(Call).where(Call.agent_id == agent.id)).all():
            assert call.checked_at is not None


@respx.mock
async def test_a_new_account_starts_from_its_first_run(db: Session) -> None:
    key, agent_id = _key(), _agent_id()
    [agent] = _account(db, key, [agent_id])
    retell = Retell()
    retell.add(key, _ended("call_before", agent_id, 30))
    retell.mock()

    await run_pull(session=db)

    assert _stored(db, agent) == []


@respx.mock
async def test_calls_already_stored_are_not_read_again(db: Session) -> None:
    key, agent_id = _key(), _agent_id()
    [agent] = _account(db, key, [agent_id])
    _start_from(db, key, 60)
    retell = Retell()
    retell.add(key, _ended("call_one", agent_id, 30))
    retell.mock()
    await run_pull(session=db)
    # Pretend the account was idle long enough to be pulled again.
    state = _state(db, key)
    state.cursor = datetime.now(UTC) - timedelta(minutes=60)
    db.add(state)
    db.commit()

    await run_pull(session=db)

    assert retell.reads == ["call_one"]
    assert _stored(db, agent) == ["call_one"]


@respx.mock
async def test_a_call_in_progress_holds_the_position_not_later_calls(
    db: Session,
) -> None:
    key, agent_id = _key(), _agent_id()
    [agent] = _account(db, key, [agent_id])
    _start_from(db, key, 300)
    retell = Retell()
    retell.add(key, _ongoing("call_stuck", agent_id, 180))  # never ended: passed over
    retell.add(key, _ended("call_done", agent_id, 30))
    retell.add(key, _ongoing("call_live", agent_id, 20))
    retell.add(key, _ended("call_after", agent_id, 10))
    retell.mock()

    await run_pull(session=db)

    # Calls after the live one are stored at once; the position waits for it.
    assert _stored(db, agent) == ["call_after", "call_done"]
    assert "call_stuck" not in retell.reads
    live_started = datetime.fromtimestamp(
        retell.calls[key][2]["start_timestamp"] / 1000, tz=UTC
    )
    assert _state(db, key).cursor < live_started

    # The live call ends: the next run stores it, and reads nothing twice.
    retell.calls[key][2] = _ended("call_live", agent_id, 20)
    await run_pull(session=db)

    assert _stored(db, agent) == ["call_after", "call_done", "call_live"]
    assert sorted(retell.reads) == ["call_after", "call_done", "call_live"]


@respx.mock
async def test_a_call_retell_keeps_failing_on_is_passed_over(db: Session) -> None:
    key, agent_id = _key(), _agent_id()
    [agent] = _account(db, key, [agent_id])
    _start_from(db, key, 60)
    retell = Retell()
    retell.add(key, _ended("call_bad", agent_id, 30))
    retell.add(key, _ended("call_good", agent_id, 20))
    retell.failing = {"call_bad"}
    retell.mock()

    for _ in range(call_pull.POISON_AFTER):
        await run_pull(session=db)
        state = _state(db, key)
        assert _stored(db, agent) == []
        state.paused_until = None  # skip the wait
        db.add(state)
        db.commit()

    await run_pull(session=db)

    assert _stored(db, agent) == ["call_good"]
    assert _state(db, key).failures == 0


@respx.mock
async def test_a_backlog_drains_over_runs(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(call_pull, "MAX_READS", 3)
    key, agent_id = _key(), _agent_id()
    [agent] = _account(db, key, [agent_id])
    _start_from(db, key, 60)
    retell = Retell()
    for i in range(7):
        retell.add(key, _ended(f"call_{i}", agent_id, 50 - i))
    retell.mock()

    counts = []
    for _ in range(3):
        run = await run_pull(session=db)
        counts.append(run.calls_stored)

    assert counts == [3, 3, 1]
    assert len(_stored(db, agent)) == 7


@respx.mock
async def test_a_call_without_analysis_is_read_once_more(db: Session) -> None:
    key, agent_id = _key(), _agent_id()
    [agent] = _account(db, key, [agent_id])
    _start_from(db, key, 60)
    retell = Retell()
    # Just ended: Retell has not added its analysis yet.
    retell.add(key, _ended("call_late", agent_id, 1))
    retell.mock()
    await run_pull(session=db)
    call = db.exec(select(Call).where(Call.agent_id == agent.id)).one()
    assert call.outputs is None
    assert call.reread_at is None
    # A few minutes later Retell has added it.
    assert call.ended_at is not None
    call.ended_at = call.ended_at - timedelta(minutes=5)
    db.add(call)
    db.commit()
    retell.calls[key][0] = _ended(
        "call_late",
        agent_id,
        1,
        call_analysis={"call_summary": "Invented summary", "call_successful": True},
    )

    run = await run_pull(session=db)

    assert run.calls_reread == 1
    db.expire_all()
    call = db.exec(select(Call).where(Call.agent_id == agent.id)).one()
    assert call.outputs is not None
    assert call.reread_at is not None
    reads = len(retell.reads)
    await run_pull(session=db)
    assert len(retell.reads) == reads


@respx.mock
async def test_an_idle_account_is_pulled_every_ten_minutes(db: Session) -> None:
    key, agent_id = _key(), _agent_id()
    _account(db, key, [agent_id])
    _start_from(db, key, 300)
    state = _state(db, key)
    state.last_pulled_at = datetime.now(UTC) - timedelta(minutes=2)
    db.add(state)
    db.commit()
    retell = Retell()
    retell.mock()

    run = await run_pull(session=db)

    assert run.skipped.get("idle") == 1
    assert key not in retell.lists

    state = _state(db, key)
    state.last_pulled_at = datetime.now(UTC) - timedelta(minutes=11)
    db.add(state)
    db.commit()
    await run_pull(session=db)
    assert key in retell.lists


@respx.mock
@pytest.mark.parametrize(
    ("headers", "at_least", "at_most"),
    [({"Retry-After": "300"}, 300, 316), ({}, 60, 76)],
    ids=["retry-after", "no-header"],
)
async def test_a_429_pauses_only_that_account(
    db: Session, headers: dict[str, str], at_least: int, at_most: int
) -> None:
    limited, fine = _key(), _key()
    limited_agent, fine_agent = _agent_id(), _agent_id()
    _account(db, limited, [limited_agent])
    [other] = _account(db, fine, [fine_agent])
    _start_from(db, limited, 60)
    _start_from(db, fine, 60)
    retell = Retell()
    retell.rate_limited[limited] = httpx.Response(
        429,
        headers=headers,
        json={"status": "error", "message": "Account rate limited"},
    )
    retell.add(fine, _ended("call_fine", fine_agent, 10))
    retell.mock()

    run = await run_pull(session=db)

    assert run.skipped.get("rate_limited") == 1
    assert _stored(db, other) == ["call_fine"]
    state = _state(db, limited)
    assert state.failures == 1
    assert state.paused_until is not None
    wait = (state.paused_until - datetime.now(UTC)).total_seconds()
    assert at_least - 5 <= wait <= at_most

    lists = retell.lists.count(limited)
    run = await run_pull(session=db)
    assert run.skipped.get("paused") == 1
    assert retell.lists.count(limited) == lists


@respx.mock
async def test_runs_never_overlap(db: Session) -> None:
    key, agent_id = _key(), _agent_id()
    _account(db, key, [agent_id])
    _start_from(db, key, 60)
    retell = Retell()
    retell.mock()
    db.add(
        CallPullLease(
            id=1, held_until=datetime.now(UTC) + timedelta(minutes=1), holder="other"
        )
    )
    db.commit()

    run = await run_pull(session=db)

    assert run.status == "already_running"
    assert retell.lists == []

    # A lease left by a run that crashed ends on its own.
    lease = db.get(CallPullLease, 1)
    assert lease is not None
    lease.held_until = datetime.now(UTC) - timedelta(seconds=1)
    db.add(lease)
    db.commit()
    assert (await run_pull(session=db)).status == "ok"


# ── The route ──────────────────────────────────────────────────────────────

AUDIENCE = "https://backend.example.com/api/v1/internal/calls/pull"
INVOKER = "call-pull@example.iam.gserviceaccount.com"
PULL = f"{settings.API_V1_STR}/internal/calls/pull"
GOOGLE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
STRANGER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(
    *,
    key: rsa.RSAPrivateKey = GOOGLE,
    audience: str = AUDIENCE,
    email: str = INVOKER,
    issuer: str = "https://accounts.google.com",
) -> str:
    now = int(datetime.now(UTC).timestamp())
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "email": email,
            "email_verified": True,
            "iat": now,
            "exp": now + 300,
        },
        key,
        algorithm="RS256",
    )


@pytest.fixture
def _scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CALL_PULL_AUDIENCE", AUDIENCE)
    monkeypatch.setattr(settings, "CALL_PULL_INVOKER", INVOKER)
    monkeypatch.setattr(
        internal, "google_signing_key", lambda _token: GOOGLE.public_key()
    )


def test_the_route_does_not_exist_unless_set_up(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "CALL_PULL_AUDIENCE", None)
    monkeypatch.setattr(settings, "CALL_PULL_INVOKER", None)

    assert (
        client.post(PULL, headers={"Authorization": f"Bearer {_token()}"}).status_code
        == 404
    )


@pytest.mark.usefixtures("_scheduler")
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-token"},
        {"Authorization": f"Bearer {_token(key=STRANGER)}"},
        {"Authorization": f"Bearer {_token(audience='https://elsewhere.example.com')}"},
        {"Authorization": f"Bearer {_token(email='someone@example.com')}"},
        {"Authorization": f"Bearer {_token(issuer='https://evil.example.com')}"},
    ],
    ids=[
        "none",
        "garbage",
        "wrong-signature",
        "wrong-audience",
        "wrong-sender",
        "wrong-issuer",
    ],
)
def test_only_the_scheduler_can_run_the_pull(
    client: TestClient, headers: dict[str, str]
) -> None:
    assert client.post(PULL, headers=headers).status_code == 401


@pytest.mark.usefixtures("_scheduler")
@respx.mock
def test_the_scheduler_runs_the_pull(client: TestClient) -> None:
    Retell().mock()

    r = client.post(PULL, headers={"Authorization": f"Bearer {_token()}"})

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ok"


@respx.mock
async def test_an_unexpected_failure_pauses_only_that_account(db: Session) -> None:
    broken, fine = _key(), _key()
    broken_agent, fine_agent = _agent_id(), _agent_id()
    _account(db, broken, [broken_agent])
    [other] = _account(db, fine, [fine_agent])
    _start_from(db, broken, 60)
    _start_from(db, fine, 60)
    retell = Retell()
    retell.add(broken, _ended("call_broken", broken_agent, 20))
    retell.add(fine, _ended("call_fine", fine_agent, 10))
    # Retell answers this account's read with something that is not JSON.
    retell.broken = {"call_broken"}
    retell.mock()

    run = await run_pull(session=db)

    assert run.status == "ok"
    assert _stored(db, other) == ["call_fine"]
    assert _state(db, broken).paused_until is not None
