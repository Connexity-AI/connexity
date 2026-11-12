"""The workspaces a person belongs to on the web: list, create and open.

Opening a workspace makes it the one every web route is scoped to, and answers with a
new session token for the frontend to set as the auth cookie.
"""

import uuid

from fastapi import APIRouter, HTTPException

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.models import Token, WorkspaceCreate, WorkspacePublic

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/", response_model=list[WorkspacePublic])
def list_workspaces(
    session: SessionDep, current_user: CurrentUser
) -> list[WorkspacePublic]:
    return [
        WorkspacePublic(
            id=workspace.id,
            name=workspace.name,
            is_open=workspace.id == current_user.company_id,
        )
        for workspace in crud.list_accessible_workspaces(
            session=session, user=current_user
        )
    ]


@router.post("/", response_model=WorkspacePublic)
def create_workspace(
    session: SessionDep, current_user: CurrentUser, workspace_in: WorkspaceCreate
) -> WorkspacePublic:
    name = workspace_in.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="A workspace needs a name")
    workspace = crud.create_workspace(session=session, user=current_user, name=name)
    return WorkspacePublic(id=workspace.id, name=workspace.name, is_open=False)


@router.post("/{workspace_id}/open", response_model=Token)
def open_workspace(
    session: SessionDep, current_user: CurrentUser, workspace_id: uuid.UUID
) -> Token:
    workspace = crud.get_accessible_workspace(
        session=session, user=current_user, workspace_id=workspace_id
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    user = crud.open_workspace(session=session, user=current_user, workspace=workspace)
    access_token, expires = security.create_session_token(
        user_id=user.id, company_id=user.company_id
    )
    return Token(access_token=access_token, expires=expires)
