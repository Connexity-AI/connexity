import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Run, RunCreate, RunStatus, RunUpdate


def create_run(
    *,
    session: Session,
    run_in: RunCreate,
    created_by: uuid.UUID | None = None,
) -> Run:
    run_data = run_in.model_dump()
    # RunConfig (Pydantic) → dict for JSONB column
    if run_in.config is not None:
        run_data["config"] = run_in.config.model_dump()
    if created_by is not None:
        run_data["created_by"] = created_by
    db_obj = Run.model_validate(run_data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_run(*, session: Session, run_id: uuid.UUID) -> Run | None:
    return session.get(Run, run_id)


def list_runs(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    agent_id: uuid.UUID | None = None,
    status: RunStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[Run], int]:
    statement = select(Run)
    count_statement = select(func.count()).select_from(Run)

    if agent_id is not None:
        statement = statement.where(Run.agent_id == agent_id)
        count_statement = count_statement.where(Run.agent_id == agent_id)
    if status is not None:
        statement = statement.where(Run.status == status)
        count_statement = count_statement.where(Run.status == status)
    if created_after is not None:
        statement = statement.where(Run.created_at >= created_after)
        count_statement = count_statement.where(Run.created_at >= created_after)
    if created_before is not None:
        statement = statement.where(Run.created_at <= created_before)
        count_statement = count_statement.where(Run.created_at <= created_before)

    count = session.exec(count_statement).one()
    items = list(
        session.exec(
            statement.order_by(col(Run.created_at).desc()).offset(skip).limit(limit)
        ).all()
    )
    return items, count


def update_run(*, session: Session, db_run: Run, run_in: RunUpdate) -> Run:
    update_data = run_in.model_dump(exclude_unset=True)
    # AggregateMetrics (Pydantic) → dict for JSONB column
    if "aggregate_metrics" in update_data and run_in.aggregate_metrics is not None:
        update_data["aggregate_metrics"] = run_in.aggregate_metrics.model_dump()
    db_run.sqlmodel_update(update_data)
    session.add(db_run)
    session.commit()
    session.refresh(db_run)
    return db_run


def delete_run(*, session: Session, db_run: Run) -> None:
    session.delete(db_run)
    session.commit()
