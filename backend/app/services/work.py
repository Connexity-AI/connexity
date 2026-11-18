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
from app.core.config import settings
from app.crud import work as crud_work
from app.crud.issue_list import calls_by_agent
from app.crud.readiness import connected_assistants, first_connection
from app.crud.scenario import agents_with_scenarios
from app.crud.spec import rules_of_specs
from app.models import Agent, Company, ReadinessStepKey, ReadinessStepState, User
from app.models.assistant_task import AssistantTask
from app.models.check import Issue
from app.models.enums import AssistantTaskState, IssueState, SpecOrigin, TaskKind
from app.models.task_order import TaskOrder
from app.models.work import (
    TaskState,
    WorkDoneLinkPublic,
    WorkDonePublic,
    WorkHolderPublic,
    WorkPublic,
    WorkSessionPublic,
    WorkTaskPublic,
    WorkTaskRefPublic,
)
from app.services.issue_list import IssueFilters, issue_title, workspace_issues
from app.services.onboarding import (
    ANSWERS,
    ONBOARDING_STEPS,
    SPECS,
    STEPS_BY_KEY,
    Actor,
)
from app.services.onboarding_finish import onboarding_complete
from app.services.spec import agents_needing_specs

# Unchecked calls older than this are not worth a review.
REVIEW_DAYS = 7
# A busier agent's spec comes first, by its calls in this many days.
SPEC_CALL_DAYS = 7
NO_ASSISTANT = "your assistant"
# The onboarding row for the specs, until the first scan is done.
SPECS_STEP = f"onboarding:{SPECS}"
# The onboarding row for the open questions, until onboarding is complete and while no
# question is open; each agent's own questions take its place once raised.
ANSWERS_STEP = f"onboarding:{ANSWERS}"
MAX_SESSION = 40
# A held task whose session has not asked for its next task in this long shows as quiet,
# still assigned (Dmytro, 2026-11-18: "30 minutes").
QUIET_MINUTES = 30


class Group:
    """Where a kind of task sits in the list, top first."""

    INCIDENT = 1
    CRITICAL = 2
    SETUP = 3
    OTHER = 4


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
    # The Work page's second line: the type word, then the details.
    line: str = ""
    severity: str | None = None
    # Keys of the tasks it blocks, and of those that block it, in list order.
    blocks: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)


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
                line=" · ".join(
                    ["Issue fix", item.severity.capitalize()]
                    + (["Reopened"] if item.state is IssueState.REOPENED else [])
                    + [_plural(item.calls_affected, "call")]
                ),
                severity=item.severity,
            )
        )
    return tasks


def _onboarding_tasks(
    session: Session,
    company_id: uuid.UUID,
    assistant_asking: bool,
    *,
    ask_questions: bool,
) -> list[Task]:
    readiness = crud.get_readiness(session=session, company_id=company_id, mcp_url=None)
    tasks = []
    for position, step in enumerate(readiness.steps):
        if step.state is ReadinessStepState.DONE:
            continue
        if assistant_asking and step.key is ReadinessStepKey.ASSISTANT:
            continue  # an assistant asking is connected, whatever Readiness has seen
        tasks.append(
            Task(
                key=f"onboarding:{step.key.value}",
                kind=TaskKind.ONBOARDING,
                group=Group.SETUP,
                title=STEPS_BY_KEY[step.key.value].title,
                facts=[f"Onboarding · step {position + 1} of {len(readiness.steps)}"]
                + ([step.detail] if step.detail else []),
                # A step the person acts on themselves, such as connecting the assistant.
                for_person=STEPS_BY_KEY[step.key.value].who is Actor.PERSON,
                # Readiness's one fact, such as "2 agents · 40 calls", on the second line.
                line=" · ".join(
                    ["Onboarding"]
                    + (
                        [step.detail]
                        if step.detail and step.key is not ReadinessStepKey.ASSISTANT
                        else []
                    )
                ),
            )
        )
    if not readiness.first_scan_done:
        # Before the first scan, writing the specs is one onboarding step; after it,
        # each agent's own spec task takes its place (plan
        # `plans/2026-11-16-onboarding-on-work.md`).
        tasks.append(
            Task(
                key=SPECS_STEP,
                kind=TaskKind.ONBOARDING,
                group=Group.SETUP,
                title=STEPS_BY_KEY[SPECS].title,
                facts=["Onboarding · after the first scan"],
                line="Onboarding",
            )
        )
    if ask_questions:
        tasks.append(
            Task(
                key=ANSWERS_STEP,
                kind=TaskKind.ONBOARDING,
                group=Group.SETUP,
                title=STEPS_BY_KEY[ANSWERS].title,
                facts=["Onboarding · the last step, then the dashboard is ready"],
                line="Onboarding",
            )
        )
    # The specs and questions rows too sits where `ONBOARDING_STEPS` puts it.
    order = {f"onboarding:{step.key}": n for n, step in enumerate(ONBOARDING_STEPS)}
    tasks.sort(key=lambda task: order[task.key])
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
            line=f"Spec · {agent.name}",
        )
        for agent, state in waiting
    ]


