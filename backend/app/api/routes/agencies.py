"""An agency and the people in it, for the web app.

Anyone in an agency can read it. Renaming it and changing or removing people is for its
Admins. An agency always keeps at least one Admin. Screens and invites that use these
routes come with the roadmap row "Invites and Members screen".
"""

import uuid

from fastapi import APIRouter, HTTPException, Response

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models.agency import (
    Agency,
    AgencyDetail,
    AgencyMember,
    AgencyMemberPublic,
    AgencyMemberUpdate,
    AgencyPublic,
    AgencyRole,
    AgencyUpdate,
    AgencyWorkspace,
)

router = APIRouter(prefix="/agencies", tags=["agencies"])

LAST_ADMIN = "An agency needs at least one Admin."


def _mine(
    session: SessionDep, user_id: uuid.UUID, agency_id: uuid.UUID
) -> tuple[Agency, AgencyMember]:
    """The agency and the caller's place in it; 404 when they are not in it."""
    agency = session.get(Agency, agency_id)
    membership = crud.get_membership(
        session=session, user_id=user_id, agency_id=agency_id
    )
    if agency is None or membership is None:
        raise HTTPException(status_code=404, detail="Agency not found")
    return agency, membership


def _as_admin(session: SessionDep, user_id: uuid.UUID, agency_id: uuid.UUID) -> Agency:
    agency, membership = _mine(session, user_id, agency_id)
    if membership.role != AgencyRole.admin:
        raise HTTPException(
            status_code=403, detail="Only Admins can change an agency or its people."
        )
    return agency


def _public(agency: Agency, membership: AgencyMember) -> AgencyPublic:
    return AgencyPublic(
        id=agency.id,
        name=agency.name,
        role=membership.role,
        all_workspaces=membership.all_workspaces,
        can_approve=membership.can_approve,
    )


def _member_public(row: crud.MemberRow, viewer_id: uuid.UUID) -> AgencyMemberPublic:
    return AgencyMemberPublic(
        user_id=row.user.id,
        email=row.user.email,
        full_name=row.user.full_name,
        role=row.member.role,
        all_workspaces=row.member.all_workspaces,
        workspace_ids=row.workspace_ids,
        can_approve=row.member.can_approve,
        is_you=row.user.id == viewer_id,
    )


def _their_place(
    session: SessionDep, agency: Agency, user_id: uuid.UUID
) -> AgencyMember:
    member = crud.get_membership(session=session, user_id=user_id, agency_id=agency.id)
    if member is None:
        raise HTTPException(status_code=404, detail="Person not found in this agency")
    return member


@router.get("/", response_model=list[AgencyPublic])
def list_agencies(session: SessionDep, current_user: CurrentUser) -> list[AgencyPublic]:
    """The agencies the signed-in person is in, with their role in each."""
    return [
        _public(agency, membership)
        for agency, membership in crud.list_agencies(session=session, user=current_user)
    ]


@router.get("/{agency_id}", response_model=AgencyDetail)
def read_agency(
    session: SessionDep, current_user: CurrentUser, agency_id: uuid.UUID
) -> AgencyDetail:
    """An agency, its workspaces and its people, for anyone in it."""
    agency, membership = _mine(session, current_user.id, agency_id)
    return AgencyDetail(
        **_public(agency, membership).model_dump(),
        workspaces=[
            AgencyWorkspace(id=w.id, name=w.name)
            for w in crud.agency_workspaces(session=session, agency_id=agency.id)
        ],
        members=[
            _member_public(row, current_user.id)
            for row in crud.list_members(session=session, agency_id=agency.id)
        ],
    )


@router.patch("/{agency_id}", response_model=AgencyPublic)
def rename_agency(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    body: AgencyUpdate,
) -> AgencyPublic:
    agency = _as_admin(session, current_user.id, agency_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="An agency needs a name")
    agency = crud.rename_agency(session=session, agency=agency, name=name)
    return _public(agency, _their_place(session, agency, current_user.id))


@router.patch("/{agency_id}/members/{user_id}", response_model=AgencyMemberPublic)
def update_member(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    user_id: uuid.UUID,
    body: AgencyMemberUpdate,
) -> AgencyMemberPublic:
    """Change a person's role, the workspaces they reach, or whether they can approve.
    Their access, and their assistants', changes at once."""
    agency = _as_admin(session, current_user.id, agency_id)
    member = _their_place(session, agency, user_id)
    try:
        crud.update_member(
            session=session,
            agency=agency,
            member=member,
            role=body.role,
            all_workspaces=body.all_workspaces,
            workspace_ids=body.workspace_ids,
            can_approve=body.can_approve,
        )
    except crud.LastAdminError:
        raise HTTPException(status_code=409, detail=LAST_ADMIN)
    except crud.UnknownWorkspaceError:
        raise HTTPException(
            status_code=422, detail="A chosen workspace is not one of this agency's."
        )
    row = next(
        row
        for row in crud.list_members(session=session, agency_id=agency.id)
        if row.user.id == user_id
    )
    return _member_public(row, current_user.id)


@router.delete("/{agency_id}/members/{user_id}", status_code=204)
def remove_member(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Response:
    """Remove a person from the agency. They lose its workspaces at once, and so do
    their assistants. What they did stays on record."""
    agency = _as_admin(session, current_user.id, agency_id)
    member = _their_place(session, agency, user_id)
    try:
        crud.remove_member(session=session, agency=agency, member=member)
    except crud.LastAdminError:
        raise HTTPException(status_code=409, detail=LAST_ADMIN)
    return Response(status_code=204)
