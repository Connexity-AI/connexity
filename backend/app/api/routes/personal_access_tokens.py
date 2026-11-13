"""A person's personal access tokens: how Claude Code connects without a sign-in.

Each person manages only their own tokens, from the web app. The token is returned once,
inside the setup prompt the person pastes into Claude Code.
"""

import uuid

from fastapi import APIRouter, HTTPException, status

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import (
    PersonalAccessTokenCreated,
    PersonalAccessTokenPublic,
    PersonalAccessTokensPublic,
)
from app.models.personal_access_token import CLAUDE_CODE_TOKEN_NAME

router = APIRouter(prefix="/personal-access-tokens", tags=["tokens"])


def setup_prompt(*, mcp_url: str, token: str) -> str:
    """What the person pastes into Claude Code. Claude adds Connexity itself."""
    command = (
        f"claude mcp add --transport http --scope user connexity {mcp_url} "
        f'--header "Authorization: Bearer {token}"'
    )
    return (
        "Connect Connexity to Claude Code. Run this command, and do not repeat the "
        f"token in your reply or anywhere else:\n\n{command}\n\n"
        "Then tell me to start a new Claude Code session, where Connexity's tools "
        "load. In it, call `list_workspaces` and `get_readiness`, and follow the next "
        "steps."
    )


@router.post(
    "",
    response_model=PersonalAccessTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_personal_access_token(
    session: SessionDep, current_user: CurrentUser
) -> PersonalAccessTokenCreated:
    """Create a token for Claude Code and the setup prompt that carries it.

    The token is shown only in this answer. The person's earlier tokens keep working.
    """
    mcp_url = settings.oauth_default_resource_url
    if not mcp_url:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The MCP address is not configured on this Connexity",
        )
    row, token = crud.create_personal_access_token(
        session=session, user_id=current_user.id, name=CLAUDE_CODE_TOKEN_NAME
    )
    return PersonalAccessTokenCreated(
        **PersonalAccessTokenPublic.model_validate(row).model_dump(),
        token=token,
        setup_prompt=setup_prompt(mcp_url=mcp_url, token=token),
    )


@router.get("", response_model=PersonalAccessTokensPublic)
def list_personal_access_tokens(
    session: SessionDep, current_user: CurrentUser
) -> PersonalAccessTokensPublic:
    """The person's tokens that still work, newest first. Never the token itself."""
    rows = crud.list_personal_access_tokens(session=session, user_id=current_user.id)
    data = [PersonalAccessTokenPublic.model_validate(row) for row in rows]
    return PersonalAccessTokensPublic(data=data, count=len(data))


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_personal_access_token(
    token_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> None:
    """Revoke one of the person's tokens. The next call with it is refused."""
    row = crud.get_personal_access_token(
        session=session, token_id=token_id, user_id=current_user.id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Token not found")
    crud.revoke_personal_access_token(session=session, token=row)
