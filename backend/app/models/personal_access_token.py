import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel

PERSONAL_ACCESS_TOKEN_PREFIX = "cxp_"
PERSONAL_ACCESS_TOKEN_VISIBLE_CHARS = 12
CLAUDE_CODE_TOKEN_NAME = "Claude Code"


class PersonalAccessToken(SQLModel, table=True):
    """A credential an assistant uses to act as one person, instead of OAuth.

    It belongs to the person, not a workspace: like an OAuth connection it reaches
    exactly the workspaces that person can reach. It never expires; it stops working
    when revoked. Only a hash is stored; the token is returned once, when created.
    """

    __tablename__ = "personal_access_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    name: str = Field(max_length=255)
    prefix: str = Field(
        max_length=PERSONAL_ACCESS_TOKEN_VISIBLE_CHARS,
        description="The first characters of the token, to recognise it in a list",
    )
    token_hash: str = Field(max_length=64, unique=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"server_default": text("now()")},
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )


class PersonalAccessTokenPublic(SQLModel):
    id: uuid.UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None = Field(
        description="When an assistant last called Connexity with it; empty if never"
    )


class PersonalAccessTokensPublic(SQLModel):
    data: list[PersonalAccessTokenPublic]
    count: int


class PersonalAccessTokenCreated(PersonalAccessTokenPublic):
    token: str = Field(description="The token itself. Shown only in this response.")
    setup_prompt: str = Field(
        description="The prompt to paste into Claude Code; it contains the token"
    )
