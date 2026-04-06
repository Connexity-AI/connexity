from sqlmodel import Session

from app import crud
from app.models import ScenarioResultUpdate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_run,
    create_test_scenario,
    create_test_scenario_result,
    create_test_scenario_set,
    scenario_set_members,
)


def _setup_result(db: Session) -> tuple:
    """Create agent + scenario set + run + scenario needed for a result."""
    agent = create_test_agent(db)
    scenario = create_test_scenario(db)
    scenario_set = create_test_scenario_set(
        db, members=scenario_set_members(scenario.id)
    )
    run = create_test_run(db, agent_id=agent.id, scenario_set_id=scenario_set.id)
    return run, scenario


def test_create_scenario_result(db: Session) -> None:
    run, scenario = _setup_result(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    assert result.id is not None
    assert result.run_id == run.id
    assert result.scenario_id == scenario.id
    assert result.error_message is None


def test_get_scenario_result(db: Session) -> None:
    run, scenario = _setup_result(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    fetched = crud.get_scenario_result(session=db, result_id=result.id)
    assert fetched is not None
    assert fetched.id == result.id


def test_list_scenario_results(db: Session) -> None:
    run, scenario = _setup_result(db)
    create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    items, count = crud.list_scenario_results(session=db)
    assert count >= 1


def test_list_scenario_results_filter_by_run(db: Session) -> None:
    run, scenario = _setup_result(db)
    create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    items, count = crud.list_scenario_results(session=db, run_id=run.id)
    assert count >= 1
    assert all(r.run_id == run.id for r in items)


def test_list_scenario_results_filter_by_scenario(db: Session) -> None:
    run, scenario = _setup_result(db)
    create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    items, count = crud.list_scenario_results(session=db, scenario_id=scenario.id)
    assert count >= 1
    assert all(r.scenario_id == scenario.id for r in items)


def test_update_scenario_result(db: Session) -> None:
    run, scenario = _setup_result(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    updated = crud.update_scenario_result(
        session=db,
        db_result=result,
        result_in=ScenarioResultUpdate(
            passed=True,
            turn_count=5,
            total_latency_ms=1234,
        ),
    )
    assert updated.passed is True
    assert updated.turn_count == 5
    assert updated.total_latency_ms == 1234


def test_delete_scenario_result(db: Session) -> None:
    run, scenario = _setup_result(db)
    result = create_test_scenario_result(db, run_id=run.id, scenario_id=scenario.id)
    result_id = result.id
    crud.delete_scenario_result(session=db, db_result=result)
    fetched = crud.get_scenario_result(session=db, result_id=result_id)
    assert fetched is None
