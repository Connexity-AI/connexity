"""Orchestrator dispatches each test case to the runtime selected in RunConfig."""

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
    ConnexityRuntimeConfig,
    CustomEndpointRuntimeConfig,
    RunConfig,
)
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.services.eval_runtimes import AgentSnapshot, RunSnapshot
from app.services.eval_runtimes.types import TestCaseRunResult
from app.services.orchestrator import _execute_single_test_case
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


def _make_snapshots(
    agent: Agent, *, endpoint_url: str | None
) -> tuple[AgentSnapshot, RunSnapshot]:
    agent_snapshot = AgentSnapshot(
        agent=agent,
        agent_id=agent.id,
        platform=agent.platform,
        integration_id=agent.integration_id,
        platform_agent_id=agent.platform_agent_id,
        endpoint_url=endpoint_url,
        system_prompt=None,
        tools=None,
        mode=AgentMode.ENDPOINT,
        model=None,
        provider=None,
    )
    run_snapshot = RunSnapshot(
        run_id=uuid.uuid4(),
        run_config=RunConfig(),
        cancel_event=asyncio.Event(),
    )
    return agent_snapshot, run_snapshot


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


async def test_dispatch_picks_connexity_runtime_by_default() -> None:
    run_id = uuid.uuid4()
    test_case = _make_test_case()
    result_obj = _make_result(run_id, test_case.id)

    mock_crud = MagicMock()
    mock_crud.create_test_case_result.return_value = result_obj
    mock_crud.get_test_case_result.return_value = result_obj
    mock_crud.update_test_case_result.return_value = result_obj

    manager = RunManager()
    manager.register(run_id)

    agent = _make_agent()
    agent_snapshot, run_snapshot = _make_snapshots(
        agent, endpoint_url="http://localhost:8080/agent"
    )
    run_snapshot = RunSnapshot(
        run_id=run_id,
        run_config=RunConfig(runtime=ConnexityRuntimeConfig()),
        cancel_event=asyncio.Event(),
    )

    p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
    with (
        p1,
        p2,
        p3,
        p4,
        patch(
            "app.services.eval_runtimes.text.connexity.ConnexityRuntime.run_test_case",
            new_callable=AsyncMock,
        ) as mock_connexity,
        patch(
            "app.services.eval_runtimes.text.custom_endpoint.CustomEndpointRuntime.run_test_case",
            new_callable=AsyncMock,
        ) as mock_custom,
    ):
        mock_connexity.return_value = TestCaseRunResult(
            transcript=[],
            agent_token_usage={},
            platform_token_usage={},
        )

        await _execute_single_test_case(
            run_id=run_id,
            test_case=test_case,
            agent_snapshot=agent_snapshot,
            run_snapshot=run_snapshot,
            semaphore=asyncio.Semaphore(5),
        )

    mock_connexity.assert_awaited_once()
    mock_custom.assert_not_awaited()


async def test_dispatch_picks_custom_endpoint_runtime() -> None:
    run_id = uuid.uuid4()
    test_case = _make_test_case()
    result_obj = _make_result(run_id, test_case.id)

    mock_crud = MagicMock()
    mock_crud.create_test_case_result.return_value = result_obj
    mock_crud.get_test_case_result.return_value = result_obj
    mock_crud.update_test_case_result.return_value = result_obj

    manager = RunManager()
    manager.register(run_id)

    agent = _make_agent()
    agent_snapshot, _ = _make_snapshots(agent, endpoint_url="http://stale/agent")
    run_snapshot = RunSnapshot(
        run_id=run_id,
        run_config=RunConfig(
            runtime=CustomEndpointRuntimeConfig(url="https://override/v1")
        ),
        cancel_event=asyncio.Event(),
    )

    p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
    with (
        p1,
        p2,
        p3,
        p4,
        patch(
            "app.services.eval_runtimes.text.connexity.ConnexityRuntime.run_test_case",
            new_callable=AsyncMock,
        ) as mock_connexity,
        patch(
            "app.services.eval_runtimes.text.custom_endpoint.CustomEndpointRuntime.run_test_case",
            new_callable=AsyncMock,
        ) as mock_custom,
    ):
        mock_custom.return_value = TestCaseRunResult(
            transcript=[],
            agent_token_usage={},
            platform_token_usage={},
        )

        await _execute_single_test_case(
            run_id=run_id,
            test_case=test_case,
            agent_snapshot=agent_snapshot,
            run_snapshot=run_snapshot,
            semaphore=asyncio.Semaphore(5),
        )

    mock_custom.assert_awaited_once()
    mock_connexity.assert_not_awaited()
    forwarded_cfg = mock_custom.await_args.args[0]
    assert isinstance(forwarded_cfg, CustomEndpointRuntimeConfig)
    assert forwarded_cfg.url == "https://override/v1"
