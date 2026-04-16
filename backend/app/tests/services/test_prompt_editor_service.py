"""Unit tests for :class:`~app.services.prompt_editor.core.PromptEditor` (mocked LLM)."""

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import patch

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode
from app.services.llm import (
    LLMCallConfig,
    LLMMessage,
    LLMStreamChunk,
    LLMStreamResult,
    LLMToolCall,
)
from app.services.prompt_editor.core import EditorInput, EditorStreamEvent, PromptEditor


def _agent() -> Agent:
    return Agent(
        name="Ed",
        mode=AgentMode.PLATFORM,
        system_prompt="s",
        agent_model="gpt-4o-mini",
        agent_provider="openai",
        tools=None,
    )


def _stream_factory(
    *,
    chunks: list[LLMStreamChunk],
    final: LLMStreamResult,
) -> AsyncGenerator[LLMStreamChunk | LLMStreamResult, None]:
    async def gen() -> AsyncGenerator[LLMStreamChunk | LLMStreamResult, None]:
        for c in chunks:
            yield c
        yield final

    return gen()


def _multi_turn_mock(
    turns: list[LLMStreamResult],
) -> Any:
    """Return a ``side_effect`` callable that yields a different stream per call.

    Each entry in *turns* becomes one LLM call; the continuation loop drives
    subsequent calls.
    """
    it = iter(turns)

    def factory(
        _messages: list[LLMMessage],
        _config: LLMCallConfig,
        *,
        app_settings: object | None = None,
    ) -> AsyncGenerator[LLMStreamChunk | LLMStreamResult, None]:
        _ = app_settings
        result = next(it)

        async def gen() -> AsyncGenerator[LLMStreamChunk | LLMStreamResult, None]:
            yield result

        return gen()

    return factory


@pytest.mark.asyncio
async def test_run_stream_happy_path_with_edits() -> None:
    current = "a\nb"
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="fix line 2",
        current_prompt=current,
        eval_context=None,
    )
    editor = PromptEditor(inp)
    turn0 = LLMStreamResult(
        full_content="Replacing second line.",
        tool_calls=[
            LLMToolCall(
                id="1",
                function_name="edit_prompt",
                arguments={"start_line": 2, "end_line": 2, "new_content": "B2"},
            )
        ],
        usage={"prompt_tokens": 1, "completion_tokens": 2},
        model="gpt-4o-mini",
        latency_ms=42,
        response_cost_usd=0.001,
    )
    turn1_stop = LLMStreamResult(
        full_content="",
        tool_calls=[],
        usage={"prompt_tokens": 3, "completion_tokens": 1},
        model="gpt-4o-mini",
        latency_ms=10,
        response_cost_usd=0.0002,
    )
    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        side_effect=_multi_turn_mock([turn0, turn1_stop]),
    ):
        events = [e async for e in editor.run_stream()]

    types = [e.type for e in events]
    assert types[0] == "status" and events[0].data["phase"] == "analyzing"
    assert "editing" in [e.data.get("phase") for e in events if e.type == "status"]
    assert events[-1].type == "done"
    result = events[-1].data["result"]
    assert "Replacing second line." in result.content
    assert result.edited_prompt == "a\nB2"
    assert result.edit_snapshots == ["a\nB2"]
    assert result.latency_ms == 52
    assert result.token_usage == {"prompt_tokens": 4, "completion_tokens": 3}
    assert result.cost_usd == pytest.approx(0.0012)
    assert result.tool_calls_payload is not None


@pytest.mark.asyncio
async def test_run_stream_no_edits_keeps_current_prompt() -> None:
    current = "only\nlines"
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="thoughts only",
        current_prompt=current,
        eval_context=None,
    )
    editor = PromptEditor(inp)
    final = LLMStreamResult(
        full_content="I suggest you review tone.",
        tool_calls=[],
        usage={},
        model="m",
        latency_ms=0,
        response_cost_usd=None,
    )
    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        return_value=_stream_factory(chunks=[], final=final),
    ):
        events = [e async for e in editor.run_stream()]

    assert events[-1].type == "done"
    result = events[-1].data["result"]
    assert result.edited_prompt == current
    assert result.edit_snapshots == []
    assert result.tool_calls_payload is None


