"""Joining an agency from an invite link.

The link's page is public: it says which agency invites which email. Joining needs an
account with that email: a session signed in with it, or a new account made here for
it. An expired, cancelled, used or unknown link is the same 404.
"""

from fastapi import APIRouter, HTTPException, Response

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.models import InviteLook, InviteSignIn, InviteSignUp, Token
from app.models.agency import Agency, AgencyInvite
from app.models.user import User

router = APIRouter(prefix="/invites", tags=["invites"])

NOT_WORKING = "This invite no longer works"


def _invite(session: SessionDep, token: str) -> AgencyInvite:
    invite = crud.find_invite(session=session, token=token)
    if invite is None:
        raise HTTPException(status_code=404, detail=NOT_WORKING)
    return invite


def _session_for(user: User) -> Token:
    access_token, expires = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return Token(access_token=access_token, expires=expires)


@router.get("/{token}", response_model=InviteLook)
def look_at_invite(session: SessionDep, token: str) -> InviteLook:
    """Which agency invites which email, while the link works."""
    invite = _invite(session, token)
    agency = session.get(Agency, invite.agency_id)
    inviter = (
        session.get(User, invite.invited_by_user_id)
        if invite.invited_by_user_id
        else None
    )
    existing = crud.find_user_by_email_ignoring_case(
        session=session, email=invite.email
    )
    return InviteLook(
        agency_name=agency.name if agency else "",
        invited_by=(inviter.full_name or inviter.email) if inviter else None,
        email=invite.email,
        workspaces=len(crud.workspaces_given(session=session, invite=invite)),
        has_account=existing is not None,
    )


@router.post("/{token}/accept", response_model=Token)
def accept_invite(session: SessionDep, current_user: CurrentUser, token: str) -> Token:
    """Join the agency as the signed-in person. Refused when they are signed in with
    another email than the invited one."""
    invite = _invite(session, token)
    try:
        crud.accept_invite(session=session, invite=invite, user=current_user)
    except crud.WrongEmailError:
        raise HTTPException(
            status_code=403,
            detail=f"This invite is for {invite.email}.",
        )
    except crud.NoWorkspaceChosenError:
        raise HTTPException(status_code=404, detail=NOT_WORKING)
    return _session_for(current_user)


@router.post("/{token}/decline", status_code=204)
def decline_invite(
    session: SessionDep, current_user: CurrentUser, token: str
) -> Response:
    invite = _invite(session, token)
    if current_user.email.strip().lower() != invite.email:
        raise HTTPException(
            status_code=403, detail=f"This invite is for {invite.email}."
        )
    crud.cancel_invite(session=session, invite=invite)
    return Response(status_code=204)


@router.post("/{token}/signup", response_model=Token)
def sign_up_and_join(session: SessionDep, token: str, body: InviteSignUp) -> Token:
    """Make an account for the invited email and join. The person gets the inviting
    agency only, and is signed in."""
    invite = _invite(session, token)
    try:
        user = crud.create_invited_user(
            session=session,
            invite=invite,
            full_name=body.full_name.strip(),
            password=body.password,
        )
    except crud.AccountExistsError:
        raise HTTPException(
            status_code=409,
            detail="An account already uses this email. Sign in to join.",
        )
    except crud.NoWorkspaceChosenError:
        raise HTTPException(status_code=404, detail=NOT_WORKING)
    return _session_for(user)


@router.post("/{token}/signin", response_model=Token)
def sign_in_and_join(session: SessionDep, token: str, body: InviteSignIn) -> Token:
    """Sign in to the invited email's account and join. This also works for a person
    who has no workspace left, whom the ordinary sign-in refuses: someone removed from
    an agency and invited again."""
    invite = _invite(session, token)
    account = crud.find_user_by_email_ignoring_case(session=session, email=invite.email)
    user = (
        crud.authenticate(session=session, email=account.email, password=body.password)
        if account
        else None
    )
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    try:
        crud.accept_invite(session=session, invite=invite, user=user)
    except crud.WrongEmailError:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    except crud.NoWorkspaceChosenError:
        raise HTTPException(status_code=404, detail=NOT_WORKING)
    return _session_for(user)
