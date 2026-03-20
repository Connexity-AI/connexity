import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Column, Index, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import Difficulty, ScenarioStatus, SimulationMode
from app.models.schemas import ExpectedOutcome, ScriptedStep

if TYPE_CHECKING:
    from app.models.scenario_result import ScenarioResult
    from app.models.scenario_set import ScenarioSetMember


class ScenarioBase(SQLModel):
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    difficulty: Difficulty = Field(default=Difficulty.NORMAL, index=True)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default="{}"),
    )
    status: ScenarioStatus = Field(default=ScenarioStatus.ACTIVE, index=True)
    simulation_mode: SimulationMode = Field(default=SimulationMode.LLM_DRIVEN)
    scripted_steps: list[ScriptedStep] | None = Field(
        default=None, sa_column=Column("scripted_steps", JSONB, nullable=True)
    )
    user_persona: str | None = Field(default=None)
    user_goal: str | None = Field(default=None)
    initial_message: str | None = Field(default=None)
    max_turns: int = Field(default=20)
    expected_outcomes: list[ExpectedOutcome] = Field(
        default_factory=list,
        sa_column=Column("expected_outcomes", JSONB, nullable=False, server_default="[]"),
    )
    evaluation_criteria_override: str | None = Field(default=None)


class Scenario(ScenarioBase, table=True):
    __tablename__ = "scenario"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": text("now()"), "onupdate": datetime.now},
    )

    # Relationships
    scenario_set_links: list["ScenarioSetMember"] = Relationship(
        back_populates="scenario"
    )
    scenario_results: list["ScenarioResult"] = Relationship(
        back_populates="scenario"
    )

    __table_args__ = (
        Index("ix_scenario_tags_gin", "tags", postgresql_using="gin"),
    )


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    difficulty: Difficulty | None = None
    tags: list[str] | None = None
    status: ScenarioStatus | None = None
    simulation_mode: SimulationMode | None = None
    scripted_steps: list[ScriptedStep] | None = None
    user_persona: str | None = None
    user_goal: str | None = None
    initial_message: str | None = None
    max_turns: int | None = None
    expected_outcomes: list[ExpectedOutcome] | None = None
    evaluation_criteria_override: str | None = None


class ScenarioPublic(ScenarioBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ScenariosPublic(SQLModel):
    data: list[ScenarioPublic]
    count: int
