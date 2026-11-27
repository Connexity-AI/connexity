"""False positives and dismissed flags, through the API: the assistant marks an issue's
findings, the person undoes a mark or brings back a flag the model dismissed, and a
marked finding counts nowhere (plan `plans/2026-11-27-false-positives.md`). Jev and
the LLM step are faked; agents and calls are invented."""

from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Agent, Call, Finding, User
from app.models.check import Issue
from app.models.enums import CallCheckStatus, IssueState, SpecCheckType
from app.services.call_screen import call_screen
from app.services.checks.engine import check_call, check_calls_needing_it
from app.services.checks.model.spec_rule import SPEC_CHECK_TYPE, SPEC_RULE_BROKEN
from app.services.checks.model_checks import answer_model_checks
from app.services.clarification import AnswerDraft, QuestionDraft
from app.services.spec import write_agent_spec
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _booking,
    _headers,
    _settings,
)
from app.tests.services.test_clarifications import (
    ASSISTANT,
    RULES,
    _answer,
    _raise,
    _ready,
)
from app.tests.services.test_spec_check import (  # noqa: F401
    HOURS,
    PRICE,
    FakeJev,
    FakeLLM,
    _judge,
    _rule_key,
    fake_jev,
    fake_llm,
)

API = settings.API_V1_STR


def _issue(db: Session, agent: Agent, check_type: str = SPEC_CHECK_TYPE) -> Issue:
    db.expire_all()
    return db.exec(
        select(Issue).where(Issue.agent_id == agent.id, Issue.check_type == check_type)
    ).one()


def _findings(db: Session, issue: Issue) -> list[Finding]:
    db.expire_all()
    return list(db.exec(select(Finding).where(Finding.issue_id == issue.id)).all())


def _clarify(db: Session, user: User, agent: Agent) -> str:
    """An answered clarification on the opening-hours rule; its id."""
    (question,) = _raise(
        db,
        user,
        agent,
        QuestionDraft(
            question="Is a slot that ends at closing time inside opening hours?",
            answers=[
                AnswerDraft("Yes", "A slot that ends at closing time is inside hours"),
                AnswerDraft("No", "A slot must end before closing time"),
            ],
            rule_key=_rule_key(db, agent, HOURS),
        ),
    )
    _answer(db, user, (question.id, "A"))
    return str(question.id)


def _mcp(user: User, issue: Issue, path: str = "") -> str:
    return f"{API}/mcp/workspaces/{user.company_id}/issues/{issue.id}{path}"


def _mark(
    client: TestClient, user: User, issue: Issue, ids: list[str], **body: Any
) -> Any:
    return client.post(
        _mcp(user, issue, "/false-positives"),
        headers=_headers(user),
        json={"finding_ids": ids, "reason": "Inside opening hours", **body},
    )


async def test_a_clarification_lets_the_assistant_mark_and_marked_findings_count_nowhere(
    client: TestClient,
    db: Session,
    fake_jev: FakeJev,  # noqa: F811
) -> None:
    user, agent, calls = _ready(db)
    await _judge(db, agent)
    issue = _issue(db, agent)
    ids = [str(f.id) for f in _findings(db, issue)]
    assert len(ids) == 2
    clarification = _clarify(db, user, agent)

    marked = _mark(client, user, issue, ids, clarification_id=clarification)

    assert marked.status_code == 200, marked.text
    body = marked.json()
    assert body["data"]["false_positives"] == 2
    assert body["data"]["affected_calls"] == []
    assert body["data"]["tiles"]["calls_affected"] == 0
    assert body["data"]["state"] == IssueState.OPEN.value  # unchanged (decision 3)
    assert body["data"]["history"][0]["kind"] == "marked_false"
    assert any("false positive" in r for r in body["rules"])
    for finding in _findings(db, issue):
        assert finding.false_positive_at is not None
        assert finding.false_positive_reason == "Inside opening hours"
        assert str(finding.false_positive_clarification_id) == clarification
        assert finding.false_positive_assistant is not None
        assert finding.false_positive_approved_by is None  # no approval needed

    # Shown on no call, counted in no result.
    row = db.get(Call, calls[0])
    assert row is not None
    screen = call_screen(session=db, call=row)
    assert screen is not None
    assert not any(f.model is not None for f in screen.findings)
    statuses = crud.call_check_statuses(session=db, call_ids=calls)
    assert set(statuses.values()) == {CallCheckStatus.CLEAN}
    listed = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/calls",
        headers=_headers(user),
        params={"issue_id": str(issue.id)},
    ).json()
    assert listed["data"]["calls"] == []

    # Checking the calls again keeps the marks.
    for call_id in calls:
        call = db.get(Call, call_id)
        assert call is not None
        check_call(session=db, call=call, checks=[SPEC_RULE_BROKEN])
    assert all(f.false_positive_at is not None for f in _findings(db, issue))

    # The list, from the issue: one group at a time.
    page = client.get(
        _mcp(user, issue),
        headers=_headers(user),
        params={"not_counted": "false_positives"},
    ).json()["data"]["not_counted"]
    assert page["total"] == 2 and page["next_offset"] is None
    first = page["rows"][0]
    assert first["finding_id"] in ids
    assert first["clarification"] == "A slot that ends at closing time is inside hours"
    assert first["assistant"] is not None and first["reason"] == "Inside opening hours"


