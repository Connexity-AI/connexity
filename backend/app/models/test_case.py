import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator
from sqlalchemy import Column, Index, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.agent import Agent
from app.models.enums import Difficulty, FirstTurn, TestCaseStatus
from app.models.schemas import ExpectedToolCall

if TYPE_CHECKING:
    from app.models.eval_set import EvalSetMember
    from app.models.test_case_result import TestCaseResult


class TestCaseBase(SQLModel):
    """Base fields shared by ORM and API schemas.

    JSONB columns use raw dict/list types for SQLAlchemy compatibility.
    API-facing schemas (TestCaseCreate, TestCasePublic, TestCaseUpdate)
    override expected_tool_calls with typed Pydantic models.
    """

    name: str = Field(max_length=255, description="Human-readable short name")
    description: str | None = Field(
        default=None, description="What this test case checks (for humans)"
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
    status: TestCaseStatus = Field(
        default=TestCaseStatus.ACTIVE,
        description="Lifecycle status — only active test cases run by default",
        sa_column=Column(
            SAEnum(
                TestCaseStatus,
                name="testcasestatus",
                native_enum=True,
                values_callable=lambda m: [e.name for e in m],
            ),
            nullable=False,
            index=True,
        ),
    )
    persona_context: str | None = Field(
        default=None,
        description=(
            "Free-form persona description for the LLM simulator "
            "(type, description, behavioral instructions in one text block)"
        ),
    )
    first_turn: FirstTurn = Field(
        default=FirstTurn.PERSONA,
        description="Who speaks first in the conversation: agent or persona",
        sa_column=Column(
            SAEnum(
                FirstTurn,
                name="firstturn",
                native_enum=True,
                values_callable=lambda m: [e.name for e in m],
            ),
            nullable=False,
            server_default="PERSONA",
        ),
    )
    first_message: str | None = Field(
        default=None,
        description=(
            "Opening message for whoever speaks first. "
            "When first_turn=persona this is the user's opener; "
            "when first_turn=agent this is the agent's greeting."
        ),
    )
    user_context: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column("user_context", JSONB, nullable=True),
        description="Free-form domain knowledge JSON-dumped into simulator prompt",
    )
    expected_outcomes: list[str] | None = Field(
        default=None,
        sa_column=Column("expected_outcomes", JSONB, nullable=True),
        description=(
            "List of true-statement assertions the judge evaluates "
            '(e.g. "Agent MUST confirm the appointment date")'
        ),
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
    agent_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="agent.id",
        index=True,
        description="Agent this test case belongs to (test suite pool for that agent)",
    )

    @field_validator("expected_tool_calls", mode="before")
    @classmethod
    def _serialize_expected_tool_calls(cls, v: Any) -> list[dict[str, Any]] | None:
        if isinstance(v, list):
            return [
                item.model_dump() if isinstance(item, BaseModel) else item for item in v
            ]
        return v


class TestCase(TestCaseBase, table=True):
    __tablename__ = "test_case"

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
    agent: Agent | None = Relationship(back_populates="test_cases")
    eval_set_links: list["EvalSetMember"] = Relationship(
        back_populates="test_case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    test_case_results: list["TestCaseResult"] = Relationship(
        back_populates="test_case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    __table_args__ = (Index("ix_test_case_tags_gin", "tags", postgresql_using="gin"),)


class TestCaseCreate(TestCaseBase):
    expected_tool_calls: list[ExpectedToolCall] | None = None  # type: ignore[assignment]


class TestCaseUpdate(SQLModel):
    name: str | None = Field(default=None, description="Human-readable short name")
    description: str | None = Field(
        default=None, description="What this test case checks (for humans)"
    )
    difficulty: Difficulty | None = Field(
        default=None, description="Two-level difficulty classification"
    )
    tags: list[str] | None = Field(
        default=None, description="Free-form tags for grouping and filtering"
    )
    status: TestCaseStatus | None = Field(
        default=None,
        description="Lifecycle status — only active test cases run by default",
    )
    persona_context: str | None = Field(
        default=None, description="Free-form persona description for the LLM simulator"
    )
    first_turn: FirstTurn | None = Field(
        default=None, description="Who speaks first: agent or persona"
    )
    first_message: str | None = Field(
        default=None, description="Opening message for whoever speaks first"
    )
    user_context: dict[str, Any] | None = None
    expected_outcomes: list[str] | None = None
    expected_tool_calls: list[ExpectedToolCall] | None = None
    evaluation_criteria_override: str | None = Field(
        default=None,
        description="Custom judge prompt section that overrides default criteria",
    )
    agent_id: uuid.UUID | None = Field(
        default=None,
        description="Agent this test case belongs to (test suite pool for that agent)",
    )


class TestCasePublic(TestCaseBase):
    id: uuid.UUID = Field(description="Unique test case identifier")
    created_at: datetime = Field(description="When the test case was created")
    updated_at: datetime = Field(description="When the test case was last updated")
    expected_tool_calls: list[ExpectedToolCall] | None = None  # type: ignore[assignment]


class TestCasesPublic(SQLModel):
    data: list[TestCasePublic] = Field(description="List of test cases")
    count: int = Field(description="Total number of test cases matching the query")


class OnConflict(StrEnum):
    SKIP = "skip"
    OVERWRITE = "overwrite"


class TestCaseImportItem(TestCaseCreate):
    """Test case payload for import — optional id enables round-trip and conflict detection."""

    id: uuid.UUID | None = None


class TestCaseImportResult(SQLModel):
    created: int
    skipped: int
    overwritten: int
    total: int
    errors: list[str] = Field(
        default_factory=list, description="Per-item error messages"
    )


class TestCasesExport(SQLModel):
    exported_at: datetime
    count: int
    test_cases: list[TestCasePublic]
