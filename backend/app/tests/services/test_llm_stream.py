from collections.abc import AsyncGenerator
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from litellm.exceptions import RateLimitError

from app.services.llm import (
    LLMCallConfig,
    LLMMessage,
    LLMStreamChunk,
    LLMStreamResult,
    call_llm_stream,
    collect_stream,
)


@dataclass
class _FakeLLMSettings:
    LLM_DEFAULT_MODEL: str = "gpt-4.1-nano"
    LLM_DEFAULT_PROVIDER: str | None = None
    LLM_RETRY_MAX_ATTEMPTS: int = 5
    LLM_RETRY_MIN_WAIT_SECONDS: float = 0.01
    LLM_RETRY_MAX_WAIT_SECONDS: float = 0.05

    @property
    def default_llm_id(self) -> str:
        from app.services.llm import resolve_litellm_model

        return resolve_litellm_model(self.LLM_DEFAULT_MODEL, self.LLM_DEFAULT_PROVIDER)


def _chunk(
    *,
    content: str | None = None,
    tool_calls: list[SimpleNamespace] | None = None,
    finish_reason: str | None = None,
    usage: SimpleNamespace | None = None,
    model: str | None = "gpt-4.1-nano",
    response_cost: float | None = None,
) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(delta=delta, finish_reason=finish_reason)
    hidden = {"response_cost": response_cost} if response_cost is not None else {}
    return SimpleNamespace(
        choices=[choice],
        model=model,
        usage=usage,
        _hidden_params=hidden,
    )


def _usage_ns() -> SimpleNamespace:
    return SimpleNamespace(
        prompt_tokens=2,
        completion_tokens=5,
        total_tokens=7,
    )


async def _text_only_stream() -> AsyncGenerator[SimpleNamespace, None]:
    yield _chunk(content="hello ")
    yield _chunk(content="world")
    yield _chunk(
        content=None,
        finish_reason="stop",
        usage=_usage_ns(),
        response_cost=0.0001,
    )


@pytest.mark.asyncio
async def test_call_llm_stream_text_only_yields_chunks_then_result() -> None:
    fake = _FakeLLMSettings()
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: _text_only_stream(),
    ) as mock_completion:
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="hi")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        ):
            items.append(item)

    assert mock_completion.await_count == 1
    assert mock_completion.await_args is not None
    kw = mock_completion.await_args.kwargs
    assert kw["stream"] is True
    assert kw["stream_options"] == {"include_usage": True}

    chunks = [x for x in items if isinstance(x, LLMStreamChunk)]
    results = [x for x in items if isinstance(x, LLMStreamResult)]
    assert len(chunks) == 2
    assert chunks[0].content == "hello "
    assert chunks[1].content == "world"
    assert len(results) == 1
    r = results[0]
    assert r.full_content == "hello world"
    assert r.tool_calls == []
    assert r.usage["total_tokens"] == 7
    assert r.model == "gpt-4.1-nano"
    assert r.response_cost_usd == pytest.approx(0.0001)
    assert r.latency_ms >= 0


async def _stream_with_tool_calls() -> AsyncGenerator[SimpleNamespace, None]:
    yield _chunk(content="Thinking: ")
    yield _chunk(
        content=None,
        tool_calls=[
            SimpleNamespace(
                index=0,
                id="call_1",
                function=SimpleNamespace(name="edit_", arguments=None),
            )
        ],
    )
    yield _chunk(
        content=None,
        tool_calls=[
            SimpleNamespace(
                index=0,
                id="",
                function=SimpleNamespace(name="prompt", arguments='{"start_'),
            )
        ],
    )
    yield _chunk(
        content=None,
        tool_calls=[
            SimpleNamespace(
                index=0,
                id="",
                function=SimpleNamespace(
                    name="",
                    arguments='line": 1, "end_line": 1, "new_content": "x"}',
                ),
            )
        ],
    )
    yield _chunk(
        content=None,
        finish_reason="tool_calls",
        usage=_usage_ns(),
    )


@pytest.mark.asyncio
async def test_call_llm_stream_accumulates_tool_calls() -> None:
    fake = _FakeLLMSettings()
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: _stream_with_tool_calls(),
    ):
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="edit")],
            LLMCallConfig(model="gpt-4.1-nano", tools=[{"type": "function"}]),
            app_settings=fake,
        ):
            items.append(item)

    chunks = [x for x in items if isinstance(x, LLMStreamChunk)]
    results = [x for x in items if isinstance(x, LLMStreamResult)]
    assert len(chunks) == 1
    assert chunks[0].content == "Thinking: "
    assert len(results) == 1
    r = results[0]
    assert r.full_content == "Thinking: "
    assert len(r.tool_calls) == 1
    assert r.tool_calls[0].function_name == "edit_prompt"
    assert r.tool_calls[0].arguments["start_line"] == 1
    assert r.tool_calls[0].arguments["end_line"] == 1
    assert r.tool_calls[0].arguments["new_content"] == "x"