def _scenario_tasks(session: Session, names: Mapping[uuid.UUID, str]) -> list[Task]:
    """Agents whose latest spec has rules no scenario lists (plan
    `plans/2026-11-17-scenarios.md`): the most critical rules without one first."""
    ids = list(names)
    specs = crud.latest_specs(session=session, agent_ids=ids)
    listed = agents_with_scenarios(session=session, agent_ids=list(specs))
    by_spec = rules_of_specs(session=session, spec_ids=[s.id for s in specs.values()])
    found: list[tuple[int, Task]] = []
    for agent_id, spec in specs.items():
        rules = by_spec[spec.id]
        keys = listed.get(agent_id, set())
        unlisted = [r for r in rules if r.key not in keys]
        if not unlisted:
            continue
        name = names.get(agent_id, "")
        critical = sum(1 for r in unlisted if r.critical)
        task = Task(
            key=f"scenarios:{agent_id}",
            kind=TaskKind.TESTS,
            group=Group.SETUP,
            title=f"Write scenarios for {_plural(len(unlisted), 'rule')} on {name}",
            facts=[
                f"Tests · {name}",
                f"{critical} of them critical"
                if critical
                else f"{len(rules) - len(unlisted)} of {len(rules)} rules have "
                "scenarios",
            ],
            agent_id=agent_id,
            agent_name=name,
            since=_aware(spec.created_at),
            line=f"Tests · {name}",
        )
        found.append((critical, task))
    found.sort(key=lambda pair: (-pair[0], pair[1].since, pair[1].key))
    return [task for _, task in found]


def _clarification_tasks(
    session: Session,
    company_id: uuid.UUID,
    names: Mapping[uuid.UUID, str],
    group: int = Group.OTHER,
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
                group=group,
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
                line=f"Clarifications · {name}",
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
            line=f"Calls to review · {names.get(agent_id, '')}",
        )
        for agent_id, count in counts.items()
    ]


def apply_order(tasks: Sequence[Task], keys: Sequence[str]) -> list[Task]:
    """The person's order over Connexity's (plan `plans/2026-11-16-reorder.md`).

    Tasks in ``keys`` keep the person's order among themselves. Any other task takes its
    place by Connexity's order: just before the first listed task that Connexity ranks
    below it. Incidents stay first.
    """
    base = list(tasks)
    rank = {task.key: i for i, task in enumerate(base)}
    wanted = [key for key in dict.fromkeys(keys) if key in rank]
    listed = set(wanted)
    by_key = {task.key: task for task in base}
    incidents = [t for t in base if t.kind is TaskKind.INCIDENT]
    result = [
        by_key[key] for key in wanted if by_key[key].kind is not TaskKind.INCIDENT
    ]
    for task in base:
        if task.key in listed or task.kind is TaskKind.INCIDENT:
            continue
        below = next(
            (
                i
                for i, other in enumerate(result)
                if other.key in listed and rank[other.key] > rank[task.key]
            ),
            None,
        )
        if below is None:
            result.append(task)
        else:
            result.insert(below, task)
    return incidents + result


