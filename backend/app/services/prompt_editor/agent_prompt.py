"""Editor-agent system prompts, message building, and line-based edit application."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.models.agent import Agent
from app.models.enums import AgentMode, TurnRole
from app.models.prompt_editor import PromptEditorMessage
from app.services.llm import LLMMessage, LLMToolCall
from app.services.prompt_editor.guidelines import load_provider_guidelines

logger = logging.getLogger(__name__)

EDIT_PROMPT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_prompt",
        "description": (
            "Replace lines in the agent's system prompt. Line numbers refer to the prompt as shown "
            "in <current_prompt> before any edits in this turn. For multiple edits in one turn, "
            "all line numbers reference that same original; the backend applies edits bottom-up "
            "by start_line. Use empty new_content to delete lines. If start_line > end_line, "
            "insert new_content after line start_line (1-based) without replacing lines."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_line": {
                    "type": "integer",
                    "description": "1-based start line (inclusive) for replace; for insert-after, start_line > end_line",
                },
                "end_line": {
                    "type": "integer",
                    "description": "1-based end line (inclusive) for replace",
                },
                "new_content": {
                    "type": "string",
                    "description": "Replacement text (may include newlines). Empty string deletes the range.",
                },
            },
            "required": ["start_line", "end_line", "new_content"],
        },
    },
}


def add_line_numbers(prompt: str) -> str:
    """Prefix each line with ``N | `` (1-based)."""
    if not prompt:
        return "1 | "
    lines = prompt.split("\n")
    return "\n".join(f"{i + 1} | {line}" for i, line in enumerate(lines))


def get_prompt_line_count(prompt: str) -> int:
    """Return the number of lines in the prompt (minimum 1 for empty string)."""
    if not prompt:
        return 1
    return len(prompt.split("\n"))


def apply_edits_to_prompt(
    prompt: str,
    edits: list[tuple[int, int, str]],
) -> str:
    """Apply edits to ``prompt``. Each edit is ``(start_line, end_line, new_content)`` (1-based, inclusive).

    All line numbers refer to the **original** ``prompt``. Edits are sorted by ``start_line``
    descending before application to avoid line-shift issues within one batch.
    """
    if not edits:
        return prompt
    lines = prompt.split("\n")
    ordered = sorted(edits, key=lambda e: e[0], reverse=True)
    for start_line, end_line, new_content in ordered:
        lines = _apply_one_edit_lines(lines, start_line, end_line, new_content)
    return "\n".join(lines)


def apply_edits_progressively(
    prompt: str,
    edits: list[tuple[int, int, str]],
) -> list[str]:
    """Return full-text snapshots after each successive edit (visual order: ascending ``start_line``).

    Each snapshot applies the first *k* edits from that ordering to the **original** ``prompt``,
    with those *k* edits applied bottom-up (by ``start_line`` descending).
    """
    if not edits:
        return []
    visual = sorted(edits, key=lambda e: e[0])
    out: list[str] = []
    for k in range(len(visual)):
        subset = visual[: k + 1]
        out.append(apply_edits_to_prompt(prompt, subset))
    return out


def _apply_one_edit_lines(
    lines: list[str],
    start_line: int,
    end_line: int,
    new_content: str,
) -> list[str]:
    """Apply a single edit to a list of lines (0-based indexing internally)."""
    n = len(lines)
    if start_line < 1 or start_line > n:
        logger.warning(
            "edit_prompt: start_line %s out of range (lines=%s)", start_line, n
        )
        return lines
    if start_line > end_line:
        # insert after line start_line (1-based) -> at index start_line
        insert_at = start_line
        chunk = new_content.split("\n") if new_content else []
        return lines[:insert_at] + chunk + lines[insert_at:]
    if end_line < start_line:
        logger.warning("edit_prompt: invalid range %s-%s", start_line, end_line)
        return lines
    if end_line > n:
        logger.warning("edit_prompt: end_line %s out of range (lines=%s)", end_line, n)
        return lines
    lo = start_line - 1
    hi = end_line
    chunk = new_content.split("\n") if new_content else []
    return lines[:lo] + chunk + lines[hi:]


def build_static_system_message(*, target_provider: str | None) -> str:
    """First system block: identity, behavior, guidelines, tools, reasoning-then-edit."""
    guidelines = load_provider_guidelines(target_provider)
    tool_schema = json.dumps(EDIT_PROMPT_TOOL, indent=2)
    return f"""You are an expert prompt engineer helping a user improve an **agent's system prompt** for an LLM product.

## How you work
- Be collaborative, not prescriptive. Preserve the user's intent and voice.
- Explain **why** a change helps before you edit.
- Prefer incremental improvements unless the user asks for a full rewrite.
- **First** write your reasoning in natural language for the user. **Then** call the `edit_prompt` tool one or more times to apply changes.
- All line numbers in tool calls refer to `<current_prompt>` **before any edits in this turn**.

## Prompting practices
{guidelines.strip()}

