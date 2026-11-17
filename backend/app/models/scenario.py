"""Scenarios: the stage for a simulated call, written by the assistant, with the spec
rules it expects to come up (`plans/2026-11-17-scenarios.md`,
`docs-internal/testing.md`).

A scenario is stored as a 1.x `test_case`, and a set of scenarios as an `eval_config`,
until the runner (10.1292) unfreezes the eval stack that reads them.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.models.enums import FirstTurn


class ScenarioRule(SQLModel, table=True):
    """A spec rule a scenario expects to come up, by the rule's key, so the link holds
    across spec versions."""

    __tablename__ = "scenario_rule"

    test_case_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("test_case.id", ondelete="CASCADE"), primary_key=True
        )
    )
    rule_key: str = Field(sa_column=Column(String(64), primary_key=True))
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    position: int = 0


class FakeToolResultPublic(BaseModel):
    tool: str
    arguments: dict[str, Any] | None = Field(
        default=None,
        description="The arguments it answers (keys must be present); none for any",
    )
    result: dict[str, Any] | None = Field(
        default=None, description="What the tool returns, as JSON"
    )


class ScenarioRulePublic(BaseModel):
    key: str
    text: str | None = Field(
        default=None, description="The rule in the latest spec; none when it is gone"
    )
    critical: bool = False
    gone: bool = Field(
        default=False, description="The latest spec no longer has this rule"
    )


class ScenarioPublic(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    caller: str | None = Field(default=None, description="Who the caller is")
    caller_goal: str | None = None
    caller_behaviour: str | None = None
    caller_knows: dict[str, Any] | None = None
    agent_variables: dict[str, Any] | None = None
    first_turn: FirstTurn
    first_message: str | None = None
    fake_tool_results: list[FakeToolResultPublic] = Field(default_factory=list)
    rules: list[ScenarioRulePublic]
    sets: list[str] = Field(default_factory=list, description="Names of its sets")
    from_call_id: uuid.UUID | None = None
    updated_at: datetime


class ScenarioSetPublic(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    scenario_ids: list[uuid.UUID]


class ScenarioCountsPublic(BaseModel):
    scenarios: int = Field(description="Active scenarios of the agent")
    rules: int = Field(description="Rules in the latest spec")
    rules_listed: int = Field(description="Rules at least one scenario lists")
    critical_unlisted: int = Field(description="Critical rules no scenario lists")
    listing_gone_rules: int = Field(
        description="Scenarios listing a rule the latest spec no longer has"
    )


class ScenarioListPublic(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    data: list[ScenarioPublic]
    next_cursor: str | None = None
    sets: list[ScenarioSetPublic] = Field(default_factory=list)
    counts: ScenarioCountsPublic
    unlisted_rules: list[ScenarioRulePublic] = Field(
        default_factory=list,
        description="Rules no scenario lists, critical first (at most 50)",
    )
