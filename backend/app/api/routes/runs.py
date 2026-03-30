import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Message,
    Run,
    RunCreate,
    RunPublic,
    RunsPublic,
    RunStatus,
    RunUpdate,
)
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
    run_in: RunCreate,
    auto_execute: bool = Query(
        default=False, description="Immediately start execution"
    ),
) -> Run:
    run = crud.create_run(session=session, run_in=run_in)
    if auto_execute:
        asyncio.create_task(execute_run(run.id))
    return run


@router.get("/", response_model=RunsPublic)
def list_runs(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    agent_id: uuid.UUID | None = None,
    status: RunStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> RunsPublic:
    items, count = crud.list_runs(
        session=session,
        skip=skip,
        limit=limit,
        agent_id=agent_id,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    return RunsPublic(data=items, count=count)  # type: ignore[arg-type]


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
