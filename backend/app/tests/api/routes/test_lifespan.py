"""Test crash-recovery logic that runs during app lifespan startup."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Run, RunStatus
from app.models.enums import RunScope
from app.tests.utils.eval import create_test_agent


def _run(db: Session, status: RunStatus, minutes_ago: int) -> Run:
    agent = create_test_agent(db)
    at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    run = Run(
        agent_id=agent.id,
        company_id=agent.company_id,
        scope=RunScope.ALL,
        platform_version="1",
        status=status,
        created_at=at,
        started_at=at if status is RunStatus.RUNNING else None,
        heartbeat_at=at if status is RunStatus.RUNNING else None,
    )
    db.add(run)
    db.commit()
    return run


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.PENDING])
def test_runs_whose_server_stopped_are_failed_on_startup(
    db: Session, status: RunStatus
) -> None:
    """A run lives in the process that started it and says so with a heartbeat: one
    with no sign of life for 15 minutes has lost its process."""
    run_id = _run(db, status, minutes_ago=16).id

    with TestClient(app):
        pass

    db.expire_all()
    recovered = db.get(Run, run_id)
    assert recovered is not None
    assert recovered.status == RunStatus.FAILED
    assert recovered.completed_at is not None


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.PENDING])
def test_a_run_another_server_is_running_is_left_alone_on_startup(
    db: Session, status: RunStatus
) -> None:
    """A server starting beside a live run must not fail it."""
    run_id = _run(db, status, minutes_ago=1).id

    with TestClient(app):
        pass

    db.expire_all()
    alive = db.get(Run, run_id)
    assert alive is not None
    assert alive.status == status
    # Left for the next test run's startup: fail it here so it is not found stale.
    alive.status = RunStatus.FAILED
    db.add(alive)
    db.commit()
