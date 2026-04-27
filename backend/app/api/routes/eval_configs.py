import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import Message
from app.models.eval_config import (
    EvalConfig,
    EvalConfigCreate,
    EvalConfigMembersPublic,
    EvalConfigMembersUpdate,
    EvalConfigPublic,
    EvalConfigsPublic,
    EvalConfigUpdate,
)
from app.models.schemas import RunConfig


def _to_public(
    session: SessionDep,
    eval_config: EvalConfig,
    *,
    test_case_count: int | None = None,
    sum_member_repetitions: int | None = None,
    total_runs: int | None = None,
) -> EvalConfigPublic:
    """Convert an EvalConfig ORM object to EvalConfigPublic with counts."""
    count = (
        test_case_count
        if test_case_count is not None
        else crud.count_test_cases_in_config(
            session=session, eval_config_id=eval_config.id
        )
    )
    sum_rep = (
        sum_member_repetitions
        if sum_member_repetitions is not None
        else crud.sum_member_repetitions_in_config(
            session=session, eval_config_id=eval_config.id
        )
    )
    runs_count = (
        total_runs
        if total_runs is not None
        else crud.count_runs_for_eval_config(
            session=session, eval_config_id=eval_config.id
        )
    )
    effective = sum_rep
    parsed_config = (
        RunConfig.model_validate(eval_config.config) if eval_config.config else None
    )
    return EvalConfigPublic.model_validate(
        eval_config,
        update={
            "test_case_count": count,
            "effective_test_case_count": effective,
            "total_runs": runs_count,
            "config": parsed_config,
        },
    )


router = APIRouter(
    prefix="/eval-configs",
    tags=["eval-configs"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=EvalConfigPublic)
def create_eval_config(
    session: SessionDep, eval_config_in: EvalConfigCreate
) -> EvalConfigPublic:
    try:
        eval_config = crud.create_eval_config(
            session=session, eval_config_in=eval_config_in
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(session, eval_config)


@router.get("/", response_model=EvalConfigsPublic)
def list_eval_configs(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    agent_id: uuid.UUID | None = None,
) -> EvalConfigsPublic:
    items, count = crud.list_eval_configs(
        session=session, skip=skip, limit=limit, agent_id=agent_id
    )
    ids = [s.id for s in items]
    counts = crud.count_test_cases_in_configs(session=session, eval_config_ids=ids)
    sum_reps = crud.sum_member_repetitions_in_configs(
        session=session, eval_config_ids=ids
    )
    total_runs_map = crud.count_runs_by_eval_config_ids(
        session=session, eval_config_ids=ids
    )
    public_items = [
        _to_public(
            session,
            item,
            test_case_count=counts.get(item.id, 0),
            sum_member_repetitions=sum_reps.get(item.id, 0),
            total_runs=total_runs_map.get(item.id, 0),
        )
        for item in items
    ]
    return EvalConfigsPublic(data=public_items, count=count)


@router.get("/{eval_config_id}", response_model=EvalConfigPublic)
def get_eval_config(session: SessionDep, eval_config_id: uuid.UUID) -> EvalConfigPublic:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    return _to_public(session, eval_config)


@router.patch("/{eval_config_id}", response_model=EvalConfigPublic)
def update_eval_config(
    session: SessionDep,
    eval_config_id: uuid.UUID,
    eval_config_in: EvalConfigUpdate,
) -> EvalConfigPublic:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    updated = crud.update_eval_config(
        session=session,
        db_eval_config=eval_config,
        eval_config_in=eval_config_in,
    )
    return _to_public(session, updated)


@router.delete("/{eval_config_id}", response_model=Message)
def delete_eval_config(session: SessionDep, eval_config_id: uuid.UUID) -> Message:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    crud.delete_eval_config(session=session, db_eval_config=eval_config)
    return Message(message="Eval config deleted successfully")


# ── Member management ─────────────────────────────────────────────────


@router.get("/{eval_config_id}/test-cases", response_model=EvalConfigMembersPublic)
def list_test_cases_in_config(
    session: SessionDep,
    eval_config_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> EvalConfigMembersPublic:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    members, count = crud.list_test_cases_in_config(
        session=session, eval_config_id=eval_config_id, skip=skip, limit=limit
    )
    return EvalConfigMembersPublic(data=members, count=count)


@router.post("/{eval_config_id}/test-cases", response_model=EvalConfigPublic)
def add_test_cases_to_config(
    session: SessionDep,
    eval_config_id: uuid.UUID,
    body: EvalConfigMembersUpdate,
) -> EvalConfigPublic:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    try:
        updated = crud.add_test_cases_to_config(
            session=session,
            db_eval_config=eval_config,
            members=body.members,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(session, updated)


@router.put("/{eval_config_id}/test-cases", response_model=EvalConfigPublic)
def replace_test_cases_in_config(
    session: SessionDep,
    eval_config_id: uuid.UUID,
    body: EvalConfigMembersUpdate,
) -> EvalConfigPublic:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    try:
        updated = crud.replace_test_cases_in_config(
            session=session,
            db_eval_config=eval_config,
            members=body.members,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(session, updated)


@router.delete(
    "/{eval_config_id}/test-cases/{test_case_id}", response_model=EvalConfigPublic
)
def remove_test_case_from_config(
    session: SessionDep,
    eval_config_id: uuid.UUID,
    test_case_id: uuid.UUID,
) -> EvalConfigPublic:
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    if not eval_config:
        raise HTTPException(status_code=404, detail="Eval config not found")
    updated = crud.remove_test_case_from_config(
        session=session,
        db_eval_config=eval_config,
        test_case_id=test_case_id,
    )
    return _to_public(session, updated)
