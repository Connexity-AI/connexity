"""Test crash-recovery logic that runs during app lifespan startup."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models import Run, RunStatus
from app.models.enums import RunScope
from app.tests.utils.eval import create_test_agent


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.PENDING])
def test_runs_a_restart_stopped_are_failed_on_startup(
    db: Session, status: RunStatus
) -> None:
    """A run lives in the process that started it: one left running was stopped, and
    one still pending never started."""
    agent = create_test_agent(db)
    run = Run(
        agent_id=agent.id,
        company_id=agent.company_id,
        scope=RunScope.ALL,
        platform_version="1",
        status=status,
    )
    db.add(run)
    db.commit()
    run_id = run.id

    with TestClient(app):
        pass

    db.expire_all()
    recovered = db.get(Run, run_id)
    assert recovered is not None
    assert recovered.status == RunStatus.FAILED
    assert recovered.completed_at is not None
