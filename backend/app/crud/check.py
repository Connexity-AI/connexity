"""Storing findings, decision records and when each check first existed."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from sqlalchemy import ColumnElement, and_, exists, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from app.models.agent import Agent
from app.models.call import Call
from app.models.category import OTHER, Category
from app.models.check import CallCheck, CheckRelease, DecisionRecord, Finding, Issue
from app.models.enums import (
    CallCheckStatus,
    CheckKind,
    CheckOutcome,
    DecisionKind,
    FindingEffect,
    IssueState,
)
from app.models.user import User

# Who a decision Connexity makes on its own is recorded as.
CONNEXITY = "Connexity"
# The spike rule (Dmytro, 2026-11-14): over the last 7 days, at least 3 calls and at
# least twice the share of the agent's calls it had in the 30 days before the archive.
SPIKE_WINDOW = timedelta(days=7)
SPIKE_MIN_CALLS = 3
SPIKE_FACTOR = 2.0
BASELINE_WINDOW = timedelta(days=30)

_RELEASE_TABLE = CheckRelease.__table__  # type: ignore[attr-defined]
_ISSUE_TABLE = Issue.__table__  # type: ignore[attr-defined]
_CALL_CHECK_TABLE = CallCheck.__table__  # type: ignore[attr-defined]


def _first_seen(session: Session, check_types: list[str]) -> dict[str, datetime]:
    rows = session.exec(
        select(CheckRelease.check_type, func.min(CheckRelease.first_seen_at))
        .where(col(CheckRelease.check_type).in_(check_types))
        .group_by(col(CheckRelease.check_type))
    ).all()
    return dict(rows)


def ensure_check_releases(
    *, session: Session, versions: Mapping[str, int]
) -> dict[str, datetime]:
    """Record any of ``versions`` (check type to version) not seen before.

    Commits only when something was missing; a server records its checks when it
    starts, so on a call this is one read.

    Returns:
        For each check type, when its earliest version was first seen.
    """
    if not versions:
        return {}
    known = set(
        session.exec(
            select(CheckRelease.check_type, CheckRelease.version).where(
                col(CheckRelease.check_type).in_(list(versions))
            )
        ).all()
    )
    missing = [item for item in versions.items() if item not in known]
    if missing:
        session.execute(
            pg_insert(_RELEASE_TABLE)
            .values(
                [
                    {"check_type": check_type, "version": version}
                    for check_type, version in missing
                ]
            )
            .on_conflict_do_nothing(index_elements=["check_type", "version"])
        )
        session.commit()
    return _first_seen(session, list(versions))


def check_setting_history(
    *, session: Session, agent_id: uuid.UUID
) -> dict[str, list[DecisionRecord]]:
    """Every change to a check's setting for an agent, by check type, oldest first."""
    history: dict[str, list[DecisionRecord]] = {}
    for record in session.exec(
        select(DecisionRecord)
        .where(
            DecisionRecord.agent_id == agent_id,
            DecisionRecord.kind == DecisionKind.CHECK_SETTING,
        )
        .order_by(col(DecisionRecord.created_at), col(DecisionRecord.id))
    ).all():
        history.setdefault(record.subject, []).append(record)
    return history


def lock_agent(*, session: Session, agent_id: uuid.UUID) -> None:
    """Hold the agent's row until commit, so two decisions on it are made in turn."""
    session.exec(select(Agent.id).where(Agent.id == agent_id).with_for_update()).one()


