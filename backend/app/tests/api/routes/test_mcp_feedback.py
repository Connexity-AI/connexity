"""`send_feedback`: an assistant reports a problem in Connexity; the report is stored,
then posted to the team's Notion database, and retried until it gets there (plan
`plans/2026-11-19-assistant-feedback.md`). Notion is mocked."""

import asyncio
import json
import uuid
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User
from app.models.feedback import FeedbackReport
from app.services import feedback
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import API

NOTION = "https://api.notion.com/v1/pages"

BUG = {
    "kind": "bug",
    "title": "run_scenarios refuses a set it just wrote",
    "what_happened": "Wrote the set smoke with write_scenario_set, then ran it.",
    "tool": "run_scenarios",
    "error": "The agent has no set named 'smoke'.",
    "ids": ["agent-1", "set-1"],
    "session": "Testing",
}


def _send(client: TestClient, user: User, body: dict[str, Any]) -> Any:
    return client.post(
        f"{API}/mcp/workspaces/{user.company_id}/feedback",
        headers=_headers(user),
        json=body,
    )


def _reports(db: Session, user: User) -> list[FeedbackReport]:
    db.expire_all()
    return list(
        db.exec(
            select(FeedbackReport).where(FeedbackReport.company_id == user.company_id)
        ).all()
    )


@pytest.fixture
def notion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "NOTION_FEEDBACK_TOKEN", "invented-token")
    monkeypatch.setattr(settings, "NOTION_FEEDBACK_DATABASE_ID", "invented-db")


def _post_unsent(db: Session) -> int:
    return asyncio.run(feedback.post_unsent(session=db))


def test_a_report_is_stored_and_answered_without_notion(
    client: TestClient, db: Session
) -> None:
    user = _person(db)

    r = _send(client, user, BUG)

    assert r.status_code == 200, r.text
    body = r.json()
    report_id = body["data"]["report_id"]
    assert any("reads every report" in s for s in body["next_steps"])
    assert any("caller data" in rule for rule in body["rules"])
    [stored] = _reports(db, user)
    assert str(stored.id) == report_id
    assert (stored.kind, stored.tool, stored.session_name) == (
        "bug",
        "run_scenarios",
        "Testing",
    )
    assert stored.ids == ["agent-1", "set-1"]
    assert stored.sent_by == user.id
    assert stored.connexity_version == "local"
    # Without the Notion settings, nothing is posted.
    assert _post_unsent(db) == 0
    assert stored.notion_page_id is None and stored.tries == 0


def test_a_stored_report_is_posted_to_notion_as_a_new_row(
    client: TestClient, db: Session, notion: None
) -> None:
    user = _person(db)
    with respx.mock(assert_all_called=False) as mock:
        # The background post may run during the request; let it fail so the retry
        # below is the one that reaches Notion.
        mock.post(NOTION).mock(return_value=httpx.Response(503))
        _send(client, user, BUG)
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post(NOTION).mock(
            return_value=httpx.Response(200, json={"id": "page-1"})
        )
        # Every workspace's unsent reports go on the tick, this one among them.
        assert _post_unsent(db) >= 1

    [stored] = _reports(db, user)
    [call] = [
        c
        for c in route.calls
        if json.loads(c.request.content)["properties"]["Report ID"]["rich_text"][0][
            "text"
        ]["content"]
        == str(stored.id)
    ]
    sent = json.loads(call.request.content)
    assert call.request.headers["Authorization"] == "Bearer invented-token"
    assert sent["parent"] == {"database_id": "invented-db"}
    props = sent["properties"]
    assert props["Title"]["title"][0]["text"]["content"] == BUG["title"]
    assert props["Kind"] == {"select": {"name": "Bug"}}
    assert props["Status"] == {"status": {"name": "New"}}
    assert props["Tool"]["rich_text"][0]["text"]["content"] == "run_scenarios"
    assert props["IDs"]["rich_text"][0]["text"]["content"] == "agent-1, set-1"
    assert props["Wanted"] == {"rich_text": []}
    [stored] = _reports(db, user)
    assert stored.notion_page_id == "page-1"
    assert stored.posted_at is not None
    # Posted once: the next tick does not send it again.
    with respx.mock(assert_all_called=False) as mock:
        again = mock.post(NOTION).mock(
            return_value=httpx.Response(200, json={"id": "page-2"})
        )
        _post_unsent(db)
    assert all(str(stored.id) not in c.request.content.decode() for c in again.calls)


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(400, json={"message": "invented refusal"}),
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, json={}),
        httpx.TimeoutException("timed out"),
    ],
    ids=["refused", "malformed", "empty", "timeout"],
)
def test_notion_failing_keeps_the_report_and_counts_its_tries(
    client: TestClient, db: Session, notion: None, answer: Any
) -> None:
    user = _person(db)
    with respx.mock(assert_all_called=False) as mock:
        mock.post(NOTION).mock(return_value=httpx.Response(503))
        assert _send(client, user, BUG).status_code == 200

    with respx.mock(assert_all_called=False) as mock:
        if isinstance(answer, Exception):
            mock.post(NOTION).mock(side_effect=answer)
        else:
            mock.post(NOTION).mock(return_value=answer)
        for _ in range(feedback.MAX_TRIES + 2):
            _post_unsent(db)

    [stored] = _reports(db, user)
    assert stored.notion_page_id is None
    assert stored.tries == feedback.MAX_TRIES
    assert stored.last_error