async def _multi_tool_stream() -> AsyncGenerator[SimpleNamespace, None]:
    yield _chunk(
        content=None,
        tool_calls=[
            SimpleNamespace(
                index=0,
                id="a",
                function=SimpleNamespace(name="edit_prompt", arguments='{"x": 1}'),
            ),
            SimpleNamespace(
                index=1,
                id="b",
                function=SimpleNamespace(name="edit_prompt", arguments='{"y": 2}'),
            ),
        ],
    )
    yield _chunk(content=None, finish_reason="tool_calls", usage=_usage_ns())


@pytest.mark.asyncio
async def test_call_llm_stream_multiple_tool_calls_by_index() -> None:
    fake = _FakeLLMSettings()
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: _multi_tool_stream(),
    ):
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="x")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        ):
            items.append(item)

    r = next(x for x in items if isinstance(x, LLMStreamResult))
    assert len(r.tool_calls) == 2
    assert r.tool_calls[0].arguments == {"x": 1}
    assert r.tool_calls[1].arguments == {"y": 2}


async def _malformed_and_valid_stream() -> AsyncGenerator[SimpleNamespace, None]:
    yield _chunk(
        content=None,
        tool_calls=[
            SimpleNamespace(
                index=0,
                id="bad",
                function=SimpleNamespace(name="bad_tool", arguments="{not json"),
            ),
            SimpleNamespace(
                index=1,
                id="good",
                function=SimpleNamespace(name="ok", arguments='{"ok": true}'),
            ),
        ],
    )
    yield _chunk(content=None, finish_reason="stop", usage=_usage_ns())


@pytest.mark.asyncio
async def test_call_llm_stream_malformed_tool_arguments_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = _FakeLLMSettings()
    caplog.set_level("WARNING")
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: _malformed_and_valid_stream(),
    ):
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="x")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        ):
            items.append(item)

    r = next(x for x in items if isinstance(x, LLMStreamResult))
    assert len(r.tool_calls) == 1
    assert r.tool_calls[0].function_name == "ok"
    assert "Malformed tool call arguments" in caplog.text


@pytest.mark.asyncio
async def test_call_llm_stream_retries_initial_acompletion_on_rate_limit() -> None:
    fake = _FakeLLMSettings(LLM_RETRY_MAX_ATTEMPTS=4)
    transient = RateLimitError("slow", llm_provider="openai", model="gpt-4.1-nano")

    async def ok_stream() -> AsyncGenerator[SimpleNamespace, None]:
        yield _chunk(content="ok", finish_reason="stop", usage=_usage_ns())

    ok_chunks = ok_stream()

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=[transient, ok_chunks],
    ) as mock_completion:
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="z")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        ):
            items.append(item)

    assert mock_completion.await_count == 2
    r = next(x for x in items if isinstance(x, LLMStreamResult))
    assert r.full_content == "ok"


@pytest.mark.asyncio
async def test_collect_stream_returns_only_final_result() -> None:
    fake = _FakeLLMSettings()
    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: _text_only_stream(),
    ):
        result = await collect_stream(
            call_llm_stream(
                [LLMMessage(role="user", content="hi")],
                LLMCallConfig(model="gpt-4.1-nano"),
                app_settings=fake,
            )
        )
    assert isinstance(result, LLMStreamResult)
    assert result.full_content == "hello world"


@pytest.mark.asyncio
async def test_call_llm_stream_mid_stream_error_yields_partial_without_tools() -> None:
    fake = _FakeLLMSettings()

    async def broken_stream() -> AsyncGenerator[SimpleNamespace, None]:
        yield _chunk(content="part")
        msg = "connection reset"
        raise RuntimeError(msg)

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: broken_stream(),
    ):
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="x")],
            LLMCallConfig(model="gpt-4.1-nano"),
            app_settings=fake,
        ):
            items.append(item)

    chunks = [x for x in items if isinstance(x, LLMStreamChunk)]
    results = [x for x in items if isinstance(x, LLMStreamResult)]
    assert len(chunks) == 1
    assert chunks[0].content == "part"
    assert len(results) == 1
    assert results[0].full_content == "part"
    assert results[0].tool_calls == []


@pytest.mark.asyncio
async def test_call_llm_stream_passes_stream_and_stream_options() -> None:
    fake = _FakeLLMSettings()

    async def empty_stream() -> AsyncGenerator[SimpleNamespace, None]:
        if False:  # pragma: no cover
            yield _chunk()

    with patch(
        "app.services.llm.litellm.acompletion",
        new_callable=AsyncMock,
        side_effect=lambda **kw: empty_stream(),
    ) as mock_completion:
        items: list[LLMStreamChunk | LLMStreamResult] = []
        async for item in call_llm_stream(
            [LLMMessage(role="user", content="x")],
            LLMCallConfig(model="gpt-4.1-nano", tools=[{"type": "function"}]),
            app_settings=fake,
        ):
            items.append(item)

    assert mock_completion.await_args is not None
    kw = mock_completion.await_args.kwargs
    assert kw["stream"] is True
    assert kw["stream_options"] == {"include_usage": True}
    assert kw["tools"] == [{"type": "function"}]
    assert len(items) == 1
    assert isinstance(items[0], LLMStreamResult)
