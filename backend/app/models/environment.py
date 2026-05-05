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
    current_version_number: int | None = Field(default=None)
    current_version_name: str | None = Field(default=None, max_length=255)
    current_deployed_at: datetime | None = Field(default=None)
    eval_gate_eval_config_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="eval_config.id",
        index=True,
        description=(
            "When set, deploys to this environment are gated on a passing run "
            "of this eval config for the requested agent version."
        ),
    )
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
    eval_gate_eval_config_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional: gate deploys on a passing run of this eval config for "
            "the requested agent version."
        ),
    )


class EnvironmentPublic(EnvironmentBase):
    id: uuid.UUID
    agent_id: uuid.UUID
    integration_id: uuid.UUID
    integration_name: str
    platform_agent_id: str
    platform_agent_name: str
    current_version_number: int | None
    current_version_name: str | None
    current_deployed_at: datetime | None
    eval_gate_eval_config_id: uuid.UUID | None
    created_at: datetime


class EnvironmentsPublic(SQLModel):
    data: list[EnvironmentPublic]
    count: int
