"""Sign in with Google for the web app.

`/start` sends the browser to Google. Google sends it back to `/callback`, which signs
the person in (creating the account and its first workspace for a new email) and hands
the session token to the frontend's `/api/auth/set-cookie`, as the web login does.
A failure goes back to the sign-in page with `?error=google`.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app import crud
from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.services import google_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["auth"])

NONCE_COOKIE = "cx_google_nonce"
STATE_TTL = timedelta(minutes=10)
STATE_AUDIENCE = "connexity:google-sign-in"


class GoogleSignInStatus(BaseModel):
    enabled: bool


@router.get("", response_model=GoogleSignInStatus)
def google_status() -> GoogleSignInStatus:
    """Whether sign-in with Google is offered (both Google settings are present)."""
    return GoogleSignInStatus(enabled=settings.google_enabled)


@router.get("/start", response_class=RedirectResponse, status_code=302)
def start() -> RedirectResponse:
    if not settings.google_enabled:
        raise HTTPException(status_code=404, detail="Sign-in with Google is not set up")
    nonce = secrets.token_urlsafe(32)
    state = jwt.encode(
        {
            "aud": STATE_AUDIENCE,
            "nonce": nonce,
            "exp": datetime.now(UTC) + STATE_TTL,
        },
        settings.JWT_SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    response = RedirectResponse(
        google_auth.authorize_url(state=state, nonce=nonce), status_code=302
    )
    response.set_cookie(
        NONCE_COOKIE,
        nonce,
        max_age=int(STATE_TTL.total_seconds()),
        httponly=True,
        secure=settings.ENVIRONMENT != "local",
        samesite="lax",
    )
    return response


@router.get("/callback", response_class=RedirectResponse, status_code=302)
async def callback(
    request: Request,
    session: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if not settings.google_enabled:
        raise HTTPException(status_code=404, detail="Sign-in with Google is not set up")
    nonce = _nonce_from_state(state, request.cookies.get(NONCE_COOKIE))
    if error or not code or nonce is None:
        logger.info(
            "Google sign-in stopped: error=%s code=%s state_ok=%s",
            error,
            bool(code),
            nonce is not None,
        )
        return _back_to_sign_in()

    try:
        identity = await google_auth.identity_from_code(code=code, nonce=nonce)
    except google_auth.GoogleAuthError as exc:
        logger.warning("Google sign-in failed: %s", exc)
        return _back_to_sign_in()

    user = crud.find_user_by_email_ignoring_case(session=session, email=identity.email)
    if user is None:
        user = crud.create_google_user(
            session=session, email=identity.email, full_name=identity.full_name
        )
    elif not user.is_active:
        logger.info("Google sign-in refused for an inactive account")
        return _back_to_sign_in()

    access_token, expires = security.create_session_token(
        user_id=user.id, company_id=user.company_id
    )
    query = urlencode({"access_token": access_token, "expires": expires})
    response = RedirectResponse(
        f"{_site_url()}/api/auth/set-cookie?{query}", status_code=302
    )
    response.delete_cookie(NONCE_COOKIE)
    return response


def _nonce_from_state(state: str | None, cookie_nonce: str | None) -> str | None:
    """The nonce, when the state was issued by `/start` to this same browser."""
    if not state or not cookie_nonce:
        return None
    try:
        claims = jwt.decode(
            state,
            settings.JWT_SECRET_KEY,
            algorithms=[security.ALGORITHM],
            audience=STATE_AUDIENCE,
        )
    except jwt.InvalidTokenError:
        return None
    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or not secrets.compare_digest(nonce, cookie_nonce):
        return None
    return nonce


def _site_url() -> str:
    return settings.public_site_url or "http://localhost:3000"


def _back_to_sign_in() -> RedirectResponse:
    response = RedirectResponse(f"{_site_url()}/login?error=google", status_code=302)
    response.delete_cookie(NONCE_COOKIE)
    return response
