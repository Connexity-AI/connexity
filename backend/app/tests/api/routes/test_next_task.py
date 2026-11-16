"""The assistant's task list and `get_next_task`, on invented agents and calls checked by
the real engine (plan `plans/2026-11-15-next-task.md`)."""

import time
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import Agent, Company, User
from app.models.assistant_task import AssistantTask
from app.models.enums import AssistantTaskState, TaskKind
from app.services.mappings.retell import retell_call_to_trace
from app.services.spec import write_agent_spec
from app.services.work import (
    Group,
    NextTask,
    Task,
    lift_blockers,
    next_task,
    work_list,
)
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _person,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_spec_api import _catalogue
from app.tests.services.test_clarifications import CHANGE, DEPOSIT, RULES, _raise
from app.tests.utils.retell_payloads import retell_call, speech

API = settings.API_V1_STR
DAY_MS = 86_400_000
MISSING = FULL | {"streetAddress": ""}


def _unchecked(db: Session, agent: Agent) -> None:
    """A call stored without any check running on it."""
    payload = retell_call(
        f"call_{uuid.uuid4().hex[:8]}",
        agent_id=agent.platform_agent_id or "",
        timeline=[speech("agent", "Hello", 0.5)],
        start_ms=int(time.time() * 1000 - DAY_MS),
        agent_version=7,
    )
    crud.store_trace(
        session=db,
        trace=retell_call_to_trace(payload),
        agent_id=agent.id,
        company_id=agent.company_id,
        integration_id=agent.integration_id,
        raw=payload,
    )
    db.commit()


def _workspace(db: Session, setup_done: bool = True) -> tuple[User, Agent, Agent]:
    """Front desk: a Critical issue on one call, a written spec and two open
    questions. Night line: no spec, and a call no check could run on. With
    ``setup_done``, both agents' first scans have finished."""
    user = _person(db)
    front = _agent(db, user, "Front desk")
    _catalogue(db, front, "7")
    _call(db, front, _booking(1, MISSING), days_ago=2)
    _call(db, front, _booking(1, FULL), days_ago=1)
    write_agent_spec(
        session=db, agent=front, drafts=RULES, author=user, assistant_name="Claude"
    )
    _raise(db, user, front, CHANGE, DEPOSIT)
    night = _agent(db, user, "Night line")
    _catalogue(db, night, "7")
    _unchecked(db, night)
    if setup_done:
        now = datetime.now(UTC)
        for agent in (front, night):
            agent.scan_done_at = now
            db.add(agent)
        company = db.get(Company, user.company_id)
        assert company is not None
        company.first_scan_done_at = now
        db.add(company)
        db.commit()
    return user, front, night


def _take(db: Session, user: User, assistant: str = "Claude Code") -> NextTask:
    return next_task(
        session=db, company_id=user.company_id, person=user, assistant_name=assistant
    )


def _kinds(tasks: list[Task]) -> list[str]:
    return [task.kind.value for task in tasks]


def test_the_list_is_in_connexitys_order(db: Session) -> None:
    user, front, night = _workspace(db, setup_done=False)

    tasks = work_list(session=db, company_id=user.company_id)

    groups = [task.group for task in tasks]
    assert groups == sorted(groups)  # Critical, then setup, then the rest
    assert tasks[0].kind is TaskKind.ISSUE_FIX and tasks[0].group == Group.CRITICAL
    assert tasks[0].agent_id == front.id
    setup = [t for t in tasks if t.group == Group.SETUP]
    # Onboarding steps first, in Readiness's order, then specs.
    kinds = _kinds(setup)
    assert kinds[0] == "onboarding" and kinds[-1] == "spec"
    assert kinds.index("spec") == len(kinds) - 1
    assert setup[-1].key == f"spec:{night.id}"
    other = {t.kind: t for t in tasks if t.group == Group.OTHER}
    questions = other[TaskKind.CLARIFICATIONS]
    assert questions.for_person is True
    assert questions.title == "Answer 2 questions about Front desk"
    review = other[TaskKind.CALLS_TO_REVIEW]
    assert review.agent_id == night.id and review.calls == 1


def test_a_blocker_moves_directly_above_the_highest_task_it_blocks() -> None:
    a, b, c, d = (
        Task(key=k, kind=TaskKind.SPEC, group=3, title=k, facts=[]) for k in "abcd"
    )

    order = lift_blockers([a, b, c, d], blocks={"d": ["c", "b"], "x": ["a"]})

    assert [t.key for t in order] == ["a", "d", "b", "c"]
    assert lift_blockers([a, b], blocks={"a": ["b"]}) == [a, b]  # already above


