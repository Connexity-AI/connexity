"""Every stored call is checked by every current check version. Calls are invented."""

import dataclasses
import uuid
from collections.abc import Generator

import pytest
import respx
from cryptography.fernet import Fernet
from sqlalchemy import delete
from sqlmodel import Session, select

from app import crud
from app.core import encryption
from app.core.encryption import encrypt, key_fingerprint, mask_key
from app.models import Agent, Call, CallCheck, UserCreate
from app.models.call_pull import CallPullLease
from app.models.enums import CheckOutcome, IntegrationProvider, Platform
from app.models.integration import Integration
from app.services import call_pull
from app.services.call_pull import run_pull
from app.services.checks import engine
from app.services.checks.base import CheckInput, Raised
from app.services.checks.engine import check_calls_needing_it
from app.services.checks.rules.tool_call_failed import TOOL_CALL_FAILED
from app.services.mappings.retell import retell_call_to_trace
from app.tests.utils.retell_payloads import retell_call
from app.tests.utils.utils import random_email, random_lower_string

CHECK = TOOL_CALL_FAILED.type


@pytest.fixture(autouse=True)
def _isolated(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    monkeypatch.setattr(call_pull, "_backlog_empty", None)
    original = encryption.settings.ENCRYPTION_KEY
    encryption.settings.ENCRYPTION_KEY = Fernet.generate_key().decode()
    encryption._fernet.cache_clear()
    db.execute(delete(CallPullLease))
    db.commit()
    yield
    encryption.settings.ENCRYPTION_KEY = original
    encryption._fernet.cache_clear()


def _agent(db: Session) -> Agent:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    key = f"key_invented_{uuid.uuid4().hex[:8]}"
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Retell",
        company_id=user.company_id,
        encrypted_api_key=encrypt(key),
        masked_api_key=mask_key(key),
        key_fingerprint=key_fingerprint(key),
    )
    db.add(integration)
    db.commit()
    agent, _ = crud.add_platform_agent(
        session=db,
        company_id=user.company_id,
        integration=integration,
        platform=Platform.RETELL,
        platform_agent_id=f"agent_{uuid.uuid4().hex[:8]}",
        name="Invented",
        platform_agent_name=None,
        created_by=user.id,
    )
    return agent


def _stored_unchecked(db: Session, agent: Agent, count: int) -> list[Call]:
    """Calls stored the way a store before a check existed leaves them: no runs."""
    calls = []
    for i in range(count):
        payload = retell_call(
            f"call_{uuid.uuid4().hex[:8]}",
            agent_id=agent.platform_agent_id or "",
            start_ms=1_760_000_000_000 + i * 60_000,
        )
        stored = crud.store_trace(
            session=db,
            trace=retell_call_to_trace(payload),
            agent_id=agent.id,
            company_id=agent.company_id,
            integration_id=agent.integration_id,
            raw=payload,
        )
        db.commit()
        calls.append(stored.call)
    return calls


def _runs(db: Session, call: Call) -> list[tuple[str, int, CheckOutcome]]:
    db.expire_all()
    rows = db.exec(select(CallCheck).where(CallCheck.call_id == call.id)).all()
    return sorted((r.check_type, r.check_version, r.outcome) for r in rows)


def test_calls_stored_before_a_check_existed_are_checked(db: Session) -> None:
    agent = _agent(db)
    calls = _stored_unchecked(db, agent, 3)

    checked = check_calls_needing_it(session=db, agent_ids=[agent.id])

    assert checked == 3
    for call in calls:
        assert _runs(db, call) == [(CHECK, 1, CheckOutcome.RAN)]
    assert check_calls_needing_it(session=db, agent_ids=[agent.id]) == 0


