"""The assistant's tasks: one list per workspace, sorted by Connexity, worked out from the
workspace every time it is asked for (`plans/2026-11-15-next-task.md`).

The order (Dmytro, 2026-11-16): incidents always first, then Critical tasks, then setup
tasks in Connexity's order, then all other issues and clarifications. A task that
blocks a higher task sits directly above it. The assistant only ever gets the top task
it may take (`next_task`).
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import crud
from app.crud import work as crud_work
from app.crud.issue_list import calls_by_agent
from app.models import Agent, ReadinessStepKey, ReadinessStepState, User
from app.models.assistant_task import AssistantTask
from app.models.enums import AssistantTaskState, IssueState, TaskKind
from app.services.issue_list import IssueFilters, workspace_issues
from app.services.spec import agents_needing_specs

# Unchecked calls older than this are not worth a review.
REVIEW_DAYS = 7
# A busier agent's spec comes first, by its calls in this many days.
SPEC_CALL_DAYS = 7
NO_ASSISTANT = "your assistant"
MAX_SESSION = 40


class Group:
    """Where a kind of task sits in the list, top first."""

    INCIDENT = 1
    CRITICAL = 2
    SETUP = 3
    OTHER = 4


_ONBOARDING = {
    ReadinessStepKey.ASSISTANT: "Connect your AI assistant",
    ReadinessStepKey.VOICE_PLATFORM: "Connect your voice platform",
    ReadinessStepKey.SYNC: "Add the agents to watch and bring in their calls",
    ReadinessStepKey.FIRST_SCAN: "Scan recent calls",
}


@dataclass
class Task:
    key: str
    kind: TaskKind
    group: int
    title: str
    facts: list[str]
    agent_id: uuid.UUID | None = None
    agent_name: str | None = None
    # How many calls it touches: the measure of the "all other" group.
    calls: int = 0
    # When its work first appeared, for ties: the oldest first.
    since: datetime = field(default_factory=lambda: datetime.min.replace(tzinfo=UTC))
    # The next move is the person's: open questions only they answer, or a step only
    # they take.
    for_person: bool = False
    # Its id in its own area, for the steps (an issue id).
    ref: uuid.UUID | None = None


def _aware(moment: datetime | None) -> datetime:
    if moment is None:
        return datetime.min.replace(tzinfo=UTC)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _issue_tasks(session: Session, company_id: uuid.UUID) -> list[Task]:
    """Every live issue, in the Issues page's order (worst first)."""
    _, items = workspace_issues(
        session=session,
        company_id=company_id,
        filters=IssueFilters(period="30d", status="open"),
    )
    tasks = []
    for item in items:
        critical = item.severity == "critical"
        state = "reopened" if item.state is IssueState.REOPENED else item.severity
        tasks.append(
            Task(
                key=f"issue:{item.id}",
                kind=TaskKind.ISSUE_FIX,
                group=Group.CRITICAL if critical else Group.OTHER,
                title=item.title,
                facts=[
                    f"Issue fix · {state} · "
                    f"{_plural(item.calls_affected, 'call')} of "
                    f"{item.calls_total} in the last 30 days",
                ],
                agent_id=item.agent_id,
                agent_name=item.agent_name,
                calls=item.calls_affected,
                since=_aware(item.last_seen_at),
                ref=item.id,
            )
        )
    return tasks


def _onboarding_tasks(session: Session, company_id: uuid.UUID) -> list[Task]:
    readiness = crud.get_readiness(session=session, company_id=company_id, mcp_url=None)
    tasks = []
    for position, step in enumerate(readiness.steps):
        if step.state is ReadinessStepState.DONE:
            continue
        tasks.append(
            Task(
                key=f"onboarding:{step.key.value}",
                kind=TaskKind.ONBOARDING,
                group=Group.SETUP,
                title=_ONBOARDING[step.key],
                facts=[f"Onboarding · step {position + 1} of {len(readiness.steps)}"]
                + ([step.detail] if step.detail else []),
                # The assistant connecting is the person's own step.
                for_person=step.key is ReadinessStepKey.ASSISTANT,
            )
        )
    return tasks


