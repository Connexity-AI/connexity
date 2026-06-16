from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import crud
from app.api.deps import (
    CurrentUser,
    SessionDep,
)
from app.core.security import get_password_hash, verify_password
from app.models import (
    Message,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UserUpdateMe,
)


class OnboardingStatusPublic(BaseModel):
    """Whether the user has completed the post-signup setup steps."""

    has_llm_key: bool
    onboarding_complete: bool


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """

    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not current_user.hashed_password or not verify_password(
        body.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.get("/me/onboarding-status", response_model=OnboardingStatusPublic)
def read_onboarding_status(
    session: SessionDep, current_user: CurrentUser
) -> OnboardingStatusPublic:
    """Whether the post-signup onboarding flow is complete.

    Currently the only required step is providing an LLM API key. When
    ``onboarding_complete`` is False the frontend routes the user to the
    onboarding page instead of the dashboard.
    """
    company = crud.get_company(session=session, company_id=current_user.company_id)
    has_key = company is not None and crud.company_has_any_llm_key(company=company)
    return OnboardingStatusPublic(
        has_llm_key=has_key,
        onboarding_complete=has_key,
    )


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    session.delete(current_user)
    session.commit()
    return Message(message="Account deleted successfully")
