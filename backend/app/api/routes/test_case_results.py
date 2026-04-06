import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app import crud
from app.api.deps import SessionDep, get_current_user
from app.models import (
    Message,
    TestCaseResult,
    TestCaseResultCreate,
    TestCaseResultPublic,
    TestCaseResultsPublic,
    TestCaseResultUpdate,
)

router = APIRouter(
    prefix="/test-case-results",
    tags=["test-case-results"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=TestCaseResultPublic)
def create_test_case_result(
    session: SessionDep, result_in: TestCaseResultCreate
) -> TestCaseResult:
    return crud.create_test_case_result(session=session, result_in=result_in)


@router.get("/", response_model=TestCaseResultsPublic)
def list_test_case_results(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    run_id: uuid.UUID | None = None,
    test_case_id: uuid.UUID | None = None,
    repetition_index: int | None = Query(
        default=None, description="Filter by repetition within a set pass (0-based)"
    ),
    set_repetition_index: int | None = Query(
        default=None, description="Filter by full set pass index (0-based)"
    ),
) -> TestCaseResultsPublic:
    items, count = crud.list_test_case_results(
        session=session,
        skip=skip,
        limit=limit,
        run_id=run_id,
        test_case_id=test_case_id,
        repetition_index=repetition_index,
        set_repetition_index=set_repetition_index,
    )
    return TestCaseResultsPublic(data=items, count=count)  # type: ignore[arg-type]


@router.get("/{result_id}", response_model=TestCaseResultPublic)
def get_test_case_result(session: SessionDep, result_id: uuid.UUID) -> TestCaseResult:
    result = crud.get_test_case_result(session=session, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test case result not found")
    return result


@router.patch("/{result_id}", response_model=TestCaseResultPublic)
def update_test_case_result(
    session: SessionDep,
    result_id: uuid.UUID,
    result_in: TestCaseResultUpdate,
) -> TestCaseResult:
    result = crud.get_test_case_result(session=session, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test case result not found")
    return crud.update_test_case_result(
        session=session, db_result=result, result_in=result_in
    )


@router.delete("/{result_id}", response_model=Message)
def delete_test_case_result(session: SessionDep, result_id: uuid.UUID) -> Message:
    result = crud.get_test_case_result(session=session, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test case result not found")
    crud.delete_test_case_result(session=session, db_result=result)
    return Message(message="Test case result deleted successfully")