def links(tasks: Sequence[Task]) -> dict[str, list[str]]:
    """Which task blocks which (plan `plans/2026-11-16-blocks.md`), worked out from the
    tasks themselves:

    - an agent's open questions block every issue fix on that agent;
    - an agent's spec to write or update blocks its issue fixes, calls to review and
      scenarios to write;
    - each open onboarding step blocks the next one;
    - the first scan blocks every spec task;
    - every spec task blocks the open-questions step.
    """
    out: dict[str, list[str]] = {}

    def add(blocker: Task, blocked: Task) -> None:
        if blocker.key != blocked.key:
            out.setdefault(blocker.key, []).append(blocked.key)

    by_agent: dict[uuid.UUID, list[Task]] = {}
    for task in tasks:
        if task.agent_id is not None:
            by_agent.setdefault(task.agent_id, []).append(task)
    for agent_tasks in by_agent.values():
        for blocker in agent_tasks:
            for blocked in agent_tasks:
                if blocker.kind is TaskKind.CLARIFICATIONS and blocked.kind is (
                    TaskKind.ISSUE_FIX
                ):
                    add(blocker, blocked)
                if blocker.kind is TaskKind.SPEC and blocked.kind in (
                    TaskKind.ISSUE_FIX,
                    TaskKind.CALLS_TO_REVIEW,
                    TaskKind.TESTS,
                ):
                    add(blocker, blocked)
    steps = [task for task in tasks if task.kind is TaskKind.ONBOARDING]
    for before, after in zip(steps, steps[1:], strict=False):
        add(before, after)
    scan = f"onboarding:{ReadinessStepKey.FIRST_SCAN.value}"
    for step in steps:
        if step.key == scan:
            for task in tasks:
                if task.kind is TaskKind.SPEC:
                    add(step, task)
    # The questions are asked once every spec is written.
    for step in steps:
        if step.key == ANSWERS_STEP:
            for task in tasks:
                if task.kind is TaskKind.SPEC:
                    add(task, step)
    return out


def lift_blockers(
    tasks: Sequence[Task], blocks: Mapping[str, Sequence[str]]
) -> list[Task]:
    """Move each task that blocks others directly above the highest task it blocks,
    again until nothing moves, so chains stay in order. ``blocks`` maps a task's key to
    the keys it blocks."""
    order = list(tasks)
    for _ in range(len(order) + 1):
        moved = False
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
                moved = True
        if not moved:
            break
    return order


def work_list(
    *, session: Session, company_id: uuid.UUID, assistant_asking: bool = False
) -> list[Task]:
    """Every task in the workspace, in Connexity's order. Incidents have no source yet
    (Milestone 5); tests are the scenarios to write. ``assistant_asking``: an assistant
    is asking, so connecting one is done."""
    names = {
        agent.id: agent.name
        for agent in session.exec(
            select(Agent).where(Agent.company_id == company_id)
        ).all()
    }
    issues = _issue_tasks(session, company_id)
    critical = [task for task in issues if task.group == Group.CRITICAL]
    onboarded = onboarding_complete(session=session, company_id=company_id)
    # While onboarding runs, the open questions are its last step: setup, right after
    # the specs (plan `plans/2026-11-18-onboarding-ends-with-dashboard.md`).
    questions = _clarification_tasks(
        session, company_id, names, Group.OTHER if onboarded else Group.SETUP
    )
    onboarding = _onboarding_tasks(
        session,
        company_id,
        assistant_asking,
        ask_questions=not onboarded and not questions,
    )
    before_scan = any(task.key == SPECS_STEP for task in onboarding)
    specs = [] if before_scan else _spec_tasks(session, company_id)
    scenarios = [] if before_scan else _scenario_tasks(session, names)
    setup = onboarding + specs + ([] if onboarded else questions) + scenarios
    other = sorted(
        [task for task in issues if task.group == Group.OTHER]
        + (questions if onboarded else [])
        + _review_tasks(session, company_id, names),
        key=lambda task: (-task.calls, task.since, task.key),
    )
    # Critical issues keep the Issues page's order; setup keeps Connexity's. Then the
    # person's order, then the Blocks rule, so blockers still sit above what they block.
    tasks = critical + setup + other
    saved = session.get(TaskOrder, company_id)
    if saved is not None and saved.keys:
        tasks = apply_order(tasks, saved.keys)
    blocks = links(tasks)
    order = lift_blockers(tasks, blocks)
    position = {task.key: i for i, task in enumerate(order)}
    by_key = {task.key: task for task in order}
    for blocker, blocked in blocks.items():
        for key in blocked:
            by_key[blocker].blocks.append(key)
            by_key[key].blocked_by.append(blocker)
    for task in order:
        task.blocks.sort(key=position.__getitem__)
        task.blocked_by.sort(key=position.__getitem__)
    return order


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
    # Tasks no one can take until the tasks under their Blocked by are done.
    blocked: int = 0
    # Every task's title, to name what blocks what.
    titles: dict[str, str] = field(default_factory=dict)


