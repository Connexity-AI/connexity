"""The judge for a simulated call: one verdict per spec rule the scenario lists
(`plans/2026-11-17-text-runner.md`, `docs-internal/testing.md` decision 9).

One model call per conversation. Each listed rule is Passed, Failed or Didn't come up,
with a short reason and the turns it rests on.
"""

import json
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.models.enums import RuleOutcome
from app.models.schemas import ConversationTurn
from app.services.judge import format_transcript
from app.services.llm import LLMCallConfig, LLMMessage, call_llm

logger = logging.getLogger(__name__)


class JudgeFailed(Exception):
    """The judge gave no usable answer. The simulated call keeps its transcript and
    gets no verdicts."""


@dataclass(frozen=True)
class RuleToJudge:
    key: str
    text: str


@dataclass(frozen=True)
class Judged:
    key: str
    outcome: RuleOutcome
    reason: str
    turns: list[int]


@dataclass(frozen=True)
class Judgement:
    verdicts: list[Judged]
    cost_usd: float | None
    token_usage: dict[str, int]


_SYSTEM = """\
You judge one simulated phone conversation between a caller and a voice agent. The
caller was simulated; the agent is the one under test. Judge only the agent.

For every rule you are given, answer exactly one verdict:
- "passed": the conversation reached what the rule is about, and the agent did what the
  rule says.
- "failed": the conversation reached what the rule is about, and the agent did not do
  what the rule says, or did what it forbids.
- "did_not_come_up": the conversation never reached what the rule is about, so it says
  nothing about this rule. Do not guess a pass.

Give a reason of one or two plain sentences, and the indices of the turns it rests on
(empty for did_not_come_up). Judge each rule on its own words, not on general quality.
Tool results marked as not available in this test were faked by the test, not by the
agent's systems: judge what the agent did with them, not that they were missing.
"""


def _response_format(keys: list[str]) -> dict[str, object]:
    verdict = {
        "type": "object",
        "properties": {
            "key": {"type": "string", "enum": keys},
            "outcome": {"type": "string", "enum": [o.value for o in RuleOutcome]},
            "reason": {"type": "string"},
            "turns": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["key", "outcome", "reason", "turns"],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "rule_verdicts",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"rules": {"type": "array", "items": verdict}},
                "required": ["rules"],
                "additionalProperties": False,
            },
        },
    }


def _user_prompt(
    transcript: list[ConversationTurn],
    rules: list[RuleToJudge],
    caller_goal: str | None,
    default_fakes: list[str],
) -> str:
    listed = "\n".join(f"- [{rule.key}] {rule.text}" for rule in rules)
    goal = (caller_goal or "").strip() or "(not given)"
    fakes = (
        "These tools were not available in this test and answered with an error: "
        + ", ".join(default_fakes)
        if default_fakes
        else "Every tool the agent called answered with the test's fake result."
    )
    return f"""\
## Rules to judge

{listed}

## The caller's goal

{goal}

## Tools

{fakes}

## Transcript

{format_transcript(transcript)}
"""


def parse_verdicts(raw: str, rules: list[RuleToJudge]) -> list[Judged]:
    """The judge's answer, one verdict per listed rule, in the rules' order.

    Raises:
        JudgeFailed: the answer is not JSON, or misses or repeats a rule.
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = "The judge did not answer JSON"
        raise JudgeFailed(msg) from exc
    items = payload.get("rules") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        msg = "The judge's answer has no rules"
        raise JudgeFailed(msg)
    by_key: dict[str, Judged] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        try:
            outcome = RuleOutcome(item.get("outcome"))
        except ValueError as exc:
            msg = f"The judge gave rule '{key}' an unknown verdict"
            raise JudgeFailed(msg) from exc
        if not isinstance(key, str) or key in by_key:
            msg = f"The judge answered rule '{key}' twice or without a key"
            raise JudgeFailed(msg)
        turns = item.get("turns")
        by_key[key] = Judged(
            key=key,
            outcome=outcome,
            reason=str(item.get("reason") or "").strip(),
            turns=[t for t in turns if isinstance(t, int)]
            if isinstance(turns, list)
            else [],
        )
    missing = [rule.key for rule in rules if rule.key not in by_key]
    if missing:
        msg = f"The judge did not answer {', '.join(missing)}"
        raise JudgeFailed(msg)
    return [by_key[rule.key] for rule in rules]


async def judge_rules(
    *,
    transcript: list[ConversationTurn],
    rules: list[RuleToJudge],
    caller_goal: str | None,
    default_fakes: list[str],
) -> Judgement:
    """Judge ``rules`` on ``transcript`` in one model call.

    Raises:
        JudgeFailed: the model call failed or its answer is unusable.
    """
    if not rules:
        return Judgement(verdicts=[], cost_usd=None, token_usage={})
    messages = [
        LLMMessage(role="system", content=_SYSTEM),
        LLMMessage(
            role="user",
            content=_user_prompt(transcript, rules, caller_goal, default_fakes),
        ),
    ]
    config = LLMCallConfig(
        temperature=settings.JUDGE_TEMPERATURE,
        max_tokens=settings.JUDGE_MAX_TOKENS,
        response_format=_response_format([rule.key for rule in rules]),
    )
    try:
        response = await call_llm(messages, config=config)
    except Exception as exc:
        logger.exception("The rule judge's model call failed")
        msg = "The judge's model call failed"
        raise JudgeFailed(msg) from exc
    return Judgement(
        verdicts=parse_verdicts((response.content or "").strip(), rules),
        cost_usd=response.response_cost_usd,
        token_usage=dict(response.usage or {}),
    )
