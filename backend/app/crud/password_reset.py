import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlmodel import Session, col, select

from app.core.security import get_password_hash
from app.core.security import hash_api_token as hash_token
from app.crud.user import find_user_by_email_ignoring_case
from app.models.password_reset import (
    RESET_LIMIT_PER_ADDRESS,
    RESET_LIMIT_PER_EMAIL,
    RESET_LIMIT_WINDOW,
    RESET_LINK_LIFETIME,
    RESET_RESEND_AFTER,
    PasswordResetRequest,
)
from app.models.user import User


@dataclass(frozen=True)
class ResetRequested:
    """What to email after a request: a link, the Google note, or nothing."""

    email: str | None = None
    token: str | None = None
    google_only: bool = False


def _hash(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def reset_limit_reached(
    *, session: Session, email: str, address: str, now: datetime | None = None
) -> bool:
    """Whether this email or this network address has asked too often.

    Counted from the stored requests, for an account or not, so the answer is the same
    for any email and holds across backend instances.
    """
    now = now or datetime.now(UTC)
    email_hash, address_hash = _hash(email), _hash(address)

    def _count(column: str, value: str, since: datetime) -> int:
        return session.exec(
            select(func.count())
            .select_from(PasswordResetRequest)
            .where(
                getattr(PasswordResetRequest, column) == value,
                col(PasswordResetRequest.created_at) > since,
            )
        ).one()

    if _count("email_hash", email_hash, now - RESET_RESEND_AFTER) > 0:
        return True
    if (
        _count("email_hash", email_hash, now - RESET_LIMIT_WINDOW)
        >= RESET_LIMIT_PER_EMAIL
    ):
        return True
    return (
        _count("address_hash", address_hash, now - RESET_LIMIT_WINDOW)
        >= RESET_LIMIT_PER_ADDRESS
    )


def request_password_reset(
    *, session: Session, email: str, address: str, now: datetime | None = None
) -> ResetRequested:
    """Record the request and say what to email.

    An active account with a password gets a new link, and its earlier unused links
    stop working. An active account without a password signs in only with Google and
    gets told so. Anything else gets nothing. Commits.
    """
    now = now or datetime.now(UTC)
    user = find_user_by_email_ignoring_case(session=session, email=email)
    if user is not None and not user.is_active:
        user = None

    request = PasswordResetRequest(
        email_hash=_hash(email), address_hash=_hash(address), created_at=now
    )
    result = ResetRequested()
    if user is not None and user.hashed_password:
        _end_unused_links(session=session, user=user, now=now)
        token = secrets.token_urlsafe(32)
        request.user_id = user.id
        request.token_hash = hash_token(token)
        request.expires_at = now + RESET_LINK_LIFETIME
        result = ResetRequested(email=user.email, token=token)
    elif user is not None:
        result = ResetRequested(email=user.email, google_only=True)
    session.add(request)
    session.commit()
    return result


def find_reset_link(
    *, session: Session, token: str, now: datetime | None = None
) -> tuple[PasswordResetRequest, User] | None:
    """The link and its person while the link works: not used, not expired."""
    now = now or datetime.now(UTC)
    link = session.exec(
        select(PasswordResetRequest).where(
            PasswordResetRequest.token_hash == hash_token(token),
            col(PasswordResetRequest.used_at).is_(None),
            col(PasswordResetRequest.expires_at) > now,
        )
    ).first()
    if link is None or link.user_id is None:
        return None
    user = session.get(User, link.user_id)
    if user is None or not user.is_active:
        return None
    return link, user


def reset_password(
    *,
    session: Session,
    link: PasswordResetRequest,
    user: User,
    new_password: str,
    now: datetime | None = None,
) -> bool:
    """Set the password through a link, once. False when the link was just used.

    Ends every web session the person had by raising their session version. Personal
    access tokens and assistants' OAuth tokens do not carry the version. Commits.
    """
    now = now or datetime.now(UTC)
    claimed = session.execute(
        update(PasswordResetRequest)
        .where(
            col(PasswordResetRequest.id) == link.id,
            col(PasswordResetRequest.used_at).is_(None),
        )
        .values(used_at=now)
    )
    if claimed.rowcount != 1:  # type: ignore[attr-defined]
        session.rollback()
        return False
    _end_unused_links(session=session, user=user, now=now)
    user.hashed_password = get_password_hash(new_password)
    user.session_version += 1
    session.add(user)
    session.commit()
    session.refresh(user)
    return True


def _end_unused_links(*, session: Session, user: User, now: datetime) -> None:
    session.execute(
        update(PasswordResetRequest)
        .where(
            col(PasswordResetRequest.user_id) == user.id,
            col(PasswordResetRequest.used_at).is_(None),
            col(PasswordResetRequest.token_hash).is_not(None),
        )
        .values(used_at=now)
    )