async def test_a_marking_that_needs_the_person_is_refused_without_approval(
    client: TestClient,
    db: Session,
    fake_jev: FakeJev,  # noqa: F811
) -> None:
    user, agent, calls = _ready(db)
    await _judge(db, agent)
    issue = _issue(db, agent)
    ids = [str(f.id) for f in _findings(db, issue)]

    # No clarification: the person approves.
    refused = _mark(client, user, issue, ids)
    assert refused.status_code == 422, refused.text
    assert "need the person's approval" in refused.json()["detail"]["error"]
    assert all(f.false_positive_at is None for f in _findings(db, issue))
    approved = _mark(client, user, issue, ids[:1], approved=True)
    assert approved.status_code == 200, approved.text
    (marked,) = (f for f in _findings(db, issue) if f.false_positive_at)
    assert marked.false_positive_approved_by is not None

    # A critical rule needs the person even with a clarification.
    clarification = _clarify(db, user, agent)
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(key=_rule_key(db, agent, HOURS), critical=True),
            RULES[1]._replace(key=_rule_key(db, agent, PRICE)),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    critical = _mark(client, user, issue, ids[1:], clarification_id=clarification)
    assert critical.status_code == 422
    assert "the rule is critical" in critical.json()["detail"]["error"]

    # A clarification on another rule, or another issue's finding, is refused.
    other = _mark(
        client, user, issue, ids[1:], clarification_id=str(calls[0]), approved=True
    )
    assert other.status_code == 422
    assert "not an answered one in force" in other.json()["detail"]["error"]
    stranger = _mark(client, user, issue, [str(calls[0])], approved=True)
    assert stranger.status_code == 422
    assert "not this issue's" in stranger.json()["detail"]["error"]


def test_a_code_check_finding_needs_the_person_and_can_be_undone(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db)
    _call(db, agent, _booking(1, {**FULL, "postalCode": ""}), days_ago=0.5)
    issue = _issue(db, agent, "booking_details_missing")
    (finding,) = _findings(db, issue)

    assert _mark(client, user, issue, [str(finding.id)]).status_code == 422
    marked = _mark(client, user, issue, [str(finding.id)], approved=True)
    assert marked.status_code == 200, marked.text
    assert marked.json()["data"]["affected_calls"] == []
    # All marked: it keeps its severity and its state.
    assert marked.json()["data"]["severity"] == "critical"
    assert marked.json()["data"]["state"] == IssueState.OPEN.value

    undone = client.post(
        _mcp(user, issue, "/false-positives/undo"),
        headers=_headers(user),
        json={"finding_ids": [str(finding.id)]},
    )
    assert undone.status_code == 200, undone.text
    data = undone.json()["data"]
    assert data["false_positives"] == 0
    assert len(data["affected_calls"]) == 1
    assert [h["kind"] for h in data["history"][:2]] == ["counted_again", "marked_false"]
    assert _findings(db, issue)[0].false_positive_at is None