def record_decision(
    *,
    session: Session,
    agent_id: uuid.UUID,
    company_id: uuid.UUID,
    kind: DecisionKind,
    subject: str,
    old_value: str | None,
    new_value: str | None,
    reason: str | None,
    decided_by: User,
) -> DecisionRecord:
    record = DecisionRecord(
        company_id=company_id,
        agent_id=agent_id,
        kind=kind,
        subject=subject,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        decided_by=decided_by.id,
        decided_by_email=decided_by.email,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_decision_records(
    *, session: Session, agent_id: uuid.UUID, limit: int
) -> list[DecisionRecord]:
    """An agent's decision records, newest first."""
    return list(
        session.exec(
            select(DecisionRecord)
            .where(DecisionRecord.agent_id == agent_id)
            .order_by(
                col(DecisionRecord.created_at).desc(), col(DecisionRecord.id).desc()
            )
            .limit(limit)
        ).all()
    )


def shown_finding() -> ColumnElement[bool]:
    """The finding's issue is not archived.

    While an issue is archived its findings are hidden on every call, whatever the
    call's date: they make no call fail or degrade and are never shown, to a person or
    the assistant. They are still stored, and count again once it is unarchived
    (Dmytro, 2026-11-14). Every query that works out a call's result or findings uses
    this.
    """
    # An alias, so the check never binds to an `issue` the outer query already joins.
    archived = aliased(Issue)
    return ~exists().where(
        archived.id == Finding.issue_id, archived.state == IssueState.ARCHIVED
    )


def get_findings(
    *, session: Session, call: Call, shown_only: bool = False
) -> list[Finding]:
    """The findings on ``call``, in the order they were first raised. ``shown_only``
    leaves out those of archived issues, for anything a person or assistant sees."""
    query = select(Finding).where(Finding.call_id == call.id)
    if shown_only:
        query = query.where(shown_finding())
    return list(
        session.exec(query.order_by(col(Finding.created_at), col(Finding.id))).all()
    )


def issues_of_findings(*, session: Session, call: Call) -> list[Issue]:
    """The issues the call's findings belong to."""
    return list(
        session.exec(
            select(Issue).where(
                col(Issue.id).in_(
                    select(Finding.issue_id).where(Finding.call_id == call.id)
                )
            )
        ).all()
    )


def _identity(finding: Finding) -> tuple[str, tuple[str, ...]]:
    return finding.check_type, tuple(finding.event_keys)


def lock_call(*, session: Session, call_id: uuid.UUID) -> Call:
    """Hold the call's row until commit, and return it as it is stored now.

    Storing a trace takes the same lock, so whoever holds it reads a trace that
    cannot change underneath them.
    """
    return session.exec(
        select(Call)
        .where(Call.id == call_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def _category_id(key: str) -> ColumnElement[uuid.UUID]:
    named = select(Category.id).where(Category.key == key).scalar_subquery()
    other = select(Category.id).where(Category.key == OTHER).scalar_subquery()
    return func.coalesce(named, other)


def _issues_for(
    session: Session,
    call: Call,
    identities: set[tuple[str, str]],
    categories: Mapping[str, str],
) -> dict[tuple[str, str], Issue]:
    """The agent's issues for ``identities`` (check type, key), created where missing.

    A new issue takes its check's category (``categories``: check type to category
    key); a check with none, or one not in the table, gets "Other".
    """
    if not identities:
        return {}
    session.execute(
        pg_insert(_ISSUE_TABLE)
        .values(
            [
                {
                    "id": uuid.uuid4(),
                    "company_id": call.company_id,
                    "agent_id": call.agent_id,
                    "check_type": check_type,
                    "category_id": _category_id(categories.get(check_type, OTHER)),
                    "key": key,
                    "state": IssueState.OPEN,
                }
                for check_type, key in identities
            ]
        )
        .on_conflict_do_nothing(constraint="uq_issue_identity")
    )
    rows = session.exec(
        select(Issue).where(
            Issue.agent_id == call.agent_id,
            tuple_(col(Issue.check_type), col(Issue.key)).in_(list(identities)),
        )
    ).all()
    return {(row.check_type, row.key): row for row in rows}


def replace_findings(
    *,
    session: Session,
    call: Call,
    check_types: set[str],
    findings: list[Finding],
    runs: list[CallCheck],
    categories: Mapping[str, str] | None = None,
) -> int:
    """Leave ``call`` with exactly ``findings`` for the checks in ``check_types``.

    Findings of any other check are not touched: a check that no longer exists, one
    that broke, or a finding that did not come from this run at all. A finding already
    stored for the same check and the same events keeps its row, so its id, the time it
    was first raised and the effect it had do not change.

    Each finding joins the issue for its agent, check type and key, created if it does
    not exist. A resolved issue reopens when a finding is first stored on a
    call that started after it was resolved.

    ``runs`` replace what each of those checks was recorded as doing on this call. The
    caller holds the call's lock (``lock_call``). Commits.

    Returns:
        How many findings the call now has from the checks in ``check_types``.
    """
    stored = {
        _identity(row): row
        for row in get_findings(session=session, call=call)
        if row.check_type in check_types
    }
    wanted = {_identity(finding): finding for finding in findings}
    issues = _issues_for(
        session,
        call,
        {(finding.check_type, finding.key or "") for finding in findings},
        categories or {},
    )
    started = call.started_at.replace(tzinfo=UTC)
    for identity, row in stored.items():
        finding = wanted.get(identity)
        if finding is None:
            session.delete(row)
            continue
        row.check_version = finding.check_version
        row.key = finding.key
        row.detail = finding.detail
        row.issue_id = issues[(finding.check_type, finding.key or "")].id
        session.add(row)
    added: dict[uuid.UUID, Issue] = {}
    for identity, finding in wanted.items():
        if identity in stored:
            continue
        issue = issues[(finding.check_type, finding.key or "")]
        finding.issue_id = issue.id
        session.add(finding)
        added[issue.id] = issue
        if (
            issue.state is IssueState.RESOLVED
            and issue.resolved_at is not None
            and started > issue.resolved_at
        ):
            issue.state = IssueState.REOPENED
            session.add(issue)
            session.add(
                _connexity_decision(
                    issue,
                    old=IssueState.RESOLVED,
                    reason="Found again on a call after it was resolved",
                )
            )
    for run in runs:
        session.merge(run)
    session.flush()
    for issue in added.values():
        if issue.state is IssueState.ARCHIVED and issue.archive_until_spike:
            spike = issue_spike(session=session, issue=issue, now=datetime.now(UTC))
            if spike is not None:
                issue.state = IssueState.REOPENED
                session.add(issue)
                session.add(
                    _connexity_decision(
                        issue,
                        old=IssueState.ARCHIVED,
                        reason=spike_line(spike),
                        detail=spike,
                    )
                )
    call.checked_at = datetime.now(UTC).replace(tzinfo=None)
    session.add(call)
    session.commit()
    return len(wanted)


def get_call_checks(*, session: Session, call: Call) -> list[CallCheck]:
    """What each check did on ``call`` the last time it was checked."""
    return list(
        session.exec(
            select(CallCheck)
            .where(CallCheck.call_id == call.id)
            .order_by(col(CallCheck.check_type))
        ).all()
    )


def call_check_statuses(
    *, session: Session, call_ids: list[uuid.UUID]
) -> dict[uuid.UUID, CallCheckStatus]:
    """Failed, degraded, clean or unchecked for each call, read from what is stored.

    Every finding counts, including one found by a check added after the call: "its
    still an issue" (Dmytro, 2026-11-13), except those of an archived issue. Findings stay marked retroactive, for anything
    that must leave them out later (a reliability score's history).
    """
    if not call_ids:
        return {}
    fails = func.bool_or(col(Finding.effect) == FindingEffect.FAILS)
    found = dict(
        session.exec(
            select(Finding.call_id, fails)
            .where(col(Finding.call_id).in_(call_ids), shown_finding())
            .group_by(col(Finding.call_id))
        ).all()
    )
    ran = set(
        session.exec(
            select(CallCheck.call_id)
            .where(
                col(CallCheck.call_id).in_(call_ids),
                CallCheck.outcome == CheckOutcome.RAN,
            )
            .distinct()
        ).all()
    )
    statuses: dict[uuid.UUID, CallCheckStatus] = {}
    for call_id in call_ids:
        if call_id in found:
            statuses[call_id] = (
                CallCheckStatus.FAILED if found[call_id] else CallCheckStatus.DEGRADED
            )
        elif call_id in ran:
            statuses[call_id] = CallCheckStatus.CLEAN
        else:
            statuses[call_id] = CallCheckStatus.UNCHECKED
    return statuses


def record_checks_broke(
    *,
    session: Session,
    call_id: uuid.UUID,
    company_id: uuid.UUID,
    versions: Mapping[str, int],
) -> None:
    """Record each check in ``versions`` as broke on a call, replacing a run by an
    older version, so the call is not picked up again until the check changes."""
    if not versions:
        return
    insert_stmt = pg_insert(_CALL_CHECK_TABLE).values(
        [
            {
                "call_id": call_id,
                "check_type": check_type,
                "company_id": company_id,
                "check_version": version,
                "outcome": CheckOutcome.BROKE,
            }
            for check_type, version in versions.items()
        ]
    )
    session.execute(
        insert_stmt.on_conflict_do_update(
            index_elements=["call_id", "check_type"],
            set_={
                "check_version": insert_stmt.excluded.check_version,
                "outcome": CheckOutcome.BROKE,
                "missing": None,
            },
            # Only a run by another version: a run of this version stays as it is.
            where=_CALL_CHECK_TABLE.c.check_version
            != insert_stmt.excluded.check_version,
        )
    )
    session.commit()


def _needs_checking(
    agent_ids: list[uuid.UUID], versions: Mapping[str, int]
) -> ColumnElement[bool]:
    """Condition: calls with a trace that lack a run of some current check version.

    A call checked by an older version of a check, or never by a check, needs
    checking. A call is never checked twice by the same version, whatever the outcome.
    """
    current = (
        select(func.count())
        .select_from(CallCheck)
        .where(
            CallCheck.call_id == Call.id,
            tuple_(col(CallCheck.check_type), col(CallCheck.check_version)).in_(
                list(versions.items())
            ),
        )
        .correlate(Call)
        .scalar_subquery()
    )
    return and_(
        col(Call.agent_id).in_(agent_ids),
        col(Call.deleted_at).is_(None),
        col(Call.schema_version).is_not(None),
        current < len(versions),
    )


def calls_needing_checks(
    *,
    session: Session,
    agent_ids: list[uuid.UUID],
    versions: Mapping[str, int],
    limit: int,
) -> list[Call]:
    """These agents' stored calls that some current check version never ran on,
    newest first."""
    if not versions or not agent_ids:
        return []
    return list(
        session.exec(
            select(Call)
            .where(_needs_checking(agent_ids, versions))
            .order_by(col(Call.started_at).desc())
            .limit(limit)
        ).all()
    )


def count_calls_needing_checks(
    *, session: Session, agent_ids: list[uuid.UUID], versions: Mapping[str, int]
) -> int:
    if not versions or not agent_ids:
        return 0
    return int(
        session.exec(
            select(func.count())
            .select_from(Call)
            .where(_needs_checking(agent_ids, versions))
        ).one()
    )


# ── Issues ─────────────────────────────────────────────────────────


class IssueSummary(NamedTuple):
    issue: Issue
    finding_count: int
    call_count: int
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    # Any of its findings fails the call: the issue is Critical, otherwise a Warning.
    critical: bool = False
    # How its check finds things (rule, classifier, judge), from its findings.
    kind: CheckKind | None = None


def _summaries(session: Session, issues: list[Issue]) -> list[IssueSummary]:
    if not issues:
        return []
    totals = {
        row[0]: row[1:]
        for row in session.exec(
            select(
                Finding.issue_id,
                func.count(col(Finding.id)),
                func.count(func.distinct(col(Finding.call_id))),
                func.min(col(Call.started_at)),
                func.max(col(Call.started_at)),
                func.bool_or(col(Finding.effect) == FindingEffect.FAILS),
                func.max(col(Finding.kind)),
            )
            .join(Call, col(Call.id) == col(Finding.call_id))
            .where(col(Finding.issue_id).in_([issue.id for issue in issues]))
            .group_by(col(Finding.issue_id))
        ).all()
    }
    summaries = []
    for issue in issues:
        findings, calls, first, last, critical, kind = totals.get(
            issue.id, (0, 0, None, None, False, None)
        )
        summaries.append(
            IssueSummary(
                issue=issue,
                finding_count=findings,
                call_count=calls,
                first_seen_at=first.replace(tzinfo=UTC) if first else None,
                last_seen_at=last.replace(tzinfo=UTC) if last else None,
                critical=bool(critical),
                kind=CheckKind(kind) if kind else None,
            )
        )
    return summaries


def list_issues(*, session: Session, agent_id: uuid.UUID) -> list[IssueSummary]:
    """The agent's issues, the one seen most recently first."""
    issues = list(session.exec(select(Issue).where(Issue.agent_id == agent_id)).all())
    oldest = datetime.min.replace(tzinfo=UTC)
    return sorted(
        _summaries(session, issues),
        key=lambda summary: (summary.last_seen_at or oldest, summary.issue.created_at),
        reverse=True,
    )


def list_workspace_issues(
    *, session: Session, company_id: uuid.UUID, agent_id: uuid.UUID | None = None
) -> list[IssueSummary]:
    """The workspace's issues, in no order: `app/services/issue_list.py` orders them
    for the period."""
    query = select(Issue).where(Issue.company_id == company_id)
    if agent_id is not None:
        query = query.where(Issue.agent_id == agent_id)
    return _summaries(session, list(session.exec(query).all()))


def stored_call_counts(
    *, session: Session, agent_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many calls each agent has stored, not deleted."""
    if not agent_ids:
        return {}
    rows = session.exec(
        select(Call.agent_id, func.count())
        .where(col(Call.agent_id).in_(agent_ids), col(Call.deleted_at).is_(None))
        .group_by(col(Call.agent_id))
    ).all()
    counts = dict.fromkeys(agent_ids, 0)
    for agent_id, count in rows:
        counts[agent_id] = count
    return counts


def get_issue(
    *, session: Session, issue_id: uuid.UUID, company_id: uuid.UUID
) -> Issue | None:
    return session.exec(
        select(Issue).where(Issue.id == issue_id, Issue.company_id == company_id)
    ).one_or_none()


def summarise_issue(*, session: Session, issue: Issue) -> IssueSummary:
    return _summaries(session, [issue])[0]


def _connexity_decision(
    issue: Issue,
    *,
    old: IssueState,
    reason: str,
    detail: dict[str, Any] | None = None,
) -> DecisionRecord:
    return DecisionRecord(
        company_id=issue.company_id,
        agent_id=issue.agent_id,
        kind=DecisionKind.ISSUE_STATE,
        subject=str(issue.id),
        old_value=old.value,
        new_value=issue.state.value,
        reason=reason,
        decided_by=None,
        decided_by_email=CONNEXITY,
        detail=detail,
    )


def _share(calls: int, of: int) -> float:
    return calls / of if of else 0.0


def baseline_share(*, session: Session, issue: Issue, at: datetime) -> float:
    """The issue's share of the agent's calls in the 30 days before ``at``."""
    from app.crud.issue_page import agent_calls_between, issue_calls_between

    start = at - BASELINE_WINDOW
    return _share(
        issue_calls_between(session=session, issue_id=issue.id, start=start, end=at),
        agent_calls_between(
            session=session, agent_id=issue.agent_id, start=start, end=at
        ),
    )


def issue_spike(
    *, session: Session, issue: Issue, now: datetime
) -> dict[str, Any] | None:
    """The spike's numbers if the archived issue spiked in the last 7 days since it was
    archived, else None.

    A spike is at least 3 calls, and at least twice the baseline share fixed when it
    was archived. With a baseline of 0, any 3 calls are a spike.
    """
    from app.crud.issue_page import agent_calls_between, issue_calls_between

    # Only calls since the archive count: a busy week before it is what was archived.
    start = now - SPIKE_WINDOW
    if issue.archived_at is not None:
        archived_at = issue.archived_at
        if archived_at.tzinfo is None:
            archived_at = archived_at.replace(tzinfo=UTC)
        start = max(start, archived_at)
    calls = issue_calls_between(
        session=session, issue_id=issue.id, start=start, end=now
    )
    if calls < SPIKE_MIN_CALLS:
        return None
    agent_calls = agent_calls_between(
        session=session, agent_id=issue.agent_id, start=start, end=now
    )
    share = _share(calls, agent_calls)
    baseline = issue.archive_baseline_share or 0.0
    if baseline > 0 and share < SPIKE_FACTOR * baseline:
        return None
    return {
        "calls": calls,
        "agent_calls": agent_calls,
        "share": round(share, 4),
        "baseline_share": round(baseline, 4),
    }


def spike_line(spike: dict[str, Any]) -> str:
    """'8 calls this week, twice as often as when it was archived'."""
    calls = spike["calls"]
    noun = "call" if calls == 1 else "calls"
    baseline = spike["baseline_share"]
    if not baseline:
        return f"{calls} {noun} this week; it had stopped when it was archived"
    ratio = spike["share"] / baseline
    how = "twice" if ratio < 2.5 else f"{ratio:.0f} times"
    return f"{calls} {noun} this week, {how} as often as when it was archived"


def set_issue_state(
    *,
    session: Session,
    issue_id: uuid.UUID,
    state: IssueState,
    version: str | None,
    reason: str | None,
    decided_by: User,
    until_spike: bool = True,
    assistant_name: str | None = None,
) -> Issue:
    """Set an issue's state and record the decision. A no-op if it is already there.

    Archiving fixes its duration ("until it spikes" or forever) and, for a spike, the
    baseline share. ``assistant_name`` is the assistant that acted with the person's
    approval. Two decisions on one issue are made in turn: the row is locked.
    """
    issue = session.exec(
        select(Issue)
        .where(Issue.id == issue_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if issue.state is state:
        session.rollback()
        return issue
    old = issue.state
    issue.state = state
    now = datetime.now(UTC)
    detail: dict[str, Any] | None = None
    if state is IssueState.RESOLVED:
        issue.resolved_at = now
        issue.resolved_version = version
    if state is IssueState.ARCHIVED:
        issue.archived_at = now
        issue.archive_until_spike = until_spike
        issue.archive_baseline_share = (
            baseline_share(session=session, issue=issue, at=now)
            if until_spike
            else None
        )
        detail = {"duration": "until_spike" if until_spike else "forever"}
        if until_spike:
            detail["baseline_share"] = round(issue.archive_baseline_share or 0.0, 4)
    session.add(issue)
    session.add(
        DecisionRecord(
            company_id=issue.company_id,
            agent_id=issue.agent_id,
            kind=DecisionKind.ISSUE_STATE,
            subject=str(issue.id),
            old_value=old.value,
            new_value=state.value,
            reason=reason,
            decided_by=decided_by.id,
            decided_by_email=decided_by.email,
            assistant_name=assistant_name,
            detail=detail,
        )
    )
    session.commit()
    session.refresh(issue)
    return issue
