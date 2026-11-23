"""Invites to an agency: sending, resending, cancelling and joining.

An invite is for one email address and carries what the person will be in the agency.
Joining needs an account with that address, so a forwarded link is useless to anyone
else. The person who joins gets the inviting agency only, never one of their own
(Decided by Dmytro, 2026-11-23).
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlmodel import Session, col, func, select

from app.core.security import get_password_hash
from app.core.security import hash_api_token as hash_token
from app.crud.agency import _reopen_if_needed, _set_reach, agency_workspaces
from app.models.agency import (
    INVITE_LIFETIME,
    Agency,
    AgencyInvite,
    AgencyMember,
    AgencyRole,
)
from app.models.user import AuthProvider, User

_EMAIL = TypeAdapter(EmailStr)


class NoWorkspaceChosenError(Exception):
    """An invite must give at least one of the agency's workspaces."""


class WrongEmailError(Exception):
    """The invite is for another email address than the account's."""


class AccountExistsError(Exception):
    """An account with the invited email already exists; it signs in to join."""


@dataclass(frozen=True)
class Refused:
    email: str
    reason: str  # invalid | member | invited


def _now() -> datetime:
    return datetime.now(UTC)


def _open(now: datetime) -> list:
    return [
        col(AgencyInvite.accepted_at).is_(None),
        col(AgencyInvite.cancelled_at).is_(None),
        col(AgencyInvite.expires_at) > now,
    ]


def open_invites(*, session: Session, agency_id: uuid.UUID) -> list[AgencyInvite]:
    return list(
        session.exec(
            select(AgencyInvite)
            .where(AgencyInvite.agency_id == agency_id, *_open(_now()))
            .order_by(col(AgencyInvite.created_at), col(AgencyInvite.id))
        ).all()
    )


def get_open_invite(
    *, session: Session, agency_id: uuid.UUID, invite_id: uuid.UUID
) -> AgencyInvite | None:
    return session.exec(
        select(AgencyInvite).where(
            AgencyInvite.id == invite_id,
            AgencyInvite.agency_id == agency_id,
            *_open(_now()),
        )
    ).first()


def find_invite(*, session: Session, token: str) -> AgencyInvite | None:
    """The invite a link is for, while the link works."""
    return session.exec(
        select(AgencyInvite).where(
            AgencyInvite.token_hash == hash_token(token), *_open(_now())
        )
    ).first()


def invite_people(
    *,
    session: Session,
    agency: Agency,
    invited_by: User,
    emails: list[str],
    role: AgencyRole,
    all_workspaces: bool,
    workspace_ids: list[uuid.UUID],
    can_approve: bool,
) -> tuple[list[tuple[AgencyInvite, str]], list[Refused]]:
    """Make an invite for each address that can get one. Commits.

    Returns the invites with their link tokens (to email), and the addresses refused:
    not an email, already in the agency, or already holding an open invite.

    Raises:
        NoWorkspaceChosenError: chosen workspaces were asked for and none of the
            agency's was named.
    """
    owned = {w.id for w in agency_workspaces(session=session, agency_id=agency.id)}
    chosen = [w for w in dict.fromkeys(workspace_ids) if w in owned]
    if not all_workspaces and (not chosen or len(chosen) != len(set(workspace_ids))):
        raise NoWorkspaceChosenError
    if all_workspaces and not owned:
        raise NoWorkspaceChosenError

    now = _now()
    made: list[tuple[AgencyInvite, str]] = []
    refused: list[Refused] = []
    seen: set[str] = set()
    for raw in emails:
        typed = raw.strip()
        try:
            email = _EMAIL.validate_python(typed).lower()
        except ValidationError:
            refused.append(Refused(typed, "invalid"))
            continue
        if email in seen:
            continue
        seen.add(email)
        if _is_member(session=session, agency_id=agency.id, email=email):
            refused.append(Refused(email, "member"))
            continue
        already = session.exec(
            select(AgencyInvite).where(
                AgencyInvite.agency_id == agency.id,
                AgencyInvite.email == email,
                *_open(now),
            )
        ).first()
        if already is not None:
            refused.append(Refused(email, "invited"))
            continue
        token = secrets.token_urlsafe(32)
        invite = AgencyInvite(
            agency_id=agency.id,
            email=email,
            role=role,
            all_workspaces=all_workspaces,
            workspace_ids=[] if all_workspaces else [str(w) for w in chosen],
            can_approve=can_approve,
            invited_by_user_id=invited_by.id,
            token_hash=hash_token(token),
            sent_at=now,
            expires_at=now + INVITE_LIFETIME,
        )
        session.add(invite)
        made.append((invite, token))
    session.commit()
    for invite, _ in made:
        session.refresh(invite)
    return made, refused


