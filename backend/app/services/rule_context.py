"""A spec rule as every check reads it: its text with the person's clarifications in
force, its check type, and only the call inputs it names (plans
`plans/2026-11-26-clarification-on-rule.md`, `plans/2026-11-26-rule-data-and-check.md`).

The judge of simulated calls reads rules this way now; the spec check (roadmap 105.15)
reads them the same way, and keys any stored model answer on ``fingerprint``, so a new
clarification, check type or input name makes an earlier answer stale. A check is
given only the inputs its rule names: the classifier step the short ones, the LLM step
all of them.
"""

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlmodel import Session

from app.crud.clarification import chosen_sentence, clarifications_in_force
from app.crud.spec import KnownInput, known_inputs
from app.models.enums import SpecCheckType
from app.models.spec import SpecRule

NOT_SET = "not set"
# The inputs a rule may name: those the agent's calls carried in this many days. One
# whose longest value is over LONG_INPUT_CHARS is long and goes only to the LLM step
# (Decided, Dmytro 2026-11-26: "Measured, over 200 chars").
INPUT_DAYS = 30
LONG_INPUT_CHARS = 200


def long_inputs(
    *, session: Session, agent_id: uuid.UUID
) -> tuple[dict[str, KnownInput], set[str]]:
    """The agent's known inputs by name, and the names of the long ones."""
    known = {
        k.name: k
        for k in known_inputs(
            session=session,
            agent_id=agent_id,
            since=datetime.now(UTC) - timedelta(days=INPUT_DAYS),
        )
    }
    return known, {k.name for k in known.values() if k.longest > LONG_INPUT_CHARS}


@dataclass(frozen=True)
class Clarified:
    id: uuid.UUID
    sentence: str


@dataclass(frozen=True)
class RuleWithClarifications:
    key: str
    text: str
    clarifications: tuple[Clarified, ...] = ()
    check: SpecCheckType = SpecCheckType.CLASSIFIER
    inputs: tuple[str, ...] = ()
    # Of ``inputs``, those long enough to go only to the LLM step.
    long_inputs: frozenset[str] = frozenset()

    @property
    def fingerprint(self) -> str:
        """Changes when the rule's text, a clarification in force, its check type, the
        names of its inputs, or which of them are long change."""
        payload = json.dumps(
            [
                self.text,
                [c.sentence for c in self.clarifications],
                self.check.value,
                list(self.inputs),
                sorted(self.long_inputs),
            ],
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def given(
        self, values: Mapping[str, object] | None, *, llm: bool
    ) -> dict[str, str]:
        """The values of this rule's inputs on one call, and nothing else: for the
        classifier step (``llm`` false) only the short ones, for the LLM step all. An
        input the call lacks is "not set"."""
        values = values or {}
        return {
            name: str(values[name]) if values.get(name) is not None else NOT_SET
            for name in self.inputs
            if llm or name not in self.long_inputs
        }

    @property
    def clarification_ids(self) -> list[str]:
        return [str(c.id) for c in self.clarifications]


def rules_with_clarifications(
    *,
    session: Session,
    agent_id: uuid.UUID,
    rules: Sequence[SpecRule],
    at: datetime | None = None,
    long: set[str] | None = None,
) -> dict[str, RuleWithClarifications]:
    """``rules`` by key, each with the clarifications in force at ``at`` (now when not
    given), oldest first. ``long``: the agent's long input names, measured on its calls
    when not given."""
    in_force = clarifications_in_force(session=session, agent_id=agent_id, at=at)
    if long is None:
        _, long = long_inputs(session=session, agent_id=agent_id)
    return {
        rule.key: RuleWithClarifications(
            key=rule.key,
            text=rule.text,
            clarifications=tuple(
                Clarified(id=c.id, sentence=chosen_sentence(c))
                for c in in_force.get(rule.key, [])
            ),
            check=rule.check,
            inputs=tuple(rule.inputs),
            long_inputs=frozenset(i for i in rule.inputs if i in long),
        )
        for rule in rules
    }
