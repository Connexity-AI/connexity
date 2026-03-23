import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Message,
    ScenarioSet,
    ScenarioSetCreate,
    ScenarioSetMembersUpdate,
    ScenarioSetPublic,
    ScenarioSetsPublic,
    ScenarioSetUpdate,
    ScenariosPublic,
)

router = APIRouter(
    prefix="/scenario-sets",
    tags=["scenario-sets"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=ScenarioSetPublic)
def create_scenario_set(
    session: SessionDep, scenario_set_in: ScenarioSetCreate
) -> ScenarioSet:
    return crud.create_scenario_set(session=session, scenario_set_in=scenario_set_in)


@router.get("/", response_model=ScenarioSetsPublic)
def list_scenario_sets(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> ScenarioSetsPublic:
    items, count = crud.list_scenario_sets(session=session, skip=skip, limit=limit)
    return ScenarioSetsPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/{scenario_set_id}", response_model=ScenarioSetPublic)
def get_scenario_set(session: SessionDep, scenario_set_id: uuid.UUID) -> ScenarioSet:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    return scenario_set


@router.patch("/{scenario_set_id}", response_model=ScenarioSetPublic)
def update_scenario_set(
    session: SessionDep,
    scenario_set_id: uuid.UUID,
    scenario_set_in: ScenarioSetUpdate,
) -> ScenarioSet:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    return crud.update_scenario_set(
        session=session,
        db_scenario_set=scenario_set,
        scenario_set_in=scenario_set_in,
    )


@router.delete("/{scenario_set_id}", response_model=Message)
def delete_scenario_set(session: SessionDep, scenario_set_id: uuid.UUID) -> Message:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    crud.delete_scenario_set(session=session, db_scenario_set=scenario_set)
    return Message(message="Scenario set deleted successfully")


# ── Member management ─────────────────────────────────────────────────


@router.get("/{scenario_set_id}/scenarios", response_model=ScenariosPublic)
def list_scenarios_in_set(
    session: SessionDep, scenario_set_id: uuid.UUID
) -> ScenariosPublic:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    scenarios = crud.list_scenarios_in_set(
        session=session, scenario_set_id=scenario_set_id
    )
    return ScenariosPublic(data=scenarios, count=len(scenarios))  # type: ignore[arg-type]


@router.post("/{scenario_set_id}/scenarios", response_model=Message)
def add_scenarios_to_set(
    session: SessionDep,
    scenario_set_id: uuid.UUID,
    body: ScenarioSetMembersUpdate,
) -> Message:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    for scenario_id in body.scenario_ids:
        crud.add_scenario_to_set(
            session=session,
            scenario_set_id=scenario_set_id,
            scenario_id=scenario_id,
        )
    return Message(message="Scenarios added to set")


@router.put("/{scenario_set_id}/scenarios", response_model=Message)
def replace_scenarios_in_set(
    session: SessionDep,
    scenario_set_id: uuid.UUID,
    body: ScenarioSetMembersUpdate,
) -> Message:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    crud.replace_scenarios_in_set(
        session=session,
        scenario_set_id=scenario_set_id,
        scenario_ids=body.scenario_ids,
    )
    return Message(message="Scenarios replaced in set")


@router.delete("/{scenario_set_id}/scenarios/{scenario_id}", response_model=Message)
def remove_scenario_from_set(
    session: SessionDep,
    scenario_set_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> Message:
    scenario_set = crud.get_scenario_set(
        session=session, scenario_set_id=scenario_set_id
    )
    if not scenario_set:
        raise HTTPException(status_code=404, detail="Scenario set not found")
    crud.remove_scenario_from_set(
        session=session,
        scenario_set_id=scenario_set_id,
        scenario_id=scenario_id,
    )
    return Message(message="Scenario removed from set")