## Tool available
```json
{tool_schema}
```
"""


def build_dynamic_system_message(
    *,
    current_prompt: str,
    agent: Agent,
    eval_context: str | None = None,
) -> str:
    """Second system block: numbered current prompt + agent summary + optional eval context."""
    numbered = add_line_numbers(current_prompt)
    tool_names: list[str] = []
    if agent.tools:
        for t in agent.tools:
            if isinstance(t, dict) and "function" in t:
                fn = t.get("function")
                if isinstance(fn, dict) and "name" in fn:
                    tool_names.append(str(fn["name"]))
            elif isinstance(t, dict) and "name" in t:
                tool_names.append(str(t["name"]))
    mode = agent.mode
    model = agent.agent_model or ""
    provider = agent.agent_provider or ""
    tools_line = ", ".join(tool_names) if tool_names else "(none)"
    parts = [
        "## Current prompt (with line numbers)\n<current_prompt>\n"
        f"{numbered}\n"
        "</current_prompt>",
        "## Target agent configuration\n<agent_config>\n"
        f"Agent: {agent.name} | Mode: {mode} | Model: {model} | Provider: {provider}\n"
        f"Tools ({len(tool_names)}): {tools_line}\n"
        "</agent_config>",
    ]
    if eval_context and eval_context.strip():
        parts.append(
            f"## Eval context\n<eval_context>\n{eval_context.strip()}\n</eval_context>"
        )
    return "\n\n".join(parts)


def prompt_editor_messages_to_llm_history(
    messages: list[PromptEditorMessage],
) -> list[LLMMessage]:
    """Turn stored DB messages into LLM messages including synthetic tool results."""
    history: list[LLMMessage] = []
    for msg in messages:
        if msg.role == TurnRole.USER:
            history.append(LLMMessage(role="user", content=msg.content))
        elif msg.role == TurnRole.ASSISTANT:
            history.append(
                LLMMessage(
                    role="assistant",
                    content=msg.content,
                    tool_calls=msg.tool_calls,
                )
            )
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tid = tc.get("id")
                    if not tid:
                        continue
                    history.append(
                        LLMMessage(
                            role="tool",
                            content="Edit applied successfully.",
                            tool_call_id=str(tid),
                            name="edit_prompt",
                        )
                    )
    return history


def build_editor_messages(
    *,
    agent: Agent,
    session_messages: list[PromptEditorMessage],
    user_message: str,
    current_prompt: str,
    eval_context: str | None = None,
) -> list[LLMMessage]:
    """Build messages for the editor LLM.

    Returns two system messages: static identity (cacheable) then dynamic working state.
    """
    static = build_static_system_message(target_provider=agent.agent_provider)
    dynamic = build_dynamic_system_message(
        current_prompt=current_prompt,
        agent=agent,
        eval_context=eval_context,
    )
    out: list[LLMMessage] = [
        LLMMessage(role="system", content=static),
        LLMMessage(role="system", content=dynamic),
    ]
    out.extend(prompt_editor_messages_to_llm_history(session_messages))
    out.append(LLMMessage(role="user", content=user_message))
    return out


def parse_edit_prompt_tool_calls(
    tool_calls: list[LLMToolCall],
) -> list[tuple[int, int, str]]:
    """Extract ``(start_line, end_line, new_content)`` from ``edit_prompt`` tool calls only."""
    edits: list[tuple[int, int, str]] = []
    for tc in tool_calls:
        if tc.function_name != "edit_prompt":
            logger.warning("Skipping unknown tool call: %s", tc.function_name)
            continue
        args = tc.arguments
        try:
            s = int(args["start_line"])
            e = int(args["end_line"])
            new_content = str(args.get("new_content", ""))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid edit_prompt arguments: %s", exc)
            continue
        edits.append((s, e, new_content))
    return edits


def validate_edits_against_line_count(
    edits: list[tuple[int, int, str]],
    line_count: int,
) -> list[tuple[int, int, str]]:
    """Drop edits whose replace range is out of bounds; inserts validated separately in apply."""
    valid: list[tuple[int, int, str]] = []
    for start_line, end_line, new_content in edits:
        if start_line > end_line:
            if start_line < 1 or start_line > line_count:
                logger.warning(
                    "Dropping insert-after edit: start_line %s invalid", start_line
                )
                continue
            valid.append((start_line, end_line, new_content))
            continue
        if start_line < 1 or end_line > line_count or end_line < start_line:
            logger.warning(
                "Dropping edit: range %s-%s invalid for %s lines",
                start_line,
                end_line,
                line_count,
            )
            continue
        valid.append((start_line, end_line, new_content))
    return valid


def llm_tool_calls_to_openai_dicts(
    tool_calls: list[LLMToolCall],
) -> list[dict[str, Any]]:
    """Serialize tool calls for JSONB storage / replay."""
    out: list[dict[str, Any]] = []
    for tc in tool_calls:
        out.append(
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function_name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
        )
    return out


def platform_agent_required(agent: Agent) -> None:
    """Raise ``ValueError`` if the agent is not a platform agent."""
    if agent.mode != AgentMode.PLATFORM:
        msg = "Prompt editor requires a platform agent"
        raise ValueError(msg)
