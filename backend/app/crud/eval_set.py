import uuid

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import (
    EvalSet,
    EvalSetCreate,
    EvalSetMember,
    EvalSetMemberEntry,
    EvalSetMemberPublic,
    EvalSetUpdate,
    TestCase,
)
from app.models.enums import TestCaseStatus
from app.models.schemas import TestCaseExecution


def validate_test_case_ids(
    *, session: Session, test_case_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Return any test case IDs that do not exist in the database."""
    if not test_case_ids:
        return []
    existing_ids = set(
        session.exec(
            select(TestCase.id).where(col(TestCase.id).in_(test_case_ids))
        ).all()
    )
    return [tid for tid in test_case_ids if tid not in existing_ids]


def create_eval_set(*, session: Session, eval_set_in: EvalSetCreate) -> EvalSet:
    create_data = eval_set_in.model_dump(exclude={"members"})
    db_obj = EvalSet.model_validate(create_data)
    session.add(db_obj)
    session.flush()

    if eval_set_in.members:
        ids = [m.test_case_id for m in eval_set_in.members]
        missing = validate_test_case_ids(session=session, test_case_ids=ids)
        if missing:
            raise ValueError(f"Test cases not found: {missing}")
        for position, entry in enumerate(eval_set_in.members):
            member = EvalSetMember(
                eval_set_id=db_obj.id,
                test_case_id=entry.test_case_id,
                position=position,
                repetitions=entry.repetitions,
            )
            session.add(member)

    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_eval_set(*, session: Session, eval_set_id: uuid.UUID) -> EvalSet | None:
    return session.get(EvalSet, eval_set_id)


def list_eval_sets(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[EvalSet], int]:
    count = session.exec(select(func.count()).select_from(EvalSet)).one()
    items = list(session.exec(select(EvalSet).offset(skip).limit(limit)).all())
    return items, count


def update_eval_set(
    *,
    session: Session,
    db_eval_set: EvalSet,
    eval_set_in: EvalSetUpdate,
) -> EvalSet:
    update_data = eval_set_in.model_dump(exclude_unset=True)
    db_eval_set.sqlmodel_update(update_data)
    session.add(db_eval_set)
    session.commit()
    session.refresh(db_eval_set)
    return db_eval_set


def delete_eval_set(*, session: Session, db_eval_set: EvalSet) -> None:
    session.delete(db_eval_set)
    session.commit()


def _bump_version(*, session: Session, eval_set: EvalSet) -> None:
    """Atomically increment the version at the SQL level to avoid race conditions."""
    session.execute(
        sa_update(EvalSet)
        .where(EvalSet.id == eval_set.id)
        .values(version=EvalSet.version + 1)
    )


def _next_position(*, session: Session, eval_set_id: uuid.UUID) -> int:
    """Return max(position) + 1 for existing members, or 0 if empty."""
    result = session.exec(
        select(func.max(EvalSetMember.position)).where(
            EvalSetMember.eval_set_id == eval_set_id
        )
    ).one()
    return (result + 1) if result is not None else 0


def add_test_cases_to_set(
    *,
    session: Session,
    db_eval_set: EvalSet,
    members: list[EvalSetMemberEntry],
) -> EvalSet:
    test_case_ids = [m.test_case_id for m in members]
    if len(test_case_ids) != len(set(test_case_ids)):
        msg = "Duplicate test_case_id in request body"
        raise ValueError(msg)
    missing = validate_test_case_ids(session=session, test_case_ids=test_case_ids)
    if missing:
        raise ValueError(f"Test cases not found: {missing}")
    existing = set(
        session.exec(
            select(EvalSetMember.test_case_id).where(
                EvalSetMember.eval_set_id == db_eval_set.id,
                col(EvalSetMember.test_case_id).in_(test_case_ids),
            )
        ).all()
    )
    if existing:
        raise ValueError(f"Test cases already in set: {sorted(existing)}")
    next_pos = _next_position(session=session, eval_set_id=db_eval_set.id)
    for i, entry in enumerate(members):
        member = EvalSetMember(
            eval_set_id=db_eval_set.id,
            test_case_id=entry.test_case_id,
            position=next_pos + i,
            repetitions=entry.repetitions,
        )
        session.add(member)
    _bump_version(session=session, eval_set=db_eval_set)
    session.commit()
    session.refresh(db_eval_set)
    return db_eval_set


def remove_test_case_from_set(
    *,
    session: Session,
    db_eval_set: EvalSet,
    test_case_id: uuid.UUID,
) -> EvalSet:
    member = session.exec(
        select(EvalSetMember).where(
            EvalSetMember.eval_set_id == db_eval_set.id,
            EvalSetMember.test_case_id == test_case_id,
        )
    ).first()
    if member:
        session.delete(member)
        _bump_version(session=session, eval_set=db_eval_set)
    session.commit()
    session.refresh(db_eval_set)
    return db_eval_set


def replace_test_cases_in_set(
    *,
    session: Session,
    db_eval_set: EvalSet,
    members: list[EvalSetMemberEntry],
) -> EvalSet:
    test_case_ids = [m.test_case_id for m in members]
    missing = validate_test_case_ids(session=session, test_case_ids=test_case_ids)
    if missing:
        raise ValueError(f"Test cases not found: {missing}")
    existing = session.exec(
        select(EvalSetMember).where(EvalSetMember.eval_set_id == db_eval_set.id)
    ).all()
    for member in existing:
        session.delete(member)
    session.flush()

    for position, entry in enumerate(members):
        member = EvalSetMember(
            eval_set_id=db_eval_set.id,
            test_case_id=entry.test_case_id,
            position=position,
            repetitions=entry.repetitions,
        )
        session.add(member)

    _bump_version(session=session, eval_set=db_eval_set)
    session.commit()
    session.refresh(db_eval_set)
    return db_eval_set


def count_test_cases_in_set(*, session: Session, eval_set_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count()).where(EvalSetMember.eval_set_id == eval_set_id)
    ).one()


def sum_member_repetitions_in_set(*, session: Session, eval_set_id: uuid.UUID) -> int:
    """Sum of repetitions across all members (one set pass, before set_repetitions)."""
    total = session.exec(
        select(func.coalesce(func.sum(EvalSetMember.repetitions), 0)).where(
            EvalSetMember.eval_set_id == eval_set_id
        )
    ).one()
    return int(total)


def count_test_cases_in_sets(
    *, session: Session, eval_set_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch test case counts for multiple sets in a single query."""
    if not eval_set_ids:
        return {}
    rows = session.exec(
        select(EvalSetMember.eval_set_id, func.count())
        .where(col(EvalSetMember.eval_set_id).in_(eval_set_ids))
        .group_by(EvalSetMember.eval_set_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def sum_member_repetitions_in_sets(
    *, session: Session, eval_set_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch sum of member repetitions per set (one set pass, before set_repetitions)."""
    if not eval_set_ids:
        return {}
    rows = session.exec(
        select(
            EvalSetMember.eval_set_id,
            func.coalesce(func.sum(EvalSetMember.repetitions), 0),
        )
        .where(col(EvalSetMember.eval_set_id).in_(eval_set_ids))
        .group_by(EvalSetMember.eval_set_id)
    ).all()
    result = {eid: 0 for eid in eval_set_ids}
    for eid, total in rows:
        result[eid] = int(total)
    return result


def list_test_cases_in_set(
    *,
    session: Session,
    eval_set_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[EvalSetMemberPublic], int]:
    count = session.exec(
        select(func.count())
        .select_from(EvalSetMember)
        .where(EvalSetMember.eval_set_id == eval_set_id)
    ).one()
    rows = list(
        session.exec(
            select(EvalSetMember)
            .where(EvalSetMember.eval_set_id == eval_set_id)
            .order_by(EvalSetMember.position)
            .offset(skip)
            .limit(limit)
        ).all()
    )
    public = [
        EvalSetMemberPublic(
            test_case_id=m.test_case_id,
            position=m.position,
            repetitions=m.repetitions,
        )
        for m in rows
    ]
    return public, count


def get_test_cases_for_set(
    *, session: Session, eval_set_id: uuid.UUID
) -> list[TestCaseExecution]:
    """Get all active test cases for a set, ordered by position, with member repetitions."""

    statement = (
        select(TestCase, EvalSetMember.repetitions, EvalSetMember.position)
        .join(EvalSetMember, TestCase.id == EvalSetMember.test_case_id)
        .where(
            EvalSetMember.eval_set_id == eval_set_id,
            TestCase.status == TestCaseStatus.ACTIVE,
        )
        .order_by(EvalSetMember.position)
    )
    rows = session.exec(statement).all()
    return [
        TestCaseExecution(test_case=row[0], repetitions=row[1], position=row[2])
        for row in rows
    ]
