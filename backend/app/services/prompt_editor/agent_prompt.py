"""Editor-agent system prompts, message building, and line-based edit application.

Supports two modes selected by whether ``current_prompt`` is empty:

* **Creating** — multi-turn interview to collect requirements, then generate the
  full prompt via the ``generate_prompt`` tool.
* **Editing** — incremental line-based edits via the ``edit_prompt`` tool.
"""

import json
import logging
from typing import Any

from app.models.agent import Agent
from app.models.enums import AgentMode, TurnRole
from app.models.prompt_editor import PromptEditorMessage
from app.services.llm import LLMMessage, LLMToolCall

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in default prompting practices (editor agent; also returned by GET guidelines when custom is unset)
# ---------------------------------------------------------------------------

DEFAULT_EDITOR_GUIDELINES: str = """\
# Prompt engineering for voice and conversational agents

Use these practices when drafting or improving system prompts. They apply across providers (OpenAI, Anthropic, Google, etc.) and modalities (voice, chat).

## Structure and hierarchy

- Organize long prompts with **clear sections**: role, goals, constraints, tool usage, output format, edge cases, and safety. Use **XML-style tags** (e.g. `<role>`, `<tool_logic>`, `<rules>`) or **markdown headings** consistently.
- Put **non-negotiable rules first** or repeat them where they apply; models weight early and repeated constraints more reliably.
- Separate **must-follow** rules from **nice-to-have** tone or style guidance.
- For multi-step flows, use **numbered steps** or ordered bullets the model can follow in sequence.
- Avoid walls of unstructured prose; short paragraphs and lists beat dense paragraphs.

## Specificity over vagueness

- Prefer **measurable or concrete** instructions: "Reply in 1–2 sentences unless the user asks for detail" rather than "be concise."
- Specify **formats** when it matters: dates (ISO vs spoken), phone numbers, currency, how to read codes or IDs aloud.
- State **defaults** when the user is silent (e.g. default timezone, language, escalation path).

## Tool alignment

- **Name tools accurately** in the prompt only if they exist in the agent's tool list; remove references to tools that are not deployed.
- For each tool: **when to call it**, **required parameters**, **what to do on empty or error results**, and **whether to tell the user** before/after calling.
- Keep tool-related instructions **aligned** with the tool definitions (names, descriptions, argument shapes).
- If the stack uses separate system vs developer messages, keep **stable policy** in system and **task-specific** details where your platform expects them.

## Examples and edge cases

- Add **short examples** when behavior is easy to misinterpret (e.g. how to refuse a request, how to confirm a booking).
- Cover **error paths**: timeouts, failed lookups, ambiguous user input, and **fallback** behaviors (retry once, apologize, offer human).
- For voice: call out **barge-in**, **silence**, **unclear audio**, and **repeat-back** for critical data (addresses, numbers).

## Consistency

- Ensure **later sections do not contradict** earlier hard constraints unless you explicitly say the override is intentional.
- Use one term for one concept (e.g. "caller" vs "user" vs "customer" — pick one for the runbook).

## Safety, guardrails, and escalation

- State **forbidden topics** and **disallowed commitments** (medical/legal advice, guaranteed outcomes, unauthorized discounts).
- Define **escalation**: when to transfer to a human, how to phrase it, and what data to collect first.
- Handle **"Are you an AI?"** and similar in line with your brand policy (honest, brief, and on-script).
- When the model **does not know**, specify **exact phrasing** to defer or follow up rather than guessing.

## Voice AI specifics

- **Greeting**: first impression, brand voice, and any required legal disclaimer.
- **Information collection**: one question at a time when appropriate; confirm critical fields (spelling, numbers).
- **Turn-taking**: keep responses short enough for natural back-and-forth; avoid monologues unless the persona requires it.
- **Closing**: summary, next steps, and clean hangup or `end_call` behavior if applicable.
- **TTS / pronunciation**: spell out tricky brand names, acronyms, and how to say prices, dates, and phone numbers if your TTS stack needs it.

## JSON, structured output, and strict formats

- If output must match a schema, **show the schema** and a **minimal valid example**.
- Say explicitly what to do on **parse errors** or **partial** structured output.

## Reasoning and internal thought

- If the target stack uses chain-of-thought or hidden reasoning, **separate** internal reasoning from **user-visible** speech in the prompt design so the agent does not leak internal steps to the caller.

## Prompt caching and long static instructions

- Put **stable, reusable** instructions in a fixed prefix; vary only **suffixes** with per-session or per-user content so caches stay effective where supported.

## Review mindset

- After edits, mentally simulate **three paths**: happy path, user confusion, and tool failure — each should have clear instructions.
"""