@pytest.mark.asyncio
async def test_run_stream_invalid_edits_dropped_valid_applied() -> None:
    current = "a\nb"
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="edit",
        current_prompt=current,
        eval_context=None,
    )
    editor = PromptEditor(inp)
    turn0 = LLMStreamResult(
        full_content="x",
        tool_calls=[
            LLMToolCall(
                id="bad",
                function_name="edit_prompt",
                arguments={"start_line": 99, "end_line": 99, "new_content": "nope"},
            ),
            LLMToolCall(
                id="ok",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "A2"},
            ),
        ],
        usage={},
        model="m",
        latency_ms=1,
        response_cost_usd=None,
    )
    turn1_stop = LLMStreamResult(
        full_content="",
        tool_calls=[],
        usage={},
        model="m",
        latency_ms=0,
        response_cost_usd=None,
    )
    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        side_effect=_multi_turn_mock([turn0, turn1_stop]),
    ):
        events = [e async for e in editor.run_stream()]

    result = events[-1].data["result"]
    assert result.edited_prompt == "A2\nb"
    assert result.edit_snapshots == ["A2\nb"]


@pytest.mark.asyncio
async def test_run_stream_llm_raises_yields_error() -> None:
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="x",
        current_prompt="p",
        eval_context=None,
    )
    editor = PromptEditor(inp)

    async def boom():
        msg = "stream failed"
        raise RuntimeError(msg)
        yield LLMStreamChunk(content="x")  # pragma: no cover

    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        return_value=boom(),
    ):
        events = [e async for e in editor.run_stream()]

    assert len(events) == 2
    assert events[0].type == "status"
    assert events[1].type == "error"
    assert "LLM call failed" in events[1].data["detail"]


@pytest.mark.asyncio
async def test_run_stream_value_error_yields_error() -> None:
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="x",
        current_prompt="p",
        eval_context=None,
    )
    editor = PromptEditor(inp)

    async def bad_config():
        raise ValueError("missing model")
        yield LLMStreamChunk(content="x")  # pragma: no cover

    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        return_value=bad_config(),
    ):
        events = [e async for e in editor.run_stream()]

    assert events[-1].type == "error"
    assert events[-1].data["detail"] == "missing model"


@pytest.mark.asyncio
async def test_run_stream_disconnected_stops_without_done() -> None:
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="x",
        current_prompt="a\nb",
        eval_context=None,
    )
    editor = PromptEditor(inp)

    async def long_stream():
        yield LLMStreamChunk(content="x")
        yield LLMStreamResult(
            full_content="",
            tool_calls=[],
            usage={},
            model="m",
            latency_ms=0,
            response_cost_usd=None,
        )

    async def always_dc() -> bool:
        return True

    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        return_value=long_stream(),
    ):
        events = [e async for e in editor.run_stream(is_disconnected=always_dc)]

    assert all(e.type != "done" for e in events)


