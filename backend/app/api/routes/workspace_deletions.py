"""Agency settings › Workspaces: the agency's workspaces, and deleting one for good.

Anyone in the agency reads the table. Deleting is for an Admin who can approve, needs
the workspace's name typed, and cannot be undone (`app/crud/workspace_deletion.py`).
There is no way for an assistant to delete: these routes take a web session only.
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlmodel import col, func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.agencies import _mine
from app.core.config import settings
from app.crud import workspace_deletion as deleting
from app.models import (
    AgencyWorkspaceRow,
    AgencyWorkspacesTable,
    DeletionState,
    WorkspaceDeleteRequest,
    WorkspaceDeletion,
    WorkspaceDeletionPreview,
    WorkspaceDeletionPublic,
)
from app.models.agency import Agency
from app.models.agent import Agent
from app.models.call import Call
from app.models.company import Company
from app.models.user import User
from app.utils import generate_workspace_deleted_email, send_email

router = APIRouter(prefix="/agencies", tags=["agencies"])

LAST_WORKSPACE = "Create another workspace first. An agency needs at least one."


def _deletion_public(deletion: WorkspaceDeletion) -> WorkspaceDeletionPublic:
    return WorkspaceDeletionPublic(
        id=deletion.id,
        workspace_id=deletion.company_id,
        workspace_name=deletion.workspace_name,
        deleted_by=deletion.deleted_by_name,
        state=deleting.shown_state(deletion),
        calls=deletion.calls,
        agents=deletion.agents,
        issues=deletion.issues,
        created_at=deletion.created_at,
        finished_at=deletion.finished_at,
    )


def _as_deleter(session: SessionDep, user: User, agency_id: uuid.UUID) -> Agency:
    agency, _ = _mine(session, user.id, agency_id)
    if not deleting.can_delete(session=session, user=user, agency_id=agency.id):
        asking = deleting.who_can_delete(session=session, agency_id=agency.id)
        raise HTTPException(
            status_code=403,
            detail=f"Deleting a workspace needs an Admin who can approve. Ask {asking}.",
        )
    return agency


def _workspace(session: SessionDep, agency: Agency, workspace_id: uuid.UUID) -> Company:
    """One of the agency's workspaces, deleted or not; 404 otherwise."""
    workspace = session.get(Company, workspace_id)
    if workspace is None or workspace.agency_id != agency.id:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _per_workspace(
    session: SessionDep, model: type[Agent] | type[Call], ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = session.exec(
        select(model.company_id, func.count())
        .where(col(model.company_id).in_(ids))
        .group_by(col(model.company_id))
    ).all()
    return dict(rows)


def send_deleted_email(
    *, emails: list[str], workspace_name: str, deleted_by: str
) -> None:
    """Tell the agency's Admins. Without email settings nothing is sent; the agency's
    record on the Workspaces table says the same."""
    if not settings.emails_enabled:
        return
    data = generate_workspace_deleted_email(
        workspace_name=workspace_name, deleted_by=deleted_by, on=datetime.now(UTC)
    )
    for email in emails:
        send_email(email_to=email, subject=data.subject, html_content=data.html_content)


def _finished(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    agency: Agency,
    deletion: WorkspaceDeletion,
) -> WorkspaceDeletionPublic:
    if deletion.state is DeletionState.done:
        background_tasks.add_task(
            send_deleted_email,
            emails=[u.email for u in crud.admins(session=session, agency_id=agency.id)],
            workspace_name=deletion.workspace_name,
            deleted_by=deletion.deleted_by_name,
        )
    return _deletion_public(deletion)


@router.get("/{agency_id}/workspaces", response_model=AgencyWorkspacesTable)
def read_workspaces(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> AgencyWorkspacesTable:
    """The agency's workspaces with how much each holds, and its record of deleted
    ones. A deletion that is running or failed keeps its row, with its state."""
    agency, _ = _mine(session, current_user.id, agency_id)
    record = deleting.deletions(session=session, agency_id=agency.id)
    unfinished = {d.company_id: d for d in record if d.state is not DeletionState.done}
    active = crud.agency_workspaces(session=session, agency_id=agency.id)
    ids = [w.id for w in active]
    agents = _per_workspace(session, Agent, ids)
    calls = _per_workspace(session, Call, ids)
    rows = [
        AgencyWorkspaceRow(
            id=w.id,
            name=w.name,
            agents=agents.get(w.id, 0),
            calls=calls.get(w.id, 0),
            created_at=w.created_at,
            state=None,
        )
        for w in active
    ]
    rows += [
        AgencyWorkspaceRow(
            id=d.company_id,
            name=d.workspace_name,
            agents=d.agents,
            calls=d.calls,
            created_at=d.created_at,
            state=deleting.shown_state(d),
        )
        for d in unfinished.values()
    ]
    return AgencyWorkspacesTable(
        workspaces=sorted(rows, key=lambda r: (r.name.lower(), str(r.id))),
        can_delete=deleting.can_delete(
            session=session, user=current_user, agency_id=agency.id
        ),
        deleted=[_deletion_public(d) for d in record if d.state is DeletionState.done],
    )


@router.get(
    "/{agency_id}/workspaces/{workspace_id}/deletion",
    response_model=WorkspaceDeletionPreview,
)
def preview_deletion(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> WorkspaceDeletionPreview:
    """What deleting the workspace would remove. Deletes nothing."""
    agency = _as_deleter(session, current_user, agency_id)
    workspace = _workspace(session, agency, workspace_id)
    if workspace.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    held = deleting.counts(session=session, company_id=workspace.id)
    return WorkspaceDeletionPreview(
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        calls=held.calls,
        agents=held.agents,
        issues=held.issues,
        connections=deleting.connection_names(session=session, company_id=workspace.id),
        is_last=len(crud.agency_workspaces(session=session, agency_id=agency.id)) <= 1,
    )


@router.post(
    "/{agency_id}/workspaces/{workspace_id}/deletion",
    response_model=WorkspaceDeletionPublic,
)
def delete_workspace(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    agency_id: uuid.UUID,
    workspace_id: uuid.UUID,
    body: WorkspaceDeleteRequest,
) -> WorkspaceDeletionPublic:
    """Delete the workspace and its data for good. The workspace's name must be typed
    exactly. The answer's `state` is `done`, or `failed` when a step broke."""
    agency = _as_deleter(session, current_user, agency_id)
    workspace = _workspace(session, agency, workspace_id)
    if workspace.deleted_at is not None:
        raise HTTPException(status_code=409, detail="This workspace was deleted.")
    if body.name.strip() != workspace.name.strip():
        raise HTTPException(
            status_code=422, detail=f"Type {workspace.name} to confirm."
        )
    try:
        deletion = deleting.start_deletion(
            session=session, agency=agency, workspace=workspace, deleted_by=current_user
        )
    except deleting.LastWorkspaceError:
        raise HTTPException(status_code=409, detail=LAST_WORKSPACE)
    except deleting.DeletionRunningError:
        raise HTTPException(status_code=409, detail="This workspace was deleted.")
    return _finished(session, background_tasks, agency, deletion)


@router.post(
    "/{agency_id}/workspaces/{workspace_id}/deletion/retry",
    response_model=WorkspaceDeletionPublic,
)
def retry_deletion(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    agency_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> WorkspaceDeletionPublic:
    """Continue a deletion that failed, or one whose request died midway."""
    agency = _as_deleter(session, current_user, agency_id)
    deletion = deleting.get_deletion(
        session=session, agency_id=agency.id, company_id=workspace_id
    )
    if deletion is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if deleting.shown_state(deletion) is not DeletionState.failed:
        raise HTTPException(
            status_code=409, detail="This deletion does not need another try."
        )
    deletion = deleting.run_deletion(session=session, deletion=deletion)
    return _finished(session, background_tasks, agency, deletion)
