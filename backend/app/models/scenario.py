import uuid
from datetime import UTC, datetime
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
    simulation_mode: SimulationMode = Field(
        default=SimulationMode.LLM_DRIVEN,
        description="How the user side of the conversation is driven",
    )
    scripted_steps: list[ScriptedStep] | None = Field(
        default=None,
        sa_column=Column("scripted_steps", JSONB, nullable=True),
        description="Ordered steps for scripted simulation mode",
    )
    user_persona: str | None = Field(
        default=None,
        description="Persona description for the simulated user",
    )
    user_goal: str | None = Field(
        default=None,
        description="High-level goal the simulated user is trying to achieve",
    )
    initial_message: str | None = Field(
        default=None,
        description="First message the simulated user sends to the agent",
    )
    max_turns: int = Field(
        default=100,
        description="Maximum conversation turns before the scenario is stopped",
    )
    expected_outcomes: list[ExpectedOutcome] = Field(
        default_factory=list,
        sa_column=Column(
            "expected_outcomes", JSONB, nullable=False, server_default="[]"
        ),
        description="Success criteria the judge evaluates against",
    )
    evaluation_criteria_override: str | None = Field(
        default=None,
        description="Custom judge prompt section that overrides default criteria",
    )


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
    pass


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
    simulation_mode: SimulationMode | None = Field(
        default=None,
        description="How the user side of the conversation is driven",
    )
    scripted_steps: list[ScriptedStep] | None = Field(
        default=None, description="Ordered steps for scripted simulation mode"
    )
    user_persona: str | None = Field(
        default=None, description="Persona description for the simulated user"
    )
    user_goal: str | None = Field(
        default=None,
        description="High-level goal the simulated user is trying to achieve",
    )
    initial_message: str | None = Field(
        default=None,
        description="First message the simulated user sends to the agent",
    )
    max_turns: int | None = Field(
        default=None,
        description="Maximum conversation turns before the scenario is stopped",
    )
    expected_outcomes: list[ExpectedOutcome] | None = Field(
        default=None, description="Success criteria the judge evaluates against"
    )
    evaluation_criteria_override: str | None = Field(
        default=None,
        description="Custom judge prompt section that overrides default criteria",
    )


class ScenarioPublic(ScenarioBase):
    id: uuid.UUID = Field(description="Unique scenario identifier")
    created_at: datetime = Field(description="When the scenario was created")
    updated_at: datetime = Field(description="When the scenario was last updated")


class ScenariosPublic(SQLModel):
    data: list[ScenarioPublic] = Field(description="List of scenarios")
    count: int = Field(description="Total number of scenarios matching the query")
