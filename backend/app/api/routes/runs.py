import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

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

router = APIRouter(
    prefix="/runs", tags=["runs"], dependencies=[Depends(get_current_user)]
)


@router.post("/", response_model=RunPublic)
def create_run(session: SessionDep, run_in: RunCreate) -> Run:
    return crud.create_run(session=session, run_in=run_in)


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
