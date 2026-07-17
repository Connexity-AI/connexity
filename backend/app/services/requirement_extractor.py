"""Extract atomic, testable requirements from an agent's behavioral source.

Requirements are the normalized contract that test-case generation consumes,
regardless of whether the underlying agent is a single-prompt agent (Retell
``retell-llm``, Vapi, ElevenLabs) or a Retell conversation flow. A single prompt
and a flow graph look nothing alike as text, but both reduce to "the agent must
do X, Y, Z" — that list is what this service produces.

The result is an immutable snapshot persisted per agent version; this module only
performs the LLM extraction and returns drafts. Persistence lives in
``app.crud.requirement``.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.llm import LLMCallConfig, LLMMessage, call_llm

logger = logging.getLogger(__name__)

_MAX_REQUIREMENTS = 60

_CATEGORIES = ("capability", "guardrail", "routing", "tool-use", "persona", "other")

_SYSTEM_PROMPT = """\
You extract requirements from the configuration of an AI agent so they can be
used to generate evaluation test cases.

A requirement is a single, atomic, testable statement of something the agent
MUST (or MUST NOT) do. Write each as an imperative assertion a judge could check
against a conversation transcript.

RULES:
- One behavior per requirement. Split compound instructions into separate items.
- Be specific and grounded in the provided source. Do not invent behaviors that
  are not implied by the source.
- Cover: capabilities the agent offers, guardrails/constraints, conversational
  routing (when to move between topics/steps/nodes), tool usage, and required
  persona/tone behaviors.
- For conversation flows, treat each node's instruction as one or more
  requirements, and treat edges/transitions as routing requirements
  ("When <condition>, the agent must <do/route to> ...").
- Assign each requirement a "category" from: capability, guardrail, routing,
  tool-use, persona, other.
- When the source labels a section or names a node, put that label/name in
  "source_ref" so the requirement can be traced back; otherwise use null.

OUTPUT FORMAT:
Return ONLY a JSON object with a "requirements" array. No markdown, no prose.
Each item: {"text": str, "category": str, "source_ref": str | null}.\
"""


@dataclass(frozen=True)
class RequirementSource:
    """Normalized input describing an agent's behavior for extraction."""

    agent_name: str | None = None
    system_prompt: str | None = None
    tools: list[dict[str, Any]] | None = None
    # Conversation-flow shape (all optional; only set for flow agents)
    global_prompt: str | None = None
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (
            (self.system_prompt or "").strip()
            or (self.global_prompt or "").strip()
            or self.nodes
        )


class RequirementDraft(BaseModel):
    text: str
    category: str | None = None
    source_ref: str | None = None


class _ExtractionResult(BaseModel):
    requirements: list[RequirementDraft]


def _response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "agent_requirements",
            "strict": False,
            "schema": {
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "category": {
                                    "type": "string",
                                    "enum": list(_CATEGORIES),
                                },
                                "source_ref": {"type": ["string", "null"]},
                            },
                            "required": ["text"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["requirements"],
                "additionalProperties": False,
            },
        },
    }


def _node_instruction_text(node: dict[str, Any]) -> str | None:
    instruction = node.get("instruction")
    if isinstance(instruction, dict):
        text = instruction.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    if isinstance(instruction, str) and instruction.strip():
        return instruction.strip()
    return None