def test_tasks_are_handed_out_in_order_and_never_twice(db: Session) -> None:
    user, _, _ = _workspace(db)
    tasks = work_list(session=db, company_id=user.company_id)
    takeable = [t for t in tasks if not t.for_person]

    first = _take(db, user, "Claude Code")
    second = _take(db, user, "Claude")

    assert first.task is not None and second.task is not None
    assert first.task.key == takeable[0].key
    # The other assistant skips the first one's task.
    assert second.task.key == takeable[1].key
    assert second.in_progress_elsewhere == 1
    # Questions and the person's own setup step wait for them, and are never taken.
    waiting = {t.kind for t in second.waiting}
    assert TaskKind.CLARIFICATIONS in waiting


def test_asking_again_ends_the_task_by_what_is_left(db: Session) -> None:
    user, _, night = _workspace(db)

    fix = _take(db, user)
    assert fix.task.kind is TaskKind.ISSUE_FIX

    # The issue is still open: the rest (resolving it) is the person's.
    after_fix = _take(db, user)
    assert after_fix.ended.state is AssistantTaskState.WAITING
    assert fix.task.key in {t.key for t in after_fix.waiting}
    assert after_fix.task.key != fix.task.key

    # Walk to the spec task, then do its work: it is done.
    current = after_fix
    for _ in range(20):
        if current.task is None or current.task.kind is TaskKind.SPEC:
            break
        current = _take(db, user)
    assert current.task is not None
    write_agent_spec(
        session=db, agent=night, drafts=RULES, author=user, assistant_name="Claude"
    )
    done = _take(db, user)
    assert done.ended.title == "Write the spec for Night line"
    assert done.ended.state is AssistantTaskState.DONE
    keys = {t.key for t in work_list(session=db, company_id=user.company_id)}
    assert f"spec:{night.id}" not in keys

    rows = db.exec(
        select(AssistantTask).where(AssistantTask.company_id == user.company_id)
    ).all()
    assert all(
        row.ended_at is not None
        for row in rows
        if row.state is not AssistantTaskState.IN_PROGRESS
    )


def test_a_review_is_done_once_handed_out(db: Session) -> None:
    user, _, night = _workspace(db)
    key = f"calls:{night.id}"

    current = _take(db, user)
    for _ in range(20):
        if current.task is None or current.task.key == key:
            break
        current = _take(db, user)
    assert current.task is not None

    after = _take(db, user)

    assert after.ended.state is AssistantTaskState.DONE
    # The same calls are not handed out for review again.
    keys = {t.key for t in work_list(session=db, company_id=user.company_id)}
    assert key not in keys


def test_get_next_task_through_mcp(client: TestClient, db: Session) -> None:
    user, front, _ = _workspace(db)
    other = _person(db)

    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/next-task", headers=_headers(user)
    )

    assert r.status_code == 200, r.text
    body = r.json()
    task = body["data"]["task"]
    assert (task["kind"], task["position"], task["agent_name"]) == (
        "issue_fix",
        1,
        "Front desk",
    )
    assert any("`get_issue` with issue_id" in s for s in body["next_steps"])
    assert body["next_steps"][-1].startswith(
        "When this task is done, call `get_next_task`"
    )
    assert any(
        "Questions wait for the person on Front desk" in s for s in body["next_steps"]
    )
    assert any("Connexity sorts the workspace's tasks" in r for r in body["rules"])
    waiting = body["data"]["waiting_for_person"]
    assert {"clarifications"} <= {w["kind"] for w in waiting}

    # Another workspace's person cannot reach it.
    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/next-task", headers=_headers(other)
    )
    assert r.status_code in (403, 404)
    # And their own workspace has none of these tasks.
    own = client.get(
        f"{API}/mcp/workspaces/{other.company_id}/next-task", headers=_headers(other)
    ).json()["data"]
    keys = [own["task"]["key"]] if own["task"] else []
    keys += [w["key"] for w in own["waiting_for_person"]]
    assert not any(str(front.id) in key for key in keys)


def test_tools_that_finish_a_task_point_at_get_next_task(
    client: TestClient, db: Session
) -> None:
    user, _, _ = _workspace(db)

    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/readiness", headers=_headers(user)
    )

    assert r.status_code == 200, r.text
    assert any("`get_next_task`" in s for s in r.json()["next_steps"])
