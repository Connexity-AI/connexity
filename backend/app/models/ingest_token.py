import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Field, SQLModel

from app.models.enums import TraceCapability
from app.models.trace import Trace

INGEST_TOKEN_PREFIX = "cxi_"
INGEST_TOKEN_VISIBLE_CHARS = 12


class IngestToken(SQLModel, table=True):
    """A credential that can send traces for one company and do nothing else.

    Only a hash of the token is stored. The token itself is returned once, by the
    request that creates it.
    """

    __tablename__ = "ingest_token"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    name: str = Field(max_length=255)
    prefix: str = Field(
        max_length=INGEST_TOKEN_VISIBLE_CHARS,
        description="The first characters of the token, to recognise it in a list",
    )
    token_hash: str = Field(max_length=64, unique=True, index=True)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    last_used_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)


class IngestTokenCreate(SQLModel):
    name: str = Field(min_length=1, max_length=255)


class IngestTokenPublic(SQLModel):
    id: uuid.UUID
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class IngestTokenCreated(IngestTokenPublic):
    token: str = Field(description="The token itself. Shown only in this response.")


class IngestTokensPublic(SQLModel):
    data: list[IngestTokenPublic]
    count: int


class IngestTraceRequest(SQLModel):
    agent_id: uuid.UUID = Field(description="The Connexity agent the call belongs to")
    trace: Trace
    raw: dict[str, object] | None = Field(
        default=None,
        description="The provider's original payload, stored unmodified beside the call",
    )


class IngestTraceResult(SQLModel):
    call_id: uuid.UUID
    created: bool = Field(
        description="True when the call is new; false when its trace was replaced"
    )
    capabilities: list[TraceCapability]
    missing_capabilities: list[TraceCapability]
