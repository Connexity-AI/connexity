"""The agent told the caller it did something, with no tool call that did it.

A classifier (Jev) labels each agent turn with what it says is already done: booked,
cancelled or moved an appointment, sent a notification, looked something up and gave
the result, or nothing. Code then looks for a tool call that could do it, earlier in
the call or during that turn, that did not fail. A claim with none is a finding on
that turn; a claim whose only matching tool calls failed points at them too.

Which tools can back a claim is read from their names, as the booking checks do, so a
tool whose name says nothing about what it does backs nothing.
"""

import asyncio
import re

from pydantic import JsonValue

from app.core.config import settings
from app.models.enums import (
    CheckKind,
    CheckMode,
    Speaker,
    ToolCallStatus,
    TraceCapability,
)
from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services import jev
from app.services.checks.base import (
    CheckInput,
    ModelCheck,
    ModelProvider,
    ModelReply,
    Raised,
)
from app.services.jev import Choice, ChoiceAnswer

# A turn counts as a claim when Jev gives its label at least this probability.
THRESHOLD = 0.5
# Jev requests in flight for one call.
_CONCURRENCY = 8

ACTIONS = ("booked", "cancelled", "moved", "notified", "looked_up")

QUESTION = Choice(
    instructions=(
        "Read the agent's turn. What does the agent tell the caller it has already "
        "done, in this turn? Only count something the agent says is done, not "
        "something it is about to do or offers to do."
    ),
    criteria={
        "none": "The agent does not say it has done anything",
        "booked": "Says it booked or scheduled an appointment",
        "cancelled": "Says it cancelled an appointment or booking",
        "moved": "Says it moved, rescheduled or changed an appointment",
        "notified": "Says it sent a message or notification, or passed details on",
        "looked_up": "Says it checked or looked something up and tells the result",
    },
)

_BACKS = {
    "booked": re.compile(r"book|schedul|appointment|reserv", re.I),
    "cancelled": re.compile(r"cancel", re.I),
    "moved": re.compile(r"reschedul|move|update|change", re.I),
    "notified": re.compile(r"notif|message|sms|email|send|transfer|ticket", re.I),
    "looked_up": re.compile(
        r"availab|slot|get_|list|find|check|search|lookup|fetch", re.I
    ),
}
# A booking tool's name does not say it only looks or changes one.
_NOT_BOOKING = re.compile(
    r"availab|slot|get_|list|find|check|search|cancel|reschedul", re.I
)
# "No result" is its own issue type and fire-and-forget tools often return nothing, so
# it does not count as failed here.
_FAILED = (ToolCallStatus.ERROR, ToolCallStatus.TIMEOUT)


def can_back(action: str, tool_name: str) -> bool:
    if action == "booked" and _NOT_BOOKING.search(tool_name):
        return False
    return bool(_BACKS[action].search(tool_name))


def _agent_turns(trace: Trace) -> list[tuple[UtteranceEvent, str]]:
    """Each agent turn with what the caller said just before it."""
    turns = []
    previous_caller = ""
    for event in trace.events:
        if not isinstance(event, UtteranceEvent):
            continue
        if event.speaker is Speaker.AGENT:
            turns.append((event, previous_caller))
        elif event.speaker is Speaker.CALLER:
            previous_caller = event.text
    return turns


async def _ask(trace: Trace) -> ModelReply:
    turns = _agent_turns(trace)
    if not turns:
        return ModelReply(
            answer={"model": settings.JEV_MODEL, "turns": 0, "claims": {}},
            model=settings.JEV_MODEL,
            requests=0,
        )
    limiter = asyncio.Semaphore(_CONCURRENCY)

    async def label(turn: UtteranceEvent, previous_caller: str) -> jev.Decision:
        async with limiter:
            return await jev.decide(
                {"previous_caller_turn": previous_caller, "agent_turn": turn.text},
                {"claim": QUESTION},
            )

    decisions = await asyncio.gather(*(label(turn, caller) for turn, caller in turns))
    claims: dict[str, JsonValue] = {}
    for (turn, _), decision in zip(turns, decisions, strict=True):
        answer = decision.answers["claim"]
        if not isinstance(answer, ChoiceAnswer) or answer.choice == "none":
            continue
        claims[turn.id] = {
            "action": answer.choice,
            "probability": round(answer.probabilities.get(answer.choice, 0.0), 3),
        }
    model = decisions[0].model
    return ModelReply(
        answer={"model": model, "turns": len(turns), "claims": claims},
        model=model,
        input_tokens=sum(d.usage.input_tokens for d in decisions),
        output_tokens=sum(d.usage.output_tokens for d in decisions),
        cost_usd=sum(d.cost_usd for d in decisions),
        requests=len(decisions),
    )


def _run(check_input: CheckInput) -> list[Raised]:
    answer = check_input.answer
    if not isinstance(answer, dict):
        return []
    claims = answer.get("claims")
    if not isinstance(claims, dict):
        return []
    events = check_input.trace.events
    position = {event.id: index for index, event in enumerate(events)}
    raised = []
    for event_id, claim in claims.items():
        if event_id not in position or not isinstance(claim, dict):
            continue
        action = claim.get("action")
        probability = claim.get("probability")
        if action not in ACTIONS or not isinstance(probability, int | float):
            continue
        if probability < THRESHOLD:
            continue
        turn = events[position[event_id]]
        # An answer from before the trace was stored again may name another event.
        if not isinstance(turn, UtteranceEvent):
            continue
        tools = [
            event
            for index, event in enumerate(events)
            if isinstance(event, ToolCallEvent)
            and can_back(str(action), event.name)
            and (
                index < position[event_id]
                or (
                    event.start_ms is not None
                    and turn.end_ms is not None
                    and event.start_ms <= turn.end_ms
                )
            )
        ]
        if any(tool.status not in _FAILED for tool in tools):
            continue
        raised.append(
            Raised(
                event_ids=(event_id, *(tool.id for tool in tools)),
                detail={
                    "action": str(action),
                    "probability": float(probability),
                    "why": "tool_failed" if tools else "no_tool_call",
                    "model": str(answer.get("model") or ""),
                },
            )
        )
    return raised


ACTION_CLAIMED_WITHOUT_TOOL = ModelCheck(
    type="action_claimed_without_tool",
    version=1,
    title="Action claimed without a tool call",
    description=(
        "The agent told the caller it did something (booked, cancelled or moved an "
        "appointment, sent a notification, or looked something up) with no tool call "
        "that did it, or after that tool call failed."
    ),
    # Critical, from the Issue library; the kind of check does not change severity.
    default_mode=CheckMode.FAILS,
    category="tools_and_integrations",
    run=_run,
    needs=(TraceCapability.TOOL_CALLS,),
    kind=CheckKind.CLASSIFIER,
    provider=ModelProvider.TYPESAFE,
    model=settings.JEV_MODEL,
    ask=_ask,
)
