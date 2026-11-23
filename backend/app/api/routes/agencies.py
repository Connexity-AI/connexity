"""An agency and the people in it, for the web app.

Anyone in an agency can read it. Renaming it and changing or removing people is for its
Admins. An agency always keeps at least one Admin. Screens and invites that use these
routes come with the roadmap row "Invites and Members screen".
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models.agency import (
    Agency,
    AgencyDetail,
    AgencyInvite,
    AgencyInviteCreate,
    AgencyInvitePublic,
    AgencyInviteRefusal,
    AgencyInviteResult,
    AgencyMember,
    AgencyMemberPublic,
    AgencyMemberUpdate,
    AgencyPublic,
    AgencyRole,
    AgencyUpdate,
    AgencyWorkspace,
)
from app.models.user import User
from app.utils import generate_invite_email, send_email

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


def _member_public(
    row: crud.MemberRow, viewer_id: uuid.UUID, assistants: int
) -> AgencyMemberPublic:
    return AgencyMemberPublic(
        user_id=row.user.id,
        email=row.user.email,
        full_name=row.user.full_name,
        role=row.member.role,
        all_workspaces=row.member.all_workspaces,
        workspace_ids=row.workspace_ids,
        can_approve=row.member.can_approve,
        is_you=row.user.id == viewer_id,
        assistants=assistants,
    )


def _members_public(
    session: SessionDep, agency: Agency, viewer_id: uuid.UUID
) -> list[AgencyMemberPublic]:
    rows = crud.list_members(session=session, agency_id=agency.id)
    assistants = crud.connected_assistants(
        session=session, user_ids={row.user.id for row in rows}
    )
    return [_member_public(row, viewer_id, assistants[row.user.id]) for row in rows]


def invite_public(session: SessionDep, invite: AgencyInvite) -> AgencyInvitePublic:
    inviter = (
        session.get(User, invite.invited_by_user_id)
        if invite.invited_by_user_id
        else None
    )
    return AgencyInvitePublic(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        all_workspaces=invite.all_workspaces,
        workspace_ids=sorted(
            crud.workspaces_given(session=session, invite=invite), key=str
        ),
        can_approve=invite.can_approve,
        expires_at=invite.expires_at,
        invited_by=(inviter.full_name or inviter.email) if inviter else None,
    )


def send_invite_email(
    *, email: str, token: str, invited_by: str | None, agency_name: str, workspaces: int
) -> None:
    """Hand the invite to the email provider. Without email settings, or when the
    provider refuses, the invite still exists and "Resend invite" tries again."""
    if not settings.emails_enabled or not settings.public_site_url:
        return
    data = generate_invite_email(
        token=token,
        invited_by=invited_by,
        agency_name=agency_name,
        workspaces=workspaces,
    )
    send_email(email_to=email, subject=data.subject, html_content=data.html_content)


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
        members=_members_public(session, agency, current_user.id),
        invites=[
            invite_public(session, invite)
            for invite in crud.open_invites(session=session, agency_id=agency.id)
        ]
        if membership.role == AgencyRole.admin
        else [],
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
    return next(
        person
        for person in _members_public(session, agency, current_user.id)
        if person.user_id == user_id
    )


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


REFUSALS = {
    "invalid": "Enter a full email address, like alex@example.com.",
    "member": "{email} is already in {agency}.",
    "invited": "{email} already has an invite.",
}


@router.post("/{agency_id}/invites", response_model=AgencyInviteResult)
def invite_people(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    agency_id: uuid.UUID,
    body: AgencyInviteCreate,
) -> AgencyInviteResult:
    """Invite people by email. Each address that can get an invite is sent one, good
    for 7 days; the others come back with why not."""
    agency = _as_admin(session, current_user.id, agency_id)
    return make_invites(
        session, background_tasks, agency=agency, invited_by=current_user, body=body
    )


def make_invites(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    *,
    agency: Agency,
    invited_by: User,
    body: AgencyInviteCreate,
) -> AgencyInviteResult:
    try:
        made, refused = crud.invite_people(
            session=session,
            agency=agency,
            invited_by=invited_by,
            emails=body.emails,
            role=body.role,
            all_workspaces=body.all_workspaces,
            workspace_ids=body.workspace_ids,
            can_approve=body.can_approve,
        )
    except crud.NoWorkspaceChosenError:
        raise HTTPException(
            status_code=422,
            detail="Choose at least one of this agency's workspaces.",
        )
    sent = []
    for invite, token in made:
        public = invite_public(session, invite)
        background_tasks.add_task(
            send_invite_email,
            email=invite.email,
            token=token,
            invited_by=public.invited_by,
            agency_name=agency.name,
            workspaces=len(public.workspace_ids),
        )
        sent.append(public)
    return AgencyInviteResult(
        sent=sent,
        refused=[
            AgencyInviteRefusal(
                email=r.email,
                reason=r.reason,
                message=REFUSALS[r.reason].format(email=r.email, agency=agency.name),
            )
            for r in refused
        ],
    )


def _open_invite(
    session: SessionDep, agency: Agency, invite_id: uuid.UUID
) -> AgencyInvite:
    invite = crud.get_open_invite(
        session=session, agency_id=agency.id, invite_id=invite_id
    )
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    return invite


@router.post(
    "/{agency_id}/invites/{invite_id}/resend", response_model=AgencyInvitePublic
)
def resend_invite(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    agency_id: uuid.UUID,
    invite_id: uuid.UUID,
) -> AgencyInvitePublic:
    """Send the invite again with a new link and seven more days. The earlier link
    stops working."""
    agency = _as_admin(session, current_user.id, agency_id)
    invite = _open_invite(session, agency, invite_id)
    token = crud.resend_invite(session=session, invite=invite)
    public = invite_public(session, invite)
    background_tasks.add_task(
        send_invite_email,
        email=invite.email,
        token=token,
        invited_by=public.invited_by,
        agency_name=agency.name,
        workspaces=len(public.workspace_ids),
    )
    return public


@router.delete("/{agency_id}/invites/{invite_id}", status_code=204)
def cancel_invite(
    session: SessionDep,
    current_user: CurrentUser,
    agency_id: uuid.UUID,
    invite_id: uuid.UUID,
) -> Response:
    agency = _as_admin(session, current_user.id, agency_id)
    crud.cancel_invite(session=session, invite=_open_invite(session, agency, invite_id))
    return Response(status_code=204)