def test_a_new_version_of_a_check_runs_over_stored_calls_once(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _agent(db)
    [call] = _stored_unchecked(db, agent, 1)
    check_calls_needing_it(session=db, agent_ids=[agent.id])
    assert _runs(db, call) == [(CHECK, 1, CheckOutcome.RAN)]

    monkeypatch.setattr(
        engine, "CHECKS", (dataclasses.replace(TOOL_CALL_FAILED, version=2),)
    )

    assert check_calls_needing_it(session=db, agent_ids=[agent.id]) == 1
    assert _runs(db, call) == [(CHECK, 2, CheckOutcome.RAN)]
    assert check_calls_needing_it(session=db, agent_ids=[agent.id]) == 0


def test_a_call_a_check_broke_on_is_checked_again_by_its_fix(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _agent(db)
    [call] = _stored_unchecked(db, agent, 1)

    def breaks(_: CheckInput) -> list[Raised]:
        raise RuntimeError("a bug in the check")

    monkeypatch.setattr(
        engine, "CHECKS", (dataclasses.replace(TOOL_CALL_FAILED, run=breaks),)
    )
    check_calls_needing_it(session=db, agent_ids=[agent.id])
    assert _runs(db, call) == [(CHECK, 1, CheckOutcome.BROKE)]
    # Broken, but checked by this version: not picked up again.
    assert check_calls_needing_it(session=db, agent_ids=[agent.id]) == 0

    monkeypatch.setattr(
        engine, "CHECKS", (dataclasses.replace(TOOL_CALL_FAILED, version=2),)
    )

    assert check_calls_needing_it(session=db, agent_ids=[agent.id]) == 1
    assert _runs(db, call) == [(CHECK, 2, CheckOutcome.RAN)]


def test_a_call_that_cannot_be_checked_at_all_is_not_picked_up_forever(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = _agent(db)
    [call] = _stored_unchecked(db, agent, 1)
    check_calls_needing_it(session=db, agent_ids=[agent.id])
    monkeypatch.setattr(
        engine, "CHECKS", (dataclasses.replace(TOOL_CALL_FAILED, version=2),)
    )

    def fails(**_: object) -> None:
        raise RuntimeError("the database went away")

    monkeypatch.setattr(engine, "check_call", fails)

    assert check_calls_needing_it(session=db, agent_ids=[agent.id]) == 0
    # Recorded as broke by version 2, replacing version 1's run.
    assert _runs(db, call) == [(CHECK, 2, CheckOutcome.BROKE)]
    assert (
        crud.calls_needing_checks(
            session=db, agent_ids=[agent.id], versions={CHECK: 2}, limit=10
        )
        == []
    )


def test_a_pass_stops_at_its_limit_and_the_rest_wait(db: Session) -> None:
    agent = _agent(db)
    calls = _stored_unchecked(db, agent, 3)

    assert check_calls_needing_it(session=db, agent_ids=[agent.id], limit=2) == 2
    # Newest first: the oldest waits for the next pass.
    assert _runs(db, calls[0]) == []
    assert check_calls_needing_it(session=db, agent_ids=[agent.id], limit=2) == 1


def test_a_pass_stops_at_its_deadline(db: Session) -> None:
    agent = _agent(db)
    _stored_unchecked(db, agent, 2)

    assert check_calls_needing_it(session=db, agent_ids=[agent.id], deadline=0.0) == 0


@respx.mock
async def test_the_minute_pull_checks_calls_that_need_it(db: Session) -> None:
    agent = _agent(db)
    calls = _stored_unchecked(db, agent, 2)

    run = await run_pull(session=db)

    assert run.calls_checked >= 2
    for call in calls:
        assert _runs(db, call) == [(CHECK, 1, CheckOutcome.RAN)]


@respx.mock
async def test_an_empty_backlog_is_not_looked_at_again_until_checks_change(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    looked: list[int] = []
    real = call_pull.check_calls_needing_it

    def counting(**kwargs: object) -> int:
        looked.append(1)
        return real(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(call_pull, "check_calls_needing_it", counting)
    agent = _agent(db)
    _stored_unchecked(db, agent, 1)

    await run_pull(session=db)  # checks the call
    await run_pull(session=db)  # finds nothing: remembered
    await run_pull(session=db)  # not looked at
    assert len(looked) == 2

    monkeypatch.setattr(
        engine, "CHECKS", (dataclasses.replace(TOOL_CALL_FAILED, version=2),)
    )
    await run_pull(session=db)  # the checks changed: looked at again
    assert len(looked) == 3
