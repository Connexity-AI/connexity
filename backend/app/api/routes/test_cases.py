import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from litellm.exceptions import APIError
from sqlmodel import Session

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.crud import agent_version as agent_version_crud
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
from app.services.test_case_generator.agent import (
    AgentMode,
    TestCaseAgent,
    TestCaseAgentContextError,
    TestCaseAgentInput,
    TestCaseAgentRequest,
    TestCaseAgentResult,
    build_agent_context,
)
from app.services.test_case_generator.core import generate_test_cases
from app.services.test_case_generator.schemas import (
    GenerateRequest,
    GenerateResult,
    tool_definitions_from_agent_tools,
)

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


def _resolve_generate_request(
    *, session: Session, request: GenerateRequest
) -> GenerateRequest:
    """Fill agent_prompt/tools from AgentVersion when agent_id is set."""
    if request.agent_id is None:
        ap = request.agent_prompt
        if ap is None or not ap.strip():
            raise HTTPException(
                status_code=422,
                detail="Either agent_prompt or agent_id must be provided",
            )
        return request.model_copy(
            update={"agent_prompt": ap, "tools": list(request.tools)}
        )

    agent = session.get(Agent, request.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent not found: {request.agent_id}"
        )

    version_num = (
        request.agent_version if request.agent_version is not None else agent.version
    )
    version = agent_version_crud.get_version(
        session=session, agent_id=agent.id, version=version_num
    )
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent version {version_num} not found for agent {agent.id}",
        )

    prompt_in = request.agent_prompt
    if prompt_in is None or not str(prompt_in).strip():
        effective_prompt = version.system_prompt or ""
    else:
        effective_prompt = prompt_in

    tools_in = list(request.tools)
    if not tools_in:
        effective_tools = tool_definitions_from_agent_tools(version.tools)
    else:
        effective_tools = tools_in

    return request.model_copy(
        update={"agent_prompt": effective_prompt, "tools": effective_tools}
    )


@router.post("/generate", response_model=GenerateResult)
async def generate_test_cases_endpoint(
    session: SessionDep,
    request: GenerateRequest,
) -> GenerateResult:
    gen_request = _resolve_generate_request(session=session, request=request)
    try:
        test_cases, model_used, latency_ms = await generate_test_cases(gen_request)
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


@router.post("/ai", response_model=TestCaseAgentResult)
async def run_test_case_ai_agent(
    session: SessionDep,
    request: TestCaseAgentRequest,
) -> TestCaseAgentResult:
    """Single-turn tool-calling agent: create, from_transcript, or edit test cases."""
    try:
        ctx = build_agent_context(session=session, request=request)
    except TestCaseAgentContextError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    agent = TestCaseAgent(
        TestCaseAgentInput(
            mode=request.mode,
            user_message=request.user_message,
            context=ctx,
            llm_provider=request.provider,
            llm_model=request.model,
            temperature=request.temperature,
        )
    )
    try:
        out = await agent.run()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent failed: {exc}") from exc

    assert request.persist is not None

    if request.mode == AgentMode.EDIT:
        target = ctx.target_test_case
        if target is None:
            raise HTTPException(status_code=500, detail="Missing target test case")
        if out.edited is None:
            raise HTTPException(
                status_code=502, detail="Agent returned no edit payload"
            )

        if request.persist:
            payload = out.edited.model_dump()
            payload["agent_id"] = request.agent_id
            try:
                updated = crud.update_test_case(
                    session=session,
                    db_test_case=target,
                    test_case_in=TestCaseUpdate(**payload),
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            edited_pub = TestCasePublic.model_validate(updated, from_attributes=True)
        else:
            payload = out.edited.model_dump()
            payload["agent_id"] = request.agent_id
            edited_pub = TestCasePublic(
                **payload,
                id=target.id,
                created_at=target.created_at,
                updated_at=target.updated_at,
            )

        return TestCaseAgentResult(
            mode=request.mode,
            created=[],
            edited=edited_pub,
            model_used=out.model_used,
            latency_ms=out.latency_ms,
            token_usage=out.token_usage,
            cost_usd=out.cost_usd,
        )

    created_public: list[TestCasePublic] = []
    for tc in out.created:
        payload = tc.model_dump()
        payload["agent_id"] = request.agent_id
        if request.persist:
            try:
                db_obj = crud.create_test_case(
                    session=session, test_case_in=TestCaseCreate(**payload)
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            created_public.append(
                TestCasePublic.model_validate(db_obj, from_attributes=True)
            )
        else:
            pub = TestCasePublic(
                **payload,
                id=uuid.uuid4(),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            created_public.append(pub)

    return TestCaseAgentResult(
        mode=request.mode,
        created=created_public,
        edited=None,
        model_used=out.model_used,
        latency_ms=out.latency_ms,
        token_usage=out.token_usage,
        cost_usd=out.cost_usd,
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
