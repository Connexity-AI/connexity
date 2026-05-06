import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    CustomMetric,
    CustomMetricCreate,
    CustomMetricUpdate,
    MetricTier,
    ScoreType,
)
from app.tests.utils.user import create_random_user


def _sample_create(*, name: str) -> CustomMetricCreate:
    return CustomMetricCreate(
        name=name,
        display_name="Display",
        description="Measures widget quality.",
        tier=MetricTier.PROCESS,
        default_weight=0.2,
        score_type=ScoreType.SCORED,
        rubric="Measures: widget quality.\n\n5: Perfect.\n   Example: User asked; agent delivered.",
        include_in_defaults=False,
    )


def test_create_and_get_custom_metric(db: Session) -> None:
    owner = create_random_user(db)
    name = f"crud_metric_{uuid.uuid4().hex[:10]}"
    created = crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    assert created.id is not None
    assert created.name == name
    fetched = crud.get_custom_metric(session=db, metric_id=created.id)
    assert fetched is not None
    assert fetched.name == name


def test_get_custom_metric_by_name(db: Session) -> None:
    owner = create_random_user(db)
    name = f"by_name_{uuid.uuid4().hex[:10]}"
    crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    row = crud.get_custom_metric_by_name(session=db, name=name)
    assert row is not None
    assert row.name == name
    assert (
        crud.get_custom_metric_by_name(
            session=db, name=f"missing_{uuid.uuid4().hex[:10]}"
        )
        is None
    )


def test_list_custom_metrics_is_global(db: Session) -> None:
    """Metrics are global: listing returns rows regardless of who created them."""
    owner_a = create_random_user(db)
    owner_b = create_random_user(db)
    name_a = f"global_a_{uuid.uuid4().hex[:10]}"
    name_b = f"global_b_{uuid.uuid4().hex[:10]}"
    crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name_a),
        owner_id=owner_a.id,
    )
    crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name_b),
        owner_id=owner_b.id,
    )
    items, count = crud.list_custom_metrics(session=db)
    names = {m.name for m in items}
    assert name_a in names
    assert name_b in names
    assert count >= 2


def test_update_custom_metric(db: Session) -> None:
    owner = create_random_user(db)
    name = f"update_{uuid.uuid4().hex[:10]}"
    m = crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    updated = crud.update_custom_metric(
        session=db,
        db_metric=m,
        metric_in=CustomMetricUpdate(display_name="New Title"),
    )
    assert updated.display_name == "New Title"
    assert updated.name == name


def test_delete_custom_metric_is_soft(db: Session) -> None:
    owner = create_random_user(db)
    name = f"delete_{uuid.uuid4().hex[:10]}"
    m = crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    metric_id = m.id
    crud.delete_custom_metric(session=db, db_metric=m)

    # CRUD getters and listings hide soft-deleted rows.
    assert crud.get_custom_metric(session=db, metric_id=metric_id) is None
    assert crud.get_custom_metric_by_name(session=db, name=name) is None
    items, _ = crud.list_custom_metrics(session=db)
    assert all(item.id != metric_id for item in items)

    # The row is still physically present with a non-null deleted_at.
    raw = db.get(CustomMetric, metric_id)
    assert raw is not None
    assert raw.deleted_at is not None


def test_create_after_soft_delete_reuses_name(db: Session) -> None:
    owner = create_random_user(db)
    name = f"reuse_{uuid.uuid4().hex[:10]}"

    first = crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    crud.delete_custom_metric(session=db, db_metric=first)

    second = crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    assert second.id != first.id
    assert second.name == name
