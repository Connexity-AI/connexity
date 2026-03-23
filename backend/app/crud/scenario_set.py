import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import (
    Scenario,
    ScenarioSet,
    ScenarioSetCreate,
    ScenarioSetMember,
    ScenarioSetUpdate,
)


def create_scenario_set(
    *, session: Session, scenario_set_in: ScenarioSetCreate
) -> ScenarioSet:
    create_data = scenario_set_in.model_dump(exclude={"scenario_ids"})
    db_obj = ScenarioSet.model_validate(create_data)
    session.add(db_obj)
    session.flush()  # generate id without committing — members use the same transaction

    if scenario_set_in.scenario_ids:
        for position, scenario_id in enumerate(scenario_set_in.scenario_ids):
            member = ScenarioSetMember(
                scenario_set_id=db_obj.id,
                scenario_id=scenario_id,
                position=position,
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


def _next_position(*, session: Session, scenario_set_id: uuid.UUID) -> int:
    """Return max(position) + 1 for existing members, or 0 if empty."""
    result = session.exec(
        select(func.max(ScenarioSetMember.position)).where(
            ScenarioSetMember.scenario_set_id == scenario_set_id
        )
    ).one()
    return (result + 1) if result is not None else 0


def add_scenario_to_set(
    *,
    session: Session,
    scenario_set_id: uuid.UUID,
    scenario_id: uuid.UUID,
    position: int | None = None,
) -> ScenarioSetMember:
    if position is None:
        position = _next_position(session=session, scenario_set_id=scenario_set_id)
    member = ScenarioSetMember(
        scenario_set_id=scenario_set_id,
        scenario_id=scenario_id,
        position=position,
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    return member


def remove_scenario_from_set(
    *, session: Session, scenario_set_id: uuid.UUID, scenario_id: uuid.UUID
) -> None:
    member = session.exec(
        select(ScenarioSetMember).where(
            ScenarioSetMember.scenario_set_id == scenario_set_id,
            ScenarioSetMember.scenario_id == scenario_id,
        )
    ).first()
    if member:
        session.delete(member)
        session.commit()


def replace_scenarios_in_set(
    *,
    session: Session,
    scenario_set_id: uuid.UUID,
    scenario_ids: list[uuid.UUID],
) -> list[ScenarioSetMember]:
    # Delete existing members
    existing = session.exec(
        select(ScenarioSetMember).where(
            ScenarioSetMember.scenario_set_id == scenario_set_id
        )
    ).all()
    for member in existing:
        session.delete(member)
    session.flush()

    # Insert new members
    new_members = []
    for position, scenario_id in enumerate(scenario_ids):
        member = ScenarioSetMember(
            scenario_set_id=scenario_set_id,
            scenario_id=scenario_id,
            position=position,
        )
        session.add(member)
        new_members.append(member)

    session.commit()
    for m in new_members:
        session.refresh(m)
    return new_members


def list_scenarios_in_set(
    *, session: Session, scenario_set_id: uuid.UUID
) -> list[Scenario]:
    statement = (
        select(Scenario)
        .join(ScenarioSetMember, Scenario.id == ScenarioSetMember.scenario_id)
        .where(ScenarioSetMember.scenario_set_id == scenario_set_id)
        .order_by(ScenarioSetMember.position)
    )
    return list(session.exec(statement).all())
