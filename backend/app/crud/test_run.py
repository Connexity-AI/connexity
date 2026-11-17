"""Reading and writing runs of scenarios (`plans/2026-11-17-text-runner.md`).

A run is a 1.x `run`, each simulated call a `test_case_result` made when the run
starts, and each listed rule's verdict a `rule_verdict`.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import Session, and_, col, or_, select

from app.models.enums import RunStatus
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


def fail_stale_runs(*, session: Session) -> int:
    """Mark runs a restart stopped as failed. Commits; returns how many.

    Runs live in the process that started them: one left running was stopped, and a
    run of scenarios still pending never started.
    """
    stale = session.exec(
        select(Run).where(
            or_(
                col(Run.status) == RunStatus.RUNNING,
                and_(
                    col(Run.status) == RunStatus.PENDING,
                    col(Run.scope).is_not(None),
                ),
            )
        )
    ).all()
    for run in stale:
        run.status = RunStatus.FAILED
        run.completed_at = datetime.now(UTC)
        if run.scope is not None:
            run.status_detail = "Stopped by a restart of Connexity; run it again."
        session.add(run)
    if stale:
        session.commit()
    return len(stale)
