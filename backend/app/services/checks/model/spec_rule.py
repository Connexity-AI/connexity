"""A spec rule broken: each real call judged against its agent's spec (roadmap 105.15
and 105.16, plans `plans/2026-11-26-spec-check.md` and `plans/2026-11-27-llm-step.md`).

A classifier (Jev) answers one yes or no question per rule: did the agent break this
rule in this call? Each rule is read through ``rule_context`` with its clarifications
in force. Two requests at most (Decided, Dmytro 2026-11-26):

- the rules that name no input, with the call alone;
- the rules that name inputs, with the union of their short inputs.

A "yes" at ``BAR`` or above is a finding for a ``classifier`` rule. The classifier
gives no moment and no reason, so such a finding points at the call as a whole.

Then the LLM step (105.16), one rule per request (Decided, Dmytro 2026-11-27):

- each ``classifier_then_llm`` rule the classifier scored at ``BAR`` or above, which the
  LLM confirms or dismisses;
- each ``llm`` rule, which only the LLM judges.

A request holds the call, the inputs the rule names (long ones too) and the one rule
with its clarifications. Never the agent's prompt, another rule or the classifier's
score (Decided, Dmytro 2026-11-27). A broken verdict is a finding with the moment the
reason rests on and the reason; a dismissed flag is stored and raises nothing.

Which calls: real ones that qualify (105.11), on an agent version a spec covers. A call
is judged once and keeps its answer when a rule changes later (Decided, Dmytro
2026-11-26: "New calls only"). Calls are judged from the check's release, except that
an agent's first spec, written after the release, judges its last 30 days once, as
retroactive findings (Decided, Dmytro 2026-11-26: "First spec, 30 days"). A later
version reads the answer an earlier one stored (``answers_carry_over``): a call version
1 judged is never asked about again.
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
from app.models.enums import (
    CheckKind,
    CheckMode,
    RuleOutcome,
    SpecCheckType,
    TraceSource,
)
from app.models.trace import ToolCallEvent, Trace, UtteranceEvent
from app.services import jev
from app.services.checks.base import (
    Applies,
    AskFailed,
    CheckInput,
    ModelCheck,
    ModelProvider,
    ModelReply,
    Raised,
)
from app.services.checks.judge import ask_judge
from app.services.checks.providers import missing_key
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

# The types the classifier asks about; ``llm`` rules go to the LLM step alone.
ASKED = (SpecCheckType.CLASSIFIER, SpecCheckType.CLASSIFIER_THEN_LLM)
# Enough for a reason of a sentence or two and a few line ids.
_LLM_MAX_TOKENS = 1000
# A call's LLM requests asked at once, and how long they may take together. Inside
# the scheduled pull's minute, so a slow provider is a failed attempt, counted.
_LLM_REQUESTS_AT_ONCE = 4
_LLM_SECONDS = 30.0

LLM_SYSTEM = """\
You judge one real phone call between a caller and an AI voice agent against one rule
the agent must follow. Judge only the agent.

Answer exactly one verdict:
- "failed": the call reached what the rule is about, and the agent broke the rule.
- "passed": the call reached what the rule is about, and the agent followed it.
- "did_not_come_up": the call never reached what the rule is about.

The rule may come with notes from the people who own the agent. A note says where the
rule's boundary lies; judge the rule as its notes explain it. The rule may come with
inputs: values the agent was given before the call. Saying one of them is using what it
was given, not inventing it; "not set" means the agent had no value.

Each line of the call starts with its id in brackets. A TOOL line shows the tool's
arguments, its status and its result: read them before saying whether a tool was
called or what it returned.

