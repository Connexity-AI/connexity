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


def _platform_config_template() -> dict[str, Any]:
    return {"terminating": True, "predefined": True}


def canonical_end_call_tool_dict() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "end_call",
            "description": "End the call when the user's need is resolved.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
        "platform_config": _platform_config_template(),
    }


def canonical_transfer_call_tool_dict() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Transfer the call to another phone number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_phone_number": {
                        "type": "string",
                        "description": "Phone number to transfer the call to.",
                    }
                },
                "required": ["to_phone_number"],
                "additionalProperties": False,
            },
        },
        "platform_config": _platform_config_template(),
    }


def list_predefined_tools_for_api() -> list[dict[str, Any]]:
    """Return predefined tool rows (same shape as ``Agent.tools`` JSONB elements)."""
    return [
        canonical_end_call_tool_dict(),
        canonical_transfer_call_tool_dict(),
    ]


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


def normalize_and_validate_agent_tools(
    tools: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    """Validate tool list shape, reject duplicate function names, deep-copy each row.

    Does not rewrite ``end_call`` / ``transfer_call`` (or other names): descriptions
    and parameter schemas may be user-edited. Predefined vs terminating semantics
    stay in ``platform_config`` (e.g. ``predefined``, ``terminating``).
    """
    if tools is None:
        return None
    if not isinstance(tools, list):
        msg = "Agent tools must be a list of objects"
        raise ValueError(msg)

    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for i, item in enumerate(tools):
        if not isinstance(item, dict):
            msg = f"Agent tools[{i}] must be an object"
            raise ValueError(msg)
        name = raw_tool_entry_name(item)
        if not name:
            msg = f"Agent tools[{i}] is missing function.name"
            raise ValueError(msg)
        if name in seen:
            msg = f"Duplicate agent tool name: {name}"
            raise ValueError(msg)
        seen.add(name)

        cloned = copy.deepcopy(item)
        pc = cloned.get("platform_config")
        if pc is not None and not isinstance(pc, dict):
            msg = f"Agent tool '{name}' platform_config must be an object"
            raise ValueError(msg)
        out.append(cloned)

    return out


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
        out.append(AgentToolDefinition(name=name, description=desc, parameters=params))
    return out


def agent_tool_definitions_as_prompt_dicts(
    raw: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """List of dicts suitable for ``json.dumps`` in prompts (judge, editor, etc.)."""
    return [t.to_prompt_dict() for t in parse_agent_tool_definitions(raw)]
