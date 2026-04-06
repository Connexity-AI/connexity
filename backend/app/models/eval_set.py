import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.test_case import TestCase


class EvalSetMember(SQLModel, table=True):
    """Many-to-many join table between EvalSet and TestCase."""

    __tablename__ = "eval_set_member"

    eval_set_id: uuid.UUID = Field(
        foreign_key="eval_set.id",
        primary_key=True,
        index=True,
        description="FK to the parent eval set",
    )
    test_case_id: uuid.UUID = Field(
        foreign_key="test_case.id",
        primary_key=True,
        description="FK to the linked test case",
    )
    position: int = Field(
        default=0, description="Sort order of the test case within the set"
    )
    repetitions: int = Field(
        default=1,
        ge=1,
        description="How many times to execute this test case within the set",
    )

    # Relationships
    eval_set: "EvalSet" = Relationship(back_populates="test_case_links")
    test_case: "TestCase" = Relationship(back_populates="eval_set_links")


class EvalSetMemberEntry(SQLModel):
    """API payload for adding or replacing set members with per-test-case repetition counts."""

    test_case_id: uuid.UUID = Field(description="Test case to include in the set")
    repetitions: int = Field(
        default=1,
        ge=1,
        description="How many times to execute this test case within one set pass",
    )


class EvalSetMemberPublic(SQLModel):
    """Public view of one test case's membership in a set."""

    test_case_id: uuid.UUID = Field(description="Linked test case id")
    position: int = Field(description="Order within the set")
    repetitions: int = Field(
        ge=1, description="Executions per set pass for this test case"
    )


class EvalSetMembersPublic(SQLModel):
    data: list[EvalSetMemberPublic] = Field(
        description="Set members with position and repetitions"
    )
    count: int = Field(description="Total members matching the query")


class EvalSetBase(SQLModel):
    name: str = Field(max_length=255, index=True, description="Human-readable set name")
    description: str | None = Field(
        default=None, description="What this eval set covers"
    )
    version: int = Field(
        default=1,
        description="Monotonically increasing version for snapshot tracking",
    )
    set_repetitions: int = Field(
        default=1,
        ge=1,
        description="How many times to repeat the entire set during a run",
    )


class EvalSet(EvalSetBase, table=True):
    __tablename__ = "eval_set"

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
    test_case_links: list[EvalSetMember] = Relationship(
        back_populates="eval_set",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    runs: list["Run"] = Relationship(back_populates="eval_set")


class EvalSetCreate(SQLModel):
    name: str = Field(max_length=255, description="Human-readable set name")
    description: str | None = Field(
        default=None, description="What this eval set covers"
    )
    set_repetitions: int = Field(
        default=1,
        ge=1,
        description="How many times to repeat the entire set during a run",
    )
    members: list[EvalSetMemberEntry] | None = Field(
        default=None,
        description="Initial members with per-test-case repetitions (omit or empty for none)",
    )


class EvalSetUpdate(SQLModel):
    name: str | None = Field(default=None, description="Human-readable set name")
    description: str | None = Field(
        default=None, description="What this eval set covers"
    )
    set_repetitions: int | None = Field(
        default=None,
        ge=1,
        description="How many times to repeat the entire set during a run",
    )


class EvalSetPublic(EvalSetBase):
    id: uuid.UUID = Field(description="Unique eval set identifier")
    test_case_count: int = 0
    effective_test_case_count: int = Field(
        default=0,
        description="Sum(member.repetitions) * set_repetitions — total expanded executions",
    )
    created_at: datetime = Field(description="When the set was created")
    updated_at: datetime = Field(description="When the set was last updated")


class EvalSetsPublic(SQLModel):
    data: list[EvalSetPublic] = Field(description="List of eval sets")
    count: int = Field(description="Total number of sets matching the query")


class EvalSetMembersUpdate(SQLModel):
    members: list[EvalSetMemberEntry]
