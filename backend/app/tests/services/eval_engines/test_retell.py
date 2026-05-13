"""RetellEngine: integration lookup, transcript mapping, and polling."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode, Platform, TurnRole
from app.models.schemas import RetellEngineConfig, RunConfig
from app.services.eval_engines.base import EngineRunArgs
from app.services.eval_engines.retell import (
    RetellEngine,
    _map_retell_transcript,
)
from app.services.retell import RetellCall


def _make_agent(platform: Platform | None = Platform.RETELL) -> Agent:
    return Agent(
        id=uuid.uuid4(),
        name="agent",
        mode=AgentMode.PLATFORM,
        endpoint_url=None,
        platform=platform,
        integration_id=uuid.uuid4(),
        platform_agent_id="retell_agent_123",
    )


def test_supported_for_platform_only_retell() -> None:
    engine = RetellEngine()
    assert engine.supported_for_platform(Platform.RETELL) is True
    assert engine.supported_for_platform(Platform.VAPI) is False
    assert engine.supported_for_platform(Platform.WEBHOOK) is False
    assert engine.supported_for_platform(None) is False


def test_transcript_mapping_skips_unknown_roles() -> None:
    call = RetellCall(
        call_id="abc",
        agent_id="agent_xyz",
        start_timestamp=1_700_000_000_000,
        end_timestamp=1_700_000_010_000,
        call_status="ended",
        transcript_object=[
            {"role": "agent", "content": "Hello there"},
            {"role": "user", "content": "Hi"},
            {"role": "system", "content": "ignored"},
            {"role": "agent", "content": "How can I help?"},
        ],
    )

    turns = _map_retell_transcript(call)

    assert [t.role for t in turns] == [
        TurnRole.ASSISTANT,
        TurnRole.USER,
        TurnRole.ASSISTANT,
    ]
    assert [t.content for t in turns] == ["Hello there", "Hi", "How can I help?"]


def test_validate_config_raises_when_no_integration() -> None:
    engine = RetellEngine()
    agent = _make_agent()
    agent.integration_id = None
    session = MagicMock()

    with pytest.raises(ValueError, match="Retell target"):
        engine.validate_config(RetellEngineConfig(), agent, session)


async def test_test_connection_when_integration_missing() -> None:
    engine = RetellEngine()
    agent = _make_agent()
    agent.integration_id = None
    session = MagicMock()

    result = await engine.test_connection(RetellEngineConfig(), agent, session)

    assert result.ok is False
    assert "Retell target" in result.message


def _make_engine_args(agent: Agent, test_case: MagicMock) -> EngineRunArgs:
    return EngineRunArgs(
        test_case=test_case,
        run_config=RunConfig(timeout_per_test_case_ms=100),
        agent=object(),  # type: ignore[arg-type]
        agent_id=agent.id,
        agent_platform=agent.platform,
        agent_integration_id=agent.integration_id,
        agent_platform_agent_id=agent.platform_agent_id,
        agent_endpoint_url=None,
        agent_system_prompt=None,
        agent_tools=None,
        agent_mode=AgentMode.PLATFORM,
        agent_model=None,
        agent_provider=None,
        cancel_event=None,
    )


async def test_run_test_case_uses_retell_simulation_without_web_call() -> None:
    engine = RetellEngine()
    agent = _make_agent()
    session = MagicMock()

    fake_integration = MagicMock()
    fake_integration.encrypted_api_key = "enc-key"
    session.get.return_value = fake_integration

    test_case = MagicMock()
    test_case.id = uuid.uuid4()
    test_case.name = "tc"
    test_case.persona_context = "Caller is impatient."
    test_case.first_message = "hi"
    test_case.expected_outcomes = ["Agent MUST answer politely"]
    test_case.evaluation_criteria_override = None

    args = _make_engine_args(agent, test_case)

    completed_job = MagicMock(
        test_case_job_id="job_123",
        status="pass",
        transcript_snapshot={
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "agent", "content": "Happy to help."},
            ]
        },
        result_explanation="All metrics passed.",
    )

    from app.services.eval_engines import retell as retell_mod

    create_definition_mock = AsyncMock(return_value="definition_123")
    create_batch_mock = AsyncMock(return_value="batch_123")
    with (
        patch.object(retell_mod, "decrypt", return_value="api-key"),
        patch.object(
            retell_mod,
            "create_retell_web_call",
            new=AsyncMock(side_effect=AssertionError("web-call path must not be used")),
            create=True,
        ),
        patch.object(
            retell_mod,
            "get_retell_agent_response_engine",
            new=AsyncMock(return_value={"type": "retell-llm", "llm_id": "llm_123"}),
            create=True,
        ),
        patch.object(
            retell_mod,
            "create_retell_test_case_definition",
            new=create_definition_mock,
            create=True,
        ),
        patch.object(
            retell_mod,
            "create_retell_batch_test",
            new=create_batch_mock,
            create=True,
        ),
        patch.object(
            retell_mod,
            "wait_for_retell_test_run_completion",
            new=AsyncMock(return_value=completed_job),
            create=True,
        ),
        patch.object(
            retell_mod,
            "evaluate_transcript",
            new=AsyncMock(
                return_value=MagicMock(
                    passed=True,
                    overall_score=80.0,
                    judge_token_usage=None,
                    judge_cost_usd=None,
                )
            ),
        ),
    ):
        run_out, verdict = await engine.run_test_case(
            RetellEngineConfig(), args, session
        )

    assert verdict is not None
    assert [turn.role for turn in run_out.transcript] == [
        TurnRole.USER,
        TurnRole.ASSISTANT,
    ]
    create_definition_mock.assert_awaited_once()
    definition_call = create_definition_mock.await_args
    assert definition_call is not None
    definition_kwargs = definition_call.kwargs
    assert definition_kwargs["dynamic_variables"]["test_case_id"] == str(test_case.id)
    assert "Caller is impatient." in definition_kwargs["user_prompt"]
    assert "Agent MUST answer politely" in definition_kwargs["metrics"]
    create_batch_mock.assert_awaited_once_with(
        api_key="api-key",
        response_engine={"type": "retell-llm", "llm_id": "llm_123"},
        test_case_definition_ids=["definition_123"],
    )


async def test_run_test_case_propagates_retell_simulation_error() -> None:
    engine = RetellEngine()
    agent = _make_agent()
    session = MagicMock()

    fake_integration = MagicMock()
    fake_integration.encrypted_api_key = "enc-key"
    session.get.return_value = fake_integration

    test_case = MagicMock()
    test_case.id = uuid.uuid4()
    test_case.name = "tc"
    test_case.persona_context = None
    test_case.first_message = "hi"
    test_case.expected_outcomes = None
    test_case.evaluation_criteria_override = None

    args = _make_engine_args(agent, test_case)

    from app.services.eval_engines import retell as retell_mod

    with (
        patch.object(retell_mod, "decrypt", return_value="api-key"),
        patch.object(
            retell_mod,
            "get_retell_agent_response_engine",
            new=AsyncMock(return_value={"type": "retell-llm", "llm_id": "llm_123"}),
            create=True,
        ),
        patch.object(
            retell_mod,
            "create_retell_test_case_definition",
            new=AsyncMock(return_value="definition_123"),
            create=True,
        ),
        patch.object(
            retell_mod,
            "create_retell_batch_test",
            new=AsyncMock(return_value="batch_123"),
            create=True,
        ),
        patch.object(
            retell_mod,
            "wait_for_retell_test_run_completion",
            new=AsyncMock(side_effect=Exception("Retell simulation job job_123 failed: tool crashed")),
            create=True,
        ),
    ):
        with pytest.raises(Exception, match="tool crashed"):
            await engine.run_test_case(RetellEngineConfig(), args, session)


def test_map_retell_simulation_prompt_includes_case_fields() -> None:
    from app.services.eval_engines.retell_mapping import build_retell_user_prompt

    test_case = MagicMock()
    test_case.name = "billing"
    test_case.description = "Billing issue"
    test_case.persona_context = "User is confused about pricing."
    test_case.first_message = "Why was I charged twice?"
    test_case.user_context = {"plan": "pro"}
    test_case.expected_outcomes = ["Agent MUST explain duplicate charge policy"]
    test_case.evaluation_criteria_override = "Focus on billing accuracy."

    prompt = build_retell_user_prompt(test_case)

    assert "User is confused about pricing." in prompt
    assert "Why was I charged twice?" in prompt
    assert "Agent MUST explain duplicate charge policy" not in prompt
    assert "Focus on billing accuracy." not in prompt


def test_map_retell_simulation_prompt_includes_loop_prevention_guidance() -> None:
    from app.services.eval_engines.retell_mapping import build_retell_user_prompt

    test_case = MagicMock()
    test_case.name = "hydraulic leak"
    test_case.description = None
    test_case.persona_context = "Emergency caller reporting a hydraulic leak."
    test_case.first_message = "There is fluid leaking from the press."
    test_case.user_context = None
    test_case.expected_outcomes = ["Agent MUST triage the emergency"]
    test_case.evaluation_criteria_override = None

    prompt = build_retell_user_prompt(test_case, max_turns=6)

    assert "Do not repeat the same message" in prompt
    assert "end the conversation" in prompt
    assert "Keep the simulation under 6 total turns" in prompt


def test_map_retell_simulation_prompt_caps_turn_guidance() -> None:
    from app.services.eval_engines.retell_mapping import build_retell_user_prompt

    test_case = MagicMock()
    test_case.name = "hydraulic leak"
    test_case.description = None
    test_case.persona_context = "Emergency caller reporting a hydraulic leak."
    test_case.first_message = "There is fluid leaking from the press."
    test_case.user_context = None
    test_case.expected_outcomes = ["Agent MUST triage the emergency"]
    test_case.evaluation_criteria_override = None

    prompt = build_retell_user_prompt(test_case, max_turns=30)

    assert "Keep the simulation under 8 total turns" in prompt


def test_map_retell_transcript_snapshot_normalizes_messages() -> None:
    from app.services.eval_engines.retell_mapping import (
        map_retell_transcript_snapshot,
    )

    transcript = map_retell_transcript_snapshot(
        {
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "agent", "content": "hi"},
                {"role": "system", "content": "ignored"},
            ]
        }
    )

    assert [turn.role for turn in transcript] == [TurnRole.USER, TurnRole.ASSISTANT]
    assert [turn.content for turn in transcript] == ["hello", "hi"]


async def test_wait_for_retell_test_run_completion_returns_terminal_job() -> None:
    from app.services.eval_engines import retell as retell_mod

    in_progress_batch = MagicMock(status="in_progress")
    complete_batch = MagicMock(status="complete")
    completed_job = MagicMock(
        test_case_job_id="job_123",
        test_case_definition_id="definition_123",
        status="pass",
        result_explanation="passed",
    )

    with (
        patch.object(retell_mod, "get_retell_batch_test", new=AsyncMock(side_effect=[in_progress_batch, complete_batch]), create=True),
        patch.object(retell_mod, "list_retell_test_runs", new=AsyncMock(return_value=[completed_job]), create=True),
        patch.object(retell_mod.asyncio, "sleep", new=AsyncMock()),
    ):
        job = await retell_mod.wait_for_retell_test_run_completion(
            api_key="api-key",
            batch_test_id="batch_123",
            test_case_definition_id="definition_123",
            timeout_seconds=10.0,
            cancel_event=None,
        )

    assert job.status == "pass"


async def test_wait_for_retell_test_run_completion_raises_terminal_error() -> None:
    from app.services.eval_engines import retell as retell_mod

    complete_batch = MagicMock(status="complete")
    errored_job = MagicMock(
        test_case_job_id="job_123",
        test_case_definition_id="definition_123",
        status="error",
        result_explanation="Tool mock failed",
    )

    with (
        patch.object(retell_mod, "get_retell_batch_test", new=AsyncMock(return_value=complete_batch), create=True),
        patch.object(retell_mod, "list_retell_test_runs", new=AsyncMock(return_value=[errored_job]), create=True),
    ):
        with pytest.raises(Exception, match="Tool mock failed"):
            await retell_mod.wait_for_retell_test_run_completion(
                api_key="api-key",
                batch_test_id="batch_123",
                test_case_definition_id="definition_123",
                timeout_seconds=10.0,
                cancel_event=None,
            )


def test_dummy_datetime_compat() -> None:
    # Smoke test ensuring datetime usage compiles (guards against import drift).
    assert datetime.now(UTC).year >= 2024
