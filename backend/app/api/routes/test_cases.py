import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from litellm.exceptions import APIError

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Agent,
    Difficulty,
    Message,
    OnConflict,
    TestCase,
    TestCaseCreate,
    TestCaseImportItem,
    TestCaseImportResult,
    TestCasePublic,
    TestCasesExport,
    TestCasesPublic,
    TestCaseStatus,
    TestCaseUpdate,
)
from app.services.test_case_generator.core import generate_test_cases
from app.services.test_case_generator.schemas import GenerateRequest, GenerateResult

router = APIRouter(
    prefix="/test-cases", tags=["test-cases"], dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=TestCasePublic)
def create_test_case(session: SessionDep, test_case_in: TestCaseCreate) -> TestCase:
    try:
        return crud.create_test_case(session=session, test_case_in=test_case_in)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/", response_model=TestCasesPublic)
def list_test_cases(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: TestCaseStatus | None = None,
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
    agent_id: uuid.UUID | None = Query(
        default=None, description="Filter test cases bound to this agent"
    ),
) -> TestCasesPublic:
    items, count = crud.list_test_cases(
        session=session,
        skip=skip,
        limit=limit,
        tag=tag,
        difficulty=difficulty,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        agent_id=agent_id,
    )
    return TestCasesPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/export", response_model=TestCasesExport)
def export_test_cases(
    session: SessionDep,
    tag: str | None = None,
    difficulty: Difficulty | None = None,
    status: TestCaseStatus | None = None,
    agent_id: uuid.UUID | None = Query(
        default=None, description="Export only test cases bound to this agent"
    ),
) -> JSONResponse:
    items = crud.export_test_cases(
        session=session,
        tag=tag,
        difficulty=difficulty,
        status=status,
        agent_id=agent_id,
    )
    export_data = TestCasesExport(
        exported_at=datetime.now(UTC),
        count=len(items),
        test_cases=items,  # type: ignore[arg-type]
    )
    return JSONResponse(
        content=export_data.model_dump(mode="json"),
        headers={
            "Content-Disposition": 'attachment; filename="test-cases-export.json"'
        },
    )


@router.post("/import", response_model=TestCaseImportResult)
def import_test_cases(
    session: SessionDep,
    test_cases_in: list[TestCaseImportItem],
    on_conflict: OnConflict = Query(default=OnConflict.SKIP),
) -> TestCaseImportResult:
    if not test_cases_in:
        raise HTTPException(status_code=400, detail="Empty test case list")
    if len(test_cases_in) > 1000:
        raise HTTPException(
            status_code=400, detail="Maximum 1000 test cases per import"
        )
    return crud.bulk_import_test_cases(
        session=session, test_cases_in=test_cases_in, on_conflict=on_conflict
    )


@router.post("/generate", response_model=GenerateResult)
async def generate_test_cases_endpoint(
    session: SessionDep,
    request: GenerateRequest,
) -> GenerateResult:
    try:
        test_cases, model_used, latency_ms = await generate_test_cases(request)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="LLM returned invalid JSON"
        ) from exc
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}") from e
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Generation failed: {e}") from e

    if request.persist and request.agent_id is not None:
        agent = session.get(Agent, request.agent_id)
        if agent is None:
            raise HTTPException(
                status_code=404, detail=f"Agent not found: {request.agent_id}"
            )

    persisted: list[TestCasePublic] = []
    if request.persist:
        for tc in test_cases:
            payload = tc.model_dump()
            if request.agent_id is not None:
                payload["agent_id"] = request.agent_id
            try:
                db_obj = crud.create_test_case(
                    session=session, test_case_in=TestCaseCreate(**payload)
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            persisted.append(
                TestCasePublic.model_validate(db_obj, from_attributes=True)
            )
    else:
        for tc in test_cases:
            payload = tc.model_dump()
            payload.pop("agent_id", None)
            pub = TestCasePublic(
                **payload,
                id=uuid.uuid4(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                agent_id=request.agent_id,
            )
            persisted.append(pub)

    return GenerateResult(
        test_cases=persisted,
        count=len(persisted),
        model_used=model_used,
        generation_time_ms=latency_ms,
    )


@router.get("/{test_case_id}", response_model=TestCasePublic)
def get_test_case(session: SessionDep, test_case_id: uuid.UUID) -> TestCase:
    test_case = crud.get_test_case(session=session, test_case_id=test_case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return test_case


@router.patch("/{test_case_id}", response_model=TestCasePublic)
def update_test_case(
    session: SessionDep,
    test_case_id: uuid.UUID,
    test_case_in: TestCaseUpdate,
) -> TestCase:
    test_case = crud.get_test_case(session=session, test_case_id=test_case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    try:
        return crud.update_test_case(
            session=session, db_test_case=test_case, test_case_in=test_case_in
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{test_case_id}", response_model=Message)
def delete_test_case(session: SessionDep, test_case_id: uuid.UUID) -> Message:
    test_case = crud.get_test_case(session=session, test_case_id=test_case_id)
    if not test_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    crud.delete_test_case(session=session, db_test_case=test_case)
    return Message(message="Test case deleted successfully")
