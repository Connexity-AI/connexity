"""The spec check: each real call judged against its agent's spec by a classifier (Jev,
faked) and the LLM step (faked), on invented agents and calls (plans
`plans/2026-11-26-spec-check.md` and `plans/2026-11-27-llm-step.md`)."""

import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from litellm.exceptions import Timeout as LLMTimeout
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Agent, Call, CallCheck, Finding, Spec
from app.models.check import Issue
from app.models.enums import (
    CheckKind,
    CheckMode,
    CheckOutcome,
    DecisionKind,
    FindingEffect,
    ModelAnswerStatus,
    SpecCheckType,
    TraceSource,
)
from app.models.trace import Trace, UtteranceEvent
from app.services import jev
from app.services.call_screen import call_screen
from app.services.checks.base import CheckInput
from app.services.checks.engine import check_call, check_calls_needing_it
from app.services.checks.model import spec_rule
from app.services.checks.model.spec_rule import (
    SKIP_BEFORE,
    SKIP_NO_SPEC,
    SKIP_NOT_REAL,
    SPEC_CHECK_TYPE,
    SPEC_RULE_BROKEN,
    judging_from,
)
from app.services.checks.model_checks import answer_model_checks
from app.services.clarification import AnswerDraft, QuestionDraft
from app.services.grading import NOT_GRADED_REASON
from app.services.issue_page import issue_page
from app.services.jev import Decision, JevError, Usage, YesNoAnswer
from app.services.llm import LLMCallConfig, LLMMessage, LLMResponse
from app.services.spec import write_agent_spec
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,
)
from app.tests.api.routes.test_spec_api import _catalogue
from app.tests.services.test_clarifications import (
    ASSISTANT,
    RULES,
    _answer,
    _raise,
    _ready,
)

HOURS, PRICE = RULES[0].text, RULES[1].text
CHECKS = {SPEC_RULE_BROKEN.type: SPEC_RULE_BROKEN}


class FakeJev:
    """Answers each rule's question with the probability set for its text."""

    def __init__(self) -> None:
        self.scores = {HOURS: 0.92, PRICE: 0.5}
        self.requests: list[tuple[dict[str, object], list[str]]] = []
        self.fail = False

    async def decide(self, state: dict[str, object], questions: dict) -> Decision:  # type: ignore[type-arg]
        if self.fail:
            raise JevError("Jev answered 529: overloaded", status=529)
        self.requests.append((state, [q.instructions for q in questions.values()]))
        answers = {}
        for name, question in questions.items():
            p = next(
                (v for t, v in self.scores.items() if t in question.instructions), 0
            )
            answers[name] = YesNoAnswer(type="noul", noul=p)
        return Decision(
            model="jev-1.14.0",
            answers=answers,
            usage=Usage(input_tokens=2000, output_tokens=0),
        )


class FakeLLM:
    """The LLM step's model: answers each request by the rule it ends with.

    ``verdicts`` maps a rule's text to (outcome, which lines by position in the call,
    with -1 the last). A rule not in it did not come up.
    """

    def __init__(self) -> None:
        self.verdicts: dict[str, tuple[str, list[int]]] = {}
        self.requests: list[tuple[str, str]] = []
        self.reply: str | None = None  # a raw answer, for the malformed cases
        self.error: Exception | None = None
        self.delay = 0.0

    async def call_llm(
        self, messages: list[LLMMessage], config: LLMCallConfig | None = None
    ) -> LLMResponse:
        system, user = (m.content or "" for m in messages)
        self.requests.append((system, user))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        ids = re.findall(r"^\[([^\]]+)\]", user, re.MULTILINE)
        rule = user.rsplit("## The rule", 1)[1]
        outcome, lines = next(
            (v for t, v in self.verdicts.items() if t in rule),
            ("did_not_come_up", []),
        )
        content = (
            self.reply
            if self.reply is not None
            else json.dumps(
                {
                    "reason": f"Invented reason: {outcome}",
                    "event_ids": [ids[i] for i in lines] + ["not-in-the-call"],
                    "outcome": outcome,
                }
            )
        )
        assert config is not None and config.model == settings.SPEC_LLM_MODEL
        return LLMResponse(
            content=content,
            model=settings.SPEC_LLM_MODEL,
            usage={"prompt_tokens": 800, "completion_tokens": 60},
        )


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLM:
    """Never a real model request from these tests."""
    fake = FakeLLM()
    monkeypatch.setattr("app.services.checks.judge.call_llm", fake.call_llm)
    return fake


