import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette.requests import Request

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
    get_current_user,
)
from app.core import security
from app.core.config import settings
from app.models import Message, NewPassword, Token, UserPublic
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    is_prod,
    send_email,
    verify_password_reset_token,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2-compatible token login: get an access token for future requests (sent in an HTTP-only cookie)
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    expires_delta = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)

    access_token = security.create_access_token(user.id, expires_delta)

    # Absolute expiration Unix time (UTC)
    expires_at = datetime.now(timezone.utc) + expires_delta
    expires_timestamp = int(expires_at.timestamp())

    token = Token(
        access_token=access_token,
        expires=expires_timestamp,
    )

    return token


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    hashed_password = security.get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )


# get_current_user() throws if user is not logged in
@router.post("/logout", dependencies=[Depends(get_current_user)])
def logout() -> JSONResponse:
    """
    Delete the HTTP-only cookie during logout
    """
    return security.delete_auth_cookie()


# ------------------------ GitHub OAuth ---------------------------


@router.get("/login/github")
async def login_github(request: Request):
    """
    Redirect to GitHub login page
    Must initiate OAuth flow from backend
    """
    redirect_uri = request.url_for("auth_github_callback")  # matches function name

    # rewrite to https in production
    if is_prod:
        redirect_uri = redirect_uri.replace(scheme="https")

    return await security.oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/auth/github/callback")
async def auth_github_callback(
    request: Request, session: SessionDep
) -> RedirectResponse:
    """
    GitHub OAuth callback, GitHub will call this endpoint
    """
    # Exchange code for access token
    token = await security.oauth.github.authorize_access_token(request)

    # Get user profile GitHub API
    user_info = await security.oauth.github.get("user", token=token)
    profile = user_info.json()

    # Get primary email GitHub API
    emails = await security.oauth.github.get("user/emails", token=token)
    primary_email = next((e["email"] for e in emails.json() if e["primary"]), None)

    logger.info(f"Primary GitHub email: {primary_email}")

    # Authenticate or create user
    user = crud.authenticate_github(
        session=session,
        primary_email=primary_email,
        profile=profile,
    )

    expires_delta = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)

    access_token = security.create_access_token(user.id, expires_delta)

    # Absolute expiration timestamp (UTC)
    expires_at = datetime.now(timezone.utc) + expires_delta
    expires_timestamp = int(expires_at.timestamp())

    # Build redirect URL to Next.js cookie-setter
    base_url = f"{settings.SITE_URL}/api/auth/set-cookie"
    query = urlencode(
        {
            "access_token": access_token,
            "expires": expires_timestamp,
        }
    )
    redirect_url = f"{base_url}?{query}"

    response = RedirectResponse(url=redirect_url, status_code=302)

    return response
