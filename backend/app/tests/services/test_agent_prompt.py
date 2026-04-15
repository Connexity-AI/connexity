"""Unit tests for prompt editor agent_prompt helpers."""

import uuid

from app.models.agent import Agent
from app.models.enums import AgentMode, TurnRole
from app.models.prompt_editor import PromptEditorMessage
from app.services.llm import LLMToolCall
from app.services.prompt_editor.agent_prompt import (
    add_line_numbers,
    apply_edits_progressively,
    apply_edits_to_prompt,
    build_dynamic_system_message,
    build_editor_messages,
    build_static_system_message,
    get_prompt_line_count,
    parse_edit_prompt_tool_calls,
    prompt_editor_messages_to_llm_history,
    validate_edits_against_line_count,
)


def test_add_line_numbers_empty() -> None:
    assert add_line_numbers("") == "1 | "


def test_add_line_numbers_multiline() -> None:
    assert add_line_numbers("a\nb") == "1 | a\n2 | b"


def test_get_prompt_line_count() -> None:
    assert get_prompt_line_count("") == 1
    assert get_prompt_line_count("one") == 1
    assert get_prompt_line_count("one\ntwo") == 2


def test_apply_edits_single_replace() -> None:
    p = "line1\nline2\nline3"
    out = apply_edits_to_prompt(p, [(2, 2, "NEW")])
    assert out == "line1\nNEW\nline3"


def test_apply_edits_multi_bottom_up() -> None:
    p = "a\nb\nc\nd"
    out = apply_edits_to_prompt(
        p,
        [
            (1, 1, "A2"),
            (3, 3, "C2"),
        ],
    )
    assert out == "A2\nb\nC2\nd"


def test_apply_edits_progressive() -> None:
    p = "a\nb\nc"
    edits = [(2, 2, "B2"), (1, 1, "A2")]
    snaps = apply_edits_progressively(p, edits)
    assert len(snaps) == 2
    assert snaps[0] == "A2\nb\nc"
    assert snaps[1] == "A2\nB2\nc"


def test_apply_edits_insert_after() -> None:
    p = "a\nb"
    out = apply_edits_to_prompt(p, [(2, 1, "inserted")])
    assert out == "a\nb\ninserted"


def test_parse_edit_prompt_tool_calls() -> None:
    calls = [
        LLMToolCall(
            id="1",
            function_name="edit_prompt",
            arguments={"start_line": 1, "end_line": 1, "new_content": "x"},
        ),
        LLMToolCall(id="2", function_name="other", arguments={}),
    ]
    edits = parse_edit_prompt_tool_calls(calls)
    assert edits == [(1, 1, "x")]


def test_validate_edits_against_line_count() -> None:
    p_lines = 3
    raw = [(1, 3, "ok"), (0, 1, "bad"), (5, 5, "bad2")]
    v = validate_edits_against_line_count(raw, p_lines)
    assert v == [(1, 3, "ok")]


def _platform_agent(
    *,
    name: str = "Test Agent",
    agent_model: str = "gpt-4o-mini",
    agent_provider: str | None = "openai",
    tools: list[dict[str, object]] | None = None,
) -> Agent:
    return Agent(
        name=name,
        mode=AgentMode.PLATFORM,
        system_prompt="Agent under test",
        agent_model=agent_model,
        agent_provider=agent_provider,
        tools=tools,
    )


def test_build_static_system_message_includes_role_and_tool() -> None:
    text = build_static_system_message(target_provider="openai")
    assert "senior prompt engineer" in text.lower()
    assert "edit_prompt" in text
    assert "Prompting practices" in text or "prompt" in text.lower()


def test_build_dynamic_system_message_numbered_prompt_and_config() -> None:
    agent = _platform_agent(
        name="MyBot",
        agent_model="gpt-4o",
        agent_provider="anthropic",
        tools=[{"type": "function", "function": {"name": "lookup"}}],
    )
    body = build_dynamic_system_message(
        current_prompt="line_a\nline_b",
        agent=agent,
        eval_context=None,
    )
    assert "<current_prompt>" in body
    assert "1 | line_a" in body
    assert "2 | line_b" in body
    assert "<agent_config>" in body
    assert "MyBot" in body
    assert "lookup" in body
    assert "eval_context" not in body


def test_build_dynamic_system_message_includes_eval_context() -> None:
    agent = _platform_agent()
    body = build_dynamic_system_message(
        current_prompt="x",
        agent=agent,
        eval_context="  run failed metric X  ",
    )
    assert "<eval_context>" in body
    assert "run failed metric X" in body


def test_build_editor_messages_two_system_then_history_then_user() -> None:
    agent = _platform_agent()
    sid = uuid.uuid4()
    hist = [
        PromptEditorMessage(
            session_id=sid,
            role=TurnRole.USER,
            content="prior user",
        ),
        PromptEditorMessage(
            session_id=sid,
            role=TurnRole.ASSISTANT,
            content="prior assistant",
            tool_calls=[
                {
                    "id": "tc1",
                    "type": "function",
                    "function": {
                        "name": "edit_prompt",
                        "arguments": '{"start_line": 1, "end_line": 1, "new_content": "z"}',
                    },
                }
            ],
        ),
    ]
    msgs = build_editor_messages(
        agent=agent,
        session_messages=hist,
        user_message="new user",
        current_prompt="alpha\nbeta",
        eval_context=None,
    )
    # Two system blocks, then user / assistant / tool replay, then new user
    assert len(msgs) == 6
    assert msgs[0].role == "system"
    assert msgs[1].role == "system"
    assert msgs[0].content != msgs[1].content
    assert msgs[-1].role == "user"
    assert msgs[-1].content == "new user"

    # History: user, assistant, tool result for replay
    replay = prompt_editor_messages_to_llm_history(hist)
    assert replay[0].role == "user" and replay[0].content == "prior user"
    assert replay[1].role == "assistant"
    assert replay[2].role == "tool" and replay[2].tool_call_id == "tc1"
