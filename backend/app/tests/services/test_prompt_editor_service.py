"""Unit tests for :class:`~app.services.prompt_editor.core.PromptEditor` (mocked LLM)."""

from unittest.mock import patch

import pytest

from app.models.agent import Agent
from app.models.enums import AgentMode
from app.services.llm import LLMStreamChunk, LLMStreamResult, LLMToolCall
from app.services.prompt_editor.core import EditorInput, PromptEditor


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
):
    async def gen():
        for c in chunks:
            yield c
        yield final

    return gen()


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
    final = LLMStreamResult(
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
    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        return_value=_stream_factory(
            chunks=[LLMStreamChunk(content="Let me ")],
            final=final,
        ),
    ):
        events = [e async for e in editor.run_stream()]

    types = [e.type for e in events]
    assert types[0] == "status" and events[0].data["phase"] == "analyzing"
    assert "reasoning" in types
    assert "editing" in [e.data.get("phase") for e in events if e.type == "status"]
    assert events[-1].type == "done"
    result = events[-1].data["result"]
    assert result.content == "Replacing second line."
    assert result.edited_prompt == "a\nB2"
    assert result.edit_snapshots == ["a\nB2"]
    assert result.latency_ms == 42
    assert result.token_usage == {"prompt_tokens": 1, "completion_tokens": 2}
    assert result.cost_usd == 0.001
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
    final = LLMStreamResult(
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
    with patch(
        "app.services.prompt_editor.core.call_llm_stream",
        return_value=_stream_factory(chunks=[], final=final),
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