def _spec_tasks(session: Session, company_id: uuid.UUID) -> list[Task]:
    """Missing specs before ones that need review; then the busier agent first."""
    calls = calls_by_agent(
        session=session,
        company_id=company_id,
        since=datetime.now(UTC) - timedelta(days=SPEC_CALL_DAYS),
    )
    waiting = agents_needing_specs(session=session, company_id=company_id)
    waiting.sort(key=lambda pair: (pair[1] != "none", -calls.get(pair[0].id, 0)))
    return [
        Task(
            key=f"spec:{agent.id}",
            kind=TaskKind.SPEC,
            group=Group.SETUP,
            title=(
                f"Write the spec for {agent.name}"
                if state == "none"
                else f"Update the spec for {agent.name}"
            ),
            facts=[
                "Spec · no spec yet"
                if state == "none"
                else "Spec · the agent moved to a newer version than its spec",
                f"{_plural(calls.get(agent.id, 0), 'call')} in the last "
                f"{SPEC_CALL_DAYS} days",
            ],
            agent_id=agent.id,
            agent_name=agent.name,
            since=_aware(agent.created_at),
        )
        for agent, state in waiting
    ]


def _clarification_tasks(
    session: Session, company_id: uuid.UUID, names: Mapping[uuid.UUID, str]
) -> list[Task]:
    tasks = []
    for agent_id, open_ in crud_work.open_questions_by_agent(
        session=session, company_id=company_id
    ).items():
        name = names.get(agent_id, "")
        tasks.append(
            Task(
                key=f"clarifications:{agent_id}",
                kind=TaskKind.CLARIFICATIONS,
                group=Group.OTHER,
                title=f"Answer {_plural(open_.questions, 'question')} about {name}",
                facts=[
                    f"Clarifications · {name}",
                    f"Seen on {_plural(open_.calls, 'call')}"
                    if open_.calls
                    else "Raised from the prompt",
                ],
                agent_id=agent_id,
                agent_name=name,
                calls=open_.calls,
                since=_aware(open_.oldest),
                for_person=True,
            )
        )
    return tasks


def _review_tasks(
    session: Session, company_id: uuid.UUID, names: Mapping[uuid.UUID, str]
) -> list[Task]:
    """Calls no check could run on, since the agent's calls were last reviewed."""
    counts = crud_work.unchecked_calls_by_agent(
        session=session,
        company_id=company_id,
        since=crud_work.last_reviews(session=session, company_id=company_id),
        default_since=datetime.now(UTC) - timedelta(days=REVIEW_DAYS),
    )
    return [
        Task(
            key=f"calls:{agent_id}",
            kind=TaskKind.CALLS_TO_REVIEW,
            group=Group.OTHER,
            title=f"Review {_plural(count, 'call')} Connexity could not check on "
            f"{names.get(agent_id, '')}",
            facts=[
                f"Calls to review · {names.get(agent_id, '')}",
                f"{_plural(count, 'unchecked call')} in the last {REVIEW_DAYS} days",
            ],
            agent_id=agent_id,
            agent_name=names.get(agent_id, ""),
            calls=count,
        )
        for agent_id, count in counts.items()
    ]


def lift_blockers(
    tasks: Sequence[Task], blocks: Mapping[str, Sequence[str]]
) -> list[Task]:
    """Move each task that blocks others directly above the highest task it blocks.
    ``blocks`` maps a task's key to the keys it blocks; which task blocks which is
    roadmap feature 10.126, so today it is empty."""
    order = list(tasks)
    for blocker, blocked in blocks.items():
        keys = [task.key for task in order]
        if blocker not in keys:
            continue
        targets = [keys.index(key) for key in blocked if key in keys]
        if not targets:
            continue
        top = min(targets)
        at = keys.index(blocker)
        if at > top:
            order.insert(top, order.pop(at))
    return order


def work_list(*, session: Session, company_id: uuid.UUID) -> list[Task]:
    """Every task in the workspace, in Connexity's order. Incidents (Milestone 5) and
    tests (10.17) have no source yet."""
    names = {
        agent.id: agent.name
        for agent in session.exec(
            select(Agent).where(Agent.company_id == company_id)
        ).all()
    }
    issues = _issue_tasks(session, company_id)
    critical = [task for task in issues if task.group == Group.CRITICAL]
    setup = _onboarding_tasks(session, company_id) + _spec_tasks(session, company_id)
    other = sorted(
        [task for task in issues if task.group == Group.OTHER]
        + _clarification_tasks(session, company_id, names)
        + _review_tasks(session, company_id, names),
        key=lambda task: (-task.calls, task.since, task.key),
    )
    # Critical issues keep the Issues page's order; setup keeps Connexity's.
    return lift_blockers(critical + setup + other, blocks={})


# ── Handing tasks out ─────────────────────────────────────────────


class Ended(NamedTuple):
    title: str
    state: AssistantTaskState


