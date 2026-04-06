import uuid

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import (
    Scenario,
    ScenarioSet,
    ScenarioSetCreate,
    ScenarioSetMember,
    ScenarioSetMemberEntry,
    ScenarioSetMemberPublic,
    ScenarioSetUpdate,
)
from app.models.enums import ScenarioStatus
from app.models.schemas import ScenarioExecution


def validate_scenario_ids(
    *, session: Session, scenario_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Return any scenario IDs that do not exist in the database."""
    if not scenario_ids:
        return []
    existing_ids = set(
        session.exec(
            select(Scenario.id).where(col(Scenario.id).in_(scenario_ids))
        ).all()
    )
    return [sid for sid in scenario_ids if sid not in existing_ids]


def create_scenario_set(
    *, session: Session, scenario_set_in: ScenarioSetCreate
) -> ScenarioSet:
    create_data = scenario_set_in.model_dump(exclude={"members"})
    db_obj = ScenarioSet.model_validate(create_data)
    session.add(db_obj)
    session.flush()  # generate id without committing — members use the same transaction

    if scenario_set_in.members:
        ids = [m.scenario_id for m in scenario_set_in.members]
        missing = validate_scenario_ids(session=session, scenario_ids=ids)
        if missing:
            raise ValueError(f"Scenarios not found: {missing}")
        for position, entry in enumerate(scenario_set_in.members):
            member = ScenarioSetMember(
                scenario_set_id=db_obj.id,
                scenario_id=entry.scenario_id,
                position=position,
                repetitions=entry.repetitions,
            )
            session.add(member)

    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_scenario_set(
    *, session: Session, scenario_set_id: uuid.UUID
) -> ScenarioSet | None:
    return session.get(ScenarioSet, scenario_set_id)


def list_scenario_sets(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[ScenarioSet], int]:
    count = session.exec(select(func.count()).select_from(ScenarioSet)).one()
    items = list(session.exec(select(ScenarioSet).offset(skip).limit(limit)).all())
    return items, count


def update_scenario_set(
    *,
    session: Session,
    db_scenario_set: ScenarioSet,
    scenario_set_in: ScenarioSetUpdate,
) -> ScenarioSet:
    update_data = scenario_set_in.model_dump(exclude_unset=True)
    db_scenario_set.sqlmodel_update(update_data)
    session.add(db_scenario_set)
    session.commit()
    session.refresh(db_scenario_set)
    return db_scenario_set


def delete_scenario_set(*, session: Session, db_scenario_set: ScenarioSet) -> None:
    session.delete(db_scenario_set)
    session.commit()


def _bump_version(*, session: Session, scenario_set: ScenarioSet) -> None:
    """Atomically increment the version at the SQL level to avoid race conditions."""
    session.execute(
        sa_update(ScenarioSet)
        .where(ScenarioSet.id == scenario_set.id)
        .values(version=ScenarioSet.version + 1)
    )


def _next_position(*, session: Session, scenario_set_id: uuid.UUID) -> int:
    """Return max(position) + 1 for existing members, or 0 if empty."""
    result = session.exec(
        select(func.max(ScenarioSetMember.position)).where(
            ScenarioSetMember.scenario_set_id == scenario_set_id
        )
    ).one()
    return (result + 1) if result is not None else 0


def add_scenarios_to_set(
    *,
    session: Session,
    db_scenario_set: ScenarioSet,
    members: list[ScenarioSetMemberEntry],
) -> ScenarioSet:
    scenario_ids = [m.scenario_id for m in members]
    if len(scenario_ids) != len(set(scenario_ids)):
        msg = "Duplicate scenario_id in request body"
        raise ValueError(msg)
    missing = validate_scenario_ids(session=session, scenario_ids=scenario_ids)
    if missing:
        raise ValueError(f"Scenarios not found: {missing}")
    existing = set(
        session.exec(
            select(ScenarioSetMember.scenario_id).where(
                ScenarioSetMember.scenario_set_id == db_scenario_set.id,
                col(ScenarioSetMember.scenario_id).in_(scenario_ids),
            )
        ).all()
    )
    if existing:
        raise ValueError(f"Scenarios already in set: {sorted(existing)}")
    next_pos = _next_position(session=session, scenario_set_id=db_scenario_set.id)
    for i, entry in enumerate(members):
        member = ScenarioSetMember(
            scenario_set_id=db_scenario_set.id,
            scenario_id=entry.scenario_id,
            position=next_pos + i,
            repetitions=entry.repetitions,
        )
        session.add(member)
    _bump_version(session=session, scenario_set=db_scenario_set)
    session.commit()
    session.refresh(db_scenario_set)
    return db_scenario_set


def remove_scenario_from_set(
    *,
    session: Session,
    db_scenario_set: ScenarioSet,
    scenario_id: uuid.UUID,
) -> ScenarioSet:
    member = session.exec(
        select(ScenarioSetMember).where(
            ScenarioSetMember.scenario_set_id == db_scenario_set.id,
            ScenarioSetMember.scenario_id == scenario_id,
        )
    ).first()
    if member:
        session.delete(member)
        _bump_version(session=session, scenario_set=db_scenario_set)
    session.commit()
    session.refresh(db_scenario_set)
    return db_scenario_set


def replace_scenarios_in_set(
    *,
    session: Session,
    db_scenario_set: ScenarioSet,
    members: list[ScenarioSetMemberEntry],
) -> ScenarioSet:
    scenario_ids = [m.scenario_id for m in members]
    missing = validate_scenario_ids(session=session, scenario_ids=scenario_ids)
    if missing:
        raise ValueError(f"Scenarios not found: {missing}")
    # Delete existing members
    existing = session.exec(
        select(ScenarioSetMember).where(
            ScenarioSetMember.scenario_set_id == db_scenario_set.id
        )
    ).all()
    for member in existing:
        session.delete(member)
    session.flush()

    # Insert new members
    for position, entry in enumerate(members):
        member = ScenarioSetMember(
            scenario_set_id=db_scenario_set.id,
            scenario_id=entry.scenario_id,
            position=position,
            repetitions=entry.repetitions,
        )
        session.add(member)

    _bump_version(session=session, scenario_set=db_scenario_set)
    session.commit()
    session.refresh(db_scenario_set)
    return db_scenario_set


def count_scenarios_in_set(*, session: Session, scenario_set_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count()).where(ScenarioSetMember.scenario_set_id == scenario_set_id)
    ).one()


def sum_member_repetitions_in_set(
    *, session: Session, scenario_set_id: uuid.UUID
) -> int:
    """Sum of repetitions across all members (one set pass, before set_repetitions)."""
    total = session.exec(
        select(func.coalesce(func.sum(ScenarioSetMember.repetitions), 0)).where(
            ScenarioSetMember.scenario_set_id == scenario_set_id
        )
    ).one()
    return int(total)


def count_scenarios_in_sets(
    *, session: Session, scenario_set_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch scenario counts for multiple sets in a single query."""
    if not scenario_set_ids:
        return {}
    rows = session.exec(
        select(ScenarioSetMember.scenario_set_id, func.count())
        .where(col(ScenarioSetMember.scenario_set_id).in_(scenario_set_ids))
        .group_by(ScenarioSetMember.scenario_set_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def sum_member_repetitions_in_sets(
    *, session: Session, scenario_set_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch sum of member repetitions per set (one set pass, before set_repetitions)."""
    if not scenario_set_ids:
        return {}
    rows = session.exec(
        select(
            ScenarioSetMember.scenario_set_id,
            func.coalesce(func.sum(ScenarioSetMember.repetitions), 0),
        )
        .where(col(ScenarioSetMember.scenario_set_id).in_(scenario_set_ids))
        .group_by(ScenarioSetMember.scenario_set_id)
    ).all()
    result = {sid: 0 for sid in scenario_set_ids}
    for sid, total in rows:
        result[sid] = int(total)
    return result


def list_scenarios_in_set(
    *,
    session: Session,
    scenario_set_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[ScenarioSetMemberPublic], int]:
    count = session.exec(
        select(func.count())
        .select_from(ScenarioSetMember)
        .where(ScenarioSetMember.scenario_set_id == scenario_set_id)
    ).one()
    rows = list(
        session.exec(
            select(ScenarioSetMember)
            .where(ScenarioSetMember.scenario_set_id == scenario_set_id)
            .order_by(ScenarioSetMember.position)
            .offset(skip)
            .limit(limit)
        ).all()
    )
    public = [
        ScenarioSetMemberPublic(
            scenario_id=m.scenario_id,
            position=m.position,
            repetitions=m.repetitions,
        )
        for m in rows
    ]
    return public, count


def get_scenarios_for_set(
    *, session: Session, scenario_set_id: uuid.UUID
) -> list[ScenarioExecution]:
    """Get all active scenarios for a set, ordered by position, with member repetitions."""

    statement = (
        select(Scenario, ScenarioSetMember.repetitions, ScenarioSetMember.position)
        .join(ScenarioSetMember, Scenario.id == ScenarioSetMember.scenario_id)
        .where(
            ScenarioSetMember.scenario_set_id == scenario_set_id,
            Scenario.status == ScenarioStatus.ACTIVE,
        )
        .order_by(ScenarioSetMember.position)
    )
    rows = session.exec(statement).all()
    return [
        ScenarioExecution(scenario=row[0], repetitions=row[1], position=row[2])
        for row in rows
    ]