def _build_user_prompt(source: RequirementSource) -> str:
    parts: list[str] = []
    if source.agent_name:
        parts.append(f"AGENT NAME: {source.agent_name}")

    if (source.system_prompt or "").strip():
        parts.append("AGENT SYSTEM PROMPT:\n" + source.system_prompt.strip())  # type: ignore[union-attr]

    if (source.global_prompt or "").strip():
        parts.append(
            "CONVERSATION FLOW GLOBAL PROMPT:\n" + source.global_prompt.strip()  # type: ignore[union-attr]
        )

    if source.nodes:
        node_lines: list[str] = []
        for node in source.nodes:
            instruction = _node_instruction_text(node)
            if instruction is None:
                continue
            node_id = node.get("id") or node.get("node_id") or ""
            node_name = node.get("name") or ""
            node_type = node.get("type") or ""
            label = node_name or node_id or node_type or "node"
            header = f"- [{node_type}] {label}".rstrip()
            node_lines.append(f"{header}: {instruction}")
        if node_lines:
            parts.append("CONVERSATION FLOW NODES:\n" + "\n".join(node_lines))

    if source.edges:
        edge_lines: list[str] = []
        for edge in source.edges:
            condition = edge.get("transition_condition") or edge.get("condition")
            destination = (
                edge.get("destination_node_id")
                or edge.get("to")
                or edge.get("target")
                or ""
            )
            if isinstance(condition, dict):
                condition = condition.get("prompt") or condition.get("equation") or ""
            if not condition and not destination:
                continue
            edge_lines.append(f"- When {condition!r}, go to {destination}".rstrip())
        if edge_lines:
            parts.append("CONVERSATION FLOW TRANSITIONS:\n" + "\n".join(edge_lines))

    if source.tools:
        tool_lines: list[str] = []
        for tool in source.tools:
            fn = tool.get("function") if isinstance(tool, dict) else None
            name = ""
            description = ""
            if isinstance(fn, dict):
                name = str(fn.get("name") or "")
                description = str(fn.get("description") or "")
            else:
                name = str(tool.get("name") or "") if isinstance(tool, dict) else ""
                description = (
                    str(tool.get("description") or "") if isinstance(tool, dict) else ""
                )
            if name:
                tool_lines.append(f"- {name}: {description}".rstrip())
        if tool_lines:
            parts.append("AGENT TOOLS:\n" + "\n".join(tool_lines))

    parts.append(
        "Extract the requirements as instructed. Return at most "
        f"{_MAX_REQUIREMENTS} of the most important, non-overlapping requirements."
    )
    return "\n\n".join(parts)


def _parse_requirements(raw: str) -> list[RequirementDraft]:
    data = json.loads(raw)
    result = _ExtractionResult.model_validate(data)
    out: list[RequirementDraft] = []
    seen: set[str] = set()
    for item in result.requirements:
        text = item.text.strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        category = item.category
        if category is not None and category not in _CATEGORIES:
            category = "other"
        out.append(
            RequirementDraft(
                text=text,
                category=category,
                source_ref=(item.source_ref or None),
            )
        )
        if len(out) >= _MAX_REQUIREMENTS:
            break
    return out


class RequirementExtractionError(Exception):
    """Raised when extraction could not complete (LLM call or parse failed).

    Distinct from a successful extraction that simply yielded no requirements
    (which returns an empty list). Callers use this to mark a version's
    requirements_status as ``failed`` rather than ``empty``.
    """


async def extract_requirements(
    *, source: RequirementSource, model: str | None = None
) -> list[RequirementDraft]:
    """Extract atomic requirements from an agent's behavioral source.

    Returns an empty list when the source has no behavioral content or the LLM
    legitimately found nothing to extract. Raises
    :class:`RequirementExtractionError` when the LLM call or response parsing
    fails, so callers can distinguish a failure from a genuinely empty result.
    """
    if source.is_empty:
        return []

    llm_config = LLMCallConfig(
        model=model or settings.default_llm_id,
        max_tokens=settings.GENERATOR_MAX_TOKENS,
        temperature=0.2,
        response_format=_response_format(),
    )

    try:
        response = await call_llm(
            messages=[
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=_build_user_prompt(source)),
            ],
            config=llm_config,
        )
    except Exception as exc:
        logger.exception("Requirement extraction LLM call failed")
        raise RequirementExtractionError(str(exc)) from exc

    try:
        return _parse_requirements(response.content or "")
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.warning("Requirement extraction parse failed: %s", exc)
        raise RequirementExtractionError(str(exc)) from exc
