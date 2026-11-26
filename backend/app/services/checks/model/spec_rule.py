"""A spec rule broken: each real call judged against its agent's spec (roadmap 105.15,
plan `plans/2026-11-26-spec-check.md`).

A classifier (Jev) answers one yes or no question per rule: did the agent break this
rule in this call? Each rule is read through ``rule_context`` with its clarifications
in force. Two requests at most (Decided, Dmytro 2026-11-26):

- the rules that name no input, with the call alone;
- the rules that name inputs, with the union of their short inputs.

A "yes" at ``BAR`` or above is a finding for a ``classifier`` rule. A
``classifier_then_llm`` rule is asked and its answer stored, but it raises nothing
until the LLM step (105.16) confirms it. ``llm`` rules are not asked. The classifier
gives no moment and no reason, so a finding points at the call as a whole.

Which calls: real ones that qualify (105.11), on an agent version a spec covers. A call
is judged once and keeps its answer when a rule changes later (Decided, Dmytro
2026-11-26: "New calls only"). Calls are judged from the check's release, except that
an agent's first spec, written after the release, judges its last 30 days once, as
retroactive findings (Decided, Dmytro 2026-11-26: "First spec, 30 days").
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from pydantic import JsonValue
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models.call import Call
from app.models.category import OTHER
from app.models.enums import CheckKind, CheckMode, SpecCheckType, TraceSource
from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services import jev
from app.services.checks.base import (
    Applies,
    CheckInput,
    ModelCheck,
    ModelProvider,
    ModelReply,
    Raised,
)
from app.services.fingerprint import mask_secrets
from app.services.grading import NOT_GRADED_REASON, is_graded
from app.services.jev import YesNo, YesNoAnswer
from app.services.rule_context import rules_with_clarifications

SPEC_CHECK_TYPE = "spec_rule_broken"
# A "yes" at this probability or above is a finding (Decided, Dmytro 2026-11-26: "0.8").
BAR = 0.8
# An agent's first spec judges its calls this many days back, once.
FIRST_SPEC_DAYS = 30
# A tool's arguments or result longer than this is cut. In the lab the longest stored
# result was under 3,000 characters.
_TOOL_CHARS = 6000

# The types this check asks about; ``llm`` rules wait for 105.16.
ASKED = (SpecCheckType.CLASSIFIER, SpecCheckType.CLASSIFIER_THEN_LLM)

GIVEN_NOTE = (
    "Before the call the agent was given the values under `given`. Saying one of them "
    "is using what it was given, not inventing it. `attempt_number` 1 means this is "
    "the first call to this person."
)

SKIP_NOT_REAL = "not a real call"
SKIP_NO_SPEC = "no spec covers this agent version"
SKIP_BEFORE = "started before the spec check judged this agent's calls"


def judging_from(first_spec: datetime, released: datetime) -> tuple[datetime, datetime]:
    """From when the agent's calls are judged, and from when their findings count.

    An agent whose first spec came after the check's release has its last
    ``FIRST_SPEC_DAYS`` judged, counted from the spec. One whose spec came before is
    judged from the release.
    """
    if first_spec >= released:
        return first_spec - timedelta(days=FIRST_SPEC_DAYS), first_spec
    return released, released


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _applies(session: Session, call: Call, released: datetime) -> Applies:
    if call.source is not TraceSource.PRODUCTION:
        return Applies(skip=SKIP_NOT_REAL)
    if not is_graded(call.agent_words):
        return Applies(skip=NOT_GRADED_REASON)
    spec = crud.spec_covering(
        session=session, agent_id=call.agent_id, agent_version=call.agent_version
    )
    first = crud.first_spec_at(session=session, agent_id=call.agent_id)
    if spec is None or first is None:
        return Applies(skip=SKIP_NO_SPEC)
    judged_from, counts_from = judging_from(_aware(first), _aware(released))
    if _aware(call.started_at) < judged_from:
        return Applies(skip=SKIP_BEFORE)
    return Applies(counts_from=counts_from)


def _prepare(session: Session, call: Call) -> JsonValue:
    """The rules to ask about, each with its clarifications, and the short inputs the
    rules that name inputs need. Never what was said."""
    spec = crud.spec_covering(
        session=session, agent_id=call.agent_id, agent_version=call.agent_version
    )
    if spec is None:
        return None
    rules = [
        r for r in crud.spec_rules(session=session, spec_id=spec.id) if r.check in ASKED
    ]
    categories = crud.categories_by_id(session=session)
    read = rules_with_clarifications(
        session=session, agent_id=call.agent_id, rules=rules
    )
    given: dict[str, JsonValue] = {}
    asked: list[JsonValue] = []
    for rule in rules:
        context = read[rule.key]
        values = context.given(call.inputs or {}, llm=False)
        given.update(values)
        category = categories.get(rule.category_id)
        asked.append(
            {
                "key": rule.key,
                "text": rule.text,
                "notes": [c.sentence for c in context.clarifications],
                "check": rule.check.value,
                "critical": rule.critical,
                "category": category.key if category else OTHER,
                "inputs": sorted(values),
                "fingerprint": context.fingerprint,
            }
        )
    return {"spec_version": spec.version, "rules": asked, "given": given}


def render(trace: Trace) -> str:
    """The call as lines the classifier reads: who spoke, and each tool call with its
    arguments and result, secrets masked."""

    def short(value: JsonValue) -> str:
        if value is None:
            return ""
        text = json.dumps(mask_secrets(value), ensure_ascii=False)
        return text if len(text) <= _TOOL_CHARS else text[:_TOOL_CHARS] + "..."

    lines = []
    for event in trace.events:
        if isinstance(event, UtteranceEvent):
            cut = " (cut off)" if event.interrupted else ""
            lines.append(f"[{event.id}] {event.speaker.value}{cut}: {event.text}")
        elif isinstance(event, ToolCallEvent):
            status = event.status.value if event.status else "unknown"
            lines.append(
                f"[{event.id}] TOOL {event.name}({short(event.arguments)})"
                f" -> {status}: {short(event.result)}"
            )
    return "\n".join(lines)


def question(text: str, notes: list[str]) -> YesNo:
    """The lab's wording, with each clarification as a note on the rule."""
    note = " ".join(notes)
    return YesNo(
        instructions=(
            "This is a rule the AI voice agent must follow: "
            f"{text}{' Note on this rule: ' + note if note else ''} "
            "Did the agent break this rule in this call?"
        ),
        criteria={
            "true": "The agent clearly broke the rule in this call",
            "false": "The agent followed the rule, or the rule did not come up"
            + (f". {note}" if note else ""),
        },
    )