@pytest.fixture
def fake_jev(monkeypatch: pytest.MonkeyPatch) -> FakeJev:
    fake = FakeJev()
    monkeypatch.setattr(jev, "decide", fake.decide)
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", "test-key")
    return fake


def _outcome(db: Session, call_id: object) -> tuple[CheckOutcome, str | None]:
    db.expire_all()
    row = db.get(CallCheck, (call_id, SPEC_CHECK_TYPE))
    assert row is not None
    return row.outcome, row.missing


def _spec_findings(db: Session, call_id: object) -> list[Finding]:
    db.expire_all()
    return list(
        db.exec(
            select(Finding).where(
                Finding.call_id == call_id, Finding.check_type == SPEC_CHECK_TYPE
            )
        ).all()
    )


async def _judge(db: Session, agent: Agent) -> None:
    """The scheduled pass: check what needs it, then ask the model."""
    check_calls_needing_it(session=db, agent_ids=[agent.id])
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)


def _rule_key(db: Session, agent: Agent, text: str) -> str:
    spec = crud.latest_spec(session=db, agent_id=agent.id)
    assert spec is not None
    return next(
        r.key for r in crud.spec_rules(session=db, spec_id=spec.id) if r.text == text
    )


# ── The check's code, on a stored answer ──────────────────────────


def _stored(**rules: tuple[float, str, bool]) -> dict[str, object]:
    return {
        "model": "jev-1.14.0",
        "spec_version": 3,
        "rules": {
            key: {
                "probability": p,
                "check": check,
                "critical": critical,
                "category": "booking",
                "text": f"Rule {key}",
                "fingerprint": "f",
            }
            for key, (p, check, critical) in rules.items()
        },
    }


def test_a_classifier_rule_at_the_bar_is_a_finding_on_the_whole_call() -> None:
    trace = Trace(
        provider="invented",
        external_id="c",
        started_at=datetime.now(UTC),
        events=[UtteranceEvent(id="a1", speaker="agent", text="Hi")],
    )
    raised = SPEC_RULE_BROKEN.run(
        CheckInput(
            trace=trace,
            executions=[],
            answer=_stored(
                k1=(0.8, "classifier", True),
                k2=(0.79, "classifier", False),
                k3=(0.97, "classifier_then_llm", False),  # held for the LLM step
                k4=(0.85, "classifier", False),
            ),
        )
    )

    assert [(r.key, r.event_ids, r.flags_only) for r in raised] == [
        ("k1", (), False),
        ("k4", (), True),
    ]
    first = raised[0]
    assert (first.category, first.subject) == ("booking", "Rule k1")
    assert first.detail == {
        "rule_text": "Rule k1",
        "probability": 0.8,
        "model": "jev-1.14.0",
        "spec_version": 3,
    }


def test_judging_starts_at_the_release_or_30_days_before_a_later_first_spec() -> None:
    released = datetime(2026, 11, 27, tzinfo=UTC)
    early = released - timedelta(days=60)
    late = released + timedelta(days=5)
    assert judging_from(early, released) == (released, released)
    assert judging_from(late, released) == (late - timedelta(days=30), late)


# ── On stored calls ───────────────────────────────────────────────


