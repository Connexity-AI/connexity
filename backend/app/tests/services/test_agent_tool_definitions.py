"""Tests for centralized agent tool normalization."""

from app.services.agent_tool_definitions import (
    raw_tool_entry_name,
)


def test_raw_tool_entry_name_wrapped() -> None:
    assert (
        raw_tool_entry_name(
            {"type": "function", "function": {"name": "  x ", "description": ""}}
        )
        == "x"
    )
    assert raw_tool_entry_name({"function": {}}) is None
    assert raw_tool_entry_name({"name": "y"}) is None
