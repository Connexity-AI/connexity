import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, field_validator
from sqlalchemy import Column, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.agent import Agent
from app.models.columns import enum_type
from app.models.enums import FirstTurn, TestCaseStatus

if TYPE_CHECKING:
    from app.models.eval_config import EvalConfigMember
    from app.models.test_case_result import TestCaseResult


class TestCaseBase(SQLModel):
    """A scenario's stored fields (`plans/2026-11-17-scenarios.md`)."""

    name: str = Field(max_length=255, description="Human-readable short name")
    description: str | None = Field(
        default=None, description="What this test case checks (for humans)"
    )
    status: TestCaseStatus = Field(
        default=TestCaseStatus.ACTIVE,
        description="Lifecycle status — only active test cases run by default",
        nullable=False,
        index=True,
        sa_type=enum_type(TestCaseStatus),
    )
    persona_context: str | None = Field(
        default=None,
        description=(
            "Free-form persona description for the LLM simulator "
            "(type, description, behavioral instructions in one text block)"
        ),
    )
    first_turn: FirstTurn = Field(
        default=FirstTurn.USER,
        description="Who speaks first in the conversation: agent or user",
        nullable=False,
        sa_type=enum_type(FirstTurn),
    )
    first_message: str | None = Field(
        default=None,
        description=(
            "Opening message for whoever speaks first. "
            "When first_turn=user this is the user's opener; "
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
    agent_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="agent.id",
        index=True,
        description="Agent this test case belongs to (test suite pool for that agent)",
    )
    source_call_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="call.id",
        index=True,
        description="Call this test case was created from (Observer drawer)",
    )

    @field_validator("expected_tool_calls", mode="before")
    @classmethod
    def _serialize_expected_tool_calls(cls, v: Any) -> list[dict[str, Any]] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            return v  # type: ignore[return-value]
        return [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in v
        ]


class TestCase(TestCaseBase, table=True):
    __tablename__ = "test_case"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
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
    deleted_at: datetime | None = Field(default=None, index=True)
    # A scenario's caller, beside who they are (`persona_context`): their goal and how
    # they behave (`plans/2026-11-17-scenarios.md`).
    caller_goal: str | None = Field(default=None, sa_column=Column(Text))
    caller_behaviour: str | None = Field(default=None, sa_column=Column(Text))
    # The values the agent's platform passes in (dynamic variables), kept apart from
    # what the caller knows (`user_context`).
    agent_variables: dict[str, Any] | None = Field(
        default=None, sa_column=Column("agent_variables", JSONB, nullable=True)
    )

    # Relationships
    agent: Agent | None = Relationship(back_populates="test_cases")
    eval_config_links: list["EvalConfigMember"] = Relationship(
        back_populates="test_case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    test_case_results: list["TestCaseResult"] = Relationship(
        back_populates="test_case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
