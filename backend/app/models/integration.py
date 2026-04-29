import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, Text, text
from sqlmodel import Field, SQLModel

from app.models.enums import IntegrationProvider


class IntegrationBase(SQLModel):
    provider: IntegrationProvider = Field(max_length=64, index=True)
    name: str = Field(max_length=255)


class Integration(IntegrationBase, table=True):
    __tablename__ = "integration"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    encrypted_api_key: str = Field(sa_column=Column(Text, nullable=False))
    masked_api_key: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class IntegrationCreate(IntegrationBase):
    api_key: str


class IntegrationPublic(IntegrationBase):
    id: uuid.UUID
    created_at: datetime
    masked_api_key: str


class IntegrationsPublic(SQLModel):
    data: list[IntegrationPublic]
    count: int
