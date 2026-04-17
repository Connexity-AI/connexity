import uuid

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import TestCase
from app.models.enums import TestCaseStatus
from app.models.eval_config import (
    EvalConfig,
    EvalConfigCreate,
    EvalConfigMember,
    EvalConfigMemberEntry,
    EvalConfigMemberPublic,
    EvalConfigUpdate,
)
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


def create_eval_config(
    *, session: Session, eval_config_in: EvalConfigCreate
) -> EvalConfig:
    create_data = eval_config_in.model_dump(exclude={"members", "config"})
    db_obj = EvalConfig.model_validate(create_data)
    if eval_config_in.config is not None:
        db_obj.config = eval_config_in.config.model_dump()
    session.add(db_obj)
    session.flush()

    if eval_config_in.members:
        ids = [m.test_case_id for m in eval_config_in.members]
        missing = validate_test_case_ids(session=session, test_case_ids=ids)
        if missing:
            raise ValueError(f"Test cases not found: {missing}")
        for position, entry in enumerate(eval_config_in.members):
            member = EvalConfigMember(
                eval_config_id=db_obj.id,
                test_case_id=entry.test_case_id,
                position=position,
                repetitions=entry.repetitions,
            )
            session.add(member)

    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_eval_config(
    *, session: Session, eval_config_id: uuid.UUID
) -> EvalConfig | None:
    return session.get(EvalConfig, eval_config_id)


def list_eval_configs(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    agent_id: uuid.UUID | None = None,
) -> tuple[list[EvalConfig], int]:
    statement = select(EvalConfig)
    count_statement = select(func.count()).select_from(EvalConfig)

    if agent_id is not None:
        statement = statement.where(EvalConfig.agent_id == agent_id)
        count_statement = count_statement.where(EvalConfig.agent_id == agent_id)

    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_eval_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    eval_config_in: EvalConfigUpdate,
) -> EvalConfig:
    update_data = eval_config_in.model_dump(exclude_unset=True, exclude={"config"})
    db_eval_config.sqlmodel_update(update_data)
    if eval_config_in.config is not None:
        db_eval_config.config = eval_config_in.config.model_dump()
        _bump_version(session=session, eval_config=db_eval_config)
    session.add(db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def delete_eval_config(*, session: Session, db_eval_config: EvalConfig) -> None:
    session.delete(db_eval_config)
    session.commit()


def _bump_version(*, session: Session, eval_config: EvalConfig) -> None:
    """Atomically increment the version at the SQL level to avoid race conditions."""
    session.execute(
        sa_update(EvalConfig)
        .where(EvalConfig.id == eval_config.id)
        .values(version=EvalConfig.version + 1)
    )


def _next_position(*, session: Session, eval_config_id: uuid.UUID) -> int:
    """Return max(position) + 1 for existing members, or 0 if empty."""
    result = session.exec(
        select(func.max(EvalConfigMember.position)).where(
            EvalConfigMember.eval_config_id == eval_config_id
        )
    ).one()
    return (result + 1) if result is not None else 0


def add_test_cases_to_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    members: list[EvalConfigMemberEntry],
) -> EvalConfig:
    test_case_ids = [m.test_case_id for m in members]
    if len(test_case_ids) != len(set(test_case_ids)):
        msg = "Duplicate test_case_id in request body"
        raise ValueError(msg)
    missing = validate_test_case_ids(session=session, test_case_ids=test_case_ids)
    if missing:
        raise ValueError(f"Test cases not found: {missing}")
    existing = set(
        session.exec(
            select(EvalConfigMember.test_case_id).where(
                EvalConfigMember.eval_config_id == db_eval_config.id,
                col(EvalConfigMember.test_case_id).in_(test_case_ids),
            )
        ).all()
    )
    if existing:
        raise ValueError(f"Test cases already in config: {sorted(existing)}")
    next_pos = _next_position(session=session, eval_config_id=db_eval_config.id)
    for i, entry in enumerate(members):
        member = EvalConfigMember(
            eval_config_id=db_eval_config.id,
            test_case_id=entry.test_case_id,
            position=next_pos + i,
            repetitions=entry.repetitions,
        )
        session.add(member)
    _bump_version(session=session, eval_config=db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def remove_test_case_from_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    test_case_id: uuid.UUID,
) -> EvalConfig:
    member = session.exec(
        select(EvalConfigMember).where(
            EvalConfigMember.eval_config_id == db_eval_config.id,
            EvalConfigMember.test_case_id == test_case_id,
        )
    ).first()
    if member:
        session.delete(member)
        _bump_version(session=session, eval_config=db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def replace_test_cases_in_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    members: list[EvalConfigMemberEntry],
) -> EvalConfig:
    test_case_ids = [m.test_case_id for m in members]
    missing = validate_test_case_ids(session=session, test_case_ids=test_case_ids)
    if missing:
        raise ValueError(f"Test cases not found: {missing}")
    existing = session.exec(
        select(EvalConfigMember).where(
            EvalConfigMember.eval_config_id == db_eval_config.id
        )
    ).all()
    for member in existing:
        session.delete(member)
    session.flush()

    for position, entry in enumerate(members):
        member = EvalConfigMember(
            eval_config_id=db_eval_config.id,
            test_case_id=entry.test_case_id,
            position=position,
            repetitions=entry.repetitions,
        )
        session.add(member)

    _bump_version(session=session, eval_config=db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def count_test_cases_in_config(*, session: Session, eval_config_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count()).where(EvalConfigMember.eval_config_id == eval_config_id)
    ).one()


