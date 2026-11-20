from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.enums import SimulatorMode, TurnRole
from app.models.schemas import (
    ConversationTurn,
    RetellRuntimeConfig,
    RunConfig,
    ToolCall,
    ToolCallFunction,
    UserSimulatorConfig,
)


def _round_trip(model_class, instance):
    """Serialize to dict, then validate back — assert equality."""
    data = instance.model_dump()
    restored = model_class.model_validate(data)
    assert restored == instance
    return restored


# ── ExpectedToolCall ──────────────────────────────────────────────


# ── ToolPlatformConfig ────────────────────────────────────────────


# ── PythonImplementation ──────────────────────────────────────────


# ── HttpWebhookImplementation ─────────────────────────────────────


# ── ToolPlatformConfig JSON round-trip (JSONB simulation) ─────────


# ── ToolCall ───────────────────────────────────────────────────────


def test_tool_call_minimal():
    tc = ToolCall(
        id="call_search1",
        function=ToolCallFunction(
            name="search",
            arguments='{"query": "test"}',
        ),
    )
    restored = _round_trip(ToolCall, tc)
    assert restored.tool_result is None


def test_tool_call_with_result():
    tc = ToolCall(
        id="call_balance1",
        function=ToolCallFunction(
            name="get_balance",
            arguments='{"account_id": "123"}',
        ),
        tool_result={"balance": 42.50, "currency": "USD"},
    )
    _round_trip(ToolCall, tc)


# ── ConversationTurn ───────────────────────────────────────────────


def test_conversation_turn_minimal():
    turn = ConversationTurn(
        index=0,
        role=TurnRole.USER,
        content="Hello",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    restored = _round_trip(ConversationTurn, turn)
    assert restored.tool_calls is None
    assert restored.latency_ms is None


def test_conversation_turn_with_tool_calls():
    turn = ConversationTurn(
        index=1,
        role=TurnRole.ASSISTANT,
        content="Let me look that up.",
        tool_calls=[
            ToolCall(
                id="call_w1",
                function=ToolCallFunction(name="search", arguments='{"q": "weather"}'),
            ),
            ToolCall(
                id="call_w2",
                function=ToolCallFunction(
                    name="format",
                    arguments='{"template": "result"}',
                ),
                tool_result="Sunny, 72F",
            ),
        ],
        latency_ms=250,
        token_count=150,
        timestamp=datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
    )
    restored = _round_trip(ConversationTurn, turn)
    assert len(restored.tool_calls) == 2
    assert restored.tool_calls[0].function.name == "search"
    assert restored.tool_calls[1].tool_result == "Sunny, 72F"


def test_conversation_turn_enum_serialization():
    """Enum values serialize as strings and deserialize back."""
    for role in TurnRole:
        turn = ConversationTurn(
            index=0,
            role=role,
            content="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        data = turn.model_dump()
        assert data["role"] == role.value
        restored = ConversationTurn.model_validate(data)
        assert restored.role == role


# ── MetricScore ─────────────────────────────────────────────────


# ── JudgeVerdict ───────────────────────────────────────────────────


# ── RunConfig ──────────────────────────────────────────────────────


def test_run_config_requires_runtime():
    with pytest.raises(ValidationError):
        RunConfig()  # type: ignore[call-arg]


def test_run_config_defaults():
    config = RunConfig(runtime=RetellRuntimeConfig())
    restored = _round_trip(RunConfig, config)
    assert restored.concurrency == 5
    assert restored.timeout_per_test_case_ms == 120_000
    assert restored.user_simulator is None


def test_user_simulator_config_round_trip():
    cfg = UserSimulatorConfig(
        mode=SimulatorMode.SCRIPTED,
        scripted_messages=["hi", "thanks"],
        model="gpt-4o-mini",
        provider="openai",
        temperature=0.2,
    )
    restored = _round_trip(UserSimulatorConfig, cfg)
    assert restored.scripted_messages == ["hi", "thanks"]


def test_run_config_with_user_simulator_round_trip():
    config = RunConfig(
        user_simulator=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["a"],
            model="base-model",
            provider="openai",
            temperature=0.5,
        ),
        runtime=RetellRuntimeConfig(),
    )
    restored = _round_trip(RunConfig, config)
    assert restored.user_simulator is not None
    assert restored.user_simulator.mode == SimulatorMode.SCRIPTED


# ── AggregateMetrics ───────────────────────────────────────────────


# ── JSON round-trip (simulates JSONB storage) ──────────────────────
