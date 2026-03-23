import uuid

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import (
    Difficulty,
    Scenario,
    ScenarioCreate,
    ScenarioStatus,
    ScenarioUpdate,
)


def create_scenario(*, session: Session, scenario_in: ScenarioCreate) -> Scenario:
    db_obj = Scenario.model_validate(scenario_in.model_dump())
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_scenario(*, session: Session, scenario_id: uuid.UUID) -> Scenario | None:
    return session.get(Scenario, scenario_id)


def list_scenarios(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: ScenarioStatus | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[Scenario], int]:
    statement = select(Scenario)
    count_statement = select(func.count()).select_from(Scenario)

    if tag is not None:
        statement = statement.where(col(Scenario.tags).any(tag))
        count_statement = count_statement.where(col(Scenario.tags).any(tag))
    if difficulty is not None:
        statement = statement.where(Scenario.difficulty == difficulty)
        count_statement = count_statement.where(Scenario.difficulty == difficulty)
    if status is not None:
        statement = statement.where(Scenario.status == status)
        count_statement = count_statement.where(Scenario.status == status)
    if search is not None:
        pattern = f"%{search}%"
        search_filter = col(Scenario.name).ilike(pattern) | col(
            Scenario.description
        ).ilike(pattern)
        statement = statement.where(search_filter)
        count_statement = count_statement.where(search_filter)

    allowed_sort_fields = {"created_at", "updated_at", "name", "difficulty", "status"}
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"
    sort_column = getattr(Scenario, sort_by)
    order = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    statement = statement.order_by(order)

    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_scenario(
    *, session: Session, db_scenario: Scenario, scenario_in: ScenarioUpdate
) -> Scenario:
    update_data = scenario_in.model_dump(exclude_unset=True)
    db_scenario.sqlmodel_update(update_data)
    session.add(db_scenario)
    session.commit()
    session.refresh(db_scenario)
    return db_scenario


def delete_scenario(*, session: Session, db_scenario: Scenario) -> None:
    session.delete(db_scenario)
    session.commit()