class Held(NamedTuple):
    """A task another session is working on."""

    task: Task
    position: int
    person: str
    assistant: str
    session: str


@dataclass
class NextTask:
    task: Task | None
    position: int | None
    # The caller's previous task, if asking for this one ended it.
    ended: Ended | None
    # Tasks whose next move is the person's, in list order.
    waiting: list[Task]
    to_do: int
    in_progress_elsewhere: int
    # What other sessions hold, in list order.
    held: list[Held] = field(default_factory=list)


def _person_name(session: Session, row: AssistantTask) -> str:
    """The person's name as the app shows it, or their email's first part."""
    user = session.get(User, row.taken_by) if row.taken_by else None
    if user is not None and (user.full_name or "").strip():
        return (user.full_name or "").strip()
    return row.taken_by_email.split("@")[0]


def _ending(row: AssistantTask, live: Mapping[str, Task]) -> AssistantTaskState:
    """What becomes of a task when the assistant that held it asks for the next one
    (Dmytro, 2026-11-16: asking for the next task means its part is done)."""
    if row.task_key not in live:
        return AssistantTaskState.DONE
    if row.kind is TaskKind.CALLS_TO_REVIEW:
        return AssistantTaskState.DONE  # a review is done once handed out
    if row.kind is TaskKind.ISSUE_FIX:
        return AssistantTaskState.WAITING  # the person resolves it
    return AssistantTaskState.RETURNED


def next_task(
    *,
    session: Session,
    company_id: uuid.UUID,
    person: User,
    assistant_name: str | None,
    session_name: str | None = None,
) -> NextTask:
    """End the caller's current task, then take the first task that is neither the
    person's to do nor held by another assistant."""
    assistant = assistant_name or NO_ASSISTANT
    label = (session_name or "").strip()[:MAX_SESSION]
    tasks = work_list(session=session, company_id=company_id)
    live = {task.key: task for task in tasks}

    held = crud_work.open_tasks(session=session, company_id=company_id)
    mine = [
        row
        for row in held
        if row.state is AssistantTaskState.IN_PROGRESS
        and row.taken_by == person.id
        and row.assistant_name == assistant
        and row.session_name == label
    ]
    ended: Ended | None = None
    # A task the caller just handed back goes to someone else, or to the caller later:
    # never straight back, or asking again would loop on it.
    returned: set[str] = set()
    for row in mine:
        state = _ending(row, live)
        crud_work.end_tasks(session=session, rows=[row], state=state)
        ended = Ended(row.title, state)
        if state is AssistantTaskState.RETURNED:
            returned.add(row.task_key)
    # Work that disappeared is done, whoever held it.
    crud_work.end_tasks(
        session=session,
        rows=[row for row in held if row not in mine and row.task_key not in live],
        state=AssistantTaskState.DONE,
    )
    session.commit()

    for attempt in range(3):
        held = crud_work.open_tasks(session=session, company_id=company_id)
        open_keys = {row.task_key for row in held}
        waiting_keys = {
            row.task_key for row in held if row.state is AssistantTaskState.WAITING
        }
        waiting = [
            task for task in tasks if task.for_person or task.key in waiting_keys
        ]
        free = [
            task for task in tasks if not task.for_person and task.key not in open_keys
        ]
        if len(free) > 1:
            free = [task for task in free if task.key not in returned] or free
        others = [
            Held(
                live[row.task_key],
                tasks.index(live[row.task_key]) + 1,
                _person_name(session, row),
                row.assistant_name,
                row.session_name,
            )
            for row in held
            if row.state is AssistantTaskState.IN_PROGRESS and row.task_key in live
        ]
        others.sort(key=lambda h: h.position)
        elsewhere = len(others)
        if not free:
            return NextTask(None, None, ended, waiting, 0, elsewhere, others)
        task = free[0]
        session.add(
            AssistantTask(
                company_id=company_id,
                task_key=task.key,
                kind=task.kind,
                title=task.title,
                agent_id=task.agent_id,
                taken_by=person.id,
                taken_by_email=person.email,
                assistant_name=assistant,
                session_name=label,
            )
        )
        try:
            session.commit()
        except IntegrityError:
            # Another assistant took it at the same moment: look again.
            session.rollback()
            if attempt == 2:
                raise
            continue
        return NextTask(
            task=task,
            position=tasks.index(task) + 1,
            ended=ended,
            waiting=waiting,
            to_do=len(free) - 1,
            in_progress_elsewhere=elsewhere,
            held=others,
        )
    raise AssertionError("unreachable")