def _person_name(session: Session, row: AssistantTask) -> str:
    """The person's name as the app shows it, or their email's first part."""
    user = session.get(User, row.taken_by) if row.taken_by else None
    if user is not None and (user.full_name or "").strip():
        return (user.full_name or "").strip()
    return row.taken_by_email.split("@")[0]


def _ending(row: AssistantTask, live: Mapping[str, Task]) -> AssistantTaskState | None:
    """What becomes of a task when the assistant that held it asks for the next one
    (Dmytro, 2026-11-16: asking for the next task means its part is done). None: it
    stays with the session."""
    if row.task_key not in live:
        return AssistantTaskState.DONE
    if row.kind is TaskKind.CALLS_TO_REVIEW:
        return AssistantTaskState.DONE  # a review is done once handed out
    if row.kind is TaskKind.ISSUE_FIX:
        # The fix stays In progress with its session until the issue is resolved or
        # archived, or the session puts it back (Dmytro, 2026-11-18: "Waiting for you
        # IS ONLY FOR CLARIFICATIONS").
        return None
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
    tasks = work_list(session=session, company_id=company_id, assistant_asking=True)
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
    now = datetime.now(UTC)
    for row in mine:
        state = _ending(row, live)
        if state is None:
            row.last_seen_at = now  # the session is alive; the task stays with it
            session.add(row)
            continue
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
        # Only questions wait for the person (Dmytro, 2026-11-18).
        waiting = [task for task in tasks if task.kind is TaskKind.CLARIFICATIONS]
        takeable = [
            task for task in tasks if not task.for_person and task.key not in open_keys
        ]
        free = [task for task in takeable if not task.blocked_by]
        blocked = len(takeable) - len(free)
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
            return NextTask(
                None,
                None,
                ended,
                waiting,
                0,
                elsewhere,
                others,
                blocked,
                {t.key: t.title for t in tasks},
            )
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
            blocked=blocked,
            titles={t.key: t.title for t in tasks},
        )
    raise AssertionError("unreachable")


# ── The Work page ─────────────────────────────────────────────────

DONE_DAYS = 7


def _display(session: Session, user_id: uuid.UUID | None, email: str | None) -> str:
    """A person as the app names them: their name, or their email's first part."""
    user = session.get(User, user_id) if user_id else None
    if user is not None and (user.full_name or "").strip():
        return (user.full_name or "").strip()
    return (email or "").split("@")[0] or "Someone"


def _by(person: str, assistant: str | None, session_name: str = "") -> str:
    """ "Alex's Claude Code · Onboarding", or the person alone."""
    if not assistant:
        return person
    who = f"{person}'s {assistant}"
    return f"{who} · {session_name}" if session_name else who


