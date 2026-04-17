from sqlmodel import Session

from app import crud
from app.models import TestCaseResultUpdate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_case_result_fixture,
    create_test_eval_config,
    create_test_run,
    eval_config_members,
)


def _setup_result(db: Session) -> tuple:
    """Create agent + eval set + run + test case needed for a result."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    return run, test_case


def test_create_test_case_result(db: Session) -> None:
    run, test_case = _setup_result(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    assert result.id is not None
    assert result.run_id == run.id
    assert result.test_case_id == test_case.id
    assert result.error_message is None


def test_get_test_case_result(db: Session) -> None:
    run, test_case = _setup_result(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    fetched = crud.get_test_case_result(session=db, result_id=result.id)
    assert fetched is not None
    assert fetched.id == result.id


def test_list_test_case_results(db: Session) -> None:
    run, test_case = _setup_result(db)
    create_test_case_result_fixture(db, run_id=run.id, test_case_id=test_case.id)
    items, count = crud.list_test_case_results(session=db)
    assert count >= 1


def test_list_test_case_results_filter_by_run(db: Session) -> None:
    run, test_case = _setup_result(db)
    create_test_case_result_fixture(db, run_id=run.id, test_case_id=test_case.id)
    items, count = crud.list_test_case_results(session=db, run_id=run.id)
    assert count >= 1
    assert all(r.run_id == run.id for r in items)


def test_list_test_case_results_filter_by_test_case(db: Session) -> None:
    run, test_case = _setup_result(db)
    create_test_case_result_fixture(db, run_id=run.id, test_case_id=test_case.id)
    items, count = crud.list_test_case_results(session=db, test_case_id=test_case.id)
    assert count >= 1
    assert all(r.test_case_id == test_case.id for r in items)


def test_update_test_case_result(db: Session) -> None:
    run, test_case = _setup_result(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    updated = crud.update_test_case_result(
        session=db,
        db_result=result,
        result_in=TestCaseResultUpdate(
            passed=True,
            turn_count=5,
            total_latency_ms=1234,
        ),
    )
    assert updated.passed is True
    assert updated.turn_count == 5
    assert updated.total_latency_ms == 1234


def test_delete_test_case_result(db: Session) -> None:
    run, test_case = _setup_result(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    result_id = result.id
    crud.delete_test_case_result(session=db, db_result=result)
    fetched = crud.get_test_case_result(session=db, result_id=result_id)
    assert fetched is None
