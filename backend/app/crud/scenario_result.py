import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import ScenarioResult, ScenarioResultCreate, ScenarioResultUpdate


def create_scenario_result(
    *, session: Session, result_in: ScenarioResultCreate
) -> ScenarioResult:
    db_obj = ScenarioResult.model_validate(result_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_scenario_result(
    *, session: Session, result_id: uuid.UUID
) -> ScenarioResult | None:
    return session.get(ScenarioResult, result_id)


def list_scenario_results(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    run_id: uuid.UUID | None = None,
    scenario_id: uuid.UUID | None = None,
) -> tuple[list[ScenarioResult], int]:
    statement = select(ScenarioResult)
    count_statement = select(func.count()).select_from(ScenarioResult)

    if run_id is not None:
        statement = statement.where(ScenarioResult.run_id == run_id)
        count_statement = count_statement.where(ScenarioResult.run_id == run_id)
    if scenario_id is not None:
        statement = statement.where(ScenarioResult.scenario_id == scenario_id)
        count_statement = count_statement.where(
            ScenarioResult.scenario_id == scenario_id
        )

    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_scenario_result(
    *,
    session: Session,
    db_result: ScenarioResult,
    result_in: ScenarioResultUpdate,
) -> ScenarioResult:
    update_data = result_in.model_dump(exclude_unset=True)
    # Pydantic models → JSON-safe dicts for JSONB columns (datetime → ISO string)
    if "transcript" in update_data and result_in.transcript is not None:
        update_data["transcript"] = [
            t.model_dump(mode="json") for t in result_in.transcript
        ]
    if "verdict" in update_data and result_in.verdict is not None:
        update_data["verdict"] = result_in.verdict.model_dump(mode="json")
    db_result.sqlmodel_update(update_data)
    session.add(db_result)
    session.commit()
    session.refresh(db_result)
    return db_result


def delete_scenario_result(*, session: Session, db_result: ScenarioResult) -> None:
    session.delete(db_result)
    session.commit()
