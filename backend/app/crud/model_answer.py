"""Stored model answers for model checks, and the calls waiting for one."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import and_, or_, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col, func, select

from app.crud.usage import record_call_usage_safely
from app.models.call import Call
from app.models.check import CallCheck
from app.models.enums import CheckOutcome, ModelAnswerStatus
from app.models.model_answer import ModelAnswer

_TABLE = ModelAnswer.__table__  # type: ignore[attr-defined]


def get_model_answers(
    *, session: Session, call_id: uuid.UUID, versions: Mapping[str, int]
) -> dict[str, ModelAnswer]:
    """The answers stored for ``call_id`` by these check versions, by check type."""
    if not versions:
        return {}
    rows = session.exec(
        select(ModelAnswer).where(
            ModelAnswer.call_id == call_id,
            tuple_(col(ModelAnswer.check_type), col(ModelAnswer.check_version)).in_(
                list(versions.items())
            ),
        )
    ).all()
    return {row.check_type: row for row in rows}


def earlier_model_answer(
    *, session: Session, call_id: uuid.UUID, check_type: str, below: int
) -> ModelAnswer | None:
    """The newest answer an earlier version of ``check_type`` stored for the call
    without failing, or None."""
    return session.exec(
        select(ModelAnswer)
        .where(
            ModelAnswer.call_id == call_id,
            ModelAnswer.check_type == check_type,
            col(ModelAnswer.check_version) < below,
            ModelAnswer.status == ModelAnswerStatus.OK,
        )
        .order_by(col(ModelAnswer.check_version).desc())
        .limit(1)
    ).first()


def model_spend_since(*, session: Session, since: datetime) -> float:
    """What model checks have cost the whole product since ``since``, in dollars."""
    total = session.exec(
        select(func.coalesce(func.sum(col(ModelAnswer.cost_usd)), 0.0)).where(
            col(ModelAnswer.updated_at) >= since
        )
    ).one()
    return float(total)


def calls_waiting_for_models(
    *,
    session: Session,
    versions: Mapping[str, int],
    agent_ids: list[uuid.UUID] | None,
    limit: int,
    keys_present: tuple[str, ...] = (),
) -> list[tuple[Call, str]]:
    """Calls with a model check recorded as pending at its current version, newest
    first, with the check's type. One row per call and check.

    A check skipped because a key was missing (``CallCheck.missing`` names it) waits
    too once that key is in ``keys_present``, so adding a key later checks the calls
    stored without it."""
    if not versions or limit <= 0:
        return []
    query = (
        select(Call, CallCheck.check_type)
        .join(CallCheck, col(CallCheck.call_id) == col(Call.id))
        .where(
            or_(
                CallCheck.outcome == CheckOutcome.PENDING,
                and_(
                    CallCheck.outcome == CheckOutcome.SKIPPED,
                    col(CallCheck.missing).in_(keys_present),
                ),
            ),
            tuple_(col(CallCheck.check_type), col(CallCheck.check_version)).in_(
                list(versions.items())
            ),
            col(Call.deleted_at).is_(None),
        )
        .order_by(col(Call.started_at).desc())
        .limit(limit)
    )
    if agent_ids is not None:
        query = query.where(col(Call.agent_id).in_(agent_ids))
    return list(session.exec(query).all())


def save_model_answer(
    *,
    session: Session,
    call: Call,
    check_type: str,
    check_version: int,
    status: ModelAnswerStatus,
    model: str = "",
    answer: object = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    requests: int = 0,
    cost_usd: float = 0.0,
    error: str | None = None,
) -> ModelAnswer:
    """Store the answer, or a failed attempt, for one call and check version.

    A second attempt replaces a failed one and counts it; costs add up, because a
    failed attempt may still have been billed. An answer that is already OK is kept.
    Commits.
    """
    now = datetime.now(UTC)
    insert_stmt = pg_insert(_TABLE).values(
        id=uuid.uuid4(),
        company_id=call.company_id,
        call_id=call.id,
        check_type=check_type,
        check_version=check_version,
        status=status.value,
        model=model,
        answer=answer,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        requests=requests,
        cost_usd=cost_usd,
        attempts=1,
        error=error,
        created_at=now,
        updated_at=now,
    )
    excluded = insert_stmt.excluded
    session.execute(
        insert_stmt.on_conflict_do_update(
            constraint="uq_model_answer_call_check",
            set_={
                "status": excluded.status,
                "model": excluded.model,
                "answer": excluded.answer,
                "input_tokens": _TABLE.c.input_tokens + excluded.input_tokens,
                "output_tokens": _TABLE.c.output_tokens + excluded.output_tokens,
                "requests": _TABLE.c.requests + excluded.requests,
                "cost_usd": _TABLE.c.cost_usd + excluded.cost_usd,
                "attempts": _TABLE.c.attempts + 1,
                "error": excluded.error,
                "updated_at": excluded.updated_at,
            },
            where=_TABLE.c.status != ModelAnswerStatus.OK.value,
        )
    )
    session.commit()
    # What the check cost goes on the call's usage record.
    record_call_usage_safely(session=session, call=call)
    return session.exec(
        select(ModelAnswer).where(
            ModelAnswer.call_id == call.id,
            ModelAnswer.check_type == check_type,
            ModelAnswer.check_version == check_version,
        )
    ).one()


def record_model_check(
    *,
    session: Session,
    call_id: uuid.UUID,
    check_type: str,
    outcome: CheckOutcome,
    missing: str | None = None,
) -> None:
    """Change what a model check is recorded as doing on a call (pending to broke, or
    the reason it waits). Commits."""
    row = session.get(CallCheck, (call_id, check_type))
    if row is None:
        return
    row.outcome = outcome
    row.missing = missing
    session.add(row)
    session.commit()
