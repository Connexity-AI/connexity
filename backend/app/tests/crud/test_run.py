from datetime import UTC, datetime

from sqlmodel import Session

from app import crud
from app.models import RunStatus, RunUpdate
from app.models.schemas import RunConfig
from app.tests.utils.eval import (
    create_test_agent,
    create_test_run,
    create_test_scenario,
    create_test_scenario_set,
)


def _setup_run(db: Session) -> tuple:
    """Create agent + scenario set needed for a run."""
    agent = create_test_agent(db)
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(db, scenario_ids=[scenario.id])
    return agent, scenario_set


def test_create_run(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    assert run.id is not None
    assert run.agent_id == agent.id
    assert run.scenario_set_id == scenario_set.id
    assert run.status == RunStatus.PENDING


def test_create_run_with_config(db: Session) -> None:
    from app.models import RunCreate

    agent, scenario_set = _setup_run(db)
    config = RunConfig(judge_model="claude-3-5-sonnet", concurrency=3)
    run_in = RunCreate(
        agent_id=agent.id,
        agent_endpoint_url="http://localhost:8080/agent",
        scenario_set_id=scenario_set.id,
        config=config,
    )
    run = crud.create_run(session=db, run_in=run_in)
    assert run.config is not None
    assert run.config["judge_model"] == "claude-3-5-sonnet"
    assert run.config["concurrency"] == 3


def test_get_run(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    fetched = crud.get_run(session=db, run_id=run.id)
    assert fetched is not None
    assert fetched.id == run.id


def test_list_runs(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    items, count = crud.list_runs(session=db)
    assert count >= 1


def test_list_runs_filter_by_agent(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    items, count = crud.list_runs(session=db, agent_id=agent.id)
    assert count >= 1
    assert all(r.agent_id == agent.id for r in items)


def test_list_runs_filter_by_status(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    crud.update_run(
        session=db, db_run=run, run_in=RunUpdate(status=RunStatus.COMPLETED)
    )
    items, count = crud.list_runs(session=db, status=RunStatus.COMPLETED)
    assert count >= 1
    assert all(r.status == RunStatus.COMPLETED for r in items)


def test_list_runs_filter_by_date_range(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    now = datetime.now(UTC)
    items, count = crud.list_runs(
        session=db,
        created_after=datetime(2020, 1, 1, tzinfo=UTC),
        created_before=now,
    )
    assert count >= 1


def test_update_run(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    updated = crud.update_run(
        session=db,
        db_run=run,
        run_in=RunUpdate(status=RunStatus.RUNNING),
    )
    assert updated.status == RunStatus.RUNNING


def test_delete_run(db: Session) -> None:
    agent, scenario_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    run_id = run.id
    crud.delete_run(session=db, db_run=run)
    fetched = crud.get_run(session=db, run_id=run_id)
    assert fetched is None
