"""Storing findings, decision records and when each check first existed."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, func, select

from app.models.agent import Agent
from app.models.call import Call
from app.models.check import CheckRelease, DecisionRecord, Finding
from app.models.enums import DecisionKind
from app.models.user import User

_RELEASE_TABLE = CheckRelease.__table__  # type: ignore[attr-defined]


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


def replace_findings(
    *,
    session: Session,
    call: Call,
    check_types: set[str],
    findings: list[Finding],
    checked: bool,
) -> int:
    """Leave ``call`` with exactly ``findings`` for the checks in ``check_types``.

    Findings of any other check are not touched: a check that no longer exists, one
    that could not run, or a finding that did not come from this run at all. A finding
    already stored for the same check and the same events keeps its row, so its id, the
    time it was first raised and the effect it had do not change.

    The caller holds the call's lock (``lock_call``). Commits. ``checked`` says whether
    to note the call as checked.

    Returns:
        How many findings the call now has from the checks in ``check_types``.
    """
    stored = {
        _identity(row): row
        for row in get_findings(session=session, call=call)
        if row.check_type in check_types
    }
    wanted = {_identity(finding): finding for finding in findings}
    for identity, row in stored.items():
        finding = wanted.get(identity)
        if finding is None:
            session.delete(row)
            continue
        row.check_version = finding.check_version
        row.key = finding.key
        row.detail = finding.detail
        session.add(row)
    for identity, finding in wanted.items():
        if identity not in stored:
            session.add(finding)
    if checked:
        call.checked_at = datetime.now(UTC).replace(tzinfo=None)
        session.add(call)
    session.commit()
    return len(wanted)
