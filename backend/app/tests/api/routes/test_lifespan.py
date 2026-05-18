"""Test crash-recovery logic that runs during app lifespan startup."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.main import app
from app.models import IntegrationCreate, RunStatus, RunUpdate, TestCaseResultCreate
from app.models.enums import IntegrationProvider, Platform
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_config,
    create_test_platform_agent,
    create_test_run,
    eval_config_members,
)
from app.models.schemas import RetellRuntimeConfig, RunConfig


def test_stale_running_runs_marked_failed_on_startup(db: Session) -> None:
    """Runs left in RUNNING status from a prior crash become FAILED on startup."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
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
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    db.commit()
    run_id = run.id

    with TestClient(app):
        pass

    db.expire_all()
    recovered = crud.get_run(session=db, run_id=run_id)
    assert recovered is not None
    assert recovered.status == RunStatus.PENDING


def test_stale_running_retell_resources_are_cleaned_on_startup(db: Session) -> None:
    integration = crud.create_integration(
        session=db,
        data=IntegrationCreate(
            provider=IntegrationProvider.RETELL,
            name="retell-test",
            api_key="key_test_12345678",
        ),
    )
    agent = create_test_platform_agent(db)
    agent.platform = Platform.RETELL
    agent.integration_id = integration.id
    agent.platform_agent_id = "retell_agent_123"
    db.add(agent)
    db.commit()
    db.refresh(agent)

    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db,
        agent_id=agent.id,
        members=eval_config_members(test_case.id),
        config=RunConfig(runtime=RetellRuntimeConfig()),
    )
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    crud.update_run(session=db, db_run=run, run_in=RunUpdate(status=RunStatus.RUNNING))

    result = crud.create_test_case_result(
        session=db,
        result_in=TestCaseResultCreate(run_id=run.id, test_case_id=test_case.id),
    )
    result.retell_chat_id = "chat_123"
    result.retell_temp_chat_agent_id = "temp_agent_123"
    db.add(result)
    db.commit()
    db.refresh(result)

    with (
        patch("app.main.end_retell_chat", new=AsyncMock(return_value=True)) as mock_end,
        patch(
            "app.main.delete_retell_chat_agent",
            new=AsyncMock(return_value=True),
        ) as mock_delete,
        TestClient(app),
    ):
        pass

    db.expire_all()
    recovered_run = crud.get_run(session=db, run_id=run.id)
    recovered_result = crud.get_test_case_result(session=db, result_id=result.id)
    assert recovered_run is not None
    assert recovered_run.status == RunStatus.FAILED
    assert recovered_result is not None
    assert recovered_result.retell_chat_ended_at is not None
    assert recovered_result.retell_temp_chat_agent_deleted_at is not None
    mock_end.assert_awaited_once_with(api_key="key_test_12345678", chat_id="chat_123")
    mock_delete.assert_awaited_once_with(
        api_key="key_test_12345678",
        agent_id="temp_agent_123",
    )
