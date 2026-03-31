import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models.custom_metric import (
    CustomMetric,
    CustomMetricCreate,
    CustomMetricUpdate,
)


def create_custom_metric(
    *, session: Session, metric_in: CustomMetricCreate, owner_id: uuid.UUID
) -> CustomMetric:
    db_obj = CustomMetric.model_validate(
        {**metric_in.model_dump(), "created_by": owner_id}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_custom_metric(*, session: Session, metric_id: uuid.UUID) -> CustomMetric | None:
    return session.get(CustomMetric, metric_id)


def get_custom_metric_by_name_and_owner(
    *, session: Session, name: str, owner_id: uuid.UUID
) -> CustomMetric | None:
    statement = select(CustomMetric).where(
        CustomMetric.name == name,
        CustomMetric.created_by == owner_id,
    )
    return session.exec(statement).first()


def list_custom_metrics(
    *,
    session: Session,
    owner_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[CustomMetric], int]:
    statement = (
        select(CustomMetric)
        .where(CustomMetric.created_by == owner_id)
        .order_by(col(CustomMetric.created_at).desc())
    )
    count_statement = (
        select(func.count())
        .select_from(CustomMetric)
        .where(CustomMetric.created_by == owner_id)
    )
    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_custom_metric(
    *, session: Session, db_metric: CustomMetric, metric_in: CustomMetricUpdate
) -> CustomMetric:
    update_data = metric_in.model_dump(exclude_unset=True)
    db_metric.sqlmodel_update(update_data)
    session.add(db_metric)
    session.commit()
    session.refresh(db_metric)
    return db_metric


def delete_custom_metric(*, session: Session, db_metric: CustomMetric) -> None:
    session.delete(db_metric)
    session.commit()
