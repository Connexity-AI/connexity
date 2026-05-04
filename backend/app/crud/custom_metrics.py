import uuid
from datetime import UTC, datetime

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
    """Create a new metric. ``owner_id`` is recorded on ``created_by`` for
    audit purposes only — metrics are globally readable and editable by any
    authenticated user.
    """
    db_obj = CustomMetric.model_validate(
        {**metric_in.model_dump(), "created_by": owner_id}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_custom_metric(*, session: Session, metric_id: uuid.UUID) -> CustomMetric | None:
    metric = session.get(CustomMetric, metric_id)
    if metric is None or metric.deleted_at is not None:
        return None
    return metric


def get_custom_metric_by_name(
    *, session: Session, name: str, include_deleted: bool = False
) -> CustomMetric | None:
    """Look up a metric by name.

    By default returns only the live row. With ``include_deleted=True``, falls
    back to the most-recently-deleted row when no live one exists — used by
    judge resolution so historical eval configs can still find a metric whose
    name has been soft-deleted.
    """
    statement = select(CustomMetric).where(CustomMetric.name == name)
    if not include_deleted:
        statement = statement.where(col(CustomMetric.deleted_at).is_(None))
    else:
        statement = statement.order_by(
            col(CustomMetric.deleted_at).desc().nulls_first()
        )
    return session.exec(statement).first()


def list_custom_metrics(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = False,
) -> tuple[list[CustomMetric], int]:
    """List metrics that are not soft-deleted.

    When ``only_active`` is True, also exclude metrics flagged ``is_draft``.
    Predefined rows are returned first (so the UI lists built-ins above
    user-created ones), then by creation time ascending within each group.
    """
    base_filters = [CustomMetric.deleted_at.is_(None)]  # type: ignore[union-attr]
    if only_active:
        base_filters.append(CustomMetric.is_draft.is_(False))  # type: ignore[union-attr]

    statement = (
        select(CustomMetric)
        .where(*base_filters)
        .order_by(
            col(CustomMetric.is_predefined).desc(),
            col(CustomMetric.created_at).asc(),
        )
    )
    count_statement = (
        select(func.count()).select_from(CustomMetric).where(*base_filters)
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
    """Soft-delete: stamp ``deleted_at`` so historical eval configs that
    reference the metric by name can still resolve it, while live listings
    and the partial unique index on ``name`` exclude it.
    """
    db_metric.deleted_at = datetime.now(UTC)
    session.add(db_metric)
    session.commit()
