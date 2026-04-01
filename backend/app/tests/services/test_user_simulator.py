from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import SimulatorMode
from app.models.schemas import Persona, UserSimulatorConfig
from app.services.llm import LLMMessage, LLMResponse
from app.services.user_simulator import UserSimulator, _build_system_prompt


def _persona() -> Persona:
    return Persona(
        type="shopper",
        description="A careful online shopper.",
        instructions="Ask concise questions about shipping and returns.",
    )


def test_get_initial_message() -> None:
    sim = UserSimulator(
        persona=_persona(),
        initial_message="Do you ship to Canada?",
        user_context=None,
        expected_outcomes=None,
        config=UserSimulatorConfig(mode=SimulatorMode.LLM),
    )
    assert sim.get_initial_message() == "Do you ship to Canada?"


@pytest.mark.asyncio
async def test_llm_mode_generates_message() -> None:
    resp = LLMResponse(
        content="  What is the return policy?  ",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        latency_ms=42,
    )
    sim = UserSimulator(
        persona=_persona(),
        initial_message="Hi",
        user_context=None,
        expected_outcomes=None,
        config=UserSimulatorConfig(mode=SimulatorMode.LLM, model="gpt-4o-mini"),
    )
    with patch(
        "app.services.user_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_llm:
        out = await sim.generate_message(
            [LLMMessage(role="user", content="We ship worldwide.")]
        )

    assert out.content == "What is the return policy?"
    assert out.latency_ms == 42
    assert out.token_usage["total_tokens"] == 15
    mock_llm.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_mode_prepends_system_prompt() -> None:
    resp = LLMResponse(
        content="ok",
        model="m",
        usage={},
        latency_ms=1,
    )
    sim = UserSimulator(
        persona=_persona(),
        initial_message="x",
        user_context=None,
        expected_outcomes=None,
        config=UserSimulatorConfig(mode=SimulatorMode.LLM, model="gpt-4o-mini"),
    )
    with patch(
        "app.services.user_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_llm:
        await sim.generate_message([])

    messages = mock_llm.await_args.args[0]
    assert messages[0].role == "system"
    assert "simulating the USER" in messages[0].content
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_llm_mode_system_prompt_contains_persona() -> None:
    resp = LLMResponse(content="x", model="m", usage={}, latency_ms=1)
    persona = _persona()
    sim = UserSimulator(
        persona=persona,
        initial_message="x",
        user_context=None,
        expected_outcomes=None,
        config=UserSimulatorConfig(mode=SimulatorMode.LLM, model="gpt-4o-mini"),
    )
    with patch(
        "app.services.user_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_llm:
        await sim.generate_message([])

    system = mock_llm.await_args.args[0][0].content
    assert persona.type in system
    assert persona.description in system
    assert persona.instructions in system


@pytest.mark.asyncio
async def test_llm_mode_system_prompt_contains_context() -> None:
    resp = LLMResponse(content="x", model="m", usage={}, latency_ms=1)
    ctx = {"order_id": "123"}
    outcomes = {"must": "get refund policy"}
    sim = UserSimulator(
        persona=_persona(),
        initial_message="x",
        user_context=ctx,
        expected_outcomes=outcomes,
        config=UserSimulatorConfig(mode=SimulatorMode.LLM, model="gpt-4o-mini"),
    )
    with patch(
        "app.services.user_simulator.call_llm",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_llm:
        await sim.generate_message([])

    system = mock_llm.await_args.args[0][0].content
    assert "123" in system
    assert "refund" in system


@pytest.mark.asyncio
async def test_scripted_mode_returns_messages_in_order() -> None:
    sim = UserSimulator(
        persona=_persona(),
        initial_message="First",
        user_context=None,
        expected_outcomes=None,
        config=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["Second", "Third"],
        ),
    )
    assert sim.get_initial_message() == "First"
    a = await sim.generate_message([])
    b = await sim.generate_message([])
    assert a.content == "Second"
    assert b.content == "Third"
    assert a.latency_ms == 0


@pytest.mark.asyncio
async def test_scripted_mode_is_exhausted() -> None:
    sim = UserSimulator(
        persona=_persona(),
        initial_message="x",
        user_context=None,
        expected_outcomes=None,
        config=UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=["only"],
        ),
    )
    assert not sim.is_exhausted
    await sim.generate_message([])
    assert sim.is_exhausted


@pytest.mark.asyncio
async def test_scripted_mode_raises_when_exhausted() -> None:
    # Empty scripted list is invalid for UserSimulatorConfig validation; use
    # model_construct to simulate an already-exhausted scripted buffer.
    bad_config = UserSimulatorConfig.model_construct(
        mode=SimulatorMode.SCRIPTED,
        scripted_messages=[],
    )
    sim = UserSimulator(
        persona=_persona(),
        initial_message="x",
        user_context=None,
        expected_outcomes=None,
        config=bad_config,
    )
    assert sim.is_exhausted
    with pytest.raises(RuntimeError, match="No more scripted"):
        await sim.generate_message([])


def test_build_system_prompt_with_none_context() -> None:
    text = _build_system_prompt(_persona(), None, None)
    assert "shopper" in text
    assert "(none)" in text
