import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Field, SQLModel

from app.models.enums import Platform


class EnvironmentBase(SQLModel):
    name: str = Field(max_length=255)
    platform: Platform = Field(...)


class Environment(EnvironmentBase, table=True):
    __tablename__ = "environment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    integration_id: uuid.UUID = Field(foreign_key="integration.id", index=True)
    platform_agent_id: str = Field(max_length=255, index=True)
    platform_agent_name: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": lambda: datetime.now(UTC),
        },
    )


class EnvironmentCreate(EnvironmentBase):
    agent_id: uuid.UUID
    integration_id: uuid.UUID
    platform_agent_id: str
    platform_agent_name: str


class EnvironmentPublic(EnvironmentBase):
    id: uuid.UUID
    agent_id: uuid.UUID
    integration_id: uuid.UUID
    integration_name: str
    platform_agent_id: str
    platform_agent_name: str
    created_at: datetime


class EnvironmentsPublic(SQLModel):
    data: list[EnvironmentPublic]
    count: int
