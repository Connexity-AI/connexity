import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    EvalSet,
    EvalSetCreate,
    EvalSetMembersPublic,
    EvalSetMembersUpdate,
    EvalSetPublic,
    EvalSetsPublic,
    EvalSetUpdate,
    Message,
)


def _to_public(
    session: SessionDep,
    eval_set: EvalSet,
    *,
    test_case_count: int | None = None,
    sum_member_repetitions: int | None = None,
) -> EvalSetPublic:
    """Convert an EvalSet ORM object to EvalSetPublic with counts."""
    count = (
        test_case_count
        if test_case_count is not None
        else crud.count_test_cases_in_set(session=session, eval_set_id=eval_set.id)
    )
    sum_rep = (
        sum_member_repetitions
        if sum_member_repetitions is not None
        else crud.sum_member_repetitions_in_set(
            session=session, eval_set_id=eval_set.id
        )
    )
    effective = sum_rep
    return EvalSetPublic.model_validate(
        eval_set,
        update={
            "test_case_count": count,
            "effective_test_case_count": effective,
        },
    )


router = APIRouter(
    prefix="/eval-sets",
    tags=["eval-sets"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=EvalSetPublic)
def create_eval_set(session: SessionDep, eval_set_in: EvalSetCreate) -> EvalSetPublic:
    try:
        eval_set = crud.create_eval_set(session=session, eval_set_in=eval_set_in)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(session, eval_set)


@router.get("/", response_model=EvalSetsPublic)
def list_eval_sets(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> EvalSetsPublic:
    items, count = crud.list_eval_sets(session=session, skip=skip, limit=limit)
    ids = [s.id for s in items]
    counts = crud.count_test_cases_in_sets(session=session, eval_set_ids=ids)
    sum_reps = crud.sum_member_repetitions_in_sets(session=session, eval_set_ids=ids)
    public_items = [
        _to_public(
            session,
            item,
            test_case_count=counts.get(item.id, 0),
            sum_member_repetitions=sum_reps.get(item.id, 0),
        )
        for item in items
    ]
    return EvalSetsPublic(data=public_items, count=count)


@router.get("/{eval_set_id}", response_model=EvalSetPublic)
def get_eval_set(session: SessionDep, eval_set_id: uuid.UUID) -> EvalSetPublic:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    return _to_public(session, eval_set)


@router.patch("/{eval_set_id}", response_model=EvalSetPublic)
def update_eval_set(
    session: SessionDep,
    eval_set_id: uuid.UUID,
    eval_set_in: EvalSetUpdate,
) -> EvalSetPublic:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    updated = crud.update_eval_set(
        session=session,
        db_eval_set=eval_set,
        eval_set_in=eval_set_in,
    )
    return _to_public(session, updated)


@router.delete("/{eval_set_id}", response_model=Message)
def delete_eval_set(session: SessionDep, eval_set_id: uuid.UUID) -> Message:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    crud.delete_eval_set(session=session, db_eval_set=eval_set)
    return Message(message="Eval set deleted successfully")


# ── Member management ─────────────────────────────────────────────────


@router.get("/{eval_set_id}/test-cases", response_model=EvalSetMembersPublic)
def list_test_cases_in_set(
    session: SessionDep,
    eval_set_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> EvalSetMembersPublic:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    members, count = crud.list_test_cases_in_set(
        session=session, eval_set_id=eval_set_id, skip=skip, limit=limit
    )
    return EvalSetMembersPublic(data=members, count=count)


@router.post("/{eval_set_id}/test-cases", response_model=EvalSetPublic)
def add_test_cases_to_set(
    session: SessionDep,
    eval_set_id: uuid.UUID,
    body: EvalSetMembersUpdate,
) -> EvalSetPublic:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    try:
        updated = crud.add_test_cases_to_set(
            session=session,
            db_eval_set=eval_set,
            members=body.members,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(session, updated)


@router.put("/{eval_set_id}/test-cases", response_model=EvalSetPublic)
def replace_test_cases_in_set(
    session: SessionDep,
    eval_set_id: uuid.UUID,
    body: EvalSetMembersUpdate,
) -> EvalSetPublic:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    try:
        updated = crud.replace_test_cases_in_set(
            session=session,
            db_eval_set=eval_set,
            members=body.members,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(session, updated)


@router.delete("/{eval_set_id}/test-cases/{test_case_id}", response_model=EvalSetPublic)
def remove_test_case_from_set(
    session: SessionDep,
    eval_set_id: uuid.UUID,
    test_case_id: uuid.UUID,
) -> EvalSetPublic:
    eval_set = crud.get_eval_set(session=session, eval_set_id=eval_set_id)
    if not eval_set:
        raise HTTPException(status_code=404, detail="Eval set not found")
    updated = crud.remove_test_case_from_set(
        session=session,
        db_eval_set=eval_set,
        test_case_id=test_case_id,
    )
    return _to_public(session, updated)
