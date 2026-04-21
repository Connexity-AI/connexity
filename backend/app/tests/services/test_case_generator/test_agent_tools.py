"""Unit tests for test-case AI agent tool schemas and parsers."""

import json

from app.services.test_case_generator.agent.tools import (
    CREATE_TEST_CASE_TOOL,
    EDIT_TEST_CASE_TOOL,
    parse_create_test_case_tool_calls,
    parse_edit_test_case_tool_call,
)


def test_tool_schemas_omit_status_from_required() -> None:
    for tool in (CREATE_TEST_CASE_TOOL, EDIT_TEST_CASE_TOOL):
        params = tool["function"]["parameters"]
        assert "status" not in params.get("properties", {})
        assert "status" not in (params.get("required") or [])


def test_parse_create_defaults_status_to_active() -> None:
    # ``status`` is not in the tool schema; if the LLM emits one anyway, it is
    # stripped and the model default (ACTIVE) applies.
    raw = [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "create_test_case",
                "arguments": json.dumps(
                    {
                        "name": "n1",
                        "tags": ["normal"],
                        "difficulty": "normal",
                        "persona_context": "p",
                        "first_message": "hi",
                        "status": "draft",
                    }
                ),
            },
        }
    ]
    out = parse_create_test_case_tool_calls(raw)
    assert len(out) == 1
    assert out[0].status.value == "active"


def test_parse_create_skips_wrong_tool_name() -> None:
    raw = [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "other",
                "arguments": json.dumps(
                    {
                        "name": "n1",
                        "tags": ["normal"],
                        "difficulty": "normal",
                    }
                ),
            },
        }
    ]
    assert parse_create_test_case_tool_calls(raw) == []


def test_parse_edit_returns_first_valid() -> None:
    raw = [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "edit_test_case",
                "arguments": json.dumps(
                    {
                        "name": "patched",
                        "tags": ["edge-case"],
                        "difficulty": "hard",
                        "persona_context": "pc",
                        "first_message": "x",
                    }
                ),
            },
        }
    ]
    out = parse_edit_test_case_tool_call(raw)
    assert out is not None
    assert out.name == "patched"
    assert out.status.value == "active"


def test_invalid_payload_dropped() -> None:
    raw = [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "create_test_case",
                "arguments": json.dumps(
                    {
                        "name": "n",
                        "tags": ["normal"],
                        "difficulty": "not_a_real_difficulty",
                        "persona_context": "p",
                        "first_message": "hi",
                    }
                ),
            },
        }
    ]
    assert parse_create_test_case_tool_calls(raw) == []