def get_effective_guidelines(custom: str | None) -> str:
    """Return custom guidelines if set and non-empty after strip; otherwise the built-in default."""
    if custom is not None and custom.strip():
        return custom.strip()
    return DEFAULT_EDITOR_GUIDELINES


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

EDIT_PROMPT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "edit_prompt",
        "description": (
            "Replace lines in the agent's system prompt. Line numbers refer to the prompt "
            "as shown in <current_prompt>. For multiple edits in one response, all line "
            "numbers reference the same snapshot; the backend applies edits bottom-up by "
            "start_line. Use empty new_content to delete lines. If start_line > end_line, "
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


# ---------------------------------------------------------------------------
# Agent-config block (used by editing + creating dynamic system messages)
# ---------------------------------------------------------------------------


def _extract_agent_tools(agent: Agent) -> list[dict[str, Any]]:
    """Return OpenAI-style tool dicts defined on the agent (``type``/``function``).

    Entries that do not match the expected shape are skipped so we never
    surface malformed tools to the LLM.
    """
    tools: list[dict[str, Any]] = []
    if not agent.tools:
        return tools
    for t in agent.tools:
        if not isinstance(t, dict):
            continue
        fn = t.get("function") if "function" in t else None
        if isinstance(fn, dict) and fn.get("name"):
            tools.append(
                {
                    "name": str(fn.get("name", "")),
                    "description": str(fn.get("description") or ""),
                    "parameters": fn.get("parameters") or {},
                }
            )
        elif t.get("name"):
            tools.append(
                {
                    "name": str(t.get("name", "")),
                    "description": str(t.get("description") or ""),
                    "parameters": t.get("parameters") or {},
                }
            )
    return tools


def build_agent_config_block(agent: Agent) -> str:
    """Render ``<agent_config>`` with full tool schemas (not just names).

    The editor needs to see each tool's description and parameter schema so it
    can align prompt instructions with the actual tool surface the agent has.
    """
    tools = _extract_agent_tools(agent)
    header = (
        f"Agent: {agent.name} | Mode: {agent.mode} "
        f"| Model: {agent.agent_model or ''} "
        f"| Provider: {agent.agent_provider or ''}"
    )
    tools_json = json.dumps(tools, indent=2, ensure_ascii=False) if tools else "(none)"
    return (
        "## Target agent configuration\n<agent_config>\n"
        f"{header}\n"
        f"Tools ({len(tools)}):\n{tools_json}\n"
        "</agent_config>"
    )


# ---------------------------------------------------------------------------
# EDITING mode prompts (existing prompt is non-empty)
# ---------------------------------------------------------------------------


def build_static_system_message(*, editor_guidelines: str | None) -> str:
    """First system block: identity, behavior, guidelines, brief-summary-then-edit."""
    guidelines = get_effective_guidelines(editor_guidelines)
    return f"""\
You are a senior prompt engineer specializing in **Voice AI and conversational agent** system prompts. You help users iteratively improve their agent's system prompt — making it clearer, more robust, and better aligned with how the target LLM will interpret it.

The `<agent_config>` block tells you what agent this prompt powers (name, mode, model, provider, tools). Use it to tailor your advice — e.g. align prompt instructions with the declared tools, respect provider-specific idioms, and match the agent's purpose.

## How you work
- Be collaborative, not prescriptive. Preserve the user's intent, voice, and existing structure.
- Use a **separate `edit_prompt` call for each logically distinct change**. If the user asks for three things, make three `edit_prompt` calls (one per change). Never silently drop part of a request.
- **Address every part of the user's request.** If the user mentions N changes, you should generally produce N tool calls.
- All line numbers in tool calls refer to `<current_prompt>` as shown — the backend handles line-shift math.
- If the user's request is vague or could be interpreted multiple ways, ask a clarifying question instead of guessing.

## Your response format
Before calling tools, write **1–3 sentences** summarizing what you will change and why. This text is shown directly to the user in a chat bubble — keep it conversational and brief. The user sees a diff viewer for the actual changes, so your text should explain intent, not implementation.

**Do NOT** include any of the following in your text:
- Markdown headers (no `###`, `## `, etc.)
- Numbered or bulleted breakdowns of changes
- Line numbers or line ranges
- Echoed/quoted new content — the diff viewer shows that
- Sections like "Observations", "Impact", "Plan", or "Let me implement"

Good example: "I'll add the funeral service context to the location and update the AI-disclosure response to mention funeral arrangements."

Bad example: "### Change 1: Modify location\\nTarget lines: 44-44\\nNew content: `- Location: ...`\\n### Change 2: ..."

When you have finished all edits, stop calling tools. Any text you write after your last tool call is also shown to the user.

## Edit strategy
Match your approach to the size of the request:

- **Surgical fix** (typo, wording tweak, add a sentence): one `edit_prompt` call per fix.
- **Targeted improvement** (improve greeting, add error handling, fix a section): focused edits to the relevant section(s). Use separate `edit_prompt` calls when changes target different sections.
- **General review** ("make this better", "improve this prompt"): identify the 2–3 highest-impact issues and address those. Don't try to fix everything at once.
- **Restructure / rewrite**: apply edits section by section.

Prefer incremental improvements unless the user explicitly asks for a full rewrite.

## Quality checklist (internal guidance)
Use these dimensions to decide *what* to edit (in priority order). Do not expose this structure in your response.

1. **Clarity** — Are instructions unambiguous?
2. **Completeness** — Are edge cases, error paths, and fallback behaviors covered?
3. **Tool alignment** — Do prompt instructions match the agent's declared tools?
4. **Structure** — Logical section flow? Recommended: `<role>`, `<tool_logic>`, `<objective>`, `<goal>`, `<communicationStyle>`, `<rules>`, `<business_information>`, `<guidelines>`.
5. **Specificity** — Concrete instructions vs. vague adjectives?
6. **Consistency** — No contradictory rules?
7. **Guardrails** — Safety rules, forbidden topics, and escalation paths present?

## Using eval context
When `<eval_context>` is present, it contains results from running the agent against test scenarios. Prioritize fixes that address observed failures or regressions.

## Prompting practices
{guidelines}
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
        build_agent_config_block(agent),
    ]
    if eval_context and eval_context.strip():
        parts.append(
            f"## Eval context\n<eval_context>\n{eval_context.strip()}\n</eval_context>"
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# CREATING mode prompts (prompt is empty — interview → generate)
# ---------------------------------------------------------------------------


def build_creator_static_system_message(*, editor_guidelines: str | None) -> str:
    """System prompt for the creating mode: interview the user then generate."""
    guidelines = get_effective_guidelines(editor_guidelines)
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
{guidelines}
"""


def build_creator_dynamic_system_message(*, agent: Agent) -> str:
    """Dynamic block for creating mode: agent config only (no current prompt)."""
    return build_agent_config_block(agent)


_TOOL_RESULT_MESSAGES: dict[str, str] = {
    "edit_prompt": "Edit applied successfully.",
    "generate_prompt": "Prompt generated and saved successfully.",
}


def build_edit_tool_result(start_line: int, end_line: int, new_line_count: int) -> str:
    """Build an informative tool result for an ``edit_prompt`` call.

    Used during continuation turns so the model knows what happened and can
    reference accurate line numbers in the refreshed ``<current_prompt>``.
    """
    if start_line > end_line:
        return (
            f"Edit applied: inserted new content after line {start_line}. "
            f"The prompt now has {new_line_count} lines. "
            "Refer to <current_prompt> for updated line numbers."
        )
    if start_line == end_line:
        return (
            f"Edit applied: replaced line {start_line}. "
            f"The prompt now has {new_line_count} lines. "
            "Refer to <current_prompt> for updated line numbers."
        )
    return (
        f"Edit applied: replaced lines {start_line}-{end_line}. "
        f"The prompt now has {new_line_count} lines. "
        "Refer to <current_prompt> for updated line numbers."
    )


def build_continuation_messages(
    *,
    stream_content: str,
    tool_calls_payload: list[dict[str, Any]],
    edits: list[tuple[int, int, str]],
    new_line_count: int,
) -> list[LLMMessage]:
    """Build assistant + tool-result messages for a continuation turn.

    Returns the assistant message (with tool calls) followed by one tool-result
    ``LLMMessage`` per tool call, using informative results for ``edit_prompt``.
    """
    msgs: list[LLMMessage] = [
        LLMMessage(
            role="assistant",
            content=stream_content,
            tool_calls=tool_calls_payload,
        ),
    ]
    edit_idx = 0
    for tc_dict in tool_calls_payload:
        tid = tc_dict.get("id")
        if not tid:
            continue
        fn_info = tc_dict.get("function", {})
        fn_name = fn_info.get("name", "") if isinstance(fn_info, dict) else ""

        if fn_name == "edit_prompt" and edit_idx < len(edits):
            start_line, end_line, _ = edits[edit_idx]
            result_text = build_edit_tool_result(start_line, end_line, new_line_count)
            edit_idx += 1
        else:
            result_text = _TOOL_RESULT_MESSAGES.get(
                fn_name, "Tool executed successfully."
            )
        msgs.append(
            LLMMessage(
                role="tool",
                content=result_text,
                tool_call_id=str(tid),
                name=fn_name,
            )
        )
    return msgs


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
            editor_guidelines=agent.editor_guidelines,
        )
        dynamic = build_creator_dynamic_system_message(agent=agent)
    else:
        static = build_static_system_message(editor_guidelines=agent.editor_guidelines)
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
