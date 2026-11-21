"""Reading and writing runs of scenarios (`plans/2026-11-17-text-runner.md`).

A run is a `run`, each simulated call a `test_case_result` made when the run
starts, and each listed rule's verdict a `rule_verdict`.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, and_, col, or_, select

from app.models.enums import RunScope, RunStatus
from app.models.run import Run
from app.models.test_case_result import TestCaseResult
from app.models.test_run import RuleVerdict


def create_run(
    *, session: Session, run: Run, scenario_ids: Sequence[uuid.UUID], repeats: int
) -> Run:
    """Store the run and one empty simulated call per scenario and repeat. Commits."""
    session.add(run)
    session.flush()
    for scenario_id in scenario_ids:
        for repeat in range(repeats):
            session.add(
                TestCaseResult(
                    run_id=run.id,
                    test_case_id=scenario_id,
                    repetition_index=repeat,
                    company_id=run.company_id,
                )
            )
    session.commit()
    session.refresh(run)
    return run


def runs_page(
    *, session: Session, agent_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[Run], bool]:
    """The agent's runs of scenarios, newest first, and whether more follow."""
    rows = list(
        session.exec(
            select(Run)
            .where(Run.agent_id == agent_id, col(Run.scope).is_not(None))
            .order_by(col(Run.created_at).desc(), col(Run.id))
            .offset(offset)
            .limit(limit + 1)
        ).all()
    )
    return rows[:limit], len(rows) > limit


def runs_of_agent(*, session: Session, agent_id: uuid.UUID) -> list[Run]:
    """Every run of scenarios of the agent, oldest first."""
    return list(
        session.exec(
            select(Run)
            .where(Run.agent_id == agent_id, col(Run.scope).is_not(None))
            .order_by(col(Run.created_at), col(Run.id))
        ).all()
    )


def run_before(*, session: Session, run: Run) -> Run | None:
    """The newest completed run before ``run`` of the same scenarios: the same set, or
    every scenario. None for a run of picked scenarios."""
    if run.scope not in (RunScope.SET, RunScope.ALL):
        return None
    same = [Run.agent_id == run.agent_id, Run.scope == run.scope]
    if run.scope is RunScope.SET:
        same.append(Run.set_name == run.set_name)
    return session.exec(
        select(Run)
        .where(
            *same,
            Run.id != run.id,
            Run.status == RunStatus.COMPLETED,
            col(Run.created_at) <= run.created_at,
        )
        .order_by(col(Run.created_at).desc(), col(Run.id))
        .limit(1)
    ).first()


def run_of_agent(
    *, session: Session, agent_id: uuid.UUID, run_id: uuid.UUID
) -> Run | None:
    run = session.get(Run, run_id)
    if run is None or run.agent_id != agent_id or run.scope is None:
        return None
    return run


def calls_of_runs(
    *, session: Session, run_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[TestCaseResult]]:
    """Each run's simulated calls, in the order they were made."""
    if not run_ids:
        return {}
    out: dict[uuid.UUID, list[TestCaseResult]] = {run_id: [] for run_id in run_ids}
    for row in session.exec(
        select(TestCaseResult)
        .where(col(TestCaseResult.run_id).in_(run_ids))
        .order_by(
            col(TestCaseResult.created_at),
            col(TestCaseResult.test_case_id),
            col(TestCaseResult.repetition_index),
        )
    ).all():
        out[row.run_id].append(row)
    return out


def verdicts_of_runs(
    *, session: Session, run_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[RuleVerdict]]:
    if not run_ids:
        return {}
    out: dict[uuid.UUID, list[RuleVerdict]] = {run_id: [] for run_id in run_ids}
    for row in session.exec(
        select(RuleVerdict).where(col(RuleVerdict.run_id).in_(run_ids))
    ).all():
        out[row.run_id].append(row)
    return out


# A run whose process has given no sign of life for this long is marked failed
# (Dmytro, 2026-11-20). Until then it reads stalled, and may still come back.
DEAD_AFTER = timedelta(minutes=15)


def alive_at(run: Run) -> datetime:
    """The run's last sign of life: its heartbeat, else when it started or was
    stored."""
    at = run.heartbeat_at or run.started_at or run.created_at
    return at if at.tzinfo else at.replace(tzinfo=UTC)


def fail_stale_runs(*, session: Session, agent_id: uuid.UUID | None = None) -> int:
    """Mark runs whose process stopped as failed. Commits; returns how many.

    A run lives in the process that started it and says so with a heartbeat. One
    still pending or running with no sign of life for ``DEAD_AFTER`` has lost its
    process: a deploy, a restart or a crash. Its finished calls keep their verdicts.
    A run with a recent heartbeat belongs to a live process, this one or another, and
    is left alone.
    """
    query = select(Run).where(
        or_(
            col(Run.status) == RunStatus.RUNNING,
            and_(col(Run.status) == RunStatus.PENDING, col(Run.scope).is_not(None)),
        )
    )
    if agent_id is not None:
        query = query.where(Run.agent_id == agent_id)
    now = datetime.now(UTC)
    stale = [
        run for run in session.exec(query).all() if now - alive_at(run) > DEAD_AFTER
    ]
    for run in stale:
        run.status = RunStatus.FAILED
        run.completed_at = now
        if run.scope is not None:
            run.status_detail = (
                "The server running it stopped (a deploy or a restart); run it again."
            )
        session.add(run)
    if stale:
        session.commit()
    return len(stale)


def progress_rows(
    *, session: Session, run_id: uuid.UUID
) -> list[tuple[datetime | None, datetime | None, bool, bool]]:
    """Each simulated call of the run as (started, finished, has an error, the judge
    was asked), without its transcript: what polling a run's status needs."""
    rows = session.exec(
        select(
            TestCaseResult.started_at,
            TestCaseResult.completed_at,
            col(TestCaseResult.error_message).is_not(None),
            col(TestCaseResult.judge_ms).is_not(None),
        ).where(TestCaseResult.run_id == run_id)
    ).all()
    return [(r[0], r[1], bool(r[2]), bool(r[3])) for r in rows]


def simulated_call(
    *, session: Session, call_id: uuid.UUID, company_id: uuid.UUID
) -> tuple[TestCaseResult, Run] | None:
    """A simulated call of a run of scenarios in the company, with its run."""
    result = session.get(TestCaseResult, call_id)
    if result is None or result.company_id != company_id:
        return None
    run = session.get(Run, result.run_id)
    if run is None or run.scope is None:
        return None
    return result, run
