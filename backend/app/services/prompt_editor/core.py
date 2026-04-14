"""Prompt editor LLM orchestration: streaming, edit application, structured events."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from app.core.config import settings
from app.services.llm import (
    LLMCallConfig,
    LLMSettingsView,
    LLMStreamChunk,
    LLMStreamResult,
    call_llm_stream,
)
from app.services.prompt_editor.agent_prompt import (
    EDIT_PROMPT_TOOL,
    apply_edits_progressively,
    build_editor_messages,
    get_prompt_line_count,
    llm_tool_calls_to_openai_dicts,
    parse_edit_prompt_tool_calls,
    validate_edits_against_line_count,
)

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.prompt_editor import PromptEditorMessage

logger = logging.getLogger(__name__)

EditorStreamEventType = Literal["reasoning", "status", "edit", "done", "error"]


@dataclass(frozen=True)
class EditorInput:
    """Inputs for one prompt-editor LLM turn (before persistence)."""

    agent: Agent
    session_messages: list[PromptEditorMessage]
    user_message: str
    current_prompt: str
    eval_context: str | None = None


@dataclass
class EditorStreamEvent:
    """Semantic event from :meth:`PromptEditor.run_stream`.

    ``done`` carries an :class:`EditorResult` in ``data`` under key ``"result"``
    (the route persists to the DB, then emits an SSE ``done`` frame).
    """

    type: EditorStreamEventType
    data: dict[str, Any]


@dataclass
class EditorResult:
    """Final LLM outcome for one editor turn (before DB write)."""

    content: str
    tool_calls_payload: list[dict[str, Any]] | None
    edited_prompt: str
    edit_snapshots: list[str]
    latency_ms: int | None
    token_usage: dict[str, int] | None
    cost_usd: float | None


class PromptEditor:
    """Runs the editor LLM stream and yields reasoning, edit snapshots, and a final result."""

    def __init__(self, inp: EditorInput) -> None:
        self._inp = inp
        self._llm_messages = build_editor_messages(
            agent=inp.agent,
            session_messages=inp.session_messages,
            user_message=inp.user_message,
            current_prompt=inp.current_prompt,
            eval_context=inp.eval_context,
        )

    async def run_stream(
        self,
        *,
        app_settings: LLMSettingsView | None = None,
        is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncGenerator[EditorStreamEvent, None]:
        """Stream editor LLM output; last successful event is ``type="done"`` with ``result``."""
        app_settings = app_settings or settings

        yield EditorStreamEvent(type="status", data={"phase": "analyzing"})

        llm_config = LLMCallConfig(
            tools=[EDIT_PROMPT_TOOL],
            max_tokens=8192,
            temperature=0.35,
        )

        stream_result: LLMStreamResult | None = None
        try:
            stream = call_llm_stream(
                self._llm_messages, llm_config, app_settings=app_settings
            )
            async for item in stream:
                if is_disconnected is not None and await is_disconnected():
                    return
                if isinstance(item, LLMStreamChunk) and item.content:
                    yield EditorStreamEvent(
                        type="reasoning",
                        data={"content": item.content},
                    )
                elif isinstance(item, LLMStreamResult):
                    stream_result = item
        except ValueError as exc:
            logger.warning("LLM configuration error: %s", exc)
            yield EditorStreamEvent(type="error", data={"detail": str(exc)})
            return
        except Exception as exc:
            logger.exception("LLM stream failed: %s", exc)
            yield EditorStreamEvent(
                type="error",
                data={"detail": f"LLM call failed: {exc}"},
            )
            return

        if stream_result is None:
            yield EditorStreamEvent(
                type="error",
                data={"detail": "Stream ended without a final result"},
            )
            return

        raw_edits = parse_edit_prompt_tool_calls(stream_result.tool_calls)
        line_count = get_prompt_line_count(self._inp.current_prompt)
        valid_edits = validate_edits_against_line_count(raw_edits, line_count)

        edit_snapshots: list[str] = []
        if valid_edits:
            yield EditorStreamEvent(type="status", data={"phase": "editing"})
            edit_snapshots = apply_edits_progressively(
                self._inp.current_prompt, valid_edits
            )
            total = len(edit_snapshots)
            for idx, snap in enumerate(edit_snapshots):
                if is_disconnected is not None and await is_disconnected():
                    return
                yield EditorStreamEvent(
                    type="edit",
                    data={
                        "edited_prompt": snap,
                        "edit_index": idx,
                        "total_edits": total,
                    },
                )
            final_prompt = edit_snapshots[-1]
        else:
            final_prompt = self._inp.current_prompt

        tool_calls_payload = (
            llm_tool_calls_to_openai_dicts(stream_result.tool_calls)
            if stream_result.tool_calls
            else None
        )

        result = EditorResult(
            content=stream_result.full_content,
            tool_calls_payload=tool_calls_payload,
            edited_prompt=final_prompt,
            edit_snapshots=edit_snapshots,
            latency_ms=stream_result.latency_ms,
            token_usage=dict(stream_result.usage) if stream_result.usage else None,
            cost_usd=stream_result.response_cost_usd,
        )
        yield EditorStreamEvent(type="done", data={"result": result})
