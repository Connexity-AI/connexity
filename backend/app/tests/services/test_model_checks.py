"""Model checks: a classifier (Jev, faked) asked once per call and check version, its
answer stored, turned into findings by code, within the daily budget. Calls are
invented; no model is called."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Agent, Call, CallCheck, Finding, UserCreate
from app.models.enums import (
    CheckKind,
    CheckOutcome,
    ModelAnswerStatus,
    Platform,
    ToolCallStatus,
)
from app.models.model_answer import ModelAnswer
from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services import jev
from app.services.checks import engine
from app.services.checks.base import CheckInput
from app.services.checks.model import action_claimed
from app.services.checks.model.action_claimed import ACTION_CLAIMED_WITHOUT_TOOL
from app.services.checks.model_checks import answer_model_checks
from app.services.jev import ChoiceAnswer, Decision, JevError, Usage
from app.tests.utils.utils import random_email, random_lower_string

CHECK = ACTION_CLAIMED_WITHOUT_TOOL
CHECKS = {CHECK.type: CHECK}
NOON = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _trace(*tools: ToolCallEvent, said: str = "Done, I've cancelled it.") -> Trace:
    return Trace(
        provider="invented",
        external_id=f"call-{uuid.uuid4().hex[:8]}",
        started_at=NOON,
        reports_tool_calls=True,
        events=[
            UtteranceEvent(id="c1", speaker="caller", text="Cancel my visit"),
            *tools,
            UtteranceEvent(id="a1", speaker="agent", text=said),
            UtteranceEvent(id="a2", speaker="agent", text="Anything else?"),
        ],
    )


def _answer(claims: dict[str, tuple[str, float]]) -> dict[str, object]:
    return {
        "model": "jev-1.14.0",
        "turns": 2,
        "claims": {
            event_id: {"action": action, "probability": p}
            for event_id, (action, p) in claims.items()
        },
    }


def _run(trace: Trace, claims: dict[str, tuple[str, float]]) -> list[tuple]:
    raised = CHECK.run(CheckInput(trace=trace, executions=[], answer=_answer(claims)))
    return [(r.event_ids, r.detail and r.detail["why"]) for r in raised]


# ── The check's code, on a stored answer ──────────────────────────


def test_a_claim_with_no_tool_call_is_a_finding_on_that_turn() -> None:
    assert _run(_trace(), {"a1": ("cancelled", 0.98)}) == [(("a1",), "no_tool_call")]


def test_a_claim_backed_by_a_tool_call_that_worked_is_not() -> None:
    tool = ToolCallEvent(id="t1", name="cancel_appointment", status=ToolCallStatus.OK)
    assert _run(_trace(tool), {"a1": ("cancelled", 0.98)}) == []


def test_a_claim_whose_tool_failed_points_at_the_tool_too() -> None:
    tool = ToolCallEvent(
        id="t1", name="cancel_appointment", status=ToolCallStatus.ERROR
    )
    assert _run(_trace(tool), {"a1": ("cancelled", 0.98)}) == [
        (("a1", "t1"), "tool_failed")
    ]


def test_a_tool_that_cannot_do_it_does_not_back_it() -> None:
    lookup = ToolCallEvent(
        id="t1", name="get_available_slots", status=ToolCallStatus.OK
    )
    assert _run(_trace(lookup), {"a1": ("booked", 0.9)}) == [(("a1",), "no_tool_call")]
    assert _run(_trace(lookup), {"a1": ("looked_up", 0.9)}) == []


def test_low_probability_and_unknown_turns_are_ignored() -> None:
    assert _run(_trace(), {"a1": ("cancelled", 0.4), "gone": ("moved", 0.99)}) == []


# ── Asking Jev ────────────────────────────────────────────────────


def _decision(choice: str, p: float = 0.97) -> Decision:
    rest = (1 - p) / 5
    probabilities = {name: rest for name in ("none", *action_claimed.ACTIONS)}
    probabilities[choice] = p
    return Decision(
        model="jev-1.14.0",
        answers={
            "claim": ChoiceAnswer(
                type="choice", choice=choice, confidence=p, probabilities=probabilities
            )
        },
        usage=Usage(input_tokens=1000, output_tokens=2),
    )


class FakeJev:
    def __init__(self, labels: dict[str, str] | None = None) -> None:
        # Agent turn text to label; anything else is "none".
        self.labels = labels or {"Done, I've cancelled it.": "cancelled"}
        self.requests = 0
        self.fail = False

    async def decide(self, state: dict[str, str], questions: object) -> Decision:
        self.requests += 1
        if self.fail:
            raise JevError("Jev answered 529: overloaded", status=529)
        return _decision(self.labels.get(state["agent_turn"], "none"))


@pytest.fixture
def fake_jev(monkeypatch: pytest.MonkeyPatch) -> FakeJev:
    fake = FakeJev()
    monkeypatch.setattr(jev, "decide", fake.decide)
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", "test-key")
    return fake


async def test_ask_labels_each_agent_turn_and_keeps_only_claims(
    fake_jev: FakeJev,
) -> None:
    reply = await CHECK.ask(_trace(), None)
    assert fake_jev.requests == 2
    assert reply.answer == {
        "model": "jev-1.14.0",
        "turns": 2,
        "claims": {"a1": {"action": "cancelled", "probability": 0.97}},
    }
    assert reply.requests == 2
    assert reply.cost_usd == pytest.approx(
        2 * 1000 * settings.JEV_USD_PER_MILLION_INPUT / 1e6
    )


async def test_a_call_with_no_agent_turn_asks_nothing(fake_jev: FakeJev) -> None:
    trace = Trace(
        provider="invented",
        external_id="silent",
        started_at=NOON,
        events=[UtteranceEvent(id="c1", speaker="caller", text="Hello?")],
    )
    reply = await CHECK.ask(trace, None)
    assert fake_jev.requests == 0
    assert reply.answer == {"model": settings.JEV_MODEL, "turns": 0, "claims": {}}


# ── Stored, checked, re-checked ───────────────────────────────────


@pytest.fixture
def agent(db: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[Agent, None, None]:
    monkeypatch.setattr(engine, "CHECKS", (CHECK,))
    monkeypatch.setattr(settings, "MODEL_CHECKS_DAILY_BUDGET_USD", 1.0)
    db.execute(delete(ModelAnswer))
    db.commit()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    agent = Agent(
        name="Invented",
        company_id=user.company_id,
        platform=Platform.RETELL,
        platform_agent_id=f"agent_{uuid.uuid4().hex[:8]}",
        created_by=user.id,
    )
    db.add(agent)
    db.commit()
    yield agent


def _stored(db: Session, agent: Agent, *tools: ToolCallEvent) -> Call:
    stored = crud.store_trace(
        session=db, trace=_trace(*tools), agent_id=agent.id, company_id=agent.company_id
    )
    db.commit()
    engine.check_call(session=db, call=stored.call)
    return stored.call


def _outcome(db: Session, call: Call) -> tuple[CheckOutcome, str | None]:
    db.expire_all()
    row = db.get(CallCheck, (call.id, CHECK.type))
    assert row is not None
    return row.outcome, row.missing


def _findings(db: Session, call: Call) -> list[Finding]:
    db.expire_all()
    return list(db.exec(select(Finding).where(Finding.call_id == call.id)).all())


async def test_a_new_call_waits_then_gets_its_finding(
    db: Session, agent: Agent, fake_jev: FakeJev
) -> None:
    call = _stored(db, agent)
    assert _outcome(db, call) == (CheckOutcome.PENDING, None)
    assert _findings(db, call) == []

    result = await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)

    assert (result.answered, result.failed) == (1, 0)
    assert _outcome(db, call) == (CheckOutcome.RAN, None)
    (finding,) = _findings(db, call)
    assert finding.kind is CheckKind.CLASSIFIER
    assert finding.event_keys == ["a1"]
    assert finding.detail == {
        "action": "cancelled",
        "probability": 0.97,
        "why": "no_tool_call",
        "model": "jev-1.14.0",
    }
    stored = db.exec(select(ModelAnswer).where(ModelAnswer.call_id == call.id)).one()
    assert (stored.status, stored.requests, stored.model) == (
        ModelAnswerStatus.OK,
        2,
        "jev-1.14.0",
    )


async def test_checking_again_asks_nothing_and_changes_nothing(
    db: Session, agent: Agent, fake_jev: FakeJev
) -> None:
    call = _stored(db, agent)
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)
    asked = fake_jev.requests
    first = [f.id for f in _findings(db, call)]

    engine.check_call(session=db, call=call)
    again = await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)

    assert fake_jev.requests == asked
    assert again.answered == 0
    assert [f.id for f in _findings(db, call)] == first


async def test_a_backed_claim_gets_no_finding(
    db: Session, agent: Agent, fake_jev: FakeJev
) -> None:
    tool = ToolCallEvent(id="t1", name="cancel_appointment", status=ToolCallStatus.OK)
    call = _stored(db, agent, tool)
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)
    assert _outcome(db, call) == (CheckOutcome.RAN, None)
    assert _findings(db, call) == []


async def test_a_failing_model_is_retried_then_recorded_as_broke(
    db: Session, agent: Agent, fake_jev: FakeJev
) -> None:
    fake_jev.fail = True
    call = _stored(db, agent)
    for _ in range(settings.MODEL_CHECK_MAX_ATTEMPTS - 1):
        result = await answer_model_checks(
            session=db, agent_ids=[agent.id], checks=CHECKS
        )
        assert result.failed == 1
        assert _outcome(db, call) == (CheckOutcome.PENDING, None)

    await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)

    assert _outcome(db, call) == (CheckOutcome.BROKE, None)
    assert _findings(db, call) == []
    stored = db.exec(select(ModelAnswer).where(ModelAnswer.call_id == call.id)).one()
    assert stored.status is ModelAnswerStatus.FAILED
    assert stored.attempts == settings.MODEL_CHECK_MAX_ATTEMPTS
    # The error's type and status, never what the provider said.
    assert stored.error == "JevError 529"


async def test_the_daily_budget_stops_asking_and_the_call_waits(
    db: Session, agent: Agent, fake_jev: FakeJev, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "MODEL_CHECKS_DAILY_BUDGET_USD", 0.0)
    call = _stored(db, agent)

    result = await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)

    assert result.budget_reached
    assert fake_jev.requests == 0
    assert _outcome(db, call) == (CheckOutcome.PENDING, None)


async def test_no_key_skips_the_check(
    db: Session, agent: Agent, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    call = _stored(db, agent)
    assert _outcome(db, call) == (CheckOutcome.SKIPPED, "TYPESAFE_API_KEY")


async def test_calls_skipped_for_a_missing_key_are_checked_once_it_is_added(
    db: Session, agent: Agent, fake_jev: FakeJev, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    call = _stored(db, agent)
    assert _outcome(db, call) == (CheckOutcome.SKIPPED, "TYPESAFE_API_KEY")

    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", "test-key")
    result = await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)

    assert result.answered == 1
    assert _outcome(db, call) == (CheckOutcome.RAN, None)
    assert len(_findings(db, call)) == 1


async def test_a_pass_out_of_time_asks_nothing_and_the_call_waits(
    db: Session, agent: Agent, fake_jev: FakeJev
) -> None:
    call = _stored(db, agent)
    result = await answer_model_checks(
        session=db, agent_ids=[agent.id], checks=CHECKS, deadline=0.0
    )
    assert (result.answered, result.left) == (0, 1)
    assert fake_jev.requests == 0
    assert _outcome(db, call) == (CheckOutcome.PENDING, None)
