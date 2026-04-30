"""System and user messages for the interactive test-case agent."""

import json
from typing import Any

from app.models.agent import Agent
from app.models.enums import Difficulty, FirstTurn, TurnRole
from app.models.schemas import ConversationTurn
from app.models.test_case import TestCasePublic
from app.services.test_case_generator.batch.schemas import ToolDefinition
from app.services.test_case_generator.interactive.context import AgentContext
from app.services.test_case_generator.interactive.schemas import AgentMode


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

## Key Field Details
- **name**: short and informative; use at most 7 words and 60 characters.
- **description**: what this case checks for humans.
- **difficulty**: either `normal` or `hard`.
- **tags**: MUST include at least one category tag: `normal`, `edge-case`, or
  `red-team`. You may add more tags from `<available_tags>` for consistency
  with this agent's suite.
- **persona_context**: a single text block with these exact sections:
  `[Persona type]`, `[Description]`, `[Behavioral instructions]`.
- **first_turn**: who speaks first — `user` by default, or `agent` for
  greeting/welcome scenarios.
- **first_message**: the opening message for whoever speaks first.
- **user_context**: optional JSON object of background the simulator knows.
- **expected_outcomes**: list of true-statement assertions the judge evaluates
  (for example: `Agent MUST confirm the appointment date`).
- **expected_tool_calls**: list of tools the agent should invoke, each with
  `tool` (name), `expected_params`, and `mock_responses`.
- **evaluation_criteria_override**: optional judge override; rarely needed.

## Persona Requirements
- Every `persona_context` MUST include all three section labels exactly:
  `[Persona type]`, `[Description]`, `[Behavioral instructions]`.
- Persona type should be a concise role/archetype, not a name.
- Description should explain the user's situation, knowledge, emotional state,
  and constraints.
- Description should include stable user-provided details the simulator may
  need to reveal. Examples: full name, phone number, street address, appliance
  type, account/order identifiers, dates already known to the user, or
  locations.
- Do not force derived or agent-selected tool arguments into `persona_context`.
  Examples: exact startTime chosen after availability lookup, computed
  startDate, current time, IDs returned by earlier tools, or other values the
  agent can derive.
- Behavioral instructions should tell the simulator how to reveal information,
  push back, omit details, or cooperate.

## Tool And Mock Requirements
- Use only tool names listed in `<agent_tools>`.
- If a case expects tool usage, include every required parameter from the tool
  schema in `expected_params`.
- Every expected tool call MUST include `mock_responses` with at least one
  canned response.
- `mock_responses[].expected_params` MUST include every required parameter for
  that tool using the same values as `expected_params`. If the tool has no
  required parameters, `mock_responses[].expected_params` may be null to match
  any call.
- `mock_responses[].response` should be realistic tool output that the agent
  can use to continue the conversation.
- If a case intentionally tests no-tool behavior, use `expected_tool_calls: []`
  or omit it.

## Diversity Requirements
- Include a mix of happy-path/normal cases, edge cases, and
  red-team/adversarial cases when generating suites.
- Vary persona types, emotional states, and communication styles.
- Vary difficulty levels (`normal` and `hard`) when generating suites.
- Include cases that test tool usage, multi-turn reasoning, safety guardrails,
  and error handling.
- Each generated test case MUST have unique, non-overlapping coverage.
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


def _tool_summary(tool: ToolDefinition) -> dict[str, object]:
    params = tool.parameters if isinstance(tool.parameters, dict) else {}
    required = params.get("required")
    required_params = (
        [str(item) for item in required if isinstance(item, str)]
        if isinstance(required, list)
        else []
    )
    return {
        "name": tool.name,
        "description": tool.description,
        "required_params": required_params,
        "parameters": params,
    }


def _format_tools(tools: list[ToolDefinition]) -> str:
    if not tools:
        return "No tools defined."
    return json.dumps([_tool_summary(t) for t in tools], indent=2)


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
    parts: list[str] = [
        _build_agent_header_block(ctx.agent),
        _build_agent_description_block(ctx.agent),
        "## Agent system prompt\n<agent_prompt>\n"
        f"{ctx.agent_prompt}\n"
        "</agent_prompt>",
        "## Agent tools\n<agent_tools>\n"
        f"{_format_tools(ctx.tools)}\n"
        "</agent_tools>",
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
            "Derive one or more test cases that reproduce important scenarios from "
            "this conversation. "
            "Set `first_turn` and `first_message` from the opening. Build "
            "`persona_context` from the user's behavior. Derive "
            "`expected_outcomes` and `expected_tool_calls` from what the agent "
            "should do. Use one `create_test_case` call per test case.\n"
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
            "Preserve fields the user did not ask to change, but keep related "
            "fields consistent when a requested change requires it.\n"
            "If you add or change `expected_tool_calls`, audit `persona_context`: "
            "any stable user-provided values that the simulator must reveal so "
            "the agent can produce those `expected_params` must appear in the "
            "`[Description]` section. Examples include names, phone numbers, "
            "addresses, appliance types, account/order identifiers, user-known "
            "dates, and locations. Do not add derived or agent-selected values "
            "such as returned IDs, computed dates, selected time slots, current "
            "time, or values the agent should obtain from a previous tool.\n"
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


def build_repair_user_prompt(
    *,
    mode: AgentMode,
    validation_errors: list[str],
    previous_tool_calls: list[dict[str, Any]] | None,
    expected_create_count: int | None,
    failed_indices: list[int] | None = None,
) -> str:
    errors = "\n".join(f"- {err}" for err in validation_errors)
    previous = (
        json.dumps(previous_tool_calls, indent=2, ensure_ascii=False)
        if previous_tool_calls
        else "No tool calls were returned."
    )

    if mode in (AgentMode.CREATE, AgentMode.FROM_TRANSCRIPT):
        if failed_indices:
            failed_index_list = ", ".join(
                f"create_test_case[{index}]" for index in failed_indices
            )
            count_instruction = (
                f"Regenerate ONLY these failed tool calls: {failed_index_list}. "
                f"Call `create_test_case` exactly {len(failed_indices)} time(s), "
                "in the same order as the failed indices. Do not include "
                "already-valid test cases."
            )
        else:
            count_instruction = (
                f"Call `create_test_case` exactly {expected_create_count} time(s)."
                if expected_create_count is not None
                else "Call `create_test_case` once per corrected test case."
            )
        tool_instruction = f"{count_instruction} Do not call any other tool."
    else:
        tool_instruction = (
            "Call `edit_test_case` exactly once with the complete corrected test case. "
            "Do not call any other tool."
        )

    return f"""\
The previous tool-call response was invalid.

Repair it by emitting corrected tool calls only. {tool_instruction}
Do not explain the fix.

Validation errors:
{errors}

Previous tool calls:
```json
{previous}
```
"""