def test_what_a_report_needs_is_refused_when_missing(
    client: TestClient, db: Session
) -> None:
    user = _person(db)

    no_title = _send(client, user, {**BUG, "title": "  "})
    no_story = _send(client, user, {**BUG, "what_happened": ""})
    no_wish = _send(client, user, {"kind": "feature_request", "title": "Versions"})

    for r in (no_title, no_story, no_wish):
        assert r.status_code == 422
        assert "Nothing was stored" in " ".join(r.json()["detail"]["next_steps"])
    assert "what_happened" in no_story.json()["detail"]["error"]
    assert "wanted" in no_wish.json()["detail"]["error"]
    assert _reports(db, user) == []


def test_a_workspace_sends_at_most_its_daily_cap(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _person(db)
    monkeypatch.setattr(feedback, "DAILY_CAP", 2)

    assert _send(client, user, BUG).status_code == 200
    assert _send(client, user, BUG).status_code == 200
    third = _send(client, user, BUG)

    assert third.status_code == 422
    assert "send it later" in third.json()["detail"]["error"]
    assert len(_reports(db, user)) == 2


def test_a_long_error_is_cut_and_another_workspace_is_refused(
    client: TestClient, db: Session
) -> None:
    user = _person(db)
    other = _person(db)

    long = _send(client, user, {**BUG, "error": "x" * 10_000})
    assert long.status_code == 200
    assert (
        feedback.notion_properties(_reports(db, user)[0], "Invented", "someone")[
            "Error"
        ]["rich_text"][0]["text"]["content"]
        == "x" * feedback.NOTION_TEXT
    )

    into_other = client.post(
        f"{API}/mcp/workspaces/{other.company_id}/feedback",
        headers=_headers(user),
        json=BUG,
    )
    assert into_other.status_code in (403, 404)
    assert _reports(db, other) == []
    assert uuid.UUID(long.json()["data"]["report_id"])


def test_a_report_is_taken_by_one_post_at_a_time(
    client: TestClient, db: Session
) -> None:
    from datetime import UTC, datetime, timedelta

    from app.crud.feedback import claim_report

    user = _person(db)
    _send(client, user, BUG)
    [stored] = _reports(db, user)
    now = datetime.now(UTC)

    def claim(at: datetime) -> bool:
        return claim_report(
            session=db,
            report_id=stored.id,
            now=at,
            stale_before=at - feedback.CLAIM_STALE,
        )

    assert claim(now) is True
    # A second post while the first is under way does not take it.
    assert claim(now + timedelta(seconds=5)) is False
    # A post that never finished can be taken again once it is stale.
    assert claim(now + feedback.CLAIM_STALE + timedelta(seconds=1)) is True
    db.expire_all()
    assert db.get(FeedbackReport, stored.id).tries == 2  # type: ignore[union-attr]
