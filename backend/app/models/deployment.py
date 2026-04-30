import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlmodel import Field, SQLModel

from app.models.enums import DeploymentStatus


class DeploymentBase(SQLModel):
    environment_id: uuid.UUID = Field(foreign_key="environment.id", index=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True)
    agent_version: int = Field(ge=1)


class Deployment(DeploymentBase, table=True):
    __tablename__ = "deployment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    retell_version_name: str | None = Field(default=None, max_length=255)
    status: DeploymentStatus = Field(default=DeploymentStatus.PENDING, index=True)
    error_message: str | None = Field(default=None)
    deployed_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    deployed_by_name: str | None = Field(default=None, max_length=255)
    deployed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
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


class DeploymentCreate(SQLModel):
    agent_version: int = Field(ge=1)


class DeploymentPublic(SQLModel):
    id: uuid.UUID
    environment_id: uuid.UUID
    environment_name: str
    agent_id: uuid.UUID
    agent_version: int
    retell_version_name: str | None
    status: DeploymentStatus
    error_message: str | None
    deployed_by_user_id: uuid.UUID | None
    deployed_by_name: str | None
    deployed_at: datetime


class DeploymentsPublic(SQLModel):
    data: list[DeploymentPublic]
    count: int
