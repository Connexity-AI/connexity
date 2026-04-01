"""Tests for execute_run() and _execute_single_scenario() with mocked DB and agent."""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import app as app_pkg
from app.models.enums import AgentMode, RunStatus, ScenarioStatus, TurnRole
from app.models.run import Run
from app.models.scenario import Scenario
from app.models.scenario_result import ScenarioResult
from app.models.schemas import ConversationTurn, JudgeVerdict, MetricScore, RunConfig
from app.services.orchestrator import (
    ScenarioRunResult,
    _execute_single_scenario,
    execute_run,
)
from app.services.run_manager import RunManager


def _make_scenario(*, name: str = "test-scenario") -> Scenario:
    return Scenario(
        id=uuid.uuid4(),
        name=name,
        status=ScenarioStatus.ACTIVE,
        initial_message="Hello",
        max_turns=5,
        tags=[],
    )


def _make_run(
    *,
    scenario_set_id: uuid.UUID | None = None,
    status: RunStatus = RunStatus.PENDING,
) -> Run:
    return Run(
        id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        agent_endpoint_url="http://localhost:8080/agent",
        scenario_set_id=scenario_set_id or uuid.uuid4(),
        status=status,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_result(
    run_id: uuid.UUID,
    scenario_id: uuid.UUID,
    *,
    passed: bool | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        id=uuid.uuid4(),
        run_id=run_id,
        scenario_id=scenario_id,
        passed=passed,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _mock_transcript() -> list[ConversationTurn]:
    return [
        ConversationTurn(
            index=0,
            role=TurnRole.USER,
            content="Hello",
            timestamp=datetime.now(UTC),
        ),
        ConversationTurn(
            index=1,
            role=TurnRole.ASSISTANT,
            content="Hi there!",
            latency_ms=150,
            timestamp=datetime.now(UTC),
        ),
    ]


def _mock_verdict() -> JudgeVerdict:
    return JudgeVerdict(
        passed=True,
        overall_score=85.0,
        metric_scores=[
            MetricScore(
                metric="response_delivery",
                score=4,
                label="good",
                justification="Responded well.",
            ),
        ],
        judge_model="test-model",
        judge_provider="test-provider",
    )


def _mock_session_ctx():
    """Return a MagicMock that works as ``with Session(engine) as session:``."""
    session = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=session)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _patch_db_and_crud(mock_crud: MagicMock, manager: RunManager):
    """Return context manager patches for Session, engine, crud, and run_manager."""
    ctx = _mock_session_ctx()
    return (
        patch("app.services.run_manager.run_manager", manager),
        patch("app.core.db.engine", MagicMock()),
        patch("sqlmodel.Session", return_value=ctx),
        patch.object(app_pkg, "crud", mock_crud),
    )


class TestExecuteSingleScenario:
    """Tests for _execute_single_scenario with mocked dependencies."""

    @patch(
        "app.services.orchestrator.run_scenario_with_evaluation",
        new_callable=AsyncMock,
    )
    async def test_happy_path(self, mock_run_eval: AsyncMock) -> None:
        run_id = uuid.uuid4()
        scenario = _make_scenario()
        result_obj = _make_result(run_id, scenario.id)
        updated_result = _make_result(run_id, scenario.id, passed=True)
        updated_result.verdict = {"overall_score": 0.85}

        mock_run_eval.return_value = (
            ScenarioRunResult(
                transcript=_mock_transcript(),
                agent_token_usage={},
                platform_token_usage={},
                platform_cost_usd=0.0,
            ),
            _mock_verdict(),
        )

        mock_crud = MagicMock()
        mock_crud.create_scenario_result.return_value = result_obj
        mock_crud.get_scenario_result.return_value = result_obj
        mock_crud.update_scenario_result.return_value = updated_result

        manager = RunManager()
        state = manager.register(run_id)
        state.progress.total_scenarios = 1

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            result = await _execute_single_scenario(
                run_id=run_id,
                scenario=scenario,
                agent_endpoint_url="http://localhost:8080/agent",
                config=RunConfig(),
                agent_mode=AgentMode.ENDPOINT,
                agent_model=None,
                agent_provider=None,
                agent_system_prompt=None,
                agent_tools=None,
                semaphore=asyncio.Semaphore(5),
                cancel_event=asyncio.Event(),
            )

        assert result.passed is True
        mock_run_eval.assert_awaited_once()
        assert state.progress.completed_count == 1
        assert state.progress.passed_count == 1

    @patch(
        "app.services.orchestrator.run_scenario_with_evaluation",
        new_callable=AsyncMock,
    )
    async def test_skips_when_cancelled(self, mock_run_eval: AsyncMock) -> None:
        run_id = uuid.uuid4()
        scenario = _make_scenario()
        result_obj = _make_result(run_id, scenario.id)

        mock_crud = MagicMock()
        mock_crud.create_scenario_result.return_value = result_obj

        cancel_event = asyncio.Event()
        cancel_event.set()

        manager = RunManager()
        manager.register(run_id)

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            result = await _execute_single_scenario(
                run_id=run_id,
                scenario=scenario,
                agent_endpoint_url="http://localhost:8080/agent",
                config=RunConfig(),
                agent_mode=AgentMode.ENDPOINT,
                agent_model=None,
                agent_provider=None,
                agent_system_prompt=None,
                agent_tools=None,
                semaphore=asyncio.Semaphore(5),
                cancel_event=cancel_event,
            )

        mock_run_eval.assert_not_awaited()
        assert result is result_obj

    @patch(
        "app.services.orchestrator.run_scenario_with_evaluation",
        new_callable=AsyncMock,
    )
    async def test_handles_exception(self, mock_run_eval: AsyncMock) -> None:
        run_id = uuid.uuid4()
        scenario = _make_scenario()
        result_obj = _make_result(run_id, scenario.id)
        updated_result = _make_result(run_id, scenario.id, passed=False)
        updated_result.error_message = "boom"

        mock_run_eval.side_effect = RuntimeError("boom")

        mock_crud = MagicMock()
        mock_crud.create_scenario_result.return_value = result_obj
        mock_crud.get_scenario_result.return_value = result_obj
        mock_crud.update_scenario_result.return_value = updated_result

        manager = RunManager()
        state = manager.register(run_id)
        state.progress.total_scenarios = 1

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            result = await _execute_single_scenario(
                run_id=run_id,
                scenario=scenario,
                agent_endpoint_url="http://localhost:8080/agent",
                config=RunConfig(),
                agent_mode=AgentMode.ENDPOINT,
                agent_model=None,
                agent_provider=None,
                agent_system_prompt=None,
                agent_tools=None,
                semaphore=asyncio.Semaphore(5),
                cancel_event=asyncio.Event(),
            )

        assert result.error_message == "boom"
        update_call = mock_crud.update_scenario_result.call_args
        update_data = update_call.kwargs.get(
            "result_in", update_call[1].get("result_in")
        )
        assert update_data.error_message == "boom"


class TestExecuteRun:
    """Tests for the top-level execute_run orchestration."""

    @patch(
        "app.services.orchestrator._execute_single_scenario",
        new_callable=AsyncMock,
    )
    async def test_completes_successfully(self, mock_single: AsyncMock) -> None:
        scenario = _make_scenario()
        run = _make_run()

        mock_crud = MagicMock()
        mock_crud.get_run.return_value = run
        mock_crud.update_run.return_value = run
        mock_crud.get_scenarios_for_set.return_value = [scenario]

        completed_result = _make_result(run.id, scenario.id, passed=True)
        completed_result.agent_latency_p50_ms = 100
        mock_single.return_value = completed_result

        manager = RunManager()

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            await execute_run(run.id)

        assert mock_crud.update_run.call_count >= 2
        final_update = mock_crud.update_run.call_args_list[-1]
        final_data = final_update.kwargs.get("run_in", final_update[1].get("run_in"))
        assert final_data.status == RunStatus.COMPLETED
        assert final_data.aggregate_metrics is not None

    @patch(
        "app.services.orchestrator._execute_single_scenario",
        new_callable=AsyncMock,
    )
    async def test_run_not_found(self, mock_single: AsyncMock) -> None:
        mock_crud = MagicMock()
        mock_crud.get_run.return_value = None

        manager = RunManager()

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            await execute_run(uuid.uuid4())

        mock_single.assert_not_called()

    @patch(
        "app.services.orchestrator._execute_single_scenario",
        new_callable=AsyncMock,
    )
    async def test_run_already_running(self, mock_single: AsyncMock) -> None:
        run = _make_run(status=RunStatus.RUNNING)
        mock_crud = MagicMock()
        mock_crud.get_run.return_value = run

        manager = RunManager()

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            await execute_run(run.id)

        mock_single.assert_not_called()

    @patch(
        "app.services.orchestrator._execute_single_scenario",
        new_callable=AsyncMock,
    )
    async def test_cancelled_run_gets_cancelled_status(
        self, mock_single: AsyncMock
    ) -> None:
        scenario = _make_scenario()
        run = _make_run()

        mock_crud = MagicMock()
        mock_crud.get_run.return_value = run
        mock_crud.update_run.return_value = run
        mock_crud.get_scenarios_for_set.return_value = [scenario]

        result = _make_result(run.id, scenario.id, passed=False)
        manager = RunManager()

        async def side_effect_with_cancel(
            *_args: Any, **_kwargs: Any
        ) -> ScenarioResult:
            manager.signal_cancel(run.id)
            return result

        mock_single.side_effect = side_effect_with_cancel

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            await execute_run(run.id)

        final_update = mock_crud.update_run.call_args_list[-1]
        final_data = final_update.kwargs.get("run_in", final_update[1].get("run_in"))
        assert final_data.status == RunStatus.CANCELLED

    @patch(
        "app.services.orchestrator._execute_single_scenario",
        new_callable=AsyncMock,
    )
    async def test_handles_unexpected_exception(self, mock_single: AsyncMock) -> None:
        run = _make_run()
        mock_crud = MagicMock()
        mock_crud.get_run.return_value = run
        mock_crud.update_run.return_value = run
        mock_crud.get_scenarios_for_set.side_effect = RuntimeError("db error")

        manager = RunManager()

        p1, p2, p3, p4 = _patch_db_and_crud(mock_crud, manager)
        with p1, p2, p3, p4:
            await execute_run(run.id)

        final_update = mock_crud.update_run.call_args_list[-1]
        final_data = final_update.kwargs.get("run_in", final_update[1].get("run_in"))
        assert final_data.status == RunStatus.FAILED
