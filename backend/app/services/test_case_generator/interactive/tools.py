"""Tool definitions and parsers for the interactive test-case agent."""

import json
import logging
from copy import deepcopy
from typing import Any

from app.models.test_case import TestCaseCreate

logger = logging.getLogger(__name__)


def _test_case_tool_parameters_schema() -> dict[str, Any]:
    """OpenAI-style JSON schema for tool arguments from :class:`TestCaseCreate`.

    ``status`` is intentionally omitted: the lifecycle status is a platform
    concern, not something the LLM needs to set or reason about. The unused
    ``TestCaseStatus`` entry is also dropped from ``$defs`` to keep the schema
    minimal.
    """
    schema = deepcopy(TestCaseCreate.model_json_schema(mode="serialization"))
    props = schema.get("properties")
    if isinstance(props, dict):
        props.pop("status", None)
    required = schema.get("required")
    if isinstance(required, list):
        schema["required"] = [r for r in required if r != "status"]
    defs = schema.get("$defs")
    if isinstance(defs, dict):
        defs.pop("TestCaseStatus", None)
    return schema


_TEST_CASE_PARAMS = _test_case_tool_parameters_schema()

CREATE_TEST_CASE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "create_test_case",
        "description": (
            "Emit one evaluation test case. Call once per test case; use parallel "
            "tool calls to emit multiple cases in one response."
        ),
        "parameters": _TEST_CASE_PARAMS,
    },
}

EDIT_TEST_CASE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_test_case",
        "description": (
            "Emit the COMPLETE updated test case exactly once. Preserve fields the "
            "user did not ask to change."
        ),
        "parameters": _TEST_CASE_PARAMS,
    },
}


def _arguments_dict(tc: dict[str, Any]) -> dict[str, Any]:
    fn = tc.get("function")
    if not isinstance(fn, dict):
        return {}
    raw = fn.get("arguments", "{}")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        logger.warning("Invalid tool arguments JSON: %s", exc)
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_test_case_create(args: dict[str, Any]) -> TestCaseCreate | None:
    try:
        # Defense in depth: if the model emits `status` despite it being absent
        # from the tool schema, drop it so the model default (ACTIVE) applies.
        cleaned = {k: v for k, v in args.items() if k != "status"}
        return TestCaseCreate.model_validate(cleaned)
    except Exception as exc:
        logger.warning("Invalid create_test_case payload: %s", exc)
        return None


def parse_create_test_case_tool_calls(
    tool_calls: list[dict[str, Any]] | None,
) -> list[TestCaseCreate]:
    """Validate every ``create_test_case`` tool call; drop invalid ones."""
    if not tool_calls:
        return []
    out: list[TestCaseCreate] = []
    for tc in tool_calls:
        fn = tc.get("function")
        name = ""
        if isinstance(fn, dict):
            name = str(fn.get("name", ""))
        if name != "create_test_case":
            continue
        created = _to_test_case_create(_arguments_dict(tc))
        if created is not None:
            out.append(created)
    return out


def parse_create_test_case_tool_call_slots(
    tool_calls: list[dict[str, Any]] | None,
) -> list[TestCaseCreate | None]:
    """Return one slot per ``create_test_case`` call, preserving invalid positions."""
    if not tool_calls:
        return []
    out: list[TestCaseCreate | None] = []
    for tc in tool_calls:
        fn = tc.get("function")
        name = ""
        if isinstance(fn, dict):
            name = str(fn.get("name", ""))
        if name != "create_test_case":
            continue
        out.append(_to_test_case_create(_arguments_dict(tc)))
    return out


def parse_edit_test_case_tool_call(
    tool_calls: list[dict[str, Any]] | None,
) -> TestCaseCreate | None:
    """Return the first valid ``edit_test_case`` payload."""
    if not tool_calls:
        return None
    for tc in tool_calls:
        fn = tc.get("function")
        name = ""
        if isinstance(fn, dict):
            name = str(fn.get("name", ""))
        if name != "edit_test_case":
            continue
        edited = _to_test_case_create(_arguments_dict(tc))
        if edited is not None:
            return edited
    return None
