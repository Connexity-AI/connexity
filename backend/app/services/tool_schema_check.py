"""Checking a simulated call's tool arguments against the tools' own schemas
(`plans/2026-11-20-tool-schemas-in-simulations.md`).

A voice platform gives a tool's JSON Schema to the agent's model as guidance; nothing
documented refuses arguments that break it. A text run fakes the tool's answer, so the
only way to know whether the agent obeyed the schema is to look at what it sent. This
reports what it finds as facts about the arguments. It never claims the platform would
have refused them, and nothing here is sent back to the agent.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from app.models.schemas import ConversationTurn

logger = logging.getLogger(__name__)

# Violations kept per simulated call; a conversation that loops must not store hundreds.
MAX_VIOLATIONS = 50


@dataclass(frozen=True)
class Violation:
    tool: str
    field: str
    problem: str
    turn: int


@dataclass(frozen=True)
class SchemaCheck:
    """What was checked in one simulated call."""

    # Tools of the tested version that declare a schema, checked or not called.
    tools: list[str]
    # Tools whose schema could not be read as JSON Schema: not checked.
    unreadable: list[str]
    violations: list[Violation]


def tool_schemas(tools: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Each tool's parameters schema by name, for the tools that declare one."""
    out: dict[str, dict[str, Any]] = {}
    for tool in tools or []:
        function = tool.get("function")
        if not isinstance(function, dict):
            continue
        name, schema = function.get("name"), function.get("parameters")
        if isinstance(name, str) and isinstance(schema, dict) and schema:
            out[name] = schema
    return out


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _problem(error: ValidationError) -> tuple[str, str]:
    """The field and, in plain words, what is wrong with it."""
    path = ".".join(str(part) for part in error.absolute_path)
    value: Any = error.instance
    rule: Any = error.validator_value
    if error.validator == "required" and isinstance(value, dict):
        missing = [name for name in rule if name not in value]
        field = ".".join(part for part in (path, missing[0] if missing else "") if part)
        return field, "is missing; the schema requires it"
    field = path or "(arguments)"
    # No lengths of the value in the words: the same problem then reads the same in
    # every call, and a run counts it once per call.
    if error.validator == "minLength":
        state = "is empty" if value == "" else "is too short"
        return (
            field,
            f"{state}; the schema asks for at least {_plural(rule, 'character')}",
        )
    if error.validator == "maxLength":
        return (
            field,
            f"is too long; the schema allows at most {_plural(rule, 'character')}",
        )
    if error.validator == "pattern":
        return field, f"does not match the schema's pattern {rule}"
    if error.validator == "enum":
        return (
            field,
            f"is not one of the schema's allowed values ({', '.join(map(str, rule))})",
        )
    if error.validator == "type":
        kind = rule if isinstance(rule, str) else " or ".join(rule)
        return field, f"is not of the schema's type ({kind})"
    if error.validator == "additionalProperties":
        return field, "has a field the schema does not allow"
    return field, f"breaks the schema's `{error.validator}` rule"


def check_tool_calls(
    transcript: list[ConversationTurn], schemas: dict[str, dict[str, Any]]
) -> SchemaCheck:
    """Validate every tool call in ``transcript`` whose tool has a schema.

    A schema the validator cannot read is listed as unreadable and its calls are not
    checked: an unreadable schema says nothing about the arguments.
    """
    validators: dict[str, Draft202012Validator] = {}
    unreadable: list[str] = []
    for name, schema in schemas.items():
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError:
            unreadable.append(name)
            continue
        validators[name] = Draft202012Validator(schema)
    violations: list[Violation] = []
    for turn in transcript:
        for call in turn.tool_calls or []:
            validator = validators.get(call.function.name)
            if validator is None:
                continue
            raw = call.function.arguments
            try:
                arguments = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                violations.append(
                    Violation(
                        tool=call.function.name,
                        field="(arguments)",
                        problem="are not JSON",
                        turn=turn.index,
                    )
                )
                continue
            try:
                errors = sorted(
                    validator.iter_errors(arguments),
                    key=lambda e: [str(part) for part in e.absolute_path],
                )
            except Exception:  # noqa: BLE001 - a schema the validator cannot follow
                # For example a reference it cannot resolve. The tool is not checked;
                # the simulated call itself is fine.
                logger.warning(
                    "Could not check the arguments of tool %s against its schema",
                    call.function.name,
                    exc_info=True,
                )
                validators.pop(call.function.name, None)
                unreadable.append(call.function.name)
                violations = [v for v in violations if v.tool != call.function.name]
                continue
            for error in errors:
                field, problem = _problem(error)
                violations.append(
                    Violation(
                        tool=call.function.name,
                        field=field,
                        problem=problem,
                        turn=turn.index,
                    )
                )
    return SchemaCheck(
        tools=sorted(schemas),
        unreadable=sorted(unreadable),
        violations=violations[:MAX_VIOLATIONS],
    )
