import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class OAuthClient(SQLModel, table=True):
    __tablename__ = "oauth_client"

    client_id: str = Field(primary_key=True, max_length=128)
    # OAuth clients are app-wide (e.g. Claude.ai). They are not scoped to a
    # single company — only the user-bound rows (authorization codes and
    # refresh tokens) carry the tenant scope.
    client_name: str | None = Field(default=None, max_length=255)
    redirect_uris: list[str] = Field(sa_column=Column(JSONB, nullable=False))
    grant_types: list[str] = Field(sa_column=Column(JSONB, nullable=False))
    response_types: list[str] = Field(sa_column=Column(JSONB, nullable=False))
    scope: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    token_endpoint_auth_method: str = Field(default="none", max_length=64)
    raw_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class OAuthAuthorizationCode(SQLModel, table=True):
    __tablename__ = "oauth_authorization_code"

    code: str = Field(primary_key=True, max_length=255)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    client_id: str = Field(foreign_key="oauth_client.client_id", index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    redirect_uri: str = Field(max_length=2048)
    scope: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    resource: str = Field(max_length=2048)
    code_challenge: str = Field(max_length=255)
    code_challenge_method: str = Field(default="S256", max_length=16)
    expires_at: datetime
    consumed_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class OAuthRefreshToken(SQLModel, table=True):
    __tablename__ = "oauth_refresh_token"

    token_hash: str = Field(primary_key=True, max_length=64)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    client_id: str = Field(foreign_key="oauth_client.client_id", index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    scope: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    resource: str = Field(max_length=2048)
    expires_at: datetime
    revoked_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class OAuthClientRegistrationRequest(SQLModel):
    redirect_uris: list[str]
    client_name: str | None = None
    grant_types: list[str] | None = None
    response_types: list[str] | None = None
    scope: str | None = None
    token_endpoint_auth_method: str | None = None


class OAuthClientRegistrationResponse(SQLModel):
    client_id: str
    client_id_issued_at: int
    client_name: str | None = None
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    scope: str | None = None
    token_endpoint_auth_method: str = "none"
