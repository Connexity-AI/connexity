"""The Work page (plans `plans/2026-11-16-work-page.md` and
`plans/2026-11-16-reorder.md`): the assistant's tasks in order, who is working on what,
and what was done. The person reorders To do here; the assistant takes tasks through
MCP."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.models.work import WorkCountsPublic, WorkMoveIn, WorkPublic
from app.services.work import MoveRefused, move_task, waiting_count, work_page

router = APIRouter(tags=["work"], dependencies=[Depends(get_current_user)])


@router.get("/work", response_model=WorkPublic)
def read_work(session: SessionDep, company_id: CurrentCompany) -> WorkPublic:
    """The workspace's tasks: in progress (held, or waiting for the person), to do in
    order with Blocks and Blocked by, done in the last 7 days, and the sessions
    working now."""
    return work_page(session=session, company_id=company_id)


@router.get("/work/counts", response_model=WorkCountsPublic)
def read_work_counts(
    session: SessionDep, company_id: CurrentCompany
) -> WorkCountsPublic:
    """The sidebar's number: tasks waiting for the person, the same as the page's."""
    return WorkCountsPublic(
        waiting=waiting_count(session=session, company_id=company_id)
    )


@router.post("/work/order", response_model=WorkPublic)
def move_work_task(
    session: SessionDep,
    company_id: CurrentCompany,
    current_user: CurrentUser,
    body: WorkMoveIn,
) -> WorkPublic:
    """Move a To do task to sit just before another (or to the end). The assistant then
    gets tasks in that order. Tasks in progress or waiting, and incidents, do not move."""
    try:
        move_task(
            session=session,
            company_id=company_id,
            key=body.key,
            before=body.before,
            person=current_user,
            assistant_name=None,
        )
    except MoveRefused as refused:
        raise HTTPException(status_code=422, detail=refused.reason) from None
    return work_page(session=session, company_id=company_id)
