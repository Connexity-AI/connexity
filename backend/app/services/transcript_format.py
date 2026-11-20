"""A simulated call's transcript as text for a model to read."""

import json
from typing import Any

from app.models.enums import TurnRole
from app.models.schemas import ConversationTurn, ToolCall


def _pretty_json_oneline(raw: str | Any) -> str:
    """Try to re-serialize as compact JSON; fall back to str()."""
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
        return json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))
    except (json.JSONDecodeError, TypeError):
        return str(raw)


def _format_tool_calls(tool_calls: list[ToolCall] | None) -> str:
    if not tool_calls:
        return ""
    parts: list[str] = []
    for tc in tool_calls:
        fn = tc.function
        args = _pretty_json_oneline(fn.arguments)
        parts.append(f"    call: {fn.name}({args})")
    return "\n".join(parts)


def _build_tool_name_index(
    transcript: list[ConversationTurn],
) -> dict[str, str]:
    """Map tool_call ids to function names for labeling tool-result turns."""
    index: dict[str, str] = {}
    for t in transcript:
        if not t.tool_calls:
            continue
        for tc in t.tool_calls:
            index[tc.id] = tc.function.name
    return index


def format_transcript(transcript: list[ConversationTurn]) -> str:
    tool_name_index = _build_tool_name_index(transcript)
    lines: list[str] = []
    for t in transcript:
        role = t.role.value
        if t.role == TurnRole.TOOL:
            fn_name = tool_name_index.get(t.tool_call_id or "", "unknown")
            body = _pretty_json_oneline(t.content) if t.content else "(empty)"
            lines.append(f"Turn {t.index} [tool → {fn_name}]: {body}")
        else:
            body = (t.content or "").strip() or "(no text)"
            lines.append(f"Turn {t.index} [{role}]: {body}")
        if t.tool_calls:
            lines.append("  tool_calls:")
            lines.append(_format_tool_calls(t.tool_calls))
    return "\n".join(lines)
