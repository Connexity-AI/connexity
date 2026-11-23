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
from app.models.agency import Agency, AgencyRole
from app.models.company import Company

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/", response_model=list[WorkspacePublic])
def list_workspaces(
    session: SessionDep, current_user: CurrentUser
) -> list[WorkspacePublic]:
    workspaces = crud.list_accessible_workspaces(session=session, user=current_user)
    agencies = crud.agencies_by_id(
        session=session, agency_ids={w.agency_id for w in workspaces}
    )
    return [
        WorkspacePublic(
            id=workspace.id,
            name=workspace.name,
            is_open=workspace.id == current_user.company_id,
            agency_id=workspace.agency_id,
            agency_name=agencies[workspace.agency_id].name,
        )
        for workspace in workspaces
    ]


@router.post("/", response_model=WorkspacePublic)
def create_workspace(
    session: SessionDep, current_user: CurrentUser, workspace_in: WorkspaceCreate
) -> WorkspacePublic:
    """A workspace for a new client, in the agency of the workspace the person has
    open unless another is named. Only an Admin of that agency may create one."""
    name = workspace_in.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="A workspace needs a name")
    agency_id = workspace_in.agency_id
    if agency_id is None:
        open_workspace = session.get(Company, current_user.company_id)
        if open_workspace is None:
            raise HTTPException(status_code=404, detail="Agency not found")
        agency_id = open_workspace.agency_id
    agency = session.get(Agency, agency_id)
    membership = crud.get_membership(
        session=session, user_id=current_user.id, agency_id=agency_id
    )
    if agency is None or membership is None:
        raise HTTPException(status_code=404, detail="Agency not found")
    if membership.role != AgencyRole.admin:
        asking = crud.admin_names(session=session, agency_id=agency.id)
        raise HTTPException(
            status_code=403,
            detail=f"Only Admins can create a workspace. Ask {asking}.",
        )
    workspace = crud.add_workspace(
        session=session, agency=agency, name=name, created_by=current_user
    )
    return WorkspacePublic(
        id=workspace.id,
        name=workspace.name,
        is_open=False,
        agency_id=agency.id,
        agency_name=agency.name,
    )


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
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return Token(access_token=access_token, expires=expires)
