"""Editor-agent system prompts, message building, and line-based edit application.

Supports two modes selected by whether ``current_prompt`` is empty:

* **Creating** — multi-turn interview to collect requirements, then generate the
  full prompt via the ``generate_prompt`` tool.
* **Editing** — incremental line-based edits via the ``edit_prompt`` tool.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.models.agent import Agent
from app.models.enums import AgentMode, TurnRole
from app.models.prompt_editor import PromptEditorMessage
from app.services.llm import LLMMessage, LLMToolCall
from app.services.prompt_editor.guidelines import load_provider_guidelines

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

EDIT_PROMPT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_prompt",
        "description": (
            "Replace lines in the agent's system prompt. Line numbers refer to the prompt as shown "
            "in <current_prompt> before any edits in this turn. For multiple edits in one turn, "
            "all line numbers reference that same original; the backend applies edits bottom-up "
            "by start_line. Use empty new_content to delete lines. If start_line > end_line, "
            "insert new_content after line start_line (1-based) without replacing lines."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_line": {
                    "type": "integer",
                    "description": "1-based start line (inclusive) for replace; for insert-after, start_line > end_line",
                },
                "end_line": {
                    "type": "integer",
                    "description": "1-based end line (inclusive) for replace",
                },
                "new_content": {
                    "type": "string",
                    "description": "Replacement text (may include newlines). Empty string deletes the range.",
                },
            },
            "required": ["start_line", "end_line", "new_content"],
        },
    },
}

GENERATE_PROMPT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_prompt",
        "description": (
            "Output the complete system prompt for the voice AI agent. "
            "Call this ONLY after you have collected enough information from "
            "the user through the interview. The content should be the full, "
            "ready-to-use system prompt text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": (
                        "The complete system prompt text for the agent. "
                        "Must include all sections (role, tools, conversation flow, "
                        "style, guidelines, etc.) based on the information collected."
                    ),
                },
            },
            "required": ["content"],
        },
    },
}


def add_line_numbers(prompt: str) -> str:
    """Prefix each line with ``N | `` (1-based)."""
    if not prompt:
        return "1 | "
    lines = prompt.split("\n")
    return "\n".join(f"{i + 1} | {line}" for i, line in enumerate(lines))


def get_prompt_line_count(prompt: str) -> int:
    """Return the number of lines in the prompt (minimum 1 for empty string)."""
    if not prompt:
        return 1
    return len(prompt.split("\n"))


def apply_edits_to_prompt(
    prompt: str,
    edits: list[tuple[int, int, str]],
) -> str:
    """Apply edits to ``prompt``. Each edit is ``(start_line, end_line, new_content)`` (1-based, inclusive).

    All line numbers refer to the **original** ``prompt``. Edits are sorted by ``start_line``
    descending before application to avoid line-shift issues within one batch.
    """
    if not edits:
        return prompt
    lines = prompt.split("\n")
    ordered = sorted(edits, key=lambda e: e[0], reverse=True)
    for start_line, end_line, new_content in ordered:
        lines = _apply_one_edit_lines(lines, start_line, end_line, new_content)
    return "\n".join(lines)


def apply_edits_progressively(
    prompt: str,
    edits: list[tuple[int, int, str]],
) -> list[str]:
    """Return full-text snapshots after each successive edit (visual order: ascending ``start_line``).

    Each snapshot applies the first *k* edits from that ordering to the **original** ``prompt``,
    with those *k* edits applied bottom-up (by ``start_line`` descending).
    """
    if not edits:
        return []
    visual = sorted(edits, key=lambda e: e[0])
    out: list[str] = []
    for k in range(len(visual)):
        subset = visual[: k + 1]
        out.append(apply_edits_to_prompt(prompt, subset))
    return out


def _apply_one_edit_lines(
    lines: list[str],
    start_line: int,
    end_line: int,
    new_content: str,
) -> list[str]:
    """Apply a single edit to a list of lines (0-based indexing internally)."""
    n = len(lines)
    if start_line < 1 or start_line > n:
        logger.warning(
            "edit_prompt: start_line %s out of range (lines=%s)", start_line, n
        )
        return lines
    if start_line > end_line:
        # insert after line start_line (1-based) -> at index start_line
        insert_at = start_line
        chunk = new_content.split("\n") if new_content else []
        return lines[:insert_at] + chunk + lines[insert_at:]
    if end_line < start_line:
        logger.warning("edit_prompt: invalid range %s-%s", start_line, end_line)
        return lines
    if end_line > n:
        logger.warning("edit_prompt: end_line %s out of range (lines=%s)", end_line, n)
        return lines
    lo = start_line - 1
    hi = end_line
    chunk = new_content.split("\n") if new_content else []
    return lines[:lo] + chunk + lines[hi:]


def _extract_agent_tool_names(agent: Agent) -> list[str]:
    """Return the tool function names declared on the agent."""
    tool_names: list[str] = []
    if agent.tools:
        for t in agent.tools:
            if isinstance(t, dict) and "function" in t:
                fn = t.get("function")
                if isinstance(fn, dict) and "name" in fn:
                    tool_names.append(str(fn["name"]))
            elif isinstance(t, dict) and "name" in t:
                tool_names.append(str(t["name"]))
    return tool_names


def _build_agent_config_block(agent: Agent) -> str:
    """Render the ``<agent_config>`` block used by both modes."""
    tool_names = _extract_agent_tool_names(agent)
    tools_line = ", ".join(tool_names) if tool_names else "(none)"
    return (
        "## Target agent configuration\n<agent_config>\n"
        f"Agent: {agent.name} | Mode: {agent.mode} "
        f"| Model: {agent.agent_model or ''} "
        f"| Provider: {agent.agent_provider or ''}\n"
        f"Tools ({len(tool_names)}): {tools_line}\n"
        "</agent_config>"
    )


# ---------------------------------------------------------------------------
# EDITING mode prompts (existing prompt is non-empty)
# ---------------------------------------------------------------------------


def build_static_system_message(*, target_provider: str | None) -> str:
    """First system block: identity, behavior, guidelines, tools, reasoning-then-edit."""
    guidelines = load_provider_guidelines(target_provider)
    tool_schema = json.dumps(EDIT_PROMPT_TOOL, indent=2)
    return f"""\
