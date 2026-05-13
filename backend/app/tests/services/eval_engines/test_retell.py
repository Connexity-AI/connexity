"""RetellEngine: integration lookup, transcript mapping, and polling."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

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

    import pytest

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


async def test_run_test_case_creates_call_polls_and_judges() -> None:
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

    args = EngineRunArgs(
        test_case=test_case,
        run_config=RunConfig(),
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

    completed_call = RetellCall(
        call_id="call_xyz",
        agent_id="retell_agent_123",
        start_timestamp=1,
        end_timestamp=2,
        call_status="ended",
        transcript_object=[
            {"role": "agent", "content": "hi"},
            {"role": "user", "content": "thanks"},
        ],
    )

    from app.services.eval_engines import retell as retell_mod
    from app.services.retell import RetellCreateWebCallResult

    with (
        patch.object(retell_mod, "decrypt", return_value="api-key"),
        patch.object(
            retell_mod,
            "create_retell_web_call",
            new=AsyncMock(
                return_value=RetellCreateWebCallResult(success=True, call_id="call_xyz")
            ),
        ),
        patch.object(
            retell_mod, "get_retell_call", new=AsyncMock(return_value=completed_call)
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
    assert run_out.transcript[0].role == TurnRole.ASSISTANT
    assert run_out.transcript[1].role == TurnRole.USER


async def test_run_test_case_raises_when_retell_call_errors() -> None:
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

    args = EngineRunArgs(
        test_case=test_case,
        run_config=RunConfig(),
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

    errored_call = RetellCall(
        call_id="call_xyz",
        agent_id="retell_agent_123",
        call_status="error",
        raw={"disconnection_reason": "error_user_not_joined"},
    )

    from app.services.eval_engines import retell as retell_mod
    from app.services.retell import RetellCreateWebCallResult

    import pytest

    with (
        patch.object(retell_mod, "decrypt", return_value="api-key"),
        patch.object(
            retell_mod,
            "create_retell_web_call",
            new=AsyncMock(
                return_value=RetellCreateWebCallResult(success=True, call_id="call_xyz")
            ),
        ),
        patch.object(retell_mod, "get_retell_call", new=AsyncMock(return_value=errored_call)),
    ):
        with pytest.raises(Exception, match="error_user_not_joined"):
            await engine.run_test_case(RetellEngineConfig(), args, session)


def test_dummy_datetime_compat() -> None:
    # Smoke test ensuring datetime usage compiles (guards against import drift).
    assert datetime.now(UTC).year >= 2024
