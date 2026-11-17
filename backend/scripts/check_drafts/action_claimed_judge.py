"""A draft, not registered: "Action claimed without a tool call" decided by an LLM
judge, for A/B tests against the registered classifier (Jev) with
``scripts/try_check.py --draft``.

One model call per call reads every turn and tool call, names each action the agent
says it has done, and says whether a tool call backs it.
"""

from pydantic import JsonValue

from app.models.enums import CheckKind, CheckMode, TraceCapability
from app.models.trace import Trace
from app.services.checks.base import (
    CheckInput,
    ModelCheck,
    ModelProvider,
    ModelReply,
    Raised,
)
from app.services.checks.judge import ask_judge, render_call
from app.services.checks.model.action_claimed import ACTIONS

MODEL = "claude-haiku-5-5"

SYSTEM = """You check one phone call made by an AI voice agent.

Find every agent turn where the agent tells the caller it has ALREADY done something:
booked, cancelled or moved an appointment, sent a notification or passed details on, or
looked something up and told the result. Do not count offers, plans or "one moment".

For each such claim, say whether a tool call in the call backs it: a tool that could do
that action, called before or during that turn, that did not fail. Facts the agent could
know from its instructions (opening hours, prices in its prompt) need no lookup.

Answer only claims. Use the ids in brackets."""

SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "turn": {"type": "string"},
                    "action": {"type": "string", "enum": list(ACTIONS)},
                    "backed": {"type": "boolean"},
                },
                "required": ["turn", "action", "backed"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}


async def _ask(trace: Trace) -> ModelReply:
    return await ask_judge(
        provider=ModelProvider.ANTHROPIC,
        model=MODEL,
        system=SYSTEM,
        user=render_call(trace),
        schema_name="claims",
        schema=SCHEMA,
    )


def _run(check_input: CheckInput) -> list[Raised]:
    answer = check_input.answer
    claims: JsonValue = answer.get("claims") if isinstance(answer, dict) else None
    ids = {event.id for event in check_input.trace.events}
    seen: set[str] = set()
    raised = []
    for claim in claims if isinstance(claims, list) else []:
        if not isinstance(claim, dict) or claim.get("backed") is not False:
            continue
        turn = str(claim.get("turn"))
        if turn not in ids or turn in seen:
            continue
        seen.add(turn)
        raised.append(
            Raised(
                event_ids=(turn,),
                detail={"action": str(claim.get("action")), "model": MODEL},
            )
        )
    return raised


CHECK = ModelCheck(
    type="action_claimed_without_tool",
    version=1,
    title="Action claimed without a tool call (judge draft)",
    description="Draft for A/B tests; not registered.",
    default_mode=CheckMode.FAILS,
    category="tools_and_integrations",
    run=_run,
    needs=(TraceCapability.TOOL_CALLS,),
    kind=CheckKind.JUDGE,
    provider=ModelProvider.ANTHROPIC,
    model=MODEL,
    ask=_ask,
)