You are a senior prompt engineer specializing in **Voice AI and conversational agent** system prompts. You help users iteratively improve their agent's system prompt — making it clearer, more robust, and better aligned with how the target LLM will interpret it.

The `<agent_config>` block tells you what agent this prompt powers (name, mode, model, provider, tools). Use it to tailor your advice — e.g. align prompt instructions with the declared tools, respect provider-specific idioms, and match the agent's purpose.

## How you work
- Be collaborative, not prescriptive. Preserve the user's intent, voice, and existing structure.
- **First** write your reasoning, **then** call `edit_prompt` one or more times.
- All line numbers in tool calls refer to `<current_prompt>` **before any edits in this turn**.
- If the user's request is vague or could be interpreted multiple ways, ask a clarifying question instead of guessing.

## Reasoning format
Structure your explanation before each edit:
1. **Observation** — What the current prompt does (or fails to do).
2. **Impact** — Why it matters for the agent's behavior or reliability.
3. **Change** — What you will edit and how it fixes the issue.

Keep reasoning concise — a few sentences per edit, not paragraphs. Group reasoning for related edits together, then apply them all.

## Edit strategy
Match your approach to the size of the request:

- **Surgical fix** (typo, wording tweak, add a sentence): Single edit, minimal explanation.
- **Targeted improvement** (improve greeting, add error handling, fix a section): Explain the issue, make focused edits to the relevant section.
- **General review** ("make this better", "improve this prompt"): Assess the prompt using the quality checklist below, identify the 2–3 highest-impact issues, and address those. Don't try to fix everything at once.
- **Restructure / rewrite**: Explain the new organization first, then apply edits section by section.

Prefer incremental improvements unless the user explicitly asks for a full rewrite.

