"""Clarifications for the question cards on Work (plan `plans/2026-11-16-question-cards.md`).

The same service as the MCP tools: the person reads and answers here, the assistant
there. An answer given here records the person alone, with no assistant.
"""

import base64
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, StringConstraints

from app import crud
from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.crud import clarification as crud_clarification
from app.models.clarification import (
    ClarificationListPublic,
    ClarificationsAnsweredPublic,
)
from app.models.enums import ClarificationState
from app.services.clarification import (
    ClarificationRefused,
    Decision,
    answer_clarifications,
    answered_public,
    clarifications_public,
    counts_public,
)

router = APIRouter(tags=["clarifications"], dependencies=[Depends(get_current_user)])


class ClarificationListPage(ClarificationListPublic):
    next_cursor: str | None = Field(
        default=None, description="Pass as `cursor` for the next page"
    )


class ClarificationDecisionIn(BaseModel):
    clarification_id: uuid.UUID
    answer: Annotated[str, StringConstraints(max_length=16)] = Field(
        description="a to d, 'other' with text, 'park', or 'reopen' for a parked one"
    )
    text: Annotated[str | None, StringConstraints(max_length=500)] = Field(
        default=None, description="For 'other': the person's answer, as the rule"
    )


class ClarificationAnswersIn(BaseModel):
    answers: list[ClarificationDecisionIn] = Field(max_length=50)


def _offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(base64.urlsafe_b64decode(cursor.encode()).decode()))
    except ValueError:
        raise HTTPException(
            status_code=422, detail="This cursor is not valid"
        ) from None


@router.get("/clarifications", response_model=ClarificationListPage)
def list_workspace_clarifications(
    session: SessionDep,
    company_id: CurrentCompany,
    state: ClarificationState = ClarificationState.OPEN,
    agent_id: uuid.UUID | None = None,
    cursor: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=5, ge=1, le=200),
) -> ClarificationListPage:
    """Open questions most important first; answered and parked ones newest first."""
    if agent_id is not None and (
        crud.get_agent(session=session, agent_id=agent_id, company_id=company_id)
        is None
    ):
        raise HTTPException(status_code=404, detail="Agent not found")
    offset = _offset(cursor)
    rows, has_more = crud_clarification.list_page(
        session=session,
        company_id=company_id,
        state=state,
        agent_id=agent_id,
        offset=offset,
        limit=limit,
    )
    return ClarificationListPage(
        counts=counts_public(session=session, company_id=company_id, agent_id=agent_id),
        data=clarifications_public(session=session, rows=rows),
        next_cursor=base64.urlsafe_b64encode(str(offset + limit).encode()).decode()
        if has_more
        else None,
    )


@router.post("/clarifications/answers", response_model=ClarificationsAnsweredPublic)
def answer_workspace_clarifications(
    session: SessionDep,
    company_id: CurrentCompany,
    current_user: CurrentUser,
    body: ClarificationAnswersIn,
) -> ClarificationsAnsweredPublic:
    """Answer, park or reopen; answers become spec rules. Refusals list every problem."""
    try:
        result = answer_clarifications(
            session=session,
            company_id=company_id,
            decisions=[
                Decision(a.clarification_id, a.answer, a.text) for a in body.answers
            ],
            decided_by=current_user,
            assistant_name=None,
        )
    except ClarificationRefused as refused:
        raise HTTPException(
            status_code=422,
            detail={"error": refused.error, "problems": refused.problems},
        ) from None
    return answered_public(session=session, company_id=company_id, result=result)
