import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.models import (
    Message,
    Run,
    RunCreate,
    RunPublic,
    RunsPublic,
    RunStatus,
    RunUpdate,
)
from app.models.comparison import (
    ImprovementSuggestions,
    RegressionThresholds,
    RunComparison,
    SuggestionsRequest,
)
from app.services.analysis import (
    compute_improvement_suggestions,
    compute_regression_analysis_with_prompts,
)
from app.services.comparison import compare_runs
from app.services.orchestrator import execute_run
from app.services.run_manager import run_manager

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}
router = APIRouter(
    prefix="/runs", tags=["runs"], dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=RunPublic)
async def create_run(
    session: SessionDep,
    current_user: CurrentUser,
    run_in: RunCreate,
    auto_execute: bool = Query(
        default=False, description="Immediately start execution"
    ),
) -> Run:
    agent = crud.get_agent(session=session, agent_id=run_in.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    try:
        run_in = crud.enrich_run_create_from_agent(
            session=session, run_in=run_in, agent=agent
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    run = crud.create_run(session=session, run_in=run_in, created_by=current_user.id)
    if auto_execute:
        asyncio.create_task(execute_run(run.id))
    return run


@router.get("/", response_model=RunsPublic)
def list_runs(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    agent_id: uuid.UUID | None = None,
    agent_version: int | None = Query(
        default=None, ge=1, description="Filter by agent config version at run creation"
    ),
    status: RunStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> RunsPublic:
    items, count = crud.list_runs(
        session=session,
        skip=skip,
        limit=limit,
        agent_id=agent_id,
        agent_version=agent_version,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    return RunsPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/compare", response_model=RunComparison)
async def compare_runs_endpoint(
    session: SessionDep,
    baseline_run_id: uuid.UUID = Query(description="UUID of the baseline run"),
    candidate_run_id: uuid.UUID = Query(description="UUID of the candidate run"),
    max_pass_rate_drop: float | None = Query(
        default=None, description="Override max pass-rate drop threshold (0.0 = strict)"
    ),
    max_avg_score_drop: float | None = Query(
        default=None, description="Override max avg score drop on 0-100 scale"
    ),
    max_latency_increase_pct: float | None = Query(
        default=None, description="Override max latency increase fraction (0.2 = 20%)"
    ),
    include_analysis: bool = Query(
        default=False,
        description="Include AI regression analysis (requires LLM call, adds latency)",
    ),
) -> RunComparison:
    baseline = crud.get_run(session=session, run_id=baseline_run_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline run not found")
    candidate = crud.get_run(session=session, run_id=candidate_run_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate run not found")

    if baseline.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Baseline run is not completed (status: {baseline.status})",
        )
    if candidate.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate run is not completed (status: {candidate.status})",
        )

    # Build thresholds only if any override is provided
    thresholds: RegressionThresholds | None = None
    overrides = {
        k: v
        for k, v in {
            "max_pass_rate_drop": max_pass_rate_drop,
            "max_avg_score_drop": max_avg_score_drop,
            "max_latency_increase_pct": max_latency_increase_pct,
        }.items()
        if v is not None
    }
    if overrides:
        thresholds = RegressionThresholds(**overrides)

    comparison = compare_runs(
        session=session, baseline=baseline, candidate=candidate, thresholds=thresholds
    )

    if include_analysis:
        analysis = await compute_regression_analysis_with_prompts(
            comparison=comparison,
            config_diff=comparison.config_diff,
            baseline_prompt=baseline.agent_system_prompt,
            candidate_prompt=candidate.agent_system_prompt,
        )
        comparison.regression_analysis = analysis

    return comparison


@router.post("/compare/suggestions", response_model=ImprovementSuggestions)
async def compare_suggestions_endpoint(
    session: SessionDep,
    body: SuggestionsRequest,
) -> ImprovementSuggestions:
    """Generate AI-powered improvement suggestions for a comparison.

    Requires a prior comparison with regression analysis. More expensive
    than the analysis — only called on-demand.
    """
    baseline = crud.get_run(session=session, run_id=body.baseline_run_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline run not found")
    candidate = crud.get_run(session=session, run_id=body.candidate_run_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate run not found")

    if baseline.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Baseline run is not completed (status: {baseline.status})",
        )
    if candidate.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate run is not completed (status: {candidate.status})",
        )

    # Compute the comparison and analysis first
    comparison = compare_runs(session=session, baseline=baseline, candidate=candidate)

    analysis = await compute_regression_analysis_with_prompts(
        comparison=comparison,
        config_diff=comparison.config_diff,
        baseline_prompt=baseline.agent_system_prompt,
        candidate_prompt=candidate.agent_system_prompt,
    )

    if analysis is None:
        return ImprovementSuggestions(
            suggestions=[],
            summary="No significant metric shifts detected — no suggestions needed.",
            model="n/a",
            cost_usd=None,
        )

    return await compute_improvement_suggestions(
        comparison=comparison,
        analysis=analysis,
        candidate_run=candidate,
    )


@router.get("/baseline", response_model=RunPublic)
def get_baseline_run(
    session: SessionDep,
    agent_id: uuid.UUID = Query(description="UUID of the agent"),
    eval_set_id: uuid.UUID = Query(description="UUID of the eval set"),
    agent_version: int | None = Query(
        default=None,
        ge=1,
        description="Only consider baselines for this agent config version",
    ),
) -> Run:
    """Resolve the current baseline run for an (agent, eval_set) pair."""
    run = crud.get_baseline_run(
        session=session,
        agent_id=agent_id,
        eval_set_id=eval_set_id,
        agent_version=agent_version,
    )
    if not run:
        raise HTTPException(
            status_code=404,
            detail="No baseline run found for this agent + eval set",
        )
    return run


@router.get("/{run_id}", response_model=RunPublic)
def get_run(session: SessionDep, run_id: uuid.UUID) -> Run:
    run = crud.get_run(session=session, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.patch("/{run_id}", response_model=RunPublic)
def update_run(
    session: SessionDep,
    run_id: uuid.UUID,
    run_in: RunUpdate,
) -> Run:
    run = crud.get_run(session=session, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    # If marking as baseline, validate + enforce before persisting
    if run_in.is_baseline is True:
        try:
            run = crud.set_baseline(session=session, db_run=run)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
    return crud.update_run(session=session, db_run=run, run_in=run_in)


@router.delete("/{run_id}", response_model=Message)
def delete_run(session: SessionDep, run_id: uuid.UUID) -> Message:
    run = crud.get_run(session=session, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    crud.delete_run(session=session, db_run=run)
    return Message(message="Run deleted successfully")


@router.post("/{run_id}/execute", response_model=RunPublic, status_code=202)
async def execute_run_endpoint(session: SessionDep, run_id: uuid.UUID) -> Run:
    run = crud.get_run(session=session, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in (RunStatus.PENDING, RunStatus.FAILED, RunStatus.CANCELLED):
        raise HTTPException(
            status_code=400, detail=f"Cannot execute run in status {run.status}"
        )

    asyncio.create_task(execute_run(run.id))
    return run


@router.post("/{run_id}/cancel", response_model=RunPublic)
def cancel_run_endpoint(session: SessionDep, run_id: uuid.UUID) -> Run:
    run = crud.get_run(session=session, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run_manager.is_active(run_id):
        run_manager.signal_cancel(run_id)
    elif run.status == RunStatus.RUNNING:
        run = crud.update_run(
            session=session,
            db_run=run,
            run_in=RunUpdate(
                status=RunStatus.CANCELLED, completed_at=datetime.now(UTC)
            ),
        )

    return run


@router.get("/{run_id}/stream")
async def stream_run(
    request: Request, session: SessionDep, run_id: uuid.UUID
) -> StreamingResponse:
    """SSE endpoint streaming real-time run progress events."""
    run = crud.get_run(session=session, run_id=run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        if not run_manager.is_active(run_id):
            snapshot = {
                "run_id": str(run_id),
                "status": run.status,
            }
            yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
            yield "event: stream_closed\ndata: {}\n\n"
            return

        try:
            async for event in run_manager.subscribe(run_id):
                if await request.is_disconnected():
                    break
                data_str = json.dumps(event.data)
                yield f"event: {event.event}\ndata: {data_str}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
