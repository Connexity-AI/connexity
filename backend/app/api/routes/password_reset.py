"""Reset a forgotten password with a single-use link sent by email.

Nothing here says whether an email has an account: asking for a link answers the same
way for every email, and the email is sent after the response, so the time taken does
not differ either. Plan: `plans/2026-11-23-password-reset.md`.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from app import crud
from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.models import PasswordResetAsk, PasswordResetLink, PasswordResetNew, Token
from app.utils import (
    generate_google_sign_in_email,
    generate_reset_password_email,
    send_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/password-reset", tags=["password-reset"])

LINK_NOT_WORKING = "This link no longer works"


def _address(request: Request) -> str:
    """The caller's network address, for the per-address limit.

    The web app asks on the person's behalf and names their address first in
    `X-Forwarded-For`; a caller that reaches the backend directly can write anything
    there, which is why the per-email limit does not depend on it.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    if first:
        return first
    return request.client.host if request.client else "unknown"


def _send(requested: crud.ResetRequested) -> None:
    if requested.email is None:
        return
    if requested.google_only:
        data = generate_google_sign_in_email()
    elif requested.token is not None:
        data = generate_reset_password_email(token=requested.token)
    else:
        return
    send_email(
        email_to=requested.email, subject=data.subject, html_content=data.html_content
    )


@router.post("", status_code=202, response_class=Response)
def ask_for_reset_link(
    *,
    session: SessionDep,
    request: Request,
    background_tasks: BackgroundTasks,
    body: PasswordResetAsk,
) -> Response:
    """Ask for a reset link. The answer is the same whether or not the email has an
    account; 429 when this email or this network address has asked too often."""
    if not settings.password_reset_enabled:
        raise HTTPException(status_code=404, detail="Password reset is not set up")
    address = _address(request)
    if crud.reset_limit_reached(session=session, email=body.email, address=address):
        raise HTTPException(
            status_code=429, detail="Too many attempts. Try again later."
        )
    requested = crud.request_password_reset(
        session=session, email=body.email, address=address
    )
    background_tasks.add_task(_send, requested)
    return Response(status_code=202)


@router.get("/{token}", response_model=PasswordResetLink)
def look_at_reset_link(*, session: SessionDep, token: str) -> PasswordResetLink:
    """The account a link is for, while the link works. Expired, used and unknown
    links are the same 404."""
    found = crud.find_reset_link(session=session, token=token)
    if found is None:
        raise HTTPException(status_code=404, detail=LINK_NOT_WORKING)
    _, user = found
    return PasswordResetLink(email=user.email)


@router.post("/{token}", response_model=Token)
def set_new_password(
    *, session: SessionDep, token: str, body: PasswordResetNew
) -> Token:
    """Set the password through a link and sign the person in.

    The link stops working, and every web session the person had ends; personal access
    tokens and connected assistants are not touched.
    """
    found = crud.find_reset_link(session=session, token=token)
    if found is None:
        raise HTTPException(status_code=404, detail=LINK_NOT_WORKING)
    link, user = found
    if not crud.reset_password(
        session=session, link=link, user=user, new_password=body.new_password
    ):
        raise HTTPException(status_code=404, detail=LINK_NOT_WORKING)
    logger.info("Password reset for user %s", user.id)
    access_token, expires = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return Token(access_token=access_token, expires=expires)
