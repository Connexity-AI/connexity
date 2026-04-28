from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from litellm.exceptions import RateLimitError

from app.services.llm import (
    LLMCallConfig,
    LLMMessage,
    _llm_message_to_litellm_dict,
    call_llm,
    resolve_litellm_model,
)


@dataclass
class _FakeLLMSettings:
    LLM_DEFAULT_MODEL: str | None = "gpt-4.1-nano"
    LLM_DEFAULT_PROVIDER: str | None = None
    LLM_RETRY_MAX_ATTEMPTS: int = 5
    LLM_RETRY_MIN_WAIT_SECONDS: float = 0.01
    LLM_RETRY_MAX_WAIT_SECONDS: float = 0.05


def _fake_response(
    *, content: str = "ok", model: str = "gpt-4.1-nano"
) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(prompt_tokens=3, completion_tokens=7, total_tokens=10)
    return SimpleNamespace(
        choices=[choice],
        model=model,
        usage=usage,
        _hidden_params={"response_cost": 0.00042},
    )


@pytest.mark.asyncio
async def test_call_llm_success_maps_response() -> None:
    fake = _FakeLLMSettings()
    resp = _fake_response(content="hello", model="gpt-4.1-nano")
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_completion:
        out = await call_llm(
            [LLMMessage(role="user", content="hi")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        )
    assert out.content == "hello"
    assert out.model == "gpt-4.1-nano"
    assert out.usage == {
        "prompt_tokens": 3,
        "completion_tokens": 7,
        "total_tokens": 10,
    }
    assert out.latency_ms is not None
    assert out.response_cost_usd == pytest.approx(0.00042)
    mock_completion.assert_awaited_once()
    assert mock_completion.await_args is not None
    _call_kw = mock_completion.await_args.kwargs
    assert _call_kw["model"] == "gpt-4.1-nano"
    assert _call_kw["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_call_llm_strips_reasoning_knobs_from_extra() -> None:
    fake = _FakeLLMSettings()
    resp = _fake_response()
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_completion:
        await call_llm(
            [LLMMessage(role="user", content="hi")],
            LLMCallConfig(
                model="gpt-4.1-nano",
                extra={
                    "reasoning_effort": "high",
                    "thinking": "disabled",
                    "seed": 42,
                },
            ),
            app_settings=fake,
        )
    assert mock_completion.await_args is not None
    kw = mock_completion.await_args.kwargs
    assert "reasoning_effort" not in kw
    assert "thinking" not in kw
    assert kw.get("seed") == 42


@pytest.mark.asyncio
async def test_call_llm_sets_reasoning_effort_none_when_supports_reasoning() -> None:
    fake = _FakeLLMSettings()
    resp = _fake_response()
    with (
        patch(
            "app.services.llm.litellm.acompletion",
            new_callable=AsyncMock,
            return_value=resp,
        ) as mock_completion,
        patch("app.services.llm.supports_reasoning", return_value=True),
    ):
        await call_llm(
            [LLMMessage(role="user", content="hi")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        )
    assert mock_completion.await_args is not None
    assert mock_completion.await_args.kwargs["reasoning_effort"] == "none"


@pytest.mark.parametrize(
    ("model", "provider", "expected"),
    [
        (
            "claude-3-5-sonnet-20241022",
            "anthropic",
            "anthropic/claude-3-5-sonnet-20241022",
        ),
        ("gpt-4o", "openai", "openai/gpt-4o"),
        ("anthropic/claude-x", None, "anthropic/claude-x"),
        ("gpt-4o", None, "gpt-4o"),
    ],
)
def test_resolve_litellm_model(model: str, provider: str | None, expected: str) -> None:
    assert resolve_litellm_model(model, provider) == expected


@pytest.mark.asyncio
async def test_call_llm_retries_on_rate_limit() -> None:
    fake = _FakeLLMSettings(LLM_RETRY_MAX_ATTEMPTS=4)
    ok = _fake_response()
    transient = RateLimitError("slow down", llm_provider="openai", model="gpt-4.1-nano")
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[transient, transient, ok],
    ) as mock_completion:
        out = await call_llm(
            [LLMMessage(role="user", content="x")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        )
    assert out.content == "ok"
    assert mock_completion.await_count == 3


@pytest.mark.asyncio
async def test_call_llm_merges_global_default_model() -> None:
    fake = _FakeLLMSettings(LLM_DEFAULT_MODEL="gpt-4o", LLM_DEFAULT_PROVIDER="openai")
    resp = _fake_response()
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_completion:
        await call_llm(
            [LLMMessage(role="user", content="y")],
            app_settings=fake,
        )
    assert mock_completion.await_args is not None
    assert mock_completion.await_args.kwargs["model"] == "openai/gpt-4o"


@pytest.mark.asyncio
async def test_call_llm_raises_when_no_model_configured() -> None:
    fake = _FakeLLMSettings(LLM_DEFAULT_MODEL=None)
    with (
        patch("app.services.llm.litellm.acompletion", new_callable=AsyncMock),
        pytest.raises(ValueError, match="No LLM model configured"),
    ):
        await call_llm([LLMMessage(role="user", content="z")], app_settings=fake)


def _fake_response_with_tool_calls(
    *,
    content: str = "",
    tool_name: str = "get_weather",
    tool_args: str = '{"city":"NYC"}',
    model: str = "gpt-4.1-nano",
) -> SimpleNamespace:
    fn = SimpleNamespace(name=tool_name, arguments=tool_args)
    tc = SimpleNamespace(id="call_1", type="function", function=fn)
    message = SimpleNamespace(content=content, tool_calls=[tc])
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(prompt_tokens=5, completion_tokens=3, total_tokens=8)
    return SimpleNamespace(
        choices=[choice],
        model=model,
        usage=usage,
        _hidden_params={"response_cost": 0.001},
    )


@pytest.mark.asyncio
async def test_call_llm_passes_tools_to_acompletion() -> None:
    fake = _FakeLLMSettings()
    tools = [{"type": "function", "function": {"name": "get_weather"}}]
    resp = _fake_response(content="sunny")
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=resp,
    ) as mock_completion:
        await call_llm(
            [LLMMessage(role="user", content="weather?")],
            LLMCallConfig(model="gpt-4.1-nano", tools=tools),
            app_settings=fake,
        )
    assert mock_completion.await_args is not None
    assert mock_completion.await_args.kwargs["tools"] == tools


@pytest.mark.asyncio
async def test_call_llm_maps_tool_calls_from_response() -> None:
    fake = _FakeLLMSettings()
    resp = _fake_response_with_tool_calls(content="")
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        return_value=resp,
    ):
        out = await call_llm(
            [LLMMessage(role="user", content="What's the weather?")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        )
    assert out.tool_calls is not None
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0]["id"] == "call_1"
    assert out.tool_calls[0]["function"]["name"] == "get_weather"
    assert out.content == ""


def test_llm_message_to_litellm_dict_includes_tool_fields() -> None:
    d = _llm_message_to_litellm_dict(
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[{"id": "c1", "type": "function", "function": {"name": "f"}}],
        )
    )
    assert d["role"] == "assistant"
    assert d["tool_calls"] is not None
    assert d.get("content") is None

    tool_msg = _llm_message_to_litellm_dict(
        LLMMessage(
            role="tool",
            content='{"ok":true}',
            tool_call_id="c1",
            name="f",
        )
    )
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "c1"
    assert tool_msg["name"] == "f"
    assert tool_msg["content"] == '{"ok":true}'
