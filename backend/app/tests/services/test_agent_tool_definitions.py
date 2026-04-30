"""Tests for centralized agent tool normalization."""

from app.services.agent_tool_definitions import (
    agent_tool_definitions_as_prompt_dicts,
    parse_agent_tool_definitions,
    raw_tool_entry_name,
)


def test_openai_wrapper_preserves_required_in_parameters() -> None:
    raw = [
        {
            "type": "function",
            "function": {
                "name": "book",
                "description": "Book slot",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "room": {"type": "string"},
                    },
                    "required": ["date", "room"],
                },
            },
            "platform_config": {"implementation": {"kind": "mock"}},
        }
    ]
    parsed = parse_agent_tool_definitions(raw)
    assert len(parsed) == 1
    assert parsed[0].name == "book"
    assert parsed[0].parameters is not None
    assert parsed[0].parameters.get("required") == ["date", "room"]
    prompt_row = agent_tool_definitions_as_prompt_dicts(raw)[0]
    assert prompt_row["parameters"]["required"] == ["date", "room"]
    assert "platform_config" not in prompt_row


def test_skips_flat_legacy_and_malformed() -> None:
    raw = [
        {
            "name": "lookup",
            "description": "Ignored without function wrapper",
            "parameters": {"type": "object"},
        },
        {},
        {"type": "function", "function": {}},
        {"type": "function", "function": {"name": ""}},
    ]
    assert parse_agent_tool_definitions(raw) == []


def test_raw_tool_entry_name_wrapped() -> None:
    assert (
        raw_tool_entry_name(
            {"type": "function", "function": {"name": "  x ", "description": ""}}
        )
        == "x"
    )
    assert raw_tool_entry_name({"function": {}}) is None
    assert raw_tool_entry_name({"name": "y"}) is None


def test_deep_copy_parameters_no_aliasing() -> None:
    params = {"type": "object", "required": ["a"]}
    raw = [{"type": "function", "function": {"name": "t", "parameters": params}}]
    parsed = parse_agent_tool_definitions(raw)
    parsed[0].parameters["required"].append("b")  # type: ignore[union-attr]
    assert params["required"] == ["a"]
