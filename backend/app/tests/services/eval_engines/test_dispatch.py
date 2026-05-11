"""Orchestrator dispatches each test case to the engine selected in RunConfig."""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import app as app_pkg
from app.models.agent import Agent
from app.models.enums import (
    AgentMode,
    Platform,
    TestCaseStatus,
)
from app.models.schemas import (
    ConnexityEngineConfig,
    CustomUrlEngineConfig,
    RunConfig,
)
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.services.orchestrator import TestCaseRunResult, _execute_single_test_case
from app.services.run_manager import RunManager


def _make_agent(platform: Platform | None = Platform.WEBHOOK) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        name="a",
        mode=AgentMode.ENDPOINT,
        endpoint_url="http://localhost:8080/agent",
        platform=platform,
    )


def _make_test_case() -> TestCase:
    return TestCase(
        id=uuid.uuid4(),
        name="t",
        status=TestCaseStatus.ACTIVE,
        first_message="Hello",
        tags=[],
    )


def _make_result(run_id: uuid.UUID, test_case_id: uuid.UUID) -> TestCaseResult:
    return TestCaseResult(
        id=uuid.uuid4(),
        run_id=run_id,
        test_case_id=test_case_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _patch_db_and_crud(mock_crud: MagicMock, manager: RunManager):
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=MagicMock())
    ctx.__exit__ = MagicMock(return_value=False)
    return (
        patch("app.services.run_manager.run_manager", manager),
        patch("app.core.db.engine", MagicMock()),
        patch("sqlmodel.Session", return_value=ctx),
        patch.object(app_pkg, "crud", mock_crud),
    )


async def test_dispatch_picks_connexity_engine_by_default() -> None:
    run_id = uuid.uuid4()
    test_case = _make_test_case()
    result_obj = _make_result(run_id, test_case.id)

    mock_crud = MagicMock()
    mock_crud.create_test_case_result.return_value = result_obj
    mock_crud.get_test_case_result.return_value = result_obj
    mock_crud.update_test_case_result.return_value = result_obj

    manager = RunManager()
    manager.register(run_id)

    p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
    with (
        p1,
        p2,
        p3,
        p4,
        patch(
            "app.services.eval_engines.connexity.run_test_case_with_evaluation",
            new_callable=AsyncMock,
        ) as mock_connexity,
        patch(
            "app.services.eval_engines.custom_url.run_test_case_with_evaluation",
            new_callable=AsyncMock,
        ) as mock_custom,
    ):
        mock_connexity.return_value = (
            TestCaseRunResult(
                transcript=[],
                agent_token_usage={},
                platform_token_usage={},
            ),
            None,
        )

        config = RunConfig(evaluation_engine=ConnexityEngineConfig())
        await _execute_single_test_case(
            run_id=run_id,
            test_case=test_case,
            agent=_make_agent(),
            agent_endpoint_url="http://localhost:8080/agent",
            config=config,
            agent_mode=AgentMode.ENDPOINT,
            agent_model=None,
            agent_provider=None,
            agent_system_prompt=None,
            agent_tools=None,
            semaphore=asyncio.Semaphore(5),
            cancel_event=asyncio.Event(),
        )

    mock_connexity.assert_awaited_once()
    mock_custom.assert_not_awaited()


async def test_dispatch_picks_custom_url_engine() -> None:
    run_id = uuid.uuid4()
    test_case = _make_test_case()
    result_obj = _make_result(run_id, test_case.id)

    mock_crud = MagicMock()
    mock_crud.create_test_case_result.return_value = result_obj
    mock_crud.get_test_case_result.return_value = result_obj
    mock_crud.update_test_case_result.return_value = result_obj

    manager = RunManager()
    manager.register(run_id)

    p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
    with (
        p1,
        p2,
        p3,
        p4,
        patch(
            "app.services.eval_engines.connexity.run_test_case_with_evaluation",
            new_callable=AsyncMock,
        ) as mock_connexity,
        patch(
            "app.services.eval_engines.custom_url.run_test_case_with_evaluation",
            new_callable=AsyncMock,
        ) as mock_custom,
    ):
        mock_custom.return_value = (
            TestCaseRunResult(
                transcript=[],
                agent_token_usage={},
                platform_token_usage={},
            ),
            None,
        )

        config = RunConfig(
            evaluation_engine=CustomUrlEngineConfig(url="https://override/v1")
        )
        await _execute_single_test_case(
            run_id=run_id,
            test_case=test_case,
            agent=_make_agent(),
            agent_endpoint_url="http://stale/agent",
            config=config,
            agent_mode=AgentMode.ENDPOINT,
            agent_model=None,
            agent_provider=None,
            agent_system_prompt=None,
            agent_tools=None,
            semaphore=asyncio.Semaphore(5),
            cancel_event=asyncio.Event(),
        )

    mock_custom.assert_awaited_once()
    mock_connexity.assert_not_awaited()
    # The forwarded URL is the engine's url, not the agent endpoint.
    assert mock_custom.await_args.args[1] == "https://override/v1"
