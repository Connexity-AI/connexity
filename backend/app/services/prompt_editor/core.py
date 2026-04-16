"""Prompt editor LLM orchestration: streaming, edit application, structured events.

Supports two modes:

* **Creating** (``current_prompt`` empty) — conversational interview followed by a
  ``generate_prompt`` tool call that produces the full prompt.
* **Editing** (``current_prompt`` non-empty) — incremental ``edit_prompt`` calls with
  an agentic continuation loop (up to ``_MAX_EDIT_CONTINUATION_TURNS`` extra LLM calls)
  to handle models that don't emit all tool calls in a single response.
"""

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.core.config import settings
from app.models.agent import Agent
from app.models.prompt_editor import PromptEditorMessage
from app.services.llm import (
    LLMCallConfig,
    LLMMessage,
    LLMSettingsView,
    LLMStreamChunk,
    LLMStreamResult,
    LLMToolCall,
    call_llm_stream,
)
from app.services.prompt_editor.agent_prompt import (
    EDIT_PROMPT_TOOL,
    GENERATE_PROMPT_TOOL,
    apply_edits_progressively,
    build_continuation_messages,
    build_dynamic_system_message,
    build_editor_messages,
    get_prompt_line_count,
    is_creating_mode,
    llm_tool_calls_to_openai_dicts,
    parse_edit_prompt_tool_calls,
    parse_generate_prompt_tool_call,
    validate_edits_against_line_count,
)

logger = logging.getLogger(__name__)

_PREVIEW_CHARS = 200
_MAX_EDIT_CONTINUATION_TURNS = 3


EditorStreamEventType = Literal["reasoning", "status", "edit", "done", "error"]


def _preview_snippet(text: str, max_chars: int = _PREVIEW_CHARS) -> str:
    """Short, log-safe preview (newlines escaped)."""
    collapsed = text.replace("\n", "\\n")
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 3]}..."


def _format_edit_tuple(edit: tuple[int, int, str]) -> str:
    start_line, end_line, new_content = edit
    preview = _preview_snippet(new_content, 120)
    if start_line > end_line:
        return f"insert_after_line_{start_line} new_content={preview!r}"
    return f"lines_{start_line}-{end_line} new_content={preview!r}"


def _format_edits_for_log(edits: list[tuple[int, int, str]]) -> str:
    if not edits:
        return "[]"
    return "[" + ", ".join(_format_edit_tuple(e) for e in edits) + "]"


def _log_parsed_tool_calls(tool_calls: list[LLMToolCall]) -> None:
    """Log each tool call from the LLM with line ranges and insertion previews."""
    if not tool_calls:
        logger.info("[prompt_editor] llm_tool_calls: (none)")
        return
    for tc in tool_calls:
        if tc.function_name == "edit_prompt":
            args = tc.arguments
            start = args.get("start_line")
            end = args.get("end_line")
            raw_new = args.get("new_content", "")
            new_s = raw_new if isinstance(raw_new, str) else str(raw_new)
            if isinstance(start, int) and isinstance(end, int) and start > end:
                logger.info(
                    "[prompt_editor] llm_tool_call edit_prompt id=%s insert_after_line=%s "
                    "new_content_preview=%r",
                    tc.id,
                    start,
                    _preview_snippet(new_s),
                )
            else:
                logger.info(
                    "[prompt_editor] llm_tool_call edit_prompt id=%s start_line=%s end_line=%s "
                    "new_content_preview=%r",
                    tc.id,
                    start,
                    end,
                    _preview_snippet(new_s),
                )
        elif tc.function_name == "generate_prompt":
            raw = tc.arguments.get("content", "")
            content = raw if isinstance(raw, str) else str(raw)
            logger.info(
                "[prompt_editor] llm_tool_call generate_prompt id=%s content_len=%s preview=%r",
                tc.id,
                len(content),
                _preview_snippet(content, 160),
            )
        else:
            logger.info(
                "[prompt_editor] llm_tool_call %s id=%s arguments=%s",
                tc.function_name,
                tc.id,
                tc.arguments,
            )


def _merge_usage(
    base: dict[str, int] | None, add: dict[str, int] | None
) -> dict[str, int] | None:
    """Sum token-usage dicts; return ``None`` if both are ``None``."""
    if base is None:
        return add
    if add is None:
        return base
    merged = dict(base)
    for k, v in add.items():
        merged[k] = merged.get(k, 0) + v
    return merged


