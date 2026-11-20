"""Read the stored tool entries of a tested agent version (OpenAI chat-completions
shapes), to know which tools end the call."""

from typing import Any


def raw_tool_entry_terminating(item: dict[str, Any]) -> bool:
    pc = item.get("platform_config")
    if not isinstance(pc, dict):
        return False
    return pc.get("terminating") is True


def snapshot_marks_tool_terminating(
    tool_name: str,
    agent_tools: list[dict[str, Any]] | None,
) -> bool:
    """Whether *tool_name* is declared on the snapshot with ``platform_config.terminating``."""
    if not agent_tools or not tool_name:
        return False
    for item in agent_tools:
        if not isinstance(item, dict):
            continue
        if raw_tool_entry_name(item) != tool_name:
            continue
        return raw_tool_entry_terminating(item)
    return False


def _function_entry_name(fn: dict[str, Any]) -> str | None:
    raw_name = fn.get("name")
    if raw_name is None:
        return None
    s = str(raw_name).strip()
    return s if s else None


def raw_tool_entry_name(item: dict[str, Any]) -> str | None:
    """Return the tool name from one stored OpenAI-style entry, if present and non-empty."""
    fn = item.get("function")
    if not isinstance(fn, dict):
        return None
    return _function_entry_name(fn)
