from app.services.test_case_generator.prompt import (
    build_system_prompt,
    build_user_prompt,
)
from app.services.test_case_generator.schemas import ToolDefinition


def test_build_system_prompt_contains_schema_fields() -> None:
    prompt = build_system_prompt()
    assert "name" in prompt
    assert "difficulty" in prompt
    assert "tags" in prompt
    assert "persona_context" in prompt
    assert "first_message" in prompt
    assert "expected_tool_calls" in prompt
    assert "draft" in prompt


def test_build_system_prompt_contains_diversity_requirements() -> None:
    prompt = build_system_prompt()
    assert "edge" in prompt.lower()
    assert "red-team" in prompt.lower()
    assert "normal" in prompt.lower()


def test_build_user_prompt_includes_agent_prompt() -> None:
    agent_prompt = "You are a helpful customer support agent."
    prompt = build_user_prompt(agent_prompt=agent_prompt, tools=[], count=10)
    assert agent_prompt in prompt


def test_build_user_prompt_includes_tools() -> None:
    tools = [
        ToolDefinition(
            name="lookup_order",
            description="Look up order by ID",
            parameters={"order_id": {"type": "string"}},
        )
    ]
    prompt = build_user_prompt(agent_prompt="Test agent", tools=tools, count=10)
    assert "lookup_order" in prompt
    assert "Look up order by ID" in prompt


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