@dataclass(frozen=True)
class EditorInput:
    """Inputs for one prompt-editor LLM turn (before persistence)."""

    agent: Agent
    session_messages: list[PromptEditorMessage]
    user_message: str
    current_prompt: str
    eval_context: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None


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
    """Runs the editor LLM stream and yields reasoning, edit snapshots, and a final result.

    Automatically selects **creating** vs **editing** mode based on whether
    ``current_prompt`` is empty. Editing mode uses an agentic continuation loop
    so the model can emit tool calls across multiple responses.
    """

    def __init__(self, inp: EditorInput) -> None:
        self._inp = inp
        self._creating = is_creating_mode(inp.current_prompt)
        self._llm_messages = build_editor_messages(
            agent=inp.agent,
            session_messages=inp.session_messages,
            user_message=inp.user_message,
            current_prompt=inp.current_prompt,
            eval_context=inp.eval_context,
        )

    # ------------------------------------------------------------------
    # Streaming a single LLM call (shared by both modes)
    # ------------------------------------------------------------------

    async def _stream_one_llm_call(
        self,
        messages: list[LLMMessage],
        llm_config: LLMCallConfig,
        *,
        app_settings: LLMSettingsView,
        is_disconnected: Callable[[], Awaitable[bool]] | None,
    ) -> AsyncGenerator[EditorStreamEvent | LLMStreamResult, None]:
        """Stream one LLM call; yields ``reasoning`` events and a final ``LLMStreamResult``.

        The caller is responsible for handling the ``LLMStreamResult`` (editing
        or creating logic). Errors are yielded as ``EditorStreamEvent(type="error")``.
        """
        try:
            stream = call_llm_stream(messages, llm_config, app_settings=app_settings)
            async for item in stream:
                if is_disconnected is not None and await is_disconnected():
                    return
                if isinstance(item, LLMStreamChunk) and item.content:
                    yield EditorStreamEvent(
                        type="reasoning",
                        data={"content": item.content},
                    )
                elif isinstance(item, LLMStreamResult):
                    yield item
        except ValueError as exc:
            logger.warning("LLM configuration error: %s", exc)
            yield EditorStreamEvent(type="error", data={"detail": str(exc)})
        except Exception as exc:
            logger.exception("LLM stream failed: %s", exc)
            yield EditorStreamEvent(
                type="error",
                data={"detail": f"LLM call failed: {exc}"},
            )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run_stream(
        self,
        *,
        app_settings: LLMSettingsView | None = None,
        is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncGenerator[EditorStreamEvent, None]:
        """Stream editor LLM output; last successful event is ``type="done"`` with ``result``."""
        app_settings = app_settings or settings

        prompt_lines = (
            0 if self._creating else get_prompt_line_count(self._inp.current_prompt)
        )
        logger.info(
            "[prompt_editor] turn_start agent_id=%s creating=%s request_model=%s "
            "request_provider=%s session_prior_messages=%s user_chars=%s prompt_chars=%s "
            "prompt_lines=%s",
            self._inp.agent.id,
            self._creating,
            self._inp.llm_model,
            self._inp.llm_provider,
            len(self._inp.session_messages),
            len(self._inp.user_message),
            len(self._inp.current_prompt),
            prompt_lines,
        )

        yield EditorStreamEvent(type="status", data={"phase": "analyzing"})

        if self._creating:
            async for ev in self._run_creating_mode(
                app_settings=app_settings, is_disconnected=is_disconnected
            ):
                yield ev
        else:
            async for ev in self._run_editing_mode(
                app_settings=app_settings, is_disconnected=is_disconnected
            ):
                yield ev

    # ------------------------------------------------------------------
    # Creating mode: generate_prompt tool call (single-shot)
    # ------------------------------------------------------------------

    async def _run_creating_mode(
        self,
        *,
        app_settings: LLMSettingsView,
        is_disconnected: Callable[[], Awaitable[bool]] | None,
    ) -> AsyncGenerator[EditorStreamEvent, None]:
        llm_config = LLMCallConfig(
            tools=[GENERATE_PROMPT_TOOL],
            max_tokens=16384,
            temperature=0.35,
            provider=self._inp.llm_provider,
            model=self._inp.llm_model,
            parallel_tool_calls=True,
        )

        stream_result: LLMStreamResult | None = None
        async for item in self._stream_one_llm_call(
            self._llm_messages,
            llm_config,
            app_settings=app_settings,
            is_disconnected=is_disconnected,
        ):
            if isinstance(item, EditorStreamEvent):
                if item.type == "error":
                    yield item
                    return
                yield item
            elif isinstance(item, LLMStreamResult):
                stream_result = item

        if stream_result is None:
            yield EditorStreamEvent(
                type="error",
                data={"detail": "Stream ended without a final result"},
            )
            return

        self._log_llm_result(stream_result)

        generated = parse_generate_prompt_tool_call(stream_result.tool_calls)
        if generated is None:
            logger.warning(
                "[prompt_editor] creating_mode: no generate_prompt tool result — "
                "prompt unchanged (clarification turn or missing tool call)"
            )
        else:
            logger.info(
                "[prompt_editor] creating_mode: generate_prompt applied content_len=%s",
                len(generated),
            )

        edit_snapshots: list[str] = []
        if generated:
            yield EditorStreamEvent(type="status", data={"phase": "generating"})
            edit_snapshots = [generated]
            yield EditorStreamEvent(
                type="edit",
                data={
                    "edited_prompt": generated,
                    "edit_index": 0,
                    "total_edits": 1,
                },
            )
            final_prompt = generated
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

    # ------------------------------------------------------------------
    # Editing mode: edit_prompt calls with continuation loop
    # ------------------------------------------------------------------

    async def _run_editing_mode(
        self,
        *,
        app_settings: LLMSettingsView,
        is_disconnected: Callable[[], Awaitable[bool]] | None,
    ) -> AsyncGenerator[EditorStreamEvent, None]:
        llm_config = LLMCallConfig(
            tools=[EDIT_PROMPT_TOOL],
            max_tokens=8192,
            temperature=0.35,
            provider=self._inp.llm_provider,
            model=self._inp.llm_model,
            parallel_tool_calls=True,
        )

        messages = list(self._llm_messages)
        current_prompt = self._inp.current_prompt

        all_content_parts: list[str] = []
        all_tool_calls_payload: list[dict[str, Any]] = []
        all_edit_snapshots: list[str] = []
        total_latency_ms: int | None = None
        total_usage: dict[str, int] | None = None
        total_cost: float | None = None
        running_edit_index = 0
        emitted_editing_status = False

        for turn in range(_MAX_EDIT_CONTINUATION_TURNS + 1):
            if is_disconnected is not None and await is_disconnected():
                return

            logger.info(
                "[prompt_editor] editing_mode: turn=%s messages=%s prompt_lines=%s",
                turn,
                len(messages),
                get_prompt_line_count(current_prompt),
            )

            stream_result: LLMStreamResult | None = None
            async for item in self._stream_one_llm_call(
                messages,
                llm_config,
                app_settings=app_settings,
                is_disconnected=is_disconnected,
            ):
                if isinstance(item, EditorStreamEvent):
                    if item.type == "error":
                        yield item
                        return
                    yield item
                elif isinstance(item, LLMStreamResult):
                    stream_result = item

            if stream_result is None:
                yield EditorStreamEvent(
                    type="error",
                    data={"detail": "Stream ended without a final result"},
                )
                return

            self._log_llm_result(stream_result, turn=turn)

            # --- Accumulate content and costs across turns ---
            if stream_result.full_content:
                all_content_parts.append(stream_result.full_content)
            if stream_result.latency_ms is not None:
                total_latency_ms = (total_latency_ms or 0) + stream_result.latency_ms
            total_usage = _merge_usage(
                total_usage,
                dict(stream_result.usage) if stream_result.usage else None,
            )
            if stream_result.response_cost_usd is not None:
                total_cost = (total_cost or 0.0) + stream_result.response_cost_usd

            # --- Parse and apply edits from this turn ---
            raw_edits = parse_edit_prompt_tool_calls(stream_result.tool_calls)
            line_count = get_prompt_line_count(current_prompt)
            valid_edits = validate_edits_against_line_count(raw_edits, line_count)

            logger.info(
                "[prompt_editor] editing_mode: turn=%s parsed_edits=%s "
                "validated_edits=%s line_count=%s",
                turn,
                _format_edits_for_log(raw_edits),
                _format_edits_for_log(valid_edits),
                line_count,
            )
            if raw_edits and (
                len(raw_edits) != len(valid_edits) or raw_edits != valid_edits
            ):
                logger.warning(
                    "[prompt_editor] editing_mode: turn=%s some edits dropped; "
                    "raw_count=%s valid_count=%s",
                    turn,
                    len(raw_edits),
                    len(valid_edits),
                )

            turn_tool_calls_payload = llm_tool_calls_to_openai_dicts(
                stream_result.tool_calls
            )
            all_tool_calls_payload.extend(turn_tool_calls_payload)

            if valid_edits:
                if not emitted_editing_status:
                    yield EditorStreamEvent(type="status", data={"phase": "editing"})
                    emitted_editing_status = True

                turn_snapshots = apply_edits_progressively(current_prompt, valid_edits)
                turn_total = len(turn_snapshots)
                for snap in turn_snapshots:
                    if is_disconnected is not None and await is_disconnected():
                        return
                    yield EditorStreamEvent(
                        type="edit",
                        data={
                            "edited_prompt": snap,
                            "edit_index": running_edit_index,
                            "total_edits": turn_total,
                        },
                    )
                    running_edit_index += 1

                all_edit_snapshots.extend(turn_snapshots)
                current_prompt = turn_snapshots[-1]

            # --- Decide whether to continue ---
            has_edit_tool_calls = any(
                tc.function_name == "edit_prompt" for tc in stream_result.tool_calls
            )
            if not has_edit_tool_calls:
                logger.info(
                    "[prompt_editor] editing_mode: turn=%s no edit_prompt calls, "
                    "terminating loop",
                    turn,
                )
                break

            if turn >= _MAX_EDIT_CONTINUATION_TURNS:
                logger.info(
                    "[prompt_editor] editing_mode: max continuation turns reached "
                    "(%s), terminating loop",
                    _MAX_EDIT_CONTINUATION_TURNS,
                )
                break

            # --- Build continuation messages for next turn ---
            new_line_count = get_prompt_line_count(current_prompt)
            continuation_msgs = build_continuation_messages(
                stream_content=stream_result.full_content,
                tool_calls_payload=turn_tool_calls_payload,
                edits=valid_edits,
                new_line_count=new_line_count,
            )
            messages.extend(continuation_msgs)

            # Refresh the dynamic system message (index 1) with the updated
            # prompt so the model sees correct line numbers.
            messages[1] = LLMMessage(
                role="system",
                content=build_dynamic_system_message(
                    current_prompt=current_prompt,
                    agent=self._inp.agent,
                    eval_context=self._inp.eval_context,
                ),
            )

            logger.info(
                "[prompt_editor] editing_mode: continuing to turn=%s "
                "new_prompt_lines=%s",
                turn + 1,
                new_line_count,
            )

        # --- Build final result ---
        final_prompt = current_prompt
        unchanged = final_prompt == self._inp.current_prompt
        logger.info(
            "[prompt_editor] editing_mode: result prompt_changed=%s final_len=%s "
            "snapshot_count=%s total_turns=%s",
            not unchanged,
            len(final_prompt),
            len(all_edit_snapshots),
            running_edit_index,
        )

        result = EditorResult(
            content="\n\n".join(all_content_parts),
            tool_calls_payload=all_tool_calls_payload or None,
            edited_prompt=final_prompt,
            edit_snapshots=all_edit_snapshots,
            latency_ms=total_latency_ms,
            token_usage=total_usage,
            cost_usd=total_cost,
        )
        yield EditorStreamEvent(type="done", data={"result": result})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_llm_result(
        stream_result: LLMStreamResult, *, turn: int | None = None
    ) -> None:
        turn_label = f" turn={turn}" if turn is not None else ""
        logger.info(
            "[prompt_editor] llm_completed%s resolved_model=%s latency_ms=%s "
            "tool_call_count=%s reasoning_chars=%s usage=%s cost_usd=%s",
            turn_label,
            stream_result.model,
            stream_result.latency_ms,
            len(stream_result.tool_calls),
            len(stream_result.full_content or ""),
            stream_result.usage,
            stream_result.response_cost_usd,
        )
        _log_parsed_tool_calls(stream_result.tool_calls)
