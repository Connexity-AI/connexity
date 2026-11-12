import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_user,
)
from app.core import security
from app.core.config import settings
from app.models import Token, UserPublic

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

    access_token, expires = security.create_session_token(
        user_id=user.id, company_id=user.company_id
    )
    return Token(access_token=access_token, expires=expires)


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


# get_current_user() throws if user is not logged in
@router.post("/logout", dependencies=[Depends(get_current_user)])
def logout() -> JSONResponse:
    """
    Delete the HTTP-only cookie during logout
    """
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie(settings.AUTH_COOKIE)
    return response
