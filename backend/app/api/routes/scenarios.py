import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from litellm.exceptions import APIError

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Difficulty,
    Message,
    OnConflict,
    Scenario,
    ScenarioCreate,
    ScenarioImportItem,
    ScenarioImportResult,
    ScenarioPublic,
    ScenariosExport,
    ScenariosPublic,
    ScenarioStatus,
    ScenarioUpdate,
)
from app.services.scenario_generator.core import generate_scenarios
from app.services.scenario_generator.schemas import GenerateRequest, GenerateResult

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


@router.get("/export", response_model=ScenariosExport)
def export_scenarios(
    session: SessionDep,
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: ScenarioStatus | None = None,
) -> JSONResponse:
    items = crud.export_scenarios(
        session=session, tag=tag, difficulty=difficulty, status=status
    )
    export_data = ScenariosExport(
        exported_at=datetime.now(UTC),
        count=len(items),
        scenarios=items,  # type: ignore[arg-type]
    )
    return JSONResponse(
        content=export_data.model_dump(mode="json"),
        headers={"Content-Disposition": 'attachment; filename="scenarios-export.json"'},
    )


@router.post("/import", response_model=ScenarioImportResult)
def import_scenarios(
    session: SessionDep,
    scenarios_in: list[ScenarioImportItem],
    on_conflict: OnConflict = Query(default=OnConflict.SKIP),
) -> ScenarioImportResult:
    if not scenarios_in:
        raise HTTPException(status_code=400, detail="Empty scenario list")
    if len(scenarios_in) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 scenarios per import")
    return crud.bulk_import_scenarios(
        session=session, scenarios_in=scenarios_in, on_conflict=on_conflict
    )


@router.post("/generate", response_model=GenerateResult)
async def generate_scenarios_endpoint(
    session: SessionDep,
    request: GenerateRequest,
) -> GenerateResult:
    try:
        scenarios, model_used, latency_ms = await generate_scenarios(request)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}")

    persisted: list[ScenarioPublic] = []
    if request.persist:
        for sc in scenarios:
            db_obj = crud.create_scenario(session=session, scenario_in=sc)
            persisted.append(
                ScenarioPublic.model_validate(db_obj, from_attributes=True)
            )
    else:
        # Return unsaved scenarios with placeholder values for required fields
        for sc in scenarios:
            pub = ScenarioPublic(
                **sc.model_dump(),
                id=uuid.uuid4(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            persisted.append(pub)

    return GenerateResult(
        scenarios=persisted,
        count=len(persisted),
        model_used=model_used,
        generation_time_ms=latency_ms,
    )


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
