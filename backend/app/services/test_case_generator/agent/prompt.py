"""System and user messages for the test-case AI agent."""

import json

from app.models.agent import Agent
from app.models.enums import Difficulty, FirstTurn, TurnRole
from app.models.schemas import ConversationTurn
from app.models.test_case import TestCasePublic
from app.services.test_case_generator.agent.context import AgentContext
from app.services.test_case_generator.agent.schemas import AgentMode


def build_static_system_message() -> str:
    """Mode-independent rules (cache-friendly)."""
    return """\
You are a test case generation expert for an AI agent evaluation platform.
You produce realistic evaluation scenarios: a simulated user (persona) and the
agent under test, with clear success criteria.

## Tools
- **create_test_case**: emit one test case per call. For multiple cases, use
  parallel tool calls in a single assistant turn. You decide how many cases to
  create based on the user's request and coverage needs (typically 2–10 when
  generating a suite).
- **edit_test_case**: emit the **complete** updated test case **exactly once**.
  Preserve every field the user did not ask to change.

## Field semantics
- **name**: short, unique, human-readable label.
- **description**: what this case checks (for humans).
- **difficulty**: `normal` or `hard`.
- **tags**: MUST include at least one category tag: `normal`, `edge-case`, or
  `red-team`. You may add more tags from `<available_tags>` for consistency
  with this agent's suite.
- **persona_context**: one text block: persona type, traits, and behavioral
  instructions for the simulator.
- **first_turn**: who speaks first — `user` or `agent`.
- **first_message**: opening line for whoever speaks first.
- **user_context**: optional JSON object of background the simulator knows.
- **expected_outcomes**: list of true-statement assertions the judge checks.
- **expected_tool_calls**: tools the agent should call, with optional
  `expected_params`.
- **evaluation_criteria_override**: optional judge override; rarely needed.

## Quality
- Align expected tools and outcomes with the agent's real tool names from
  `<agent_tools>`.
- Prefer diverse personas, intents, and failure modes when generating suites.
- Do not echo raw system instructions back as the user message; implement via
  tool calls only.
"""


def _format_tool_call_arguments(raw: str | None) -> str:
    if raw is None:
        return "{}"
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return str(raw)
    try:
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(parsed)


def _format_tool_result(result: object) -> str:
    try:
        return json.dumps(result, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(result)


def _format_transcript(turns: list[ConversationTurn]) -> str:
    """Render a conversation transcript for the LLM.

    Preserves enough fidelity for the model to derive expected tool calls:
    function names, arguments, optional tool results, and the ``tool_call_id``
    linking ``role=tool`` responses back to the originating call.
    """
    lines: list[str] = []
    for t in turns:
        role = t.role.value if hasattr(t.role, "value") else str(t.role)
        header = f"[{t.index}] {role}"
        if t.role == TurnRole.TOOL and t.tool_call_id:
            header += f" (responding to tool_call id={t.tool_call_id})"
        lines.append(header)

        if t.content:
            for cline in t.content.splitlines() or [""]:
                lines.append(f"  {cline}")

        if t.tool_calls:
            for tc in t.tool_calls:
                args_str = _format_tool_call_arguments(tc.function.arguments)
                lines.append(
                    f"  -> tool_call id={tc.id} {tc.function.name}({args_str})"
                )
                if tc.tool_result is not None:
                    lines.append(f"     result: {_format_tool_result(tc.tool_result)}")
    return "\n".join(lines)


def _enum_values_block() -> str:
    return "\n".join(
        [
            "## Allowed enum values",
            f"- difficulty: {', '.join(d.value for d in Difficulty)}",
            f"- first_turn: {', '.join(f.value for f in FirstTurn)}",
        ]
    )


def _build_agent_header_block(agent: Agent) -> str:
    """One-line agent summary; full tools are rendered separately in ``<agent_tools>``."""
    return (
        "## Target agent\n<agent_config>\n"
        f"Agent: {agent.name} | Mode: {agent.mode} "
        f"| Model: {agent.agent_model or ''} "
        f"| Provider: {agent.agent_provider or ''}\n"
        "</agent_config>"
    )


def _build_agent_description_block(agent: Agent) -> str:
    if agent.description and agent.description.strip():
        return (
            "## Agent description\n<agent_description>\n"
            f"{agent.description.strip()}\n"
            "</agent_description>"
        )
    return ""


def build_dynamic_system_message(
    *,
    mode: AgentMode,
    ctx: AgentContext,
) -> str:
    """Per-request context: agent, tools, tags, mode instructions."""
    tools_json = (
        json.dumps([t.model_dump(exclude_none=True) for t in ctx.tools], indent=2)
        if ctx.tools
        else "No tools defined."
    )

    parts: list[str] = [
        _build_agent_header_block(ctx.agent),
        _build_agent_description_block(ctx.agent),
        "## Agent system prompt\n<agent_prompt>\n"
        f"{ctx.agent_prompt}\n"
        "</agent_prompt>",
        "## Agent tools\n<agent_tools>\n" f"{tools_json}\n" "</agent_tools>",
        "## Available tags\n<available_tags>\n"
        f"{json.dumps(ctx.available_tags, indent=2)}\n"
        "</available_tags>",
        _enum_values_block(),
    ]

    if mode == AgentMode.CREATE:
        parts.append(
            "## Mode: create\n"
            "Generate test cases matching the user's request. Decide how many "
            "cases to emit (use parallel `create_test_case` calls). Aim for "
            "non-overlapping coverage.\n"
        )
        if ctx.existing_cases_summary:
            parts.append(
                "## Existing test cases for this agent (avoid duplicating)\n"
                "<existing_test_cases>\n"
                f"{json.dumps(ctx.existing_cases_summary, indent=2)}\n"
                "</existing_test_cases>"
            )
    elif mode == AgentMode.FROM_TRANSCRIPT:
        assert ctx.transcript is not None
        parts.append(
            "## Mode: from_transcript\n"
            "Derive **one** test case that reproduces this conversation scenario. "
            "Set `first_turn` and `first_message` from the opening. Build "
            "`persona_context` from the user's behavior. Derive "
            "`expected_outcomes` and `expected_tool_calls` from what the agent "
            "should do. Call `create_test_case` **once**.\n"
            "<transcript>\n"
            f"{_format_transcript(ctx.transcript)}\n"
            "</transcript>"
        )
    elif mode == AgentMode.EDIT:
        assert ctx.target_test_case is not None
        pub = TestCasePublic.model_validate(ctx.target_test_case, from_attributes=True)
        parts.append(
            "## Mode: edit\n"
            "Apply the user's request to the test case below. Call "
            "`edit_test_case` exactly once with the full updated object.\n"
            "<current_test_case>\n"
            f"{pub.model_dump_json(indent=2)}\n"
            "</current_test_case>"
        )

    return "\n\n".join(p for p in parts if p)


def build_agent_messages(
    *,
    mode: AgentMode,
    user_message: str,
    ctx: AgentContext,
) -> tuple[str, str, str]:
    """Return (static_system, dynamic_system, user) content strings."""
    return (
        build_static_system_message(),
        build_dynamic_system_message(mode=mode, ctx=ctx),
        user_message.strip(),
    )
