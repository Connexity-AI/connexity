"""The Work page's API and `list_tasks`, on invented agents and calls (plan
`plans/2026-11-16-work-page.md`)."""

from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.services.work import next_task
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _agent,
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_next_task import _workspace
from app.tests.api.routes.test_spec_api import _catalogue

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


def _to_do(client: TestClient, cookies: dict[str, str]) -> list[str]:
    return [
        t["key"] for t in client.get(f"{API}/work", cookies=cookies).json()["to_do"]
    ]


def _move(
    client: TestClient, cookies: dict[str, str], key: str, before: str | None
) -> Any:
    return client.post(
        f"{API}/work/order", cookies=cookies, json={"key": key, "before": before}
    )


def test_moving_a_task_changes_what_comes_next(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    _, front, night = _workspace(db, owner=user)
    spec, fix = (
        f"spec:{night.id}",
        next(k for k in _to_do(client, cookies) if k.startswith("issue:")),
    )
    assert _to_do(client, cookies).index(fix) < _to_do(client, cookies).index(spec)

    moved = _move(client, cookies, spec, fix)

    assert moved.status_code == 200, moved.text
    keys = [t["key"] for t in moved.json()["to_do"]]
    assert keys.index(spec) < keys.index(fix)
    taken = next_task(
        session=db,
        company_id=user.company_id,
        person=user,
        assistant_name="Claude Code",
    )
    assert taken.task is not None and taken.task.key == spec

    # Another workspace keeps Connexity's order.
    other, other_cookies = _signed_in(client, db)
    _workspace(db, owner=other)
    other_keys = _to_do(client, other_cookies)
    other_fix = next(k for k in other_keys if k.startswith("issue:"))
    other_spec = next(k for k in other_keys if k.startswith("spec:"))
    assert other_keys.index(other_fix) < other_keys.index(other_spec)
    assert str(front.id) not in "".join(other_keys)


def test_a_blocker_comes_up_with_the_task_moved_above_it(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _, _, night = _workspace(db, owner=user)
    spec, review = f"spec:{night.id}", f"calls:{night.id}"
    first = _to_do(client, cookies)[0]

    # The review is blocked by the spec; moving it to the top brings the spec with it.
    _move(client, cookies, review, first)

    keys = _to_do(client, cookies)
    assert keys[:2] == [spec, review]


def test_a_new_task_falls_in_by_connexitys_order(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _, _, night = _workspace(db, owner=user)
    fix = next(k for k in _to_do(client, cookies) if k.startswith("issue:"))
    _move(client, cookies, fix, None)  # the Critical fix to the end
    late = _agent(db, user, "Late line")
    _catalogue(db, late, "7")
    _call(db, late, days_ago=1)

    keys = _to_do(client, cookies)

    # The new spec (setup) sits by Connexity's order: before the specs Connexity ranks
    # below it, and the moved fix stays at the end.
    assert keys[-1] == fix
    assert f"spec:{late.id}" in keys
    assert f"spec:{night.id}" in keys


def test_tasks_in_progress_or_waiting_do_not_move(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    _workspace(db, owner=user)
    taken = next_task(
        session=db,
        company_id=user.company_id,
        person=user,
        assistant_name="Claude Code",
    )
    assert taken.task is not None
    page = client.get(f"{API}/work", cookies=cookies).json()
    waiting = next(t["key"] for t in page["in_progress"] if t["state"] == "waiting")
    first = page["to_do"][0]["key"]

    held = _move(client, cookies, taken.task.key, first)
    waits = _move(client, cookies, waiting, first)
    unknown = _move(client, cookies, "spec:nope", None)
    itself = _move(client, cookies, first, first)

    assert held.status_code == 422 and "in progress" in held.json()["detail"]
    assert waits.status_code == 422
    assert unknown.status_code == 422
    assert itself.status_code == 422


def test_move_task_through_mcp(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    _, _, night = _workspace(db, owner=user)
    spec = f"spec:{night.id}"
    first = _to_do(client, cookies)[0]

    r = client.post(
        f"{API}/mcp/workspaces/{user.company_id}/tasks/move",
        headers=_headers(user),
        json={"key": spec, "before": first},
    )
    refused = client.post(
        f"{API}/mcp/workspaces/{user.company_id}/tasks/move",
        headers=_headers(user),
        json={"key": "spec:nope"},
    )

    assert r.status_code == 200, r.text
    to_do = [t for t in r.json()["data"]["tasks"] if t["state"] == "to_do"]
    assert to_do[0]["key"] == spec
    assert any("only when the person asks" in rule for rule in r.json()["rules"])
    assert refused.status_code == 422
    assert refused.json()["detail"]["error"] == "No task with that key is in To do."
