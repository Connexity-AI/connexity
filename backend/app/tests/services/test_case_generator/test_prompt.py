from app.services.test_case_generator.batch.prompt import (
    build_response_format,
    build_system_prompt,
    build_user_prompt,
)
from app.services.test_case_generator.batch.schemas import ToolDefinition


def test_build_system_prompt_contains_schema_fields() -> None:
    prompt = build_system_prompt()
    assert "test_cases" in prompt
    assert "name" in prompt
    assert "difficulty" in prompt
    assert "tags" in prompt
    assert "persona_context" in prompt
    assert "first_message" in prompt
    assert "expected_tool_calls" in prompt


def test_build_system_prompt_omits_status() -> None:
    # Status is a platform concern; the LLM never sees it.
    prompt = build_system_prompt()
    assert '"status"' not in prompt
    assert "draft" not in prompt


def test_build_system_prompt_omits_response_schema_body() -> None:
    prompt = build_system_prompt()
    assert '"properties"' not in prompt
    assert '"additionalProperties"' not in prompt


def test_build_system_prompt_contains_diversity_requirements() -> None:
    prompt = build_system_prompt()
    assert "edge" in prompt.lower()
    assert "red-team" in prompt.lower()
    assert "normal" in prompt.lower()


def test_build_system_prompt_contains_persona_sections() -> None:
    prompt = build_system_prompt()
    assert "[Persona type]" in prompt
    assert "[Description]" in prompt
    assert "[Behavioral instructions]" in prompt


def test_build_system_prompt_requires_mock_responses() -> None:
    prompt = build_system_prompt()
    assert "mock_responses" in prompt
    assert "canned response" in prompt


def test_build_system_prompt_requires_short_names_and_personal_tool_details() -> None:
    prompt = build_system_prompt()
    assert "at most 7 words" in prompt
    assert "60 characters" in prompt
    assert "stable user-provided details" in prompt
    assert "derived or agent-selected tool arguments" in prompt
    assert "user_context" not in prompt


def test_build_response_format_wraps_test_cases() -> None:
    response_format = build_response_format()
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    schema = json_schema["schema"]
    assert isinstance(schema, dict)
    assert schema["required"] == ["test_cases"]
    assert "test_cases" in schema["properties"]


def test_build_user_prompt_includes_agent_prompt() -> None:
    agent_prompt = "You are a helpful customer support agent."
    prompt = build_user_prompt(agent_prompt=agent_prompt, tools=[], count=10)
    assert agent_prompt in prompt


def test_build_user_prompt_includes_tools() -> None:
    tools = [
        ToolDefinition(
            name="lookup_order",
            description="Look up order by ID",
            parameters={
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        )
    ]
    prompt = build_user_prompt(agent_prompt="Test agent", tools=tools, count=10)
    assert "lookup_order" in prompt
    assert "Look up order by ID" in prompt
    assert "required_params" in prompt
    assert "order_id" in prompt


def test_build_user_prompt_no_tools() -> None:
    prompt = build_user_prompt(agent_prompt="Test agent", tools=[], count=5)
    assert "No tools defined" in prompt
    assert "5" in prompt


def test_build_user_prompt_with_focus_tags() -> None:
    prompt = build_user_prompt(
        agent_prompt="Test agent",
        tools=[],
        count=10,
        focus_tags=["billing", "refund"],
    )
    assert "billing" in prompt
    assert "refund" in prompt
    assert "FOCUS" in prompt


def test_build_user_prompt_without_focus_tags() -> None:
    prompt = build_user_prompt(agent_prompt="Test agent", tools=[], count=10)
    assert "FOCUS" not in prompt


def test_build_user_prompt_includes_count() -> None:
    prompt = build_user_prompt(agent_prompt="Test agent", tools=[], count=15)
    assert "15" in prompt
