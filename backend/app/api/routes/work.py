"""The Work page (plan `plans/2026-11-16-work-page.md`): the assistant's tasks in
Connexity's order, who is working on what, and what was done. Read only; the person
reorders nothing here yet, and the assistant takes tasks through MCP."""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentCompany, SessionDep, get_current_user
from app.models.work import WorkCountsPublic, WorkPublic
from app.services.work import waiting_count, work_page

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
