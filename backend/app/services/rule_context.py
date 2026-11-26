"""A spec rule as every check reads it: its text with the person's clarifications in
force (plan `plans/2026-11-26-clarification-on-rule.md`).

The judge of simulated calls reads rules this way now; the spec check (roadmap 105.15)
reads them the same way, and keys any stored model answer on ``fingerprint``, so a new
clarification makes an earlier answer stale.
"""

import hashlib
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlmodel import Session

from app.crud.clarification import chosen_sentence, clarifications_in_force
from app.models.spec import SpecRule


@dataclass(frozen=True)
class Clarified:
    id: uuid.UUID
    sentence: str


@dataclass(frozen=True)
class RuleWithClarifications:
    key: str
    text: str
    clarifications: tuple[Clarified, ...] = ()

    @property
    def fingerprint(self) -> str:
        """Changes when the rule's text or any clarification in force changes."""
        payload = json.dumps(
            [self.text, [c.sentence for c in self.clarifications]], ensure_ascii=False
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def clarification_ids(self) -> list[str]:
        return [str(c.id) for c in self.clarifications]


def rules_with_clarifications(
    *,
    session: Session,
    agent_id: uuid.UUID,
    rules: Sequence[SpecRule],
    at: datetime | None = None,
) -> dict[str, RuleWithClarifications]:
    """``rules`` by key, each with the clarifications in force at ``at`` (now when not
    given), oldest first."""
    in_force = clarifications_in_force(session=session, agent_id=agent_id, at=at)
    return {
        rule.key: RuleWithClarifications(
            key=rule.key,
            text=rule.text,
            clarifications=tuple(
                Clarified(id=c.id, sentence=chosen_sentence(c))
                for c in in_force.get(rule.key, [])
            ),
        )
        for rule in rules
    }
