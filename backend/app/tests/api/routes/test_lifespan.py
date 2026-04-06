"""Test crash-recovery logic that runs during app lifespan startup."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.main import app
from app.models import RunStatus, RunUpdate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_set,
    create_test_run,
    eval_set_members,
)


def test_stale_running_runs_marked_failed_on_startup(db: Session) -> None:
    """Runs left in RUNNING status from a prior crash become FAILED on startup."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(session=db, db_run=run, run_in=RunUpdate(status=RunStatus.RUNNING))
    db.commit()
    run_id = run.id

    with TestClient(app):
        pass

    db.expire_all()
    recovered = crud.get_run(session=db, run_id=run_id)
    assert recovered is not None
    assert recovered.status == RunStatus.FAILED
    assert recovered.completed_at is not None


def test_pending_runs_unaffected_on_startup(db: Session) -> None:
    """Runs in PENDING status should not be touched by crash recovery."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    db.commit()
    run_id = run.id

    with TestClient(app):
        pass

    db.expire_all()
    recovered = crud.get_run(session=db, run_id=run_id)
    assert recovered is not None
    assert recovered.status == RunStatus.PENDING
