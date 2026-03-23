import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Difficulty,
    Message,
    Scenario,
    ScenarioCreate,
    ScenarioPublic,
    ScenariosPublic,
    ScenarioStatus,
    ScenarioUpdate,
)

router = APIRouter(
    prefix="/scenarios", tags=["scenarios"], dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=ScenarioPublic)
def create_scenario(session: SessionDep, scenario_in: ScenarioCreate) -> Scenario:
    return crud.create_scenario(session=session, scenario_in=scenario_in)


@router.get("/", response_model=ScenariosPublic)
def list_scenarios(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: ScenarioStatus | None = None,
    search: str | None = Query(
        default=None, description="Case-insensitive text search on name and description"
    ),
    sort_by: str = Query(
        default="created_at",
        description="Sort field: created_at, updated_at, name, difficulty, status",
    ),
    sort_order: str = Query(
        default="desc", pattern="^(asc|desc)$", description="Sort direction"
    ),
) -> ScenariosPublic:
    items, count = crud.list_scenarios(
        session=session,
        skip=skip,
        limit=limit,
        tag=tag,
        difficulty=difficulty,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ScenariosPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/{scenario_id}", response_model=ScenarioPublic)
def get_scenario(session: SessionDep, scenario_id: uuid.UUID) -> Scenario:
    scenario = crud.get_scenario(session=session, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.patch("/{scenario_id}", response_model=ScenarioPublic)
def update_scenario(
    session: SessionDep,
    scenario_id: uuid.UUID,
    scenario_in: ScenarioUpdate,
) -> Scenario:
    scenario = crud.get_scenario(session=session, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return crud.update_scenario(
        session=session, db_scenario=scenario, scenario_in=scenario_in
    )


@router.delete("/{scenario_id}", response_model=Message)
def delete_scenario(session: SessionDep, scenario_id: uuid.UUID) -> Message:
    scenario = crud.get_scenario(session=session, scenario_id=scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    crud.delete_scenario(session=session, db_scenario=scenario)
    return Message(message="Scenario deleted successfully")