## Quality checklist
When reviewing or improving a prompt, evaluate these dimensions (in priority order):

1. **Clarity** — Are instructions unambiguous? Could the LLM misinterpret any rule?
2. **Completeness** — Are edge cases, error paths, and fallback behaviors covered?
3. **Tool alignment** — Do prompt instructions match the agent's declared tools? Are there tools referenced in the prompt that don't exist, or declared tools the prompt never mentions?
4. **Structure** — Does it follow a logical section flow? For Voice AI agents, the recommended structure is: `<role>`, `<tool_logic>`, `<objective>`, `<goal>`, `<communicationStyle>`, `<rules>`, `<business_information>`, `<guidelines>`. Sections can be added, removed, or renamed as needed.
5. **Specificity** — Concrete instructions ("respond in 1–2 sentences") vs. vague adjectives ("be concise")?
6. **Consistency** — No contradictory rules? Later sections don't silently override earlier constraints?
7. **Guardrails** — Are safety rules, forbidden topics, and escalation paths present and clear?

## Using eval context
When `<eval_context>` is present, it contains results from running the agent against test scenarios. Prioritize fixes that address observed failures or regressions in those results. Reference specific eval findings in your reasoning.

## Prompting practices
{guidelines.strip()}

## Tool available
```json
{tool_schema}
```
"""


def build_dynamic_system_message(
    *,
    current_prompt: str,
    agent: Agent,
    eval_context: str | None = None,
) -> str:
    """Second system block: numbered current prompt + agent summary + optional eval context."""
    numbered = add_line_numbers(current_prompt)
    parts = [
        "## Current prompt (with line numbers)\n<current_prompt>\n"
        f"{numbered}\n"
        "</current_prompt>",
        _build_agent_config_block(agent),
    ]
    if eval_context and eval_context.strip():
        parts.append(
            f"## Eval context\n<eval_context>\n{eval_context.strip()}\n</eval_context>"
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# CREATING mode prompts (prompt is empty — interview → generate)
# ---------------------------------------------------------------------------


def build_creator_static_system_message(*, target_provider: str | None) -> str:
    """System prompt for the creating mode: interview the user then generate."""
    guidelines = load_provider_guidelines(target_provider)
    tool_schema = json.dumps(GENERATE_PROMPT_TOOL, indent=2)
    return f"""\
You are an expert prompt engineer helping a user **create a system prompt from scratch** for a Voice AI agent.

## How you work
You conduct a structured interview, asking questions **one at a time**, to collect the information needed to produce a professional, production-quality system prompt. After you have gathered enough detail, you generate the full prompt by calling the `generate_prompt` tool.

### Interview rules
- Ask **one question per message**. Never combine multiple questions.
- After the user answers, briefly acknowledge their answer, then ask the next question.
- If the user volunteers information that covers a future question, note it and skip that question.
- If the user says "skip" or doesn't know, move on — use sensible defaults.
- If the user wants to jump ahead and generate the prompt early, do so with what you have.
- Keep a friendly, collaborative tone. You are a partner, not an interrogator.

### Interview checklist
Collect the following information in roughly this order. Skip questions whose answers are already obvious from the agent configuration or prior answers.

**Phase 1 — Identity & Purpose**
1. Agent name (how the agent introduces itself)
2. Company / organization the agent represents
3. Agent's primary role (sales rep, receptionist, scheduler, lead qualifier, support, intake specialist, etc.)
4. Main goal of each call (book appointments, qualify leads, collect info, answer questions, transfer to sales, etc.)

**Phase 2 — Context & Audience**
5. Inbound calls, outbound calls, or both?
6. Who are the typical callers? (consumers, patients, business owners, existing customers, cold leads, etc.)
7. Industry (healthcare, home services, legal, real estate, insurance, SaaS, restaurant, etc.)

