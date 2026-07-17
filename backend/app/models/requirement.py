import uuid
from datetime import UTC, datetime

from pydantic import ConfigDict
from sqlalchemy import Column, Index, Text, text
from sqlmodel import Field, SQLModel

from app.models.enums import RequirementsStatus


class RequirementBase(SQLModel):
    text: str = Field(
        sa_column=Column(Text, nullable=False),
        description="Atomic, testable statement of what the agent must do",
    )
    category: str | None = Field(
        default=None,
        max_length=64,
        description="LLM-assigned grouping (e.g. capability, guardrail, routing, tool-use)",
    )
    source_ref: str | None = Field(
        default=None,
        max_length=255,
        description=(
            "Pointer back to where this requirement came from — a prompt section "
            "label or a Retell conversation-flow node id/name. Seeds future "
            "requirement-to-prompt mapping."
        ),
    )
    order_index: int = Field(
        default=0,
        description="Stable display order within an agent version",
    )


class Requirement(RequirementBase, table=True):
    __tablename__ = "requirement"
    __table_args__ = (Index("ix_requirement_agent_version_id", "agent_version_id"),)
    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(foreign_key="agent.id", index=True, nullable=False)
    agent_version_id: uuid.UUID = Field(
        foreign_key="agent_version.id",
        nullable=False,
        description="Version this requirement snapshot belongs to (immutable per version)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class RequirementPublic(RequirementBase):
    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    agent_version_id: uuid.UUID
    created_at: datetime


class RequirementsPublic(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    data: list[RequirementPublic]
    count: int
    status: RequirementsStatus = Field(
        default=RequirementsStatus.PENDING,
        description="Extraction lifecycle of the active version's requirements",
    )


class RequirementsExtractionStatus(SQLModel):
    model_config = ConfigDict(use_enum_values=True)

    status: RequirementsStatus