async def test_a_flag_the_model_dismissed_is_listed_and_can_be_brought_back(
    client: TestClient,
    db: Session,
    fake_jev: FakeJev,  # noqa: F811
    fake_llm: FakeLLM,  # noqa: F811
) -> None:
    user, agent, calls = _ready(db)
    write_agent_spec(
        session=db,
        agent=agent,
        drafts=[
            RULES[0]._replace(
                key=_rule_key(db, agent, HOURS), check=SpecCheckType.CLASSIFIER_THEN_LLM
            ),
            RULES[1]._replace(key=_rule_key(db, agent, PRICE)),
        ],
        author=user,
        assistant_name=ASSISTANT,
    )
    # The newer call's flag is confirmed, the older one's dismissed.
    checks = {SPEC_CHECK_TYPE: SPEC_RULE_BROKEN}
    fake_llm.verdicts = {HOURS: ("failed", [0])}
    check_calls_needing_it(session=db, agent_ids=[agent.id])
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=checks, limit=1)
    fake_llm.verdicts = {HOURS: ("passed", [0])}
    await answer_model_checks(session=db, agent_ids=[agent.id], checks=checks)
    issue = _issue(db, agent)
    assert [f.call_id for f in _findings(db, issue)] == [calls[1]]

    page = client.get(_mcp(user, issue), headers=_headers(user)).json()["data"]
    assert (page["false_positives"], page["dismissed"]) == (0, 1)
    assert page["check_counts"] == {"false_positives": 0, "dismissed": 1}
    listed = client.get(
        _mcp(user, issue), headers=_headers(user), params={"not_counted": "dismissed"}
    ).json()["data"]["not_counted"]
    (row,) = listed["rows"]
    assert row["call_id"] == str(calls[0])
    assert (row["probability"], row["model"]) == (0.92, settings.SPEC_LLM_MODEL)
    assert row["reason"] == "Invented reason: passed"
    assert row["finding_id"] is None and row["at_seconds"] is not None

    back = client.post(
        _mcp(user, issue, "/false-positives/undo"),
        headers=_headers(user),
        json={"dismissed_call_ids": [str(calls[0])]},
    )
    assert back.status_code == 200, back.text
    assert back.json()["data"]["dismissed"] == 0
    assert back.json()["data"]["history"][0]["kind"] == "brought_back"
    brought = next(f for f in _findings(db, issue) if f.call_id == calls[0])
    assert brought.detail is not None
    assert brought.detail["brought_back_by"]
    assert "confirmed_by" not in brought.detail and "reason" not in brought.detail

    # Bringing back a flag that is not dismissed is refused.
    again = client.post(
        _mcp(user, issue, "/false-positives/undo"),
        headers=_headers(user),
        json={"dismissed_call_ids": [str(calls[0])]},
    )
    assert again.status_code == 422


async def test_the_web_list_loads_a_page_at_a_time_and_counts_again(
    client: TestClient,
    db: Session,
    fake_jev: FakeJev,  # noqa: F811
) -> None:
    user, cookies = _signed_in(client, db)
    _, agent, calls = _ready(db, owner=user)
    extra = [
        _call(db, agent, _booking(1, FULL), days_ago=d / 10, version=7)
        for d in range(1, 4)
    ]
    await _judge(db, agent)
    issue = _issue(db, agent)
    ids = [str(f.id) for f in _findings(db, issue)]
    assert len(ids) == len(calls) + len(extra)
    assert _mark(client, user, issue, ids, approved=True).status_code == 200

    url = f"{API}/issues/{issue.id}"
    counts = client.get(url, cookies=cookies).json()
    assert (counts["false_positives"], counts["dismissed"]) == (len(ids), 0)
    assert "rows" not in counts  # the page carries only the counts
    first = client.get(
        f"{url}/not-counted",
        cookies=cookies,
        params={"group": "false_positives", "limit": 2},
    ).json()
    assert (first["total"], len(first["rows"]), first["next_offset"]) == (5, 2, 2)
    last = client.get(
        f"{url}/not-counted",
        cookies=cookies,
        params={"group": "false_positives", "offset": 4, "limit": 2},
    ).json()
    assert (len(last["rows"]), last["next_offset"]) == (1, None)

    again = client.post(
        f"{url}/not-counted/count-again",
        cookies=cookies,
        json={"finding_ids": [first["rows"][0]["finding_id"]]},
    )
    assert again.status_code == 200, again.text
    assert again.json() == {"undone": 1, "brought_back": 0}
    page = client.get(url, cookies=cookies).json()
    assert page["false_positives"] == len(ids) - 1
    assert page["history"][0]["kind"] == "counted_again"
    assert page["history"][0]["assistant"] is None  # the person, in the app
    other = client.get(
        f"{API}/issues/{calls[0]}/not-counted",
        cookies=cookies,
        params={"group": "dismissed"},
    )
    assert other.status_code == 404
