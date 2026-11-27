"""Marking findings as false positives, undoing it, and bringing back a flag the LLM
step dismissed (roadmap 105.17, plan `plans/2026-11-27-false-positives.md`).

Decided, Dmytro 2026-11-27:

- A false positive is marked on findings, many at once; archive stays the action for a
  whole issue. Any finding, from any check.
- The assistant marks without asking again when a clarification the person answered,
  on the issue's own rule, covers the findings. With no clarification, on a check with
  no spec rule, or on a critical rule, the person approves in the conversation first;
  a marking that needs it and is not approved is refused ("Refuse and say why").
- A marking changes nothing for future calls.
- Every marking, undo and bring-back is recorded on the issue and can be undone.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, col, select

from app import crud
from app.crud.clarification import chosen_sentence, clarifications_in_force
from app.crud.false_positive import (
    dismissed_answers_on,
    dismissed_count,
    dismissed_rows,
    event_starts,
    issue_findings,
    marked_count,
    marked_rows,
)
from app.models.call import Call
from app.models.check import DecisionRecord, Finding, Issue
from app.models.clarification import Clarification
from app.models.enums import DecisionKind
from app.models.issue_page import NotCountedPublic, NotCountedRow
from app.models.user import User
from app.services.checks.engine import check_call
from app.services.checks.model.spec_rule import SPEC_CHECK_TYPE, SPEC_RULE_BROKEN

MAX_FINDINGS = 200
MAX_REASON = 1000

Change = Literal["false_positive", "counted", "brought_back"]


class MarkRefused(Exception):
    """Nothing changed: what is wrong, and what to do instead."""

    def __init__(self, error: str, steps: list[str]) -> None:
        super().__init__(error)
        self.error = error
        self.steps = steps


@dataclass(frozen=True)
class Changed:
    count: int
    # Already in the state asked for: left as they were.
    unchanged: int = 0


def _actor(user: User) -> str:
    return (user.full_name or "").strip() or user.email


def _rule_is_critical(session: Session, issue: Issue) -> bool:
    spec = crud.latest_spec(session=session, agent_id=issue.agent_id)
    if spec is None or not issue.key:
        return False
    return any(
        rule.key == issue.key and rule.critical
        for rule in crud.spec_rules(session=session, spec_id=spec.id)
    )


def why_approval(
    session: Session, issue: Issue, clarification_id: uuid.UUID | None
) -> str | None:
    """Why the person must approve marking this issue's findings, or None when a
    clarification covers them."""
    if issue.check_type != SPEC_CHECK_TYPE:
        return "the check has no spec rule, so no clarification can cover it"
    if clarification_id is None:
        return "no clarification is named"
    if _rule_is_critical(session, issue):
        return "the rule is critical"
    return None


def _record(
    session: Session,
    issue: Issue,
    change: Change,
    count: int,
    *,
    by: User,
    assistant_name: str | None,
    reason: str | None,
    detail: dict[str, object],
) -> None:
    session.add(
        DecisionRecord(
            company_id=issue.company_id,
            agent_id=issue.agent_id,
            kind=DecisionKind.FINDINGS_COUNTED,
            subject=str(issue.id),
            old_value=None,
            new_value=change,
            reason=reason,
            decided_by=by.id,
            decided_by_email=by.email,
            assistant_name=assistant_name,
            detail={"count": count, **detail},
        )
    )


def _issue_findings(
    session: Session, issue: Issue, ids: Sequence[uuid.UUID]
) -> list[Finding]:
    if not ids:
        raise MarkRefused("No findings named", ["Name the findings by their ids."])
    if len(ids) > MAX_FINDINGS:
        raise MarkRefused(
            f"At most {MAX_FINDINGS} findings at once",
            [f"Send them in batches of {MAX_FINDINGS}."],
        )
    found = issue_findings(session=session, issue_id=issue.id, ids=ids)
    missing = sorted({str(i) for i in ids} - {str(f.id) for f in found})
    if missing:
        raise MarkRefused(
            f"{len(missing)} of these findings are not this issue's: "
            + ", ".join(missing[:20]),
            ["Take the ids from `list_calls` with this issue_id, or from `get_call`."],
        )
    return found


def mark_false_positives(
    *,
    session: Session,
    issue: Issue,
    finding_ids: Sequence[uuid.UUID],
    reason: str,
    clarification_id: uuid.UUID | None,
    approved: bool,
    by: User,
    assistant_name: str | None,
) -> Changed:
    """Mark the issue's findings as false positives, all or none.

    Raises:
        MarkRefused: a finding is not the issue's, the reason is missing, the
            clarification is not an answered one in force on the issue's rule, or the
            marking needs the person's approval and does not have it.
    """
    reason = " ".join(reason.split())
    if not reason:
        raise MarkRefused(
            "A marking needs a reason",
            ["Say in one line why these findings are wrong."],
        )
    if len(reason) > MAX_REASON:
        raise MarkRefused(
            f"The reason is over {MAX_REASON} characters", ["Say it in one line."]
        )
    findings = _issue_findings(session, issue, finding_ids)
    sentence = None
    if clarification_id is not None:
        in_force = clarifications_in_force(session=session, agent_id=issue.agent_id)
        clarification = next(
            (c for c in in_force.get(issue.key or "", []) if c.id == clarification_id),
            None,
        )
        if clarification is None:
            raise MarkRefused(
                "That clarification is not an answered one in force on this issue's "
                "rule",
                [
                    f"Name a clarification on rule `{issue.key}` the person answered "
                    "(`clarifications` in `get_issue`), or mark with the person's "
                    "approval instead."
                ],
            )
        sentence = chosen_sentence(clarification)
    needs = why_approval(session, issue, clarification_id)
    if needs is not None and not approved:
        raise MarkRefused(
            f"These {len(findings)} findings need the person's approval: {needs}",
            [
                "Ask the person in your conversation whether these findings are "
                "false positives, and why.",
                "If they agree, call again with `approved` true and their reason.",
            ],
        )
    now = datetime.now(UTC)
    changed = [f for f in findings if f.false_positive_at is None]
    for finding in changed:
        finding.false_positive_at = now
        finding.false_positive_by = by.id
        finding.false_positive_by_email = by.email
        finding.false_positive_assistant = assistant_name
        finding.false_positive_reason = reason
        finding.false_positive_clarification_id = clarification_id
        finding.false_positive_approved_by = _actor(by) if needs is not None else None
        session.add(finding)
    if changed:
        _record(
            session,
            issue,
            "false_positive",
            len(changed),
            by=by,
            assistant_name=assistant_name,
            reason=reason,
            detail={
                "finding_ids": [str(f.id) for f in changed],
                "clarification_id": str(clarification_id) if clarification_id else None,
                "clarification": sentence,
                "approved_by": _actor(by) if needs is not None else None,
            },
        )
    session.commit()
    return Changed(count=len(changed), unchanged=len(findings) - len(changed))


def undo_marks(
    *,
    session: Session,
    issue: Issue,
    finding_ids: Sequence[uuid.UUID],
    by: User,
    assistant_name: str | None,
) -> Changed:
    """The findings show on their calls and count again."""
    findings = _issue_findings(session, issue, finding_ids)
    changed = [f for f in findings if f.false_positive_at is not None]
    for finding in changed:
        finding.false_positive_at = None
        finding.false_positive_by = None
        finding.false_positive_by_email = None
        finding.false_positive_assistant = None
        finding.false_positive_reason = None
        finding.false_positive_clarification_id = None
        finding.false_positive_approved_by = None
        session.add(finding)
    if changed:
        _record(
            session,
            issue,
            "counted",
            len(changed),
            by=by,
            assistant_name=assistant_name,
            reason=None,
            detail={"finding_ids": [str(f.id) for f in changed]},
        )
    session.commit()
    return Changed(count=len(changed), unchanged=len(findings) - len(changed))


def bring_back(
    *,
    session: Session,
    issue: Issue,
    call_ids: Sequence[uuid.UUID],
    by: User,
    assistant_name: str | None,
) -> Changed:
    """Turn the flags the LLM step dismissed on these calls into findings.

    The stored answer records who brought the flag back; checking the call again then
    raises it, so the check stays a pure reading of its answer.

    Raises:
        MarkRefused: the issue is not a spec rule's, or a call holds no dismissed flag
            on its rule.
    """
    if issue.check_type != SPEC_CHECK_TYPE or not issue.key:
        raise MarkRefused(
            "Only a broken spec rule has flags the model dismissed",
            ["Use `undo_mark_false_positives` with `finding_ids` instead."],
        )
    if not call_ids:
        raise MarkRefused("No calls named", ["Name the calls by their ids."])
    if len(call_ids) > MAX_FINDINGS:
        raise MarkRefused(
            f"At most {MAX_FINDINGS} calls at once",
            [f"Send them in batches of {MAX_FINDINGS}."],
        )
    held = dismissed_answers_on(session=session, issue=issue, call_ids=call_ids)
    missing = sorted({str(i) for i in call_ids} - {str(c.id) for _, c in held})
    if missing:
        raise MarkRefused(
            f"{len(missing)} of these calls hold no flag the model dismissed on this "
            "rule: " + ", ".join(missing[:20]),
            ["Take the call ids from `get_issue` with `not_counted` true."],
        )
    now = datetime.now(UTC).isoformat()
    calls: list[Call] = []
    for answer, call in held:
        stored = dict(answer.answer or {})
        rules = dict(stored.get("rules") or {})
        rule = dict(rules[issue.key])
        rule["verdict"] = {
            **rule["verdict"],
            "brought_back": {
                "by": _actor(by),
                "assistant": assistant_name,
                "at": now,
            },
        }
        rules[issue.key] = rule
        stored["rules"] = rules
        answer.answer = stored
        flag_modified(answer, "answer")
        session.add(answer)
        calls.append(call)
    _record(
        session,
        issue,
        "brought_back",
        len(calls),
        by=by,
        assistant_name=assistant_name,
        reason=None,
        detail={"call_ids": [str(c.id) for c in calls]},
    )
    session.commit()
    for call in calls:
        check_call(session=session, call=call, checks=[SPEC_RULE_BROKEN])
    return Changed(count=len(calls))


Group = Literal["false_positives", "dismissed"]
PAGE = 10
MAX_PAGE = 100


def _seconds(
    starts: dict[tuple[uuid.UUID, str], int], call_id: uuid.UUID, keys: Sequence[str]
) -> float | None:
    """A moment is the last event it points at, as on the call screen."""
    ms = [starts[(call_id, k)] for k in keys if (call_id, k) in starts]
    return round(max(ms) / 1000, 3) if ms else None


def _names(session: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    return {
        user.id: (user.full_name or "").strip() or user.email.split("@")[0]
        for user in session.exec(select(User).where(col(User.id).in_(ids))).all()
    }


def not_counted(
    *, session: Session, issue: Issue, group: Group, offset: int, limit: int
) -> NotCountedPublic:
    """One group of the issue's "Not counted" list, newest first (Decided, Dmytro
    2026-11-27: loaded only when the list is opened)."""
    limit = max(1, min(limit, MAX_PAGE))
    offset = max(0, offset)
    rows: list[NotCountedRow] = []
    if group == "false_positives":
        total = marked_count(session=session, issue_id=issue.id)
        page = marked_rows(
            session=session, issue_id=issue.id, offset=offset, limit=limit
        )
        starts = event_starts(
            session=session, wanted=[(f.call_id, f.event_keys) for f, _ in page]
        )
        names = _names(
            session, {f.false_positive_by for f, _ in page if f.false_positive_by}
        )
        clarification_ids = {
            f.false_positive_clarification_id
            for f, _ in page
            if f.false_positive_clarification_id
        }
        sentences = (
            {
                c.id: chosen_sentence(c)
                for c in session.exec(
                    select(Clarification).where(
                        col(Clarification.id).in_(clarification_ids)
                    )
                ).all()
            }
            if clarification_ids
            else {}
        )
        for finding, call in page:
            person = finding.false_positive_by
            email = finding.false_positive_by_email or ""
            name = (names.get(person) if person else None) or email.split("@")[0]
            rows.append(
                NotCountedRow(
                    finding_id=finding.id,
                    call_id=call.id,
                    started_at=call.started_at.replace(tzinfo=UTC),
                    caller_last_four=crud.caller_last_four(call.caller_number),
                    at_seconds=_seconds(starts, call.id, finding.event_keys),
                    by=name or None,
                    assistant=finding.false_positive_assistant,
                    at=finding.false_positive_at,
                    reason=finding.false_positive_reason,
                    clarification=sentences.get(finding.false_positive_clarification_id)
                    if finding.false_positive_clarification_id
                    else None,
                    approved_by=finding.false_positive_approved_by,
                )
            )
    else:
        total = dismissed_count(session=session, issue=issue)
        page_answers = dismissed_rows(
            session=session, issue=issue, offset=offset, limit=limit
        )
        key = issue.key or ""
        verdicts = [(answer.answer or {})["rules"][key] for answer, _ in page_answers]
        starts = event_starts(
            session=session,
            wanted=[
                (call.id, [str(i) for i in rule["verdict"].get("event_ids") or []])
                for (_, call), rule in zip(page_answers, verdicts, strict=True)
            ],
        )
        for (_, call), rule in zip(page_answers, verdicts, strict=True):
            verdict = rule["verdict"]
            probability = rule.get("probability")
            rows.append(
                NotCountedRow(
                    call_id=call.id,
                    started_at=call.started_at.replace(tzinfo=UTC),
                    caller_last_four=crud.caller_last_four(call.caller_number),
                    at_seconds=_seconds(
                        starts,
                        call.id,
                        [str(i) for i in verdict.get("event_ids") or []],
                    ),
                    reason=str(verdict.get("reason") or "") or None,
                    model=str(verdict.get("model") or "") or None,
                    probability=float(probability)
                    if isinstance(probability, int | float)
                    else None,
                )
            )
    end = offset + len(rows)
    return NotCountedPublic(
        group=group,
        total=total,
        rows=rows,
        next_offset=end if end < total else None,
    )