**Phase 3 — Conversation Flow**
8. How should the agent greet the caller?
9. What information must be collected during the call? (name, phone, email, address, zip/postal code, reason for call, etc.)
10. What are the main stages / steps of the conversation? (e.g. greet → identify need → collect info → check availability → book → confirm → close)
11. Are there different paths based on caller intent? (e.g. new vs existing customer, residential vs commercial, different service types)
12. When should the agent transfer to a human? (existing customer issues, emergencies, complaints, specific requests)
13. How should the call end? (confirmation summary, goodbye script, end_call tool, etc.)

**Phase 4 — Business Knowledge**
14. What services or products does the company offer? (list with brief descriptions)
15. Common FAQs callers ask (pricing, hours, process, requirements, etc.)
16. Should the agent discuss pricing? (exact quotes, ranges, "call for quote", never)
17. Business hours
18. Contact information (phone, email, website, address)

**Phase 5 — Tools & Integrations**
19. What tools / functions does the agent have access to? (check_availability, book_appointment, transfer_call, end_call, lookup_customer, send_sms, etc.)
20. Specific rules for when each tool should be called
21. Formatting requirements for tool parameters (date formats, phone number formats, etc.)

**Phase 6 — Communication Style & Voice**
22. Tone and personality (warm & casual, professional, empathetic, energetic, etc.)
23. Response length / conciseness (e.g. "under 25 words unless more detail requested")
24. Pronunciation rules (brand names, acronyms, how to say numbers / dates / prices)

**Phase 7 — Rules & Guardrails**
25. Topics the agent must NEVER discuss (competitors, medical/legal advice, promises, discounts, etc.)
26. How to handle "are you a robot / AI?" questions
27. What to do when the agent doesn't know the answer (defer to human, "I'll have someone follow up", etc.)
28. Any other critical rules (one question at a time, never address caller by name, always confirm postal code, etc.)

You do NOT need to ask every question if the user has already provided the information or it's not relevant. Use your judgment to keep the interview efficient.

### Generating the prompt
When you have enough information (at minimum: identity, goal, conversation flow, and communication style), call the `generate_prompt` tool with the complete system prompt text.

The generated prompt MUST follow this structure for a Voice AI agent:

```
<role>
Agent identity, company, persona, and voice output requirements.
</role>

<tool_logic>
When and how to call each tool, parameter formats, output rules.
</tool_logic>

<objective>
Step-by-step conversation flow with branching logic.
</objective>

<goal>
One-liner primary objective.
</goal>

<communicationStyle>
Tone, formality, response length, natural speech patterns.
</communicationStyle>

<rules>
Interaction rules: one question at a time, keep conversation active, etc.
</rules>

<business_information>
Services, FAQs, pricing, hours, contact info.
</business_information>

<guidelines>
Guardrails, forbidden topics, escalation paths, edge case handling.
</guidelines>
```

Adapt the sections based on what's relevant. Omit sections that have no content. Add sections if the use case requires them (e.g. `<tts_pronunciation>`, `<exampleEnding>`).

## Prompting practices
{guidelines.strip()}

