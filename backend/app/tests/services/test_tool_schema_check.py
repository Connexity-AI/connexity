"""Checking simulated tool calls against the tools' own schemas
(plan `plans/2026-11-20-tool-schemas-in-simulations.md`)."""

import json
from datetime import UTC, datetime
from typing import Any

from app.models.enums import TurnRole
from app.models.schemas import ConversationTurn, ToolCall, ToolCallFunction
from app.services.component_versions import _tools_in
from app.services.tool_schema_check import (
    MAX_VIOLATIONS,
    check_tool_calls,
    tool_schemas,
)

BOOKING = {
    "type": "object",
    "properties": {
        "postalCode": {"type": "string", "minLength": 1, "pattern": "^[A-Z0-9 ]+$"},
        "slot": {"type": "string", "enum": ["morning", "afternoon"]},
        "people": {"type": "integer"},
    },
    "required": ["postalCode", "slot"],
}


def _call(index: int, name: str, arguments: Any) -> ConversationTurn:
    return ConversationTurn(
        index=index,
        role=TurnRole.ASSISTANT,
        content=None,
        timestamp=datetime(2026, 11, 20, tzinfo=UTC),
        tool_calls=[
            ToolCall(
                id=f"tc{index}",
                function=ToolCallFunction(
                    name=name,
                    arguments=arguments
                    if isinstance(arguments, str)
                    else json.dumps(arguments),
                ),
            )
        ],
    )


def _found(arguments: Any) -> list[tuple[str, str]]:
    check = check_tool_calls([_call(3, "book", arguments)], {"book": BOOKING})
    return [(v.field, v.problem) for v in check.violations]


def test_valid_arguments_break_nothing() -> None:
    check = check_tool_calls(
        [_call(3, "book", {"postalCode": "M5V 2T6", "slot": "morning", "people": 2})],
        {"book": BOOKING},
    )

    assert (check.tools, check.unreadable, check.violations) == (["book"], [], [])


def test_each_kind_of_violation_is_said_in_plain_words() -> None:
    assert _found({"postalCode": "", "slot": "morning"}) == [
        ("postalCode", "is empty; the schema asks for at least 1 character"),
        ("postalCode", "does not match the schema's pattern ^[A-Z0-9 ]+$"),
    ]
    assert _found({"postalCode": "M5V"}) == [
        ("slot", "is missing; the schema requires it")
    ]
    assert _found({"postalCode": "M5V", "slot": "night"}) == [
        ("slot", "is not one of the schema's allowed values (morning, afternoon)")
    ]
    assert _found({"postalCode": "M5V", "slot": "morning", "people": "two"}) == [
        ("people", "is not of the schema's type (integer)")
    ]
    assert _found("{not json") == [("(arguments)", "are not JSON")]


def test_a_violation_names_its_tool_and_turn_and_other_tools_are_left_alone() -> None:
    check = check_tool_calls(
        [
            _call(2, "end_call", {}),
            _call(5, "book", {"postalCode": "M5V"}),
        ],
        {"book": BOOKING},
    )

    assert [(v.tool, v.turn) for v in check.violations] == [("book", 5)]


def test_a_schema_that_cannot_be_read_is_not_checked_and_reports_no_violation() -> None:
    check = check_tool_calls(
        [_call(1, "odd", {"anything": 1})], {"odd": {"type": "not-a-type"}}
    )

    assert (check.unreadable, check.violations) == (["odd"], [])


def test_a_schema_the_validator_cannot_follow_fails_nothing() -> None:
    schemas = {
        "book": BOOKING,
        "odd": {"type": "object", "properties": {"a": {"$ref": "#/nowhere"}}},
    }

    check = check_tool_calls(
        [_call(1, "odd", {"a": 1}), _call(2, "book", {"postalCode": "M5V"})], schemas
    )

    # The tool is not checked; the other tool still is.
    assert check.unreadable == ["odd"]
    assert [(v.tool, v.field) for v in check.violations] == [("book", "slot")]


def test_the_same_problem_reads_the_same_whatever_the_value() -> None:
    schema = {
        "type": "object",
        "properties": {"phone": {"type": "string", "minLength": 10, "maxLength": 12}},
    }
    turns = [
        _call(1, "book", {"phone": "1234"}),
        _call(2, "book", {"phone": "123456"}),
        _call(3, "book", {"phone": "1234567890123"}),
    ]

    problems = [v.problem for v in check_tool_calls(turns, {"book": schema}).violations]

    assert problems == [
        "is too short; the schema asks for at least 10 characters",
        "is too short; the schema asks for at least 10 characters",
        "is too long; the schema allows at most 12 characters",
    ]


def test_a_tool_declared_twice_with_other_schemas_obeys_either() -> None:
    strict = {
        "type": "object",
        "properties": {"zip": {"type": "string"}},
        "required": ["zip"],
    }
    loose = {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    }
    read = _tools_in(
        {
            "states": [
                {
                    "name": "a",
                    "tools": [{"type": "custom", "name": "book", "parameters": strict}],
                },
                {
                    "name": "b",
                    "tools": [{"type": "custom", "name": "book", "parameters": loose}],
                },
                {
                    "name": "c",
                    "tools": [{"type": "custom", "name": "book", "parameters": strict}],
                },
            ]
        }
    )
    assert [t.parameters for t in read] == [{"anyOf": [strict, loose]}]
    schemas = {"book": read[0].parameters or {}}

    assert (
        check_tool_calls([_call(1, "book", {"city": "Lviv"})], schemas).violations == []
    )
    assert len(check_tool_calls([_call(1, "book", {})], schemas).violations) == 1


def test_a_looping_conversation_stores_a_bounded_number_of_violations() -> None:
    turns = [_call(i, "book", {}) for i in range(MAX_VIOLATIONS)]

    check = check_tool_calls(turns, {"book": BOOKING})

    assert len(check.violations) == MAX_VIOLATIONS


def test_schemas_are_read_from_the_tested_versions_tools() -> None:
    read = _tools_in(
        {
            "general_tools": [
                {"type": "custom", "name": "book", "parameters": BOOKING},
                {"type": "end_call", "name": "end_call"},
                {"type": "custom", "name": "lookup", "parameters": {}},
            ]
        }
    )
    snapshot = [
        {"type": "function", "function": {"name": t.name, "parameters": t.parameters}}
        for t in read
    ]

    assert tool_schemas(snapshot) == {"book": BOOKING}
    assert tool_schemas(None) == {}
