import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Message,
    ScenarioResult,
    ScenarioResultCreate,
    ScenarioResultPublic,
    ScenarioResultsPublic,
    ScenarioResultUpdate,
)

router = APIRouter(
    prefix="/scenario-results",
    tags=["scenario-results"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=ScenarioResultPublic)
def create_scenario_result(
    session: SessionDep, result_in: ScenarioResultCreate
) -> ScenarioResult:
    return crud.create_scenario_result(session=session, result_in=result_in)


@router.get("/", response_model=ScenarioResultsPublic)
def list_scenario_results(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    run_id: uuid.UUID | None = None,
    scenario_id: uuid.UUID | None = None,
) -> ScenarioResultsPublic:
    items, count = crud.list_scenario_results(
        session=session,
        skip=skip,
        limit=limit,
        run_id=run_id,
        scenario_id=scenario_id,
    )
    return ScenarioResultsPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/{result_id}", response_model=ScenarioResultPublic)
def get_scenario_result(session: SessionDep, result_id: uuid.UUID) -> ScenarioResult:
    result = crud.get_scenario_result(session=session, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scenario result not found")
    return result


@router.patch("/{result_id}", response_model=ScenarioResultPublic)
def update_scenario_result(
    session: SessionDep,
    result_id: uuid.UUID,
    result_in: ScenarioResultUpdate,
) -> ScenarioResult:
    result = crud.get_scenario_result(session=session, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scenario result not found")
    return crud.update_scenario_result(
        session=session, db_result=result, result_in=result_in
    )


@router.delete("/{result_id}", response_model=Message)
def delete_scenario_result(session: SessionDep, result_id: uuid.UUID) -> Message:
    result = crud.get_scenario_result(session=session, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scenario result not found")
    crud.delete_scenario_result(session=session, db_result=result)
    return Message(message="Scenario result deleted successfully")
