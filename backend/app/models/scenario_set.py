import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.scenario import Scenario


class ScenarioSetMember(SQLModel, table=True):
    """Many-to-many join table between ScenarioSet and Scenario."""

    __tablename__ = "scenario_set_member"

    scenario_set_id: uuid.UUID = Field(
        foreign_key="scenario_set.id",
        primary_key=True,
        index=True,
        description="FK to the parent scenario set",
    )
    scenario_id: uuid.UUID = Field(
        foreign_key="scenario.id",
        primary_key=True,
        description="FK to the linked scenario",
    )
    position: int = Field(
        default=0, description="Sort order of the scenario within the set"
    )

    # Relationships
    scenario_set: "ScenarioSet" = Relationship(back_populates="scenario_links")
    scenario: "Scenario" = Relationship(back_populates="scenario_set_links")


class ScenarioSetBase(SQLModel):
    name: str = Field(max_length=255, index=True, description="Human-readable set name")
    description: str | None = Field(
        default=None, description="What this scenario set covers"
    )
    version: int = Field(
        default=1,
        description="Monotonically increasing version for snapshot tracking",
    )


class ScenarioSet(ScenarioSetBase, table=True):
    __tablename__ = "scenario_set"

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
    scenario_links: list[ScenarioSetMember] = Relationship(
        back_populates="scenario_set",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    runs: list["Run"] = Relationship(back_populates="scenario_set")


class ScenarioSetCreate(ScenarioSetBase):
    scenario_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Scenarios to include in the set on creation",
    )


class ScenarioSetUpdate(SQLModel):
    name: str | None = Field(default=None, description="Human-readable set name")
    description: str | None = Field(
        default=None, description="What this scenario set covers"
    )
    version: int | None = Field(
        default=None,
        description="Monotonically increasing version for snapshot tracking",
    )


class ScenarioSetPublic(ScenarioSetBase):
    id: uuid.UUID = Field(description="Unique scenario set identifier")
    created_at: datetime = Field(description="When the set was created")
    updated_at: datetime = Field(description="When the set was last updated")


class ScenarioSetsPublic(SQLModel):
    data: list[ScenarioSetPublic] = Field(description="List of scenario sets")
    count: int = Field(description="Total number of sets matching the query")


class ScenarioSetMembersUpdate(SQLModel):
    scenario_ids: list[uuid.UUID]