def _done(session: Session, company_id: uuid.UUID) -> list[WorkDonePublic]:
    """The last 7 days, from what Connexity records (plan question 3)."""
    since = datetime.now(UTC) - timedelta(days=DONE_DAYS)
    out: list[WorkDonePublic] = []
    names = {
        agent.id: agent.name
        for agent in session.exec(
            select(Agent).where(Agent.company_id == company_id)
        ).all()
    }
    specs = crud_work.specs_since(session=session, company_id=company_id, since=since)
    answers = crud_work.answers_by_spec(
        session=session,
        spec_ids=[s.id for s in specs if s.origin is SpecOrigin.ANSWERED],
    )
    for spec in specs:
        agent = names.get(spec.agent_id, "")
        person = _display(session, spec.created_by, spec.created_by_email)
        if spec.origin is SpecOrigin.WRITTEN:
            title = f"Spec written for {agent} · version {spec.version}"
            by = _by(person, spec.assistant_name)
        else:
            count = answers.get(spec.id, 0)
            title = f"{_plural(count, 'answer')} added to the {agent} spec"
            by = person
        out.append(
            WorkDonePublic(
                title=title,
                by=by,
                at=_aware(spec.created_at),
                link=WorkDoneLinkPublic(kind="agent_spec", id=spec.agent_id),
            )
        )
    for record in crud_work.issue_decisions_since(
        session=session, company_id=company_id, since=since
    ):
        issue = session.get(Issue, uuid.UUID(record.subject))
        what = issue_title(issue.check_type, issue.key or None) if issue else "An issue"
        verb = (
            "resolved" if record.new_value == IssueState.RESOLVED.value else "archived"
        )
        out.append(
            WorkDonePublic(
                title=f"{what} · {verb}",
                by=_by(
                    _display(session, record.decided_by, record.decided_by_email),
                    record.assistant_name,
                ),
                at=_aware(record.created_at),
                link=WorkDoneLinkPublic(kind="issue", id=issue.id) if issue else None,
            )
        )
    first = first_connection(
        session=session,
        company_id=company_id,
        access_token_minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    if first is not None and _aware(first[0]) >= since:
        at, assistant, person_id = first
        out.append(
            WorkDonePublic(
                title="Assistant connected",
                by=_by(_display(session, person_id, None), assistant),
                at=_aware(at),
            )
        )
    company = session.get(Company, company_id)
    if company is not None and company.first_scan_done_at is not None:
        at = _aware(company.first_scan_done_at)
        if at >= since:
            out.append(WorkDonePublic(title="First scan done", by="Connexity", at=at))
    # Work that leaves no record of its own: reviews, scenarios written and onboarding
    # steps. Specs and issues come from their own records above.
    for row in crud_work.done_tasks(
        session=session,
        company_id=company_id,
        since=since,
        kinds=(TaskKind.CALLS_TO_REVIEW, TaskKind.TESTS, TaskKind.ONBOARDING),
    ):
        agent = names.get(row.agent_id, "") if row.agent_id else ""
        title, link = row.title, None
        if row.kind is TaskKind.TESTS and row.agent_id is not None:
            title = f"Scenarios written for {agent}"
            link = WorkDoneLinkPublic(kind="agent_tests", id=row.agent_id)
        elif row.kind is TaskKind.CALLS_TO_REVIEW and row.agent_id is not None:
            title = f"Calls reviewed for {agent}"
            link = WorkDoneLinkPublic(kind="agent_calls", id=row.agent_id)
        out.append(
            WorkDonePublic(
                title=title,
                by=_by(
                    _person_name(session, row), row.assistant_name, row.session_name
                ),
                at=_aware(row.done_at),
                link=link,
            )
        )
    out.sort(key=lambda d: d.at, reverse=True)
    return out


def work_page(*, session: Session, company_id: uuid.UUID) -> WorkPublic:
    """The Work page: the same list `get_next_task` hands out from, split into what is
    in progress (held, or waiting for the person) and what is to do."""
    tasks = work_list(session=session, company_id=company_id)
    live = {task.key: task for task in tasks}
    rows = crud_work.open_tasks(session=session, company_id=company_id)
    held = {
        row.task_key: row
        for row in rows
        if row.state is AssistantTaskState.IN_PROGRESS and row.task_key in live
    }
    quiet_before = datetime.now(UTC) - timedelta(minutes=QUIET_MINUTES)

    def state(task: Task) -> TaskState:
        # "Waiting for you" is only for questions (Dmytro, 2026-11-18); the person's
        # own onboarding step sits in To do, marked theirs.
        if task.kind is TaskKind.CLARIFICATIONS:
            return "waiting"
        if task.key in held:
            return "in_progress"
        return "to_do"

    def quiet_since(row: AssistantTask) -> datetime | None:
        seen = _aware(row.last_seen_at or row.taken_at)
        return seen if seen < quiet_before else None

    def ref(key: str) -> WorkTaskRefPublic:
        task = live[key]
        return WorkTaskRefPublic(
            key=key,
            title=task.title,
            state=state(task),
            waiting_for_person=task.for_person,
        )

    public: list[WorkTaskPublic] = []
    for position, task in enumerate(tasks, start=1):
        row = held.get(task.key)
        public.append(
            WorkTaskPublic(
                key=task.key,
                kind=task.kind,
                title=task.title,
                line=task.line,
                severity=task.severity,
                position=position,
                state=state(task),
                waiting_for_person=task.for_person,
                agent_id=task.agent_id,
                agent_name=task.agent_name,
                issue_id=task.ref if task.kind is TaskKind.ISSUE_FIX else None,
                holder=WorkHolderPublic(
                    person=_person_name(session, row),
                    assistant=row.assistant_name,
                    session=row.session_name,
                    taken_at=_aware(row.taken_at),
                    quiet_since=quiet_since(row),
                )
                if row is not None
                else None,
                blocks=[ref(k) for k in task.blocks],
                blocked_by=[ref(k) for k in task.blocked_by],
            )
        )
    sessions = [
        WorkSessionPublic(
            person=_person_name(session, row),
            assistant=row.assistant_name,
            session=row.session_name,
            task=row.title,
        )
        for row in held.values()
    ]
    in_progress = [t for t in public if t.state != "to_do"]
    connected = bool(
        connected_assistants(
            session=session,
            company_id=company_id,
            access_token_minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    )
    return WorkPublic(
        assistant_connected=connected,
        mcp_url=settings.oauth_default_resource_url,
        in_progress=in_progress,
        to_do=[t for t in public if t.state == "to_do"],
        done=_done(session, company_id),
        sessions=sessions,
        waiting=sum(1 for t in in_progress if t.state == "waiting"),
    )


def waiting_count(*, session: Session, company_id: uuid.UUID) -> int:
    """The page's waiting number, without working out the whole list: the agents with
    open questions, the only tasks that wait for the person (Dmytro, 2026-11-18)."""
    return len(
        crud_work.open_questions_by_agent(session=session, company_id=company_id)
    )


class MoveRefused(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def move_task(
    *,
    session: Session,
    company_id: uuid.UUID,
    key: str,
    before: str | None,
    person: User,
    assistant_name: str | None,
) -> None:
    """Move a To do task to sit just before ``before`` (None: the end), and keep the
    person's order. A task the caller's assistant holds goes back to To do first
    (plan `plans/2026-11-18-work-task-states.md`); one another assistant holds, a
    question waiting for the person, and incidents do not move."""
    rows = {
        row.task_key: row
        for row in crud_work.open_tasks(session=session, company_id=company_id)
    }
    mine = rows.get(key)
    if mine is not None:
        if mine.taken_by != person.id or mine.assistant_name != (
            assistant_name or NO_ASSISTANT
        ):
            raise MoveRefused(
                "Another assistant is working on this task; only it can put it back."
            )
        crud_work.end_tasks(
            session=session, rows=[mine], state=AssistantTaskState.RETURNED
        )
        session.commit()
        if before is None:
            return  # back in To do, at its place in the order
    page = work_page(session=session, company_id=company_id)
    to_do = [task.key for task in page.to_do]
    held = {task.key for task in page.in_progress}
    if key in held:
        raise MoveRefused(
            "Questions wait for the person; they do not move. Ask the person in your "
            "chat."
        )
    if key not in to_do:
        raise MoveRefused("No task with that key is in To do.")
    if key.startswith("incident:"):
        raise MoveRefused("Incidents always come first; they do not move.")
    if before == key:
        raise MoveRefused("A task cannot move before itself.")
    if before is not None and before not in to_do:
        raise MoveRefused("The task to place it before is not in To do.")
    order = [k for k in to_do if k != key]
    order.insert(order.index(before) if before is not None else len(order), key)
    saved = session.get(TaskOrder, company_id)
    if saved is None:
        saved = TaskOrder(
            company_id=company_id,
            moved_key=key,
            moved_by_email=person.email,
        )
    saved.keys = order
    saved.moved_key = key
    saved.moved_by = person.id
    saved.moved_by_email = person.email
    saved.assistant_name = assistant_name
    saved.moved_at = datetime.now(UTC)
    session.add(saved)
    session.commit()
