"""Storing findings, decision records and when each check first existed."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import ColumnElement, and_, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, func, select

from app.models.agent import Agent
from app.models.call import Call
from app.models.check import CallCheck, CheckRelease, DecisionRecord, Finding, Issue
from app.models.enums import (
    CallCheckStatus,
    CheckOutcome,
    DecisionKind,
    FindingEffect,
    IssueState,
)
from app.models.user import User

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


def get_findings(*, session: Session, call: Call) -> list[Finding]:
    """The findings on ``call``, in the order they were first raised."""
    return list(
        session.exec(
            select(Finding)
            .where(Finding.call_id == call.id)
            .order_by(col(Finding.created_at), col(Finding.id))
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


def _issues_for(
    session: Session, call: Call, identities: set[tuple[str, str]]
) -> dict[tuple[str, str], Issue]:
    """The agent's issues for ``identities`` (check type, key), created where missing."""
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
) -> int:
    """Leave ``call`` with exactly ``findings`` for the checks in ``check_types``.

    Findings of any other check are not touched: a check that no longer exists, one
    that broke, or a finding that did not come from this run at all. A finding already
    stored for the same check and the same events keeps its row, so its id, the time it
    was first raised and the effect it had do not change.

    Each finding joins the issue for its agent, check type and key, created if it does
    not exist. A resolved issue becomes regressed when a finding is first stored on a
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
        session, call, {(finding.check_type, finding.key or "") for finding in findings}
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
    for identity, finding in wanted.items():
        if identity in stored:
            continue
        issue = issues[(finding.check_type, finding.key or "")]
        finding.issue_id = issue.id
        session.add(finding)
        if (
            issue.state is IssueState.RESOLVED
            and issue.resolved_at is not None
            and started > issue.resolved_at
        ):
            issue.state = IssueState.REGRESSED
            session.add(issue)
    for run in runs:
        session.merge(run)
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

    Retroactive findings count for nothing.
    """
    if not call_ids:
        return {}
    fails = func.bool_or(col(Finding.effect) == FindingEffect.FAILS)
    found = dict(
        session.exec(
            select(Finding.call_id, fails)
            .where(
                col(Finding.call_id).in_(call_ids), col(Finding.retroactive).is_(False)
            )
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
    """Record each check in ``versions`` as broke on a call, where it has no row yet."""
    if not versions:
        return
    session.execute(
        pg_insert(_CALL_CHECK_TABLE)
        .values(
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
        .on_conflict_do_nothing(index_elements=["call_id", "check_type"])
    )
    session.commit()


def _missing_check_runs(
    agent_id: uuid.UUID, check_types: list[str]
) -> ColumnElement[bool]:
    """Condition: the agent's calls with a trace that lack a run row for some check."""
    recorded = (
        select(func.count())
        .select_from(CallCheck)
        .where(CallCheck.call_id == Call.id, col(CallCheck.check_type).in_(check_types))
        .correlate(Call)
        .scalar_subquery()
    )
    return and_(
        Call.agent_id == agent_id,
        col(Call.deleted_at).is_(None),
        col(Call.schema_version).is_not(None),
        recorded < len(check_types),
    )


def calls_missing_check_runs(
    *, session: Session, agent_id: uuid.UUID, check_types: list[str], limit: int
) -> list[Call]:
    """The agent's stored calls that some check in ``check_types`` never ran on."""
    if not check_types:
        return []
    return list(
        session.exec(
            select(Call)
            .where(_missing_check_runs(agent_id, check_types))
            .order_by(col(Call.started_at).desc())
            .limit(limit)
        ).all()
    )


def count_calls_missing_check_runs(
    *, session: Session, agent_id: uuid.UUID, check_types: list[str]
) -> int:
    if not check_types:
        return 0
    return int(
        session.exec(
            select(func.count())
            .select_from(Call)
            .where(_missing_check_runs(agent_id, check_types))
        ).one()
    )


# ── Issues ─────────────────────────────────────────────────────────


class IssueSummary(NamedTuple):
    issue: Issue
    finding_count: int
    call_count: int
    first_seen_at: datetime | None
    last_seen_at: datetime | None


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
            )
            .join(Call, col(Call.id) == col(Finding.call_id))
            .where(col(Finding.issue_id).in_([issue.id for issue in issues]))
            .group_by(col(Finding.issue_id))
        ).all()
    }
    summaries = []
    for issue in issues:
        findings, calls, first, last = totals.get(issue.id, (0, 0, None, None))
        summaries.append(
            IssueSummary(
                issue=issue,
                finding_count=findings,
                call_count=calls,
                first_seen_at=first.replace(tzinfo=UTC) if first else None,
                last_seen_at=last.replace(tzinfo=UTC) if last else None,
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


def get_issue(
    *, session: Session, issue_id: uuid.UUID, company_id: uuid.UUID
) -> Issue | None:
    return session.exec(
        select(Issue).where(Issue.id == issue_id, Issue.company_id == company_id)
    ).one_or_none()


def summarise_issue(*, session: Session, issue: Issue) -> IssueSummary:
    return _summaries(session, [issue])[0]


def list_issue_findings(
    *, session: Session, issue_id: uuid.UUID, limit: int
) -> list[tuple[Finding, datetime]]:
    """An issue's findings with when their call started, newest call first."""
    rows = session.exec(
        select(Finding, Call.started_at)
        .join(Call, col(Call.id) == col(Finding.call_id))
        .where(Finding.issue_id == issue_id)
        .order_by(col(Call.started_at).desc(), col(Finding.id))
        .limit(limit)
    ).all()
    return [(finding, started.replace(tzinfo=UTC)) for finding, started in rows]


def set_issue_state(
    *,
    session: Session,
    issue_id: uuid.UUID,
    state: IssueState,
    version: str | None,
    reason: str | None,
    decided_by: User,
) -> Issue:
    """Set an issue's state and record the decision. A no-op if it is already there.

    Two decisions on one issue are made in turn: the row is locked.
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
    if state is IssueState.RESOLVED:
        issue.resolved_at = datetime.now(UTC)
        issue.resolved_version = version
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
        )
    )
    session.commit()
    session.refresh(issue)
    return issue