async def test_a_first_spec_judges_its_recent_calls_once(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, calls = _ready(db)
    hours = _rule_key(db, agent, HOURS)

    await _judge(db, agent)

    for call_id in calls:
        assert _outcome(db, call_id) == (CheckOutcome.RAN, None)
        (finding,) = _spec_findings(db, call_id)
        assert (finding.key, finding.event_keys) == (hours, [])
        assert finding.effect is FindingEffect.FLAGS  # not a critical rule
        assert finding.retroactive  # before the first spec: counts for nothing
        assert finding.detail is not None and finding.detail["rule_text"] == HOURS
    issue = db.exec(
        select(Issue).where(
            Issue.agent_id == agent.id, Issue.check_type == SPEC_CHECK_TYPE
        )
    ).one()
    assert (issue.key, issue.subject) == (hours, HOURS)
    category = crud.categories_by_id(session=db)[issue.category_id]
    assert category.key == "booking"
    # Two calls, each one request: the rules name no input.
    assert len(fake_jev.requests) == 2
    assert all(set(state) == {"call"} for state, _ in fake_jev.requests)

    # Judged once: checking again asks nothing.
    await _judge(db, agent)
    assert len(fake_jev.requests) == 2


async def test_a_critical_rule_fails_the_call_and_flags_mode_only_flags(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, _ = _ready(db)
    hours = _rule_key(db, agent, HOURS)
    spec = write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(key=hours, critical=True),
            RULES[1]._replace(key=_rule_key(db, agent, PRICE)),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    assert spec is not None
    # Calls after the first spec count (they start a moment from now).
    failing = _call(db, agent, _booking(1, FULL), days_ago=-0.01)
    await _judge(db, agent)
    (finding,) = _spec_findings(db, failing)
    assert finding.effect is FindingEffect.FAILS
    assert not finding.retroactive

    # Set to Flags before the next call: nothing fails.
    record = crud.record_decision(
        session=db,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind=DecisionKind.CHECK_SETTING,
        subject=SPEC_CHECK_TYPE,
        old_value=CheckMode.FAILS.value,
        new_value=CheckMode.FLAGS.value,
        reason="Trying it out",
        decided_by=user,
    )
    record.created_at = datetime.now(UTC) - timedelta(hours=1)
    db.add(record)
    db.commit()
    flagged = _call(db, agent, _booking(1, FULL), days_ago=-0.02)
    await _judge(db, agent)
    (finding,) = _spec_findings(db, flagged)
    assert finding.effect is FindingEffect.FLAGS

    # Off: it does not run.
    record = crud.record_decision(
        session=db,
        agent_id=agent.id,
        company_id=agent.company_id,
        kind=DecisionKind.CHECK_SETTING,
        subject=SPEC_CHECK_TYPE,
        old_value=CheckMode.FLAGS.value,
        new_value=CheckMode.OFF.value,
        reason="Off for now",
        decided_by=user,
    )
    record.created_at = datetime.now(UTC) - timedelta(minutes=30)
    db.add(record)
    db.commit()
    off = _call(db, agent, _booking(1, FULL), days_ago=-0.03)
    assert _outcome(db, off) == (CheckOutcome.OFF, None)


async def test_rules_with_inputs_get_a_second_request_with_their_short_inputs(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, calls = _ready(db)
    for call in db.exec(select(Call).where(Call.agent_id == agent.id)).all():
        call.inputs = {
            "attempt_number": "1",
            "clinic_hours": "9 to 5",
            "previous_conversations": "Earlier call. "
            * 30,  # long: never to the classifier
        }
        db.add(call)
    db.commit()
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(
                key=_rule_key(db, agent, HOURS),
                inputs=["clinic_hours", "attempt_number"],
            ),
            RULES[1]._replace(
                key=_rule_key(db, agent, PRICE),
                inputs=["previous_conversations"],
                check=SpecCheckType.LLM,  # only the LLM step asks
            ),
            RULES[0]._replace(text="Greet the caller by the clinic's name"),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    new = _call(db, agent, _booking(1, FULL), days_ago=0.01)
    new_row = db.get(Call, new)
    assert new_row is not None
    new_row.inputs = {"attempt_number": "2", "clinic_hours": "9 to 5", "lead_id": "x"}
    db.add(new_row)
    db.commit()
    fake_jev.requests.clear()

    check_call(session=db, call=new_row, checks=[SPEC_RULE_BROKEN])
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)

    states = [state for state, _ in fake_jev.requests]
    assert {"call"} in [set(s) for s in states]
    named = next(s for s in states if "given" in s)
    assert named["given"] == {"attempt_number": "2", "clinic_hours": "9 to 5"}
    asked = [text for _, texts in fake_jev.requests for text in texts]
    assert not any(PRICE in t for t in asked)  # an llm rule is not asked
    assert sum(HOURS in t for t in asked) == 1


async def test_a_later_change_to_a_rule_judges_no_old_call_again(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, calls = _ready(db)
    hours = _rule_key(db, agent, HOURS)
    await _judge(db, agent)
    before = len(fake_jev.requests)

    # The rule's text changes: calls already judged keep their answer.
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(key=hours, text="Never book outside 9 to 5"),
            RULES[1]._replace(key=_rule_key(db, agent, PRICE)),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    for call_id in calls:
        row = db.get(Call, call_id)
        assert row is not None
        check_call(session=db, call=row, checks=[SPEC_RULE_BROKEN])
        (finding,) = _spec_findings(db, call_id)
        assert finding.detail is not None and finding.detail["rule_text"] == HOURS
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=CHECKS)
    assert len(fake_jev.requests) == before


async def test_calls_it_does_not_judge_are_skipped_with_the_reason(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, _ = _ready(db, version=7)
    short = _call(db, agent, days_ago=0.01)
    row = db.get(Call, short)
    assert row is not None
    row.agent_words = 3
    db.add(row)
    db.commit()
    check_call(session=db, call=row, checks=[SPEC_RULE_BROKEN])
    assert _outcome(db, short) == (CheckOutcome.SKIPPED, NOT_GRADED_REASON)

    # Older than the version-7 calls, so the agent does not adopt a spec for it.
    older = _call(db, agent, _booking(1, FULL), days_ago=3, version=5)
    assert _outcome(db, older) == (CheckOutcome.SKIPPED, SKIP_NO_SPEC)

    test_call = _call(db, agent, _booking(1, FULL), days_ago=0.01)
    row = db.get(Call, test_call)
    assert row is not None
    row.source = TraceSource.TEST_CALL
    db.add(row)
    db.commit()
    check_call(session=db, call=row, checks=[SPEC_RULE_BROKEN])
    assert _outcome(db, test_call) == (CheckOutcome.SKIPPED, SKIP_NOT_REAL)

    other = _agent(db, user, "No spec yet")
    _catalogue(db, other, "7")
    unspecced = _call(db, other, _booking(1, FULL), days_ago=0.01)
    assert _outcome(db, unspecced) == (CheckOutcome.SKIPPED, SKIP_NO_SPEC)


def test_a_spec_written_before_the_release_judges_only_calls_after_it(
    db: Session,
) -> None:
    _, agent, calls = _ready(db)
    for spec in db.exec(select(Spec).where(Spec.agent_id == agent.id)).all():
        spec.created_at = datetime.now(UTC) - timedelta(days=90)
        db.add(spec)
    db.commit()
    row = db.get(Call, calls[0])  # started a day or two ago
    assert row is not None
    released = datetime.now(UTC) - timedelta(hours=1)

    assert spec_rule._applies(db, row, released).skip == SKIP_BEFORE
    later = spec_rule._applies(db, row, released - timedelta(days=10))
    assert later.skip is None
    assert later.counts_from == released - timedelta(days=10)


async def test_a_failed_request_is_tried_again_and_nothing_is_raised(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, calls = _ready(db)
    fake_jev.fail = True
    await _judge(db, agent)
    assert _outcome(db, calls[0]) == (CheckOutcome.PENDING, None)
    assert _spec_findings(db, calls[0]) == []


async def test_screens_and_mcp_show_the_rule_with_no_moment(
    client: TestClient, db: Session, fake_jev: FakeJev
) -> None:
    user, agent, calls = _ready(db)
    hours = _rule_key(db, agent, HOURS)
    (clarification,) = _raise(
        db,
        user,
        agent,
        QuestionDraft(
            question="Is a slot booked for a holiday outside opening hours?",
            answers=[
                AnswerDraft("Yes", "A holiday counts as outside opening hours"),
                AnswerDraft("No", "A holiday does not change opening hours"),
            ],
            rule_key=hours,
        ),
    )
    _answer(db, user, (clarification.id, "A"))
    await _judge(db, agent)
    asked = [text for _, texts in fake_jev.requests for text in texts]
    assert any("Note on this rule: A holiday counts as outside" in t for t in asked)

    row = db.get(Call, calls[0])
    assert row is not None
    screen = call_screen(session=db, call=row)
    assert screen is not None
    (spec_finding,) = (f for f in screen.findings if f.probability is not None)
    assert (spec_finding.text, spec_finding.probability, spec_finding.entry_index) == (
        HOURS,
        0.92,
        None,
    )
    issue = db.exec(
        select(Issue).where(
            Issue.agent_id == agent.id, Issue.check_type == SPEC_CHECK_TYPE
        )
    ).one()
    assert spec_finding.issue_id == issue.id
    page = issue_page(
        session=db, issue=issue, summary=crud.summarise_issue(session=db, issue=issue)
    )
    assert (page.title, page.whole_call) == (HOURS, True)
    assert [c.sentence for c in page.clarifications] == [
        "A holiday counts as outside opening hours"
    ]
    assert {(c.moment, c.probability) for c in page.affected_calls} == {(None, 0.92)}

    answer = client.get(
        f"{settings.API_V1_STR}/mcp/workspaces/{user.company_id}/issues/{issue.id}",
        headers=_headers(user),
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["data"]["whole_call"] is True
    assert any(f"`rule_key` `{hours}`" in s for s in body["next_steps"])
    assert any("no moment and no reason" in r for r in body["rules"])
    call = client.get(
        f"{settings.API_V1_STR}/mcp/workspaces/{user.company_id}/calls/{calls[0]}",
        headers=_headers(user),
    ).json()
    assert any(f["probability"] == 0.92 for f in call["data"]["findings"])
    assert any("with no moment (`whole_call`)" in s for s in call["next_steps"])
    listed = client.get(
        f"{settings.API_V1_STR}/mcp/workspaces/{user.company_id}/issues",
        headers=_headers(user),
    ).json()
    titles = [i["title"] for i in listed["data"]["issues"]]
    assert HOURS in titles
    assert spec_rule.BAR == 0.8


async def test_retyping_every_rule_keeps_the_findings_of_calls_already_judged(
    db: Session, fake_jev: FakeJev
) -> None:
    user, agent, calls = _ready(db)
    await _judge(db, agent)
    assert len(_spec_findings(db, calls[0])) == 1
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(key=_rule_key(db, agent, HOURS), check=SpecCheckType.LLM),
            RULES[1]._replace(key=_rule_key(db, agent, PRICE), check=SpecCheckType.LLM),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    row = db.get(Call, calls[0])
    assert row is not None
    check_call(session=db, call=row)

    assert _outcome(db, calls[0]) == (CheckOutcome.RAN, None)
    assert len(_spec_findings(db, calls[0])) == 1


# ── The LLM step (105.16) ─────────────────────────────────────────


def _retype(
    db: Session,
    user: Any,
    agent: Agent,
    hours: SpecCheckType,
    price: SpecCheckType,
    price_inputs: list[str] | None = None,
) -> None:
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(key=_rule_key(db, agent, HOURS), check=hours),
            RULES[1]._replace(
                key=_rule_key(db, agent, PRICE), check=price, inputs=price_inputs
            ),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )


def _ids(db: Session, call_id: object) -> list[str]:
    """The ids of the call's lines, as the LLM step reads them."""
    row = db.get(Call, call_id)
    assert row is not None
    trace = crud.get_trace(session=db, call=row)
    assert trace is not None
    return re.findall(r"^\[([^\]]+)\]", spec_rule.render(trace), re.MULTILINE)


def _answer_of(db: Session, call_id: object) -> dict[str, Any]:
    stored = crud.get_model_answers(
        session=db,
        call_id=call_id,
        versions={SPEC_CHECK_TYPE: SPEC_RULE_BROKEN.version},
    )[SPEC_CHECK_TYPE]
    assert isinstance(stored.answer, dict)
    return stored.answer


async def test_a_flag_the_llm_confirms_has_its_moment_and_reason(
    client: TestClient, db: Session, fake_jev: FakeJev, fake_llm: FakeLLM
) -> None:
    user, agent, calls = _ready(db)
    _retype(
        db, user, agent, SpecCheckType.CLASSIFIER_THEN_LLM, SpecCheckType.CLASSIFIER
    )
    fake_llm.verdicts = {HOURS: ("failed", [0, -1])}

    await _judge(db, agent)

    hours = _rule_key(db, agent, HOURS)
    for call_id in calls:
        ids = _ids(db, call_id)
        (finding,) = _spec_findings(db, call_id)
        # The id the LLM made up is dropped; the moment is in the call's order.
        assert ids[0] != ids[-1]
        assert (finding.key, finding.event_keys) == (hours, [ids[0], ids[-1]])
        assert finding.kind.value == "classifier"
        assert finding.detail == {
            "rule_text": HOURS,
            "spec_version": 2,
            "reason": "Invented reason: failed",
            "probability": 0.92,
            "model": "jev-1.14.0",
            "confirmed_by": settings.SPEC_LLM_MODEL,
        }
    # One LLM request per call: the flag. The price rule scored 0.5 and is not sent.
    assert len(fake_llm.requests) == len(calls)
    system, user_text = fake_llm.requests[0]
    assert user_text.index("## The call") < user_text.index("## The rule")
    assert user_text.rstrip().endswith(HOURS)
    assert PRICE not in user_text and "0.92" not in user_text
    assert "prompt" not in system.lower()

    row = db.get(Call, calls[0])
    assert row is not None
    screen = call_screen(session=db, call=row)
    assert screen is not None
    (seen,) = (f for f in screen.findings if f.model is not None)
    assert (seen.whole_call, seen.reason, seen.confirmed_by, seen.probability) == (
        False,
        "Invented reason: failed",
        settings.SPEC_LLM_MODEL,
        0.92,
    )
    assert seen.entry_index == max(seen.entry_indexes)
    assert len(seen.entry_indexes) == 2

    issue = db.exec(
        select(Issue).where(
            Issue.agent_id == agent.id, Issue.check_type == SPEC_CHECK_TYPE
        )
    ).one()
    page = issue_page(
        session=db, issue=issue, summary=crud.summarise_issue(session=db, issue=issue)
    )
    assert page.found_how == "confirmed"
    assert all(
        c.moment is not None and c.reason == "Invented reason: failed"
        for c in page.affected_calls
    )

    call = client.get(
        f"{settings.API_V1_STR}/mcp/workspaces/{user.company_id}/calls/{calls[0]}",
        headers=_headers(user),
    ).json()
    (mcp_finding,) = (f for f in call["data"]["findings"] if f["model"])
    assert mcp_finding["reason"] == "Invented reason: failed"
    assert mcp_finding["confirmed_by"] == settings.SPEC_LLM_MODEL
    assert any("`entry_indexes`" in s for s in call["next_steps"])
    body = client.get(
        f"{settings.API_V1_STR}/mcp/workspaces/{user.company_id}/issues/{issue.id}",
        headers=_headers(user),
    ).json()
    assert body["data"]["found_how"] == "confirmed"


async def test_a_flag_the_llm_dismisses_raises_nothing_and_is_stored(
    db: Session, fake_jev: FakeJev, fake_llm: FakeLLM
) -> None:
    user, agent, calls = _ready(db)
    _retype(
        db, user, agent, SpecCheckType.CLASSIFIER_THEN_LLM, SpecCheckType.CLASSIFIER
    )
    fake_llm.verdicts = {HOURS: ("passed", [1])}

    await _judge(db, agent)

    assert _outcome(db, calls[0]) == (CheckOutcome.RAN, None)
    assert _spec_findings(db, calls[0]) == []
    verdict = _answer_of(db, calls[0])["rules"][_rule_key(db, agent, HOURS)]["verdict"]
    assert (verdict["outcome"], verdict["reason"]) == (
        "passed",
        "Invented reason: passed",
    )


async def test_an_llm_rule_is_judged_alone_on_every_call_with_its_long_inputs(
    db: Session, fake_jev: FakeJev, fake_llm: FakeLLM
) -> None:
    user, agent, calls = _ready(db)
    history = "Earlier call about a cleaning. " * 10  # long: only the LLM step
    for call_id in calls:
        row = db.get(Call, call_id)
        assert row is not None
        row.inputs = {"previous_conversations": history, "attempt_number": "2"}
        db.add(row)
    db.commit()
    _retype(
        db,
        user,
        agent,
        SpecCheckType.CLASSIFIER_THEN_LLM,
        SpecCheckType.LLM,
        price_inputs=["previous_conversations"],
    )
    # Both rules broken at the same lines: two findings, told apart by rule.
    fake_llm.verdicts = {HOURS: ("failed", [1]), PRICE: ("failed", [1])}

    await _judge(db, agent)

    asked = [text for _, texts in fake_jev.requests for text in texts]
    assert not any(PRICE in t for t in asked)  # never the classifier
    price_requests = [u for _, u in fake_llm.requests if u.rstrip().endswith(PRICE)]
    assert len(price_requests) == len(calls)
    assert all(history.strip() in u for u in price_requests)
    assert all("attempt_number" not in u for u in price_requests)  # not named
    for call_id in calls:
        findings = {f.key: f for f in _spec_findings(db, call_id)}
        price = findings[_rule_key(db, agent, PRICE)]
        hours = findings[_rule_key(db, agent, HOURS)]
        assert price.event_keys == hours.event_keys == [_ids(db, call_id)[1]]
        assert price.kind.value == "judge"
        assert price.detail is not None
        assert "probability" not in price.detail
        assert price.detail["model"] == settings.SPEC_LLM_MODEL
        assert price.effect is FindingEffect.FLAGS


def test_a_verdict_naming_no_line_of_the_call_is_on_the_whole_call() -> None:
    trace = Trace(
        provider="invented",
        external_id="c",
        started_at=datetime.now(UTC),
        events=[UtteranceEvent(id="a1", speaker="agent", text="Hi")],
    )
    answer = _stored(k1=(0.9, "classifier_then_llm", True))
    rules: Any = answer["rules"]
    rules["k1"]["verdict"] = {
        "outcome": "failed",
        "reason": "Booked at 7:00",
        "event_ids": ["made-up"],
        "model": "claude-haiku-5-5",
    }
    rules["k2"] = {
        "probability": None,
        "check": "llm",
        "critical": False,
        "category": "booking",
        "text": "Rule k2",
        "fingerprint": "f",
        "verdict": {
            "outcome": "failed",
            "reason": "Said a price",
            "event_ids": ["a1"],
            "model": "claude-haiku-5-5",
        },
    }
    raised = SPEC_RULE_BROKEN.run(CheckInput(trace=trace, executions=[], answer=answer))
    assert [(r.key, r.event_ids, r.flags_only, r.kind) for r in raised] == [
        ("k1", (), False, None),
        ("k2", ("a1",), True, CheckKind.JUDGE),
    ]
    assert raised[0].detail is not None
    assert raised[0].detail["confirmed_by"] == "claude-haiku-5-5"


async def test_a_call_version_1_judged_keeps_its_answer_and_is_not_asked_again(
    db: Session, fake_jev: FakeJev, fake_llm: FakeLLM
) -> None:
    user, agent, calls = _ready(db)
    hours, price = _rule_key(db, agent, HOURS), _rule_key(db, agent, PRICE)
    row = db.get(Call, calls[0])
    assert row is not None

    def rule(probability: float, check: str, text: str) -> dict[str, Any]:
        return {
            "probability": probability,
            "check": check,
            "critical": False,
            "category": "booking",
            "text": text,
            "fingerprint": "f",
        }

    crud.save_model_answer(
        session=db,
        call=row,
        check_type=SPEC_CHECK_TYPE,
        check_version=1,
        status=ModelAnswerStatus.OK,
        model="jev-1.14.0",
        answer={
            "model": "jev-1.14.0",
            "spec_version": 1,
            "rules": {
                hours: rule(0.92, "classifier", HOURS),
                price: rule(0.95, "classifier_then_llm", PRICE),
            },
        },
    )

    check_call(session=db, call=row, checks=[SPEC_RULE_BROKEN])

    # Version 2 read version 1's answer: ran, nothing left to ask about this call.
    assert _outcome(db, calls[0]) == (CheckOutcome.RAN, None)
    (finding,) = _spec_findings(db, calls[0])
    assert (finding.key, finding.event_keys, finding.check_version) == (hours, [], 2)
    waiting = crud.calls_waiting_for_models(
        session=db,
        versions={SPEC_CHECK_TYPE: SPEC_RULE_BROKEN.version},
        agent_ids=[agent.id],
        limit=10,
    )
    assert calls[0] not in {c.id for c, _ in waiting}  # the held flag stays held


async def test_without_the_llm_key_the_classifier_part_still_counts(
    db: Session,
    fake_jev: FakeJev,
    fake_llm: FakeLLM,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    user, agent, calls = _ready(db)
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(
                key=_rule_key(db, agent, HOURS), check=SpecCheckType.CLASSIFIER_THEN_LLM
            ),
            RULES[1]._replace(key=_rule_key(db, agent, PRICE)),
            RULES[0]._replace(text="Say the clinic's name first"),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    fake_jev.scores["Say the clinic's name first"] = 0.9

    await _judge(db, agent)

    assert fake_llm.requests == []
    (finding,) = _spec_findings(db, calls[0])
    assert finding.detail is not None
    assert finding.detail["rule_text"] == "Say the clinic's name first"
    assert _answer_of(db, calls[0])["llm_missing"] == "ANTHROPIC_API_KEY"


@pytest.mark.parametrize(
    "fault",
    ["timeout", "slow", "empty", "not json", "unknown verdict"],
)
async def test_a_failed_llm_request_fails_the_answer_and_raises_nothing(
    db: Session,
    fake_jev: FakeJev,
    fake_llm: FakeLLM,
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, agent, calls = _ready(db)
    _retype(
        db, user, agent, SpecCheckType.CLASSIFIER_THEN_LLM, SpecCheckType.CLASSIFIER
    )
    if fault == "timeout":
        fake_llm.error = LLMTimeout(
            message="timed out", model="claude-haiku-5-5", llm_provider="anthropic"
        )
    elif fault == "slow":
        # Slower than the step's own bound: a counted attempt, not the pass's time.
        monkeypatch.setattr(spec_rule, "_LLM_SECONDS", 0.01)
        fake_llm.delay = 0.2
    else:
        fake_llm.reply = {
            "empty": "",
            "not json": "The agent broke it.",
            "unknown verdict": '{"reason": "x", "event_ids": [], "outcome": "maybe"}',
        }[fault]

    await _judge(db, agent)

    assert _outcome(db, calls[0]) == (CheckOutcome.PENDING, None)
    assert _spec_findings(db, calls[0]) == []
    stored = crud.get_model_answers(
        session=db, call_id=calls[0], versions={SPEC_CHECK_TYPE: 2}
    )[SPEC_CHECK_TYPE]
    assert (stored.status.value, stored.attempts) == ("failed", 1)
    # What was billed before the failure still counts for the daily budget.
    assert stored.cost_usd > 0