## Tool available
```json
{tool_schema}
```
"""


def build_creator_dynamic_system_message(*, agent: Agent) -> str:
    """Dynamic block for creating mode: agent config only (no current prompt)."""
    return _build_agent_config_block(agent)


_TOOL_RESULT_MESSAGES: dict[str, str] = {
    "edit_prompt": "Edit applied successfully.",
    "generate_prompt": "Prompt generated and saved successfully.",
}


def prompt_editor_messages_to_llm_history(
    messages: list[PromptEditorMessage],
) -> list[LLMMessage]:
    """Turn stored DB messages into LLM messages including synthetic tool results."""
    history: list[LLMMessage] = []
    for msg in messages:
        if msg.role == TurnRole.USER:
            history.append(LLMMessage(role="user", content=msg.content))
        elif msg.role == TurnRole.ASSISTANT:
            history.append(
                LLMMessage(
                    role="assistant",
                    content=msg.content,
                    tool_calls=msg.tool_calls,
                )
            )
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tid = tc.get("id")
                    if not tid:
                        continue
                    fn_name = (
                        tc.get("function", {}).get("name", "edit_prompt")
                        if isinstance(tc.get("function"), dict)
                        else "edit_prompt"
                    )
                    result_text = _TOOL_RESULT_MESSAGES.get(
                        fn_name, "Tool executed successfully."
                    )
                    history.append(
                        LLMMessage(
                            role="tool",
                            content=result_text,
                            tool_call_id=str(tid),
                            name=fn_name,
                        )
                    )
    return history


def is_creating_mode(current_prompt: str) -> bool:
    """Return ``True`` when the prompt is empty (creating mode)."""
    return not current_prompt.strip()


def build_editor_messages(
    *,
    agent: Agent,
    session_messages: list[PromptEditorMessage],
    user_message: str,
    current_prompt: str,
    eval_context: str | None = None,
) -> list[LLMMessage]:
    """Build messages for the editor LLM.

    Dispatches to **creating** mode when ``current_prompt`` is empty, otherwise
    uses **editing** mode.  Both return two system messages (static + dynamic).
    """
    if is_creating_mode(current_prompt):
        static = build_creator_static_system_message(
            target_provider=agent.agent_provider,
        )
        dynamic = build_creator_dynamic_system_message(agent=agent)
    else:
        static = build_static_system_message(target_provider=agent.agent_provider)
        dynamic = build_dynamic_system_message(
            current_prompt=current_prompt,
            agent=agent,
            eval_context=eval_context,
        )
    out: list[LLMMessage] = [
        LLMMessage(role="system", content=static),
        LLMMessage(role="system", content=dynamic),
    ]
    out.extend(prompt_editor_messages_to_llm_history(session_messages))
    out.append(LLMMessage(role="user", content=user_message))
    return out


def parse_edit_prompt_tool_calls(
    tool_calls: list[LLMToolCall],
) -> list[tuple[int, int, str]]:
    """Extract ``(start_line, end_line, new_content)`` from ``edit_prompt`` tool calls only."""
    edits: list[tuple[int, int, str]] = []
    for tc in tool_calls:
        if tc.function_name != "edit_prompt":
            continue
        args = tc.arguments
        try:
            s = int(args["start_line"])
            e = int(args["end_line"])
            new_content = str(args.get("new_content", ""))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Invalid edit_prompt arguments: %s", exc)
            continue
        edits.append((s, e, new_content))
    return edits


def parse_generate_prompt_tool_call(
    tool_calls: list[LLMToolCall],
) -> str | None:
    """Return the ``content`` from the first ``generate_prompt`` tool call, or ``None``."""
    for tc in tool_calls:
        if tc.function_name != "generate_prompt":
            continue
        content = tc.arguments.get("content")
        if isinstance(content, str) and content.strip():
            return content
    return None


def validate_edits_against_line_count(
    edits: list[tuple[int, int, str]],
    line_count: int,
) -> list[tuple[int, int, str]]:
    """Drop edits whose replace range is out of bounds; inserts validated separately in apply."""
    valid: list[tuple[int, int, str]] = []
    for start_line, end_line, new_content in edits:
        if start_line > end_line:
            if start_line < 1 or start_line > line_count:
                logger.warning(
                    "Dropping insert-after edit: start_line %s invalid", start_line
                )
                continue
            valid.append((start_line, end_line, new_content))
            continue
        if start_line < 1 or end_line > line_count or end_line < start_line:
            logger.warning(
                "Dropping edit: range %s-%s invalid for %s lines",
                start_line,
                end_line,
                line_count,
            )
            continue
        valid.append((start_line, end_line, new_content))
    return valid


def llm_tool_calls_to_openai_dicts(
    tool_calls: list[LLMToolCall],
) -> list[dict[str, Any]]:
    """Serialize tool calls for JSONB storage / replay."""
    out: list[dict[str, Any]] = []
    for tc in tool_calls:
        out.append(
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function_name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
        )
    return out


def platform_agent_required(agent: Agent) -> None:
    """Raise ``ValueError`` if the agent is not a platform agent."""
    if agent.mode != AgentMode.PLATFORM:
        msg = "Prompt editor requires a platform agent"
        raise ValueError(msg)
