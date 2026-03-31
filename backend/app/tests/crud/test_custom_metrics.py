import uuid

from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import CustomMetricCreate, CustomMetricUpdate, MetricTier, ScoreType
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
    owner = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert owner is not None
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


def test_get_custom_metric_by_name_and_owner(db: Session) -> None:
    owner = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert owner is not None
    name = f"by_name_{uuid.uuid4().hex[:10]}"
    crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    row = crud.get_custom_metric_by_name_and_owner(
        session=db, name=name, owner_id=owner.id
    )
    assert row is not None
    assert row.name == name
    assert (
        crud.get_custom_metric_by_name_and_owner(
            session=db, name=name, owner_id=uuid.uuid4()
        )
        is None
    )


def test_list_custom_metrics_owner_scoped(db: Session) -> None:
    owner_a = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    owner_b = create_random_user(db)
    assert owner_a is not None
    name_a = f"owner_a_{uuid.uuid4().hex[:10]}"
    name_b = f"owner_b_{uuid.uuid4().hex[:10]}"
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
    items_a, count_a = crud.list_custom_metrics(session=db, owner_id=owner_a.id)
    items_b, count_b = crud.list_custom_metrics(session=db, owner_id=owner_b.id)
    names_a = {m.name for m in items_a}
    names_b = {m.name for m in items_b}
    assert name_a in names_a
    assert name_b not in names_a
    assert name_b in names_b
    assert name_a not in names_b
    assert count_a >= 1
    assert count_b >= 1


def test_update_custom_metric(db: Session) -> None:
    owner = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert owner is not None
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


def test_delete_custom_metric(db: Session) -> None:
    owner = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert owner is not None
    name = f"delete_{uuid.uuid4().hex[:10]}"
    m = crud.create_custom_metric(
        session=db,
        metric_in=_sample_create(name=name),
        owner_id=owner.id,
    )
    crud.delete_custom_metric(session=db, db_metric=m)
    assert crud.get_custom_metric(session=db, metric_id=m.id) is None