First write the reason in one or two plain sentences, then the ids of the lines it
rests on (none for did_not_come_up), and only then the verdict that follows from the
reason. Say what happened in your own words: never repeat a name, phone number, email
or address from the call.
"""

_VERDICT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        # The reason before the verdict, so the verdict follows from it (the test-run
        # judge saw a verdict given first contradicted by its reason in 4 of 14).
        "reason": {"type": "string"},
        "event_ids": {"type": "array", "items": {"type": "string"}},
        "outcome": {"type": "string", "enum": [o.value for o in RuleOutcome]},
    },
    "required": ["reason", "event_ids", "outcome"],
    "additionalProperties": False,
}

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
    rules = crud.spec_rules(session=session, spec_id=spec.id)
    categories = crud.categories_by_id(session=session)
    read = rules_with_clarifications(
        session=session, agent_id=call.agent_id, rules=rules
    )
    given: dict[str, JsonValue] = {}
    asked: list[JsonValue] = []
    for rule in rules:
        context = read[rule.key]
        values = context.given(call.inputs or {}, llm=False)
        if rule.check in ASKED:
            given.update(values)
        category = categories.get(rule.category_id)
        llm_given: dict[str, JsonValue] = dict(
            context.given(call.inputs or {}, llm=True)
        )
        entry: dict[str, JsonValue] = {
            "key": rule.key,
            "text": rule.text,
            "notes": list[JsonValue](c.sentence for c in context.clarifications),
            "check": rule.check.value,
            "critical": rule.critical,
            "category": category.key if category else OTHER,
            "inputs": list[JsonValue](sorted(values)),
            # Every input the rule names, long ones too: only for the LLM step.
            "llm_given": llm_given,
            "fingerprint": context.fingerprint,
        }
        asked.append(entry)
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


def _notes(rule: dict[str, JsonValue]) -> list[str]:
    notes = rule.get("notes")
    return [str(n) for n in notes] if isinstance(notes, list) else []


def llm_request(call_text: str, rule: dict[str, JsonValue]) -> str:
    """What one LLM request says: the call first, so a call's requests start the
    same way, then the inputs the rule names, then the rule."""
    given = rule.get("llm_given")
    inputs = (
        "".join(f"\n- {name}: {value}" for name, value in sorted(given.items()))
        if isinstance(given, dict) and given
        else ""
    )
    notes = "".join(f"\nNote on this rule: {note}" for note in _notes(rule))
    return (
        f"## The call\n\n{call_text}\n\n"
        f"## Inputs the agent was given\n{inputs or chr(10) + '(none)'}\n\n"
        f"## The rule\n\n{rule.get('text')}{notes}\n"
    )


def _verdict(answer: JsonValue, model: str) -> dict[str, JsonValue]:
    """The LLM's answer as stored, or a ValueError when it is not of the shape asked
    for (the call's answer then fails and is tried again)."""
    if not isinstance(answer, dict):
        msg = "The LLM step's answer is not an object"
        raise ValueError(msg)
    outcome = RuleOutcome(answer.get("outcome"))
    ids = answer.get("event_ids")
    return {
        "outcome": outcome.value,
        "reason": str(answer.get("reason") or "").strip(),
        "event_ids": [str(i) for i in ids] if isinstance(ids, list) else [],
        "model": model,
    }


def _to_llm(rule: dict[str, JsonValue], probability: float | None) -> bool:
    """Whether the LLM step judges this rule on this call."""
    if rule.get("check") == SpecCheckType.LLM.value:
        return True
    return (
        rule.get("check") == SpecCheckType.CLASSIFIER_THEN_LLM.value
        and probability is not None
        and probability >= BAR
    )


async def _ask(trace: Trace, prepared: JsonValue = None) -> ModelReply:
    rules = _rules(prepared)
    given = prepared.get("given") if isinstance(prepared, dict) else None
    spec_version = prepared.get("spec_version") if isinstance(prepared, dict) else None
    text = render(trace)
    asked = [r for r in rules if r.get("check") in {t.value for t in ASKED}]
    alone: dict[str, jev.Question] = {
        str(r["key"]): question(str(r["text"]), _notes(r))
        for r in asked
        if not r.get("inputs")
    }
    named: dict[str, jev.Question] = {
        str(r["key"]): question(str(r["text"]), _notes(r))
        for r in asked
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

    llm_model = settings.SPEC_LLM_MODEL
    provider = ModelProvider(settings.SPEC_LLM_PROVIDER)
    to_llm = [r for r in rules if _to_llm(r, scores.get(str(r["key"])))]
    no_key = missing_key(provider) if to_llm else None
    replies: list[ModelReply] = []
    verdicts: dict[str, JsonValue] = {}
    if to_llm and no_key is None:
        limiter = asyncio.Semaphore(_LLM_REQUESTS_AT_ONCE)

        async def judge(rule: dict[str, JsonValue]) -> ModelReply:
            async with limiter:
                return await ask_judge(
                    provider=provider,
                    model=llm_model,
                    system=LLM_SYSTEM,
                    user=llm_request(text, rule),
                    schema_name="spec_rule_verdict",
                    schema=_VERDICT_SCHEMA,
                    max_tokens=_LLM_MAX_TOKENS,
                )

        classifier_cost = sum(d.cost_usd for d in decisions)
        try:
            # Within a bound of its own: a slow provider fails as an attempt that is
            # counted, never as the pass running out of time.
            done = await asyncio.wait_for(
                asyncio.gather(*(judge(r) for r in to_llm), return_exceptions=True),
                timeout=_LLM_SECONDS,
            )
        except TimeoutError as exc:
            msg = f"The LLM step took over {_LLM_SECONDS:.0f} s"
            raise AskFailed(msg, cost_usd=classifier_cost) from exc
        replies = [r for r in done if isinstance(r, ModelReply)]
        spent = classifier_cost + sum(r.cost_usd for r in replies)
        failed = next((r for r in done if isinstance(r, BaseException)), None)
        if failed is not None:
            msg = f"An LLM step request failed: {type(failed).__name__}"
            raise AskFailed(msg, cost_usd=spent) from failed
        try:
            verdicts = {
                str(rule["key"]): _verdict(reply.answer, reply.model)
                for rule, reply in zip(to_llm, replies, strict=True)
            }
        except ValueError as exc:
            raise AskFailed(str(exc), cost_usd=spent) from exc

    answered: dict[str, JsonValue] = {
        str(r["key"]): {
            "probability": scores.get(str(r["key"])),
            "verdict": verdicts.get(str(r["key"])),
            "fingerprint": r["fingerprint"],
            "check": r["check"],
            "critical": r["critical"],
            "category": r["category"],
            "text": r["text"],
        }
        for r in rules
    }
    model = decisions[0].model if decisions else llm_model
    answer: dict[str, JsonValue] = {
        "model": model,
        "llm_model": llm_model if to_llm else None,
        "spec_version": spec_version,
        "rules": answered,
    }
    if no_key is not None:
        # Without the key the classifier part still counts; these rules wait.
        answer["llm_missing"] = no_key
    return ModelReply(
        answer=answer,
        model=model,
        input_tokens=sum(d.usage.input_tokens for d in decisions)
        + sum(r.input_tokens for r in replies),
        output_tokens=sum(d.usage.output_tokens for d in decisions)
        + sum(r.output_tokens for r in replies),
        cost_usd=sum(d.cost_usd for d in decisions) + sum(r.cost_usd for r in replies),
        requests=len(decisions) + len(replies),
    )


def _moment(verdict: dict[str, JsonValue], trace: Trace) -> tuple[str, ...]:
    """The verdict's line ids that are in the call, in the call's order. None left:
    the finding is on the whole call."""
    named = verdict.get("event_ids")
    wanted = {str(i) for i in named} if isinstance(named, list) else set()
    return tuple(event.id for event in trace.events if event.id in wanted)


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
        score = float(probability) if isinstance(probability, int | float) else None
        verdict = rule.get("verdict")
        check = rule.get("check")
        text = str(rule.get("text") or "")
        detail: dict[str, JsonValue] = {
            "rule_text": text,
            "spec_version": answer.get("spec_version"),
        }
        event_ids: tuple[str, ...] = ()
        kind = None
        if check == SpecCheckType.CLASSIFIER.value:
            if score is None or score < BAR:
                continue
            detail |= {"probability": score, "model": str(answer.get("model") or "")}
        elif isinstance(verdict, dict):
            # Confirmed or judged by the LLM step; a flag it dismissed raises nothing.
            if verdict.get("outcome") != RuleOutcome.FAILED.value:
                continue
            event_ids = _moment(verdict, check_input.trace)
            detail["reason"] = str(verdict.get("reason") or "")
            if check == SpecCheckType.CLASSIFIER_THEN_LLM.value and score is not None:
                detail |= {
                    "probability": score,
                    "model": str(answer.get("model") or ""),
                    "confirmed_by": str(verdict.get("model") or ""),
                }
            else:
                detail["model"] = str(verdict.get("model") or "")
                kind = CheckKind.JUDGE
        else:
            # A flag not yet confirmed (no LLM key, or judged by version 1): held.
            continue
        raised.append(
            Raised(
                event_ids=event_ids,
                key=key,
                detail=detail,
                category=str(rule.get("category") or OTHER),
                subject=text,
                flags_only=not rule.get("critical"),
                kind=kind,
            )
        )
    return raised


SPEC_RULE_BROKEN = ModelCheck(
    type=SPEC_CHECK_TYPE,
    # 2: the LLM step (105.16). Calls version 1 judged keep its answer.
    version=2,
    title="Spec rule broken",
    description=(
        "The agent broke one of its spec rules in this call. A classifier judges "
        "each rule from the call, the rule's clarifications and the inputs it names, "
        "with no moment or reason. For rules that need it, an LLM confirms the "
        "classifier's flag, or judges the rule alone, and gives the moment and the "
        "reason. Set to fail calls, only a critical rule fails the call; any other "
        "flags it."
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
        f"1; a finding from {BAR}. None for a rule only the LLM judges",
        "model": "The model that found it: the classifier, or the LLM for a rule only "
        "the LLM judges",
        "confirmed_by": "The LLM that confirmed the classifier's flag, when one did",
        "reason": "Why the rule was broken, in the LLM's words; none from the "
        "classifier alone",
        "spec_version": "The spec version the call was judged against",
    },
    whole_call=True,
    applies=_applies,
    provider=ModelProvider.TYPESAFE,
    model=settings.JEV_MODEL,
    ask=_ask,
    prepare=_prepare,
    answers_carry_over=True,
)
