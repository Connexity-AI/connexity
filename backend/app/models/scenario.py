import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator
from sqlalchemy import Column, Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import Difficulty, ScenarioStatus
from app.models.schemas import ExpectedToolCall, Persona

if TYPE_CHECKING:
    from app.models.scenario_result import ScenarioResult
    from app.models.scenario_set import ScenarioSetMember


class ScenarioBase(SQLModel):
    """Base fields shared by ORM and API schemas.

    JSONB columns use raw dict/list types for SQLAlchemy compatibility.
    API-facing schemas (ScenarioCreate, ScenarioPublic, ScenarioUpdate)
    override persona and expected_tool_calls with typed Pydantic models.
    """

    name: str = Field(max_length=255, description="Human-readable short name")
    description: str | None = Field(
        default=None, description="What this scenario tests (for humans)"
    )
    difficulty: Difficulty = Field(
        default=Difficulty.NORMAL,
        index=True,
        description="Two-level difficulty classification",
    )
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
        description="Free-form tags for grouping and filtering",
    )
    status: ScenarioStatus = Field(
        default=ScenarioStatus.ACTIVE,
        index=True,
        description="Lifecycle status — only active scenarios run by default",
    )
    persona: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("persona", JSONB, nullable=True),
        description="Structured persona for the LLM simulator (type, description, instructions)",
    )
    initial_message: str | None = Field(
        default=None,
        description="First message the simulated user sends to the agent",
    )
    user_context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("user_context", JSONB, nullable=True),
        description="Free-form domain knowledge JSON-dumped into simulator prompt",
    )
    max_turns: int | None = Field(
        default=None,
        description="Max conversation turns; null = no cap",
    )
    expected_outcomes: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("expected_outcomes", JSONB, nullable=True),
        description="Free-form success criteria the judge evaluates against",
    )
    expected_tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column("expected_tool_calls", JSONB, nullable=True),
        description="Tool call expectations for judge evaluation",
    )
    evaluation_criteria_override: str | None = Field(
        default=None,
        description="Custom judge prompt section that overrides default criteria",
    )

    @field_validator("persona", mode="before")
    @classmethod
    def _serialize_persona(cls, v: Any) -> dict[str, Any] | None:
        if isinstance(v, BaseModel):
            return v.model_dump()
        return v

    @field_validator("expected_tool_calls", mode="before")
    @classmethod
    def _serialize_expected_tool_calls(cls, v: Any) -> list[dict[str, Any]] | None:
        if isinstance(v, list):
            return [
                item.model_dump() if isinstance(item, BaseModel) else item for item in v
            ]
        return v


class Scenario(ScenarioBase, table=True):
    __tablename__ = "scenario"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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

    # Relationships
    scenario_set_links: list["ScenarioSetMember"] = Relationship(
        back_populates="scenario",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    scenario_results: list["ScenarioResult"] = Relationship(
        back_populates="scenario",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    __table_args__ = (Index("ix_scenario_tags_gin", "tags", postgresql_using="gin"),)


class ScenarioCreate(ScenarioBase):
    persona: Persona | None = None  # type: ignore[assignment]
    expected_tool_calls: list[ExpectedToolCall] | None = None  # type: ignore[assignment]


class ScenarioUpdate(SQLModel):
    name: str | None = Field(default=None, description="Human-readable short name")
    description: str | None = Field(
        default=None, description="What this scenario tests (for humans)"
    )
    difficulty: Difficulty | None = Field(
        default=None, description="Two-level difficulty classification"
    )
    tags: list[str] | None = Field(
        default=None, description="Free-form tags for grouping and filtering"
    )
    status: ScenarioStatus | None = Field(
        default=None,
        description="Lifecycle status — only active scenarios run by default",
    )
    persona: Persona | None = None
    initial_message: str | None = Field(
        default=None,
        description="First message the simulated user sends to the agent",
    )
    user_context: dict[str, Any] | None = None
    max_turns: int | None = Field(
        default=None,
        description="Max conversation turns; null = no cap",
    )
    expected_outcomes: dict[str, Any] | None = None
    expected_tool_calls: list[ExpectedToolCall] | None = None
    evaluation_criteria_override: str | None = Field(
        default=None,
        description="Custom judge prompt section that overrides default criteria",
    )


class ScenarioPublic(ScenarioBase):
    id: uuid.UUID = Field(description="Unique scenario identifier")
    created_at: datetime = Field(description="When the scenario was created")
    updated_at: datetime = Field(description="When the scenario was last updated")
    persona: Persona | None = None  # type: ignore[assignment]
    expected_tool_calls: list[ExpectedToolCall] | None = None  # type: ignore[assignment]


class ScenariosPublic(SQLModel):
    data: list[ScenarioPublic] = Field(description="List of scenarios")
    count: int = Field(description="Total number of scenarios matching the query")


class OnConflict(StrEnum):
    SKIP = "skip"
    OVERWRITE = "overwrite"


class ScenarioImportItem(ScenarioCreate):
    """Scenario payload for import — optional id enables round-trip and conflict detection."""

    id: uuid.UUID | None = None


class ScenarioImportResult(SQLModel):
    created: int
    skipped: int
    overwritten: int
    total: int
    errors: list[str] = Field(
        default_factory=list, description="Per-item error messages"
    )


class ScenariosExport(SQLModel):
    exported_at: datetime
    count: int
    scenarios: list[ScenarioPublic]