@pytest.mark.asyncio
async def test_run_stream_forwards_llm_provider_and_model() -> None:
    current = "a\nb"
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="fix line 2",
        current_prompt=current,
        eval_context=None,
        llm_provider="anthropic",
        llm_model="claude-3-5-sonnet-20241022",
    )
    editor = PromptEditor(inp)
    final = LLMStreamResult(
        full_content="done",
        tool_calls=[
            LLMToolCall(
                id="1",
                function_name="edit_prompt",
                arguments={"start_line": 2, "end_line": 2, "new_content": "B2"},
            )
        ],
        usage={},
        model="claude-3-5-sonnet-20241022",
        latency_ms=1,
        response_cost_usd=None,
    )

    async def mock_call_llm_stream(
        _messages: object,
        config: LLMCallConfig,
        *,
        app_settings: object | None = None,
    ):
        _ = app_settings
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.35
        yield final

    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        side_effect=mock_call_llm_stream,
    ):
        events = [e async for e in editor.run_stream()]

    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_run_stream_omitted_llm_overrides_pass_none_in_config() -> None:
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="x",
        current_prompt="a\nb",
        eval_context=None,
    )
    editor = PromptEditor(inp)
    final = LLMStreamResult(
        full_content="",
        tool_calls=[
            LLMToolCall(
                id="1",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "A"},
            )
        ],
        usage={},
        model="gpt-4o-mini",
        latency_ms=0,
        response_cost_usd=None,
    )

    async def mock_call_llm_stream(
        _messages: object,
        config: LLMCallConfig,
        *,
        app_settings: object | None = None,
    ):
        _ = app_settings
        assert config.provider is None
        assert config.model is None
        yield final

    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        side_effect=mock_call_llm_stream,
    ):
        events = [e async for e in editor.run_stream()]

    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_run_stream_continuation_loop_applies_edits_across_turns() -> None:
    """Model emits one edit per turn; loop should apply both and merge results."""
    current = "a\nb\nc"
    inp = EditorInput(
        agent=_agent(),
        session_messages=[],
        user_message="fix both lines",
        current_prompt=current,
        eval_context=None,
    )
    editor = PromptEditor(inp)

    turn0 = LLMStreamResult(
        full_content="Updating line 1.",
        tool_calls=[
            LLMToolCall(
                id="t0",
                function_name="edit_prompt",
                arguments={"start_line": 1, "end_line": 1, "new_content": "A2"},
            )
        ],
        usage={"prompt_tokens": 10, "completion_tokens": 5},
        model="gpt-4o-mini",
        latency_ms=30,
        response_cost_usd=0.001,
    )
    # After turn0, prompt is "A2\nb\nc". Line 3 is still "c".
    turn1 = LLMStreamResult(
        full_content="Now updating line 3.",
        tool_calls=[
            LLMToolCall(
                id="t1",
                function_name="edit_prompt",
                arguments={"start_line": 3, "end_line": 3, "new_content": "C2"},
            )
        ],
        usage={"prompt_tokens": 15, "completion_tokens": 6},
        model="gpt-4o-mini",
        latency_ms=25,
        response_cost_usd=0.0005,
    )
    turn2_stop = LLMStreamResult(
        full_content="Done.",
        tool_calls=[],
        usage={"prompt_tokens": 5, "completion_tokens": 1},
        model="gpt-4o-mini",
        latency_ms=5,
        response_cost_usd=0.0001,
    )

    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        side_effect=_multi_turn_mock([turn0, turn1, turn2_stop]),
    ):
        events: list[EditorStreamEvent] = [e async for e in editor.run_stream()]

    edit_events = [e for e in events if e.type == "edit"]
    assert len(edit_events) == 2
    assert edit_events[0].data["edited_prompt"] == "A2\nb\nc"
    assert edit_events[0].data["edit_index"] == 0
    assert edit_events[1].data["edited_prompt"] == "A2\nb\nC2"
    assert edit_events[1].data["edit_index"] == 1

    assert events[-1].type == "done"
    result = events[-1].data["result"]
    assert result.edited_prompt == "A2\nb\nC2"
    assert len(result.edit_snapshots) == 2
    assert "Updating line 1." in result.content
    assert "Now updating line 3." in result.content
    assert "Done." in result.content
    # Costs/latency/usage accumulated across all three turns
    assert result.latency_ms == 60
    assert result.token_usage == {"prompt_tokens": 30, "completion_tokens": 12}
    assert result.cost_usd == pytest.approx(0.0016)
    assert result.tool_calls_payload is not None
    assert len(result.tool_calls_payload) == 2