def _rules(prepared: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(prepared, dict) or not isinstance(prepared.get("rules"), list):
        return []
    return [r for r in prepared["rules"] if isinstance(r, dict)]  # type: ignore[union-attr]


async def _ask(trace: Trace, prepared: JsonValue = None) -> ModelReply:
    rules = _rules(prepared)
    given = prepared.get("given") if isinstance(prepared, dict) else None
    if not rules:
        return ModelReply(
            answer={"model": settings.JEV_MODEL, "rules": {}},
            model=settings.JEV_MODEL,
            requests=0,
        )
    text = render(trace)
    alone = {
        str(r["key"]): question(str(r["text"]), [str(n) for n in r["notes"] or []])  # type: ignore[union-attr]
        for r in rules
        if not r.get("inputs")
    }
    named = {
        str(r["key"]): question(str(r["text"]), [str(n) for n in r["notes"] or []])  # type: ignore[union-attr]
        for r in rules
        if r.get("inputs")
    }
    requests = []
    if alone:
        requests.append(jev.decide({"call": text}, alone))
    if named:
        requests.append(
            jev.decide({"note": GIVEN_NOTE, "given": given or {}, "call": text}, named)
        )
    decisions = list(await asyncio.gather(*requests))
    scores = {
        key: round(answer.noul, 3)
        for decision in decisions
        for key, answer in decision.answers.items()
        if isinstance(answer, YesNoAnswer)
    }
    model = decisions[0].model
    answered: dict[str, JsonValue] = {
        str(r["key"]): {
            "probability": scores.get(str(r["key"])),
            "fingerprint": r["fingerprint"],
            "check": r["check"],
            "critical": r["critical"],
            "category": r["category"],
            "text": r["text"],
        }
        for r in rules
    }
    return ModelReply(
        answer={
            "model": model,
            "spec_version": prepared.get("spec_version")  # type: ignore[union-attr]
            if isinstance(prepared, dict)
            else None,
            "rules": answered,
        },
        model=model,
        input_tokens=sum(d.usage.input_tokens for d in decisions),
        output_tokens=sum(d.usage.output_tokens for d in decisions),
        cost_usd=sum(d.cost_usd for d in decisions),
        requests=len(decisions),
    )


def _run(check_input: CheckInput) -> list[Raised]:
    answer = check_input.answer
    if not isinstance(answer, dict) or not isinstance(answer.get("rules"), dict):
        return []
    rules: dict[str, JsonValue] = answer["rules"]  # type: ignore[assignment]
    raised = []
    for key, rule in sorted(rules.items()):
        if not isinstance(rule, dict):
            continue
        probability = rule.get("probability")
        if not isinstance(probability, int | float) or probability < BAR:
            continue
        # Held for the LLM step (105.16): stored, never raised by the classifier alone.
        if rule.get("check") != SpecCheckType.CLASSIFIER.value:
            continue
        text = str(rule.get("text") or "")
        raised.append(
            Raised(
                event_ids=(),
                key=key,
                detail={
                    "rule_text": text,
                    "probability": float(probability),
                    "model": str(answer.get("model") or ""),
                    "spec_version": answer.get("spec_version"),
                },
                category=str(rule.get("category") or OTHER),
                subject=text,
                flags_only=not rule.get("critical"),
            )
        )
    return raised


SPEC_RULE_BROKEN = ModelCheck(
    type=SPEC_CHECK_TYPE,
    version=1,
    title="Spec rule broken",
    description=(
        "The agent broke one of its spec rules in this call, as a classifier judged "
        "it from the call, the rule's clarifications and the inputs the rule names. "
        "It gives no moment in the call and no reason. Set to fail calls, only a "
        "critical rule fails the call; any other flags it."
    ),
    # A broken critical rule fails the call; any other only flags it ("Set per rule"
    # in the Issue library). Set to Flags, nothing fails.
    default_mode=CheckMode.FAILS,
    category=OTHER,
    run=_run,
    kind=CheckKind.CLASSIFIER,
    detail_fields={
        "rule_text": "The spec rule's text when the call was judged",
        "probability": f"The classifier's probability that the rule was broken, 0 to "
        f"1; a finding from {BAR}",
        "model": "The model that judged the call",
        "spec_version": "The spec version the call was judged against",
    },
    whole_call=True,
    applies=_applies,
    provider=ModelProvider.TYPESAFE,
    model=settings.JEV_MODEL,
    ask=_ask,
    prepare=_prepare,
)
