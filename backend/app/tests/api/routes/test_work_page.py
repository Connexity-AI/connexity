"""The Work page's API and `list_tasks`, on invented agents and calls (plan
`plans/2026-11-16-work-page.md`)."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.services.work import next_task
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_next_task import _workspace

API = settings.API_V1_STR


def test_the_page_answers_in_progress_waiting_to_do_and_done(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _, front, _ = _workspace(db, owner=user)
    taken = next_task(
        session=db,
        company_id=user.company_id,
        person=user,
        assistant_name="Claude Code",
        session_name="Fixes",
    )
    assert taken.task is not None

    r = client.get(f"{API}/work", cookies=cookies)

    assert r.status_code == 200, r.text
    page = r.json()
    in_progress = page["in_progress"]
    held = [t for t in in_progress if t["state"] == "in_progress"]
    assert [t["key"] for t in held] == [taken.task.key]
    assert held[0]["holder"]["assistant"] == "Claude Code"
    assert held[0]["holder"]["session"] == "Fixes"
    assert held[0]["line"].startswith("Issue fix · Critical")
    waiting = [t for t in in_progress if t["state"] == "waiting"]
    assert any(t["kind"] == "clarifications" for t in waiting)
    assert page["waiting"] == len(waiting)
    positions = [t["position"] for t in page["to_do"]]
    assert positions == sorted(positions)
    blocked = [t for t in page["to_do"] if t["blocked_by"]]
    assert blocked and blocked[0]["blocked_by"][0]["title"]
    assert page["sessions"] == [
        {
            "person": user.email.split("@")[0],
            "assistant": "Claude Code",
            "session": "Fixes",
            "task": taken.task.title,
        }
    ]
    done = [d["title"] for d in page["done"]]
    assert "Spec written for Front desk · version 1" in done
    assert "First scan done" in done
    assert str(front.id) not in done  # titles, not ids

    counts = client.get(f"{API}/work/counts", cookies=cookies).json()
    assert counts == {"waiting": page["waiting"]}


def test_another_workspace_sees_none_of_it(client: TestClient, db: Session) -> None:
    owner, _ = _signed_in(client, db)
    _workspace(db, owner=owner)
    _, cookies = _signed_in(client, db)

    page = client.get(f"{API}/work", cookies=cookies).json()

    keys = [t["key"] for t in page["in_progress"] + page["to_do"]]
    assert all(k.startswith("onboarding:") for k in keys)
    assert page["done"] == [] and page["sessions"] == []


def test_list_tasks_through_mcp_reads_the_same_list(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _workspace(db, owner=user)
    page = client.get(f"{API}/work", cookies=cookies).json()
    url = f"{API}/mcp/workspaces/{user.company_id}/tasks"

    first = client.get(url, headers=_headers(user), params={"limit": 2}).json()
    rest = client.get(
        url, headers=_headers(user), params={"cursor": first["next_cursor"]}
    ).json()

    keys = [t["key"] for t in first["data"]["tasks"] + rest["data"]["tasks"]]
    expected = sorted(page["in_progress"] + page["to_do"], key=lambda t: t["position"])
    assert keys == [t["key"] for t in expected]
    assert first["data"]["total"] == len(expected)
    assert rest["next_cursor"] is None
    # Reading never takes a task.
    again = client.get(f"{API}/work", cookies=cookies).json()
    assert not [t for t in again["in_progress"] if t["state"] == "in_progress"]
