"""Normalize agent tool JSON from storage for LLM prompts and summaries.

Stored tools use OpenAI chat-completions shapes
(``{"type": "function", "function": {...}, ...}``) and may include extra keys
(e.g. ``platform_config``) that must not be stripped from the *raw* snapshot
used for execution — only omitted from *prompt* snapshots.
"""

import copy
from typing import Any

from pydantic import BaseModel, Field


class AgentToolDefinition(BaseModel):
    """Prompt-facing tool: ``parameters`` is a full JSON Schema (properties, required, ...)."""

    name: str = Field(min_length=1)
    description: str = ""
    parameters: dict[str, Any] | None = None

    def to_prompt_dict(self) -> dict[str, Any]:
        """Shape for JSON serialization in user/system prompts."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters if self.parameters is not None else {},
        }


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


def parse_agent_tool_definitions(
    raw: list[dict[str, Any]] | None,
) -> list[AgentToolDefinition]:
    """Map stored tool list to prompt-facing definitions (schema-only, no platform_config).

    Preserves the full ``parameters`` object, including ``required``, ``properties``,
    ``$defs``, etc.
    """
    if not raw:
        return []
    out: list[AgentToolDefinition] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fn = item.get("function")
        if not isinstance(fn, dict):
            continue
        name = _function_entry_name(fn)
        if not name:
            continue
        desc = str(fn.get("description") or "")
        p = fn.get("parameters")
        params = copy.deepcopy(p) if isinstance(p, dict) else None
        out.append(
            AgentToolDefinition(name=name, description=desc, parameters=params)
        )
    return out


def agent_tool_definitions_as_prompt_dicts(
    raw: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """List of dicts suitable for ``json.dumps`` in prompts (judge, editor, etc.)."""
    return [t.to_prompt_dict() for t in parse_agent_tool_definitions(raw)]
