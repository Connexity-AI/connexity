import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, ForeignKey, Text, text
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import IntegrationProvider


class IntegrationBase(SQLModel):
    provider: IntegrationProvider = Field(
        index=True, sa_type=enum_type(IntegrationProvider)
    )
    name: str = Field(max_length=255)
    # The address of the user's own instance. Only for providers that have one (n8n).
    base_url: str | None = Field(default=None, max_length=2048)


class Integration(IntegrationBase, table=True):
    __tablename__ = "integration"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
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


class AgentToolBackend(SQLModel, table=True):
    """Which workflow serves one of an agent's tools.

    A tool call's execution is looked for only among that workflow's executions. A tool
    with no row has no backend (a tool built into the voice provider, for example).
    """

    __tablename__ = "agent_tool_backend"

    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), primary_key=True, nullable=False
        )
    )
    tool_name: str = Field(max_length=255, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    integration_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("integration.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    workflow_id: str = Field(max_length=64)
    workflow_name: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class ToolBackendPublic(SQLModel):
    integration_id: uuid.UUID
    integration_name: str
    workflow_id: str
    workflow_name: str


class AgentToolPublic(SQLModel):
    """A tool seen in an agent's calls, and the workflow it is mapped to, if any."""

    name: str
    call_count: int = Field(description="Tool calls with this name across the agent")
    backend: ToolBackendPublic | None = None


class ToolBackendSet(SQLModel):
    tool_name: str = Field(min_length=1, max_length=255)
    integration_id: uuid.UUID
    workflow_id: str = Field(min_length=1, max_length=64, regex=r"^[A-Za-z0-9_-]+$")


class WorkflowSummary(SQLModel):
    id: str
    name: str
    active: bool = False
