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
        foreign_key="scenario_set.id", primary_key=True, index=True
    )
    scenario_id: uuid.UUID = Field(foreign_key="scenario.id", primary_key=True)
    position: int = Field(default=0)

    # Relationships
    scenario_set: "ScenarioSet" = Relationship(back_populates="scenario_links")
    scenario: "Scenario" = Relationship(back_populates="scenario_set_links")


class ScenarioSetBase(SQLModel):
    name: str = Field(max_length=255, index=True)
    description: str | None = Field(default=None)
    version: int = Field(default=1)


class ScenarioSet(ScenarioSetBase, table=True):
    __tablename__ = "scenario_set"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()"), "onupdate": datetime.now},
    )

    # Relationships
    scenario_links: list[ScenarioSetMember] = Relationship(
        back_populates="scenario_set"
    )
    runs: list["Run"] = Relationship(back_populates="scenario_set")


class ScenarioSetCreate(ScenarioSetBase):
    scenario_ids: list[uuid.UUID] | None = None


class ScenarioSetUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    version: int | None = None


class ScenarioSetPublic(ScenarioSetBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ScenarioSetsPublic(SQLModel):
    data: list[ScenarioSetPublic]
    count: int


class ScenarioSetMembersUpdate(SQLModel):
    scenario_ids: list[uuid.UUID]