def sum_member_repetitions_in_config(
    *, session: Session, eval_config_id: uuid.UUID
) -> int:
    """Sum of per-test-case repetitions across all members — total expanded executions."""
    total = session.exec(
        select(func.coalesce(func.sum(EvalConfigMember.repetitions), 0)).where(
            EvalConfigMember.eval_config_id == eval_config_id
        )
    ).one()
    return int(total)


def count_test_cases_in_configs(
    *, session: Session, eval_config_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch test case counts for multiple configs in a single query."""
    if not eval_config_ids:
        return {}
    rows = session.exec(
        select(EvalConfigMember.eval_config_id, func.count())
        .where(col(EvalConfigMember.eval_config_id).in_(eval_config_ids))
        .group_by(EvalConfigMember.eval_config_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def sum_member_repetitions_in_configs(
    *, session: Session, eval_config_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch sum of per-test-case repetitions per config — total expanded executions."""
    if not eval_config_ids:
        return {}
    rows = session.exec(
        select(
            EvalConfigMember.eval_config_id,
            func.coalesce(func.sum(EvalConfigMember.repetitions), 0),
        )
        .where(col(EvalConfigMember.eval_config_id).in_(eval_config_ids))
        .group_by(EvalConfigMember.eval_config_id)
    ).all()
    result = {eid: 0 for eid in eval_config_ids}
    for eid, total in rows:
        result[eid] = int(total)
    return result


def list_test_cases_in_config(
    *,
    session: Session,
    eval_config_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[EvalConfigMemberPublic], int]:
    count = session.exec(
        select(func.count())
        .select_from(EvalConfigMember)
        .where(EvalConfigMember.eval_config_id == eval_config_id)
    ).one()
    rows = list(
        session.exec(
            select(EvalConfigMember)
            .where(EvalConfigMember.eval_config_id == eval_config_id)
            .order_by(EvalConfigMember.position)
            .offset(skip)
            .limit(limit)
        ).all()
    )
    public = [
        EvalConfigMemberPublic(
            test_case_id=m.test_case_id,
            position=m.position,
            repetitions=m.repetitions,
        )
        for m in rows
    ]
    return public, count


def get_test_cases_for_config(
    *, session: Session, eval_config_id: uuid.UUID
) -> list[TestCaseExecution]:
    """Get all active test cases for a config, ordered by position, with member repetitions."""

    statement = (
        select(TestCase, EvalConfigMember.repetitions, EvalConfigMember.position)
        .join(EvalConfigMember, TestCase.id == EvalConfigMember.test_case_id)
        .where(
            EvalConfigMember.eval_config_id == eval_config_id,
            TestCase.status == TestCaseStatus.ACTIVE,
        )
        .order_by(EvalConfigMember.position)
    )
    rows = session.exec(statement).all()
    return [
        TestCaseExecution(test_case=row[0], repetitions=row[1], position=row[2])
        for row in rows
    ]
