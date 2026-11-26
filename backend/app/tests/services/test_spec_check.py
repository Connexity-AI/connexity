"""The spec check: each real call judged against its agent's spec by a classifier (Jev,
faked), on invented agents and calls (plan `plans/2026-11-26-spec-check.md`)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Agent, Call, CallCheck, Finding, Spec
from app.models.check import Issue
from app.models.enums import (
    CheckMode,
    CheckOutcome,
    DecisionKind,
    FindingEffect,
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
                check=SpecCheckType.LLM,  # not asked until 105.16
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
    assert any("has no moment" in s for s in call["next_steps"])
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