def resend_invite(*, session: Session, invite: AgencyInvite) -> str:
    """A new link and seven more days; the earlier link stops working. Commits."""
    token = secrets.token_urlsafe(32)
    now = _now()
    invite.token_hash = hash_token(token)
    invite.sent_at = now
    invite.expires_at = now + INVITE_LIFETIME
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return token


def cancel_invite(*, session: Session, invite: AgencyInvite) -> None:
    """End an invite: cancelled by an Admin or declined by the person. Commits."""
    invite.cancelled_at = _now()
    session.add(invite)
    session.commit()


def workspaces_given(*, session: Session, invite: AgencyInvite) -> set[uuid.UUID]:
    """The workspaces the invite gives today: all of the agency's, or the chosen ones
    that still exist."""
    owned = {
        w.id for w in agency_workspaces(session=session, agency_id=invite.agency_id)
    }
    if invite.all_workspaces:
        return owned
    return {uuid.UUID(w) for w in invite.workspace_ids} & owned


def accept_invite(*, session: Session, invite: AgencyInvite, user: User) -> None:
    """Put an existing account into the agency as the invite says. Commits.

    Raises:
        WrongEmailError: the account's email is not the invited one.
        NoWorkspaceChosenError: none of the invite's workspaces exists any more.
    """
    if user.email.strip().lower() != invite.email:
        raise WrongEmailError
    if not workspaces_given(session=session, invite=invite):
        raise NoWorkspaceChosenError
    _join(session=session, invite=invite, user=user)
    session.commit()
    _reopen_if_needed(session=session, user_id=user.id)
    session.refresh(user)


def create_invited_user(
    *,
    session: Session,
    invite: AgencyInvite,
    full_name: str | None,
    password: str | None,
) -> User:
    """A new account for the invited email, in the inviting agency only. With no
    password it is an account that signs in with Google. Commits.

    Raises:
        AccountExistsError: the email already has an account.
        NoWorkspaceChosenError: none of the invite's workspaces exists any more.
    """
    existing = session.exec(
        select(User).where(func.lower(User.email) == invite.email)
    ).first()
    if existing is not None:
        raise AccountExistsError
    reach = sorted(workspaces_given(session=session, invite=invite), key=str)
    if not reach:
        raise NoWorkspaceChosenError
    user = User(
        email=invite.email,
        full_name=full_name,
        provider=AuthProvider.email if password else AuthProvider.google,
        hashed_password=get_password_hash(password) if password else None,
        company_id=reach[0],
    )
    session.add(user)
    session.flush()
    _join(session=session, invite=invite, user=user)
    session.commit()
    _reopen_if_needed(session=session, user_id=user.id)
    session.refresh(user)
    return user


def _join(*, session: Session, invite: AgencyInvite, user: User) -> None:
    owned = {
        w.id for w in agency_workspaces(session=session, agency_id=invite.agency_id)
    }
    member = session.get(AgencyMember, (invite.agency_id, user.id))
    if member is None:
        member = AgencyMember(
            agency_id=invite.agency_id,
            user_id=user.id,
            role=invite.role,
            all_workspaces=invite.all_workspaces,
            can_approve=invite.can_approve,
        )
        session.add(member)
        session.flush()
        _set_reach(
            session=session,
            member=member,
            owned=owned,
            chosen=workspaces_given(session=session, invite=invite),
        )
    invite.accepted_at = _now()
    session.add(invite)


def _is_member(*, session: Session, agency_id: uuid.UUID, email: str) -> bool:
    return (
        session.exec(
            select(AgencyMember.user_id)
            .join(User, col(User.id) == AgencyMember.user_id)
            .where(AgencyMember.agency_id == agency_id, func.lower(User.email) == email)
        ).first()
        is not None
    )
