"""Runs of scenarios: a spec rule's verdict in each simulated call, and what code checks
found there (`plans/2026-11-17-text-runner.md`, `docs-internal/testing.md`).

A run is a 1.x `run` and each simulated call a `test_case_result`, until test results
(10.1293) settle how they are shown.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import CheckKind, CheckMode, RuleOutcome, RunScope, RunStatus


class RuleVerdict(SQLModel, table=True):
    """One listed rule's verdict in one simulated call."""

    __tablename__ = "rule_verdict"
    __table_args__ = (UniqueConstraint("test_case_result_id", "rule_key"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="company.id", index=True)
    agent_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("agent.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    run_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("run.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    test_case_result_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("test_case_result.id", ondelete="CASCADE"), nullable=False
        )
    )
    test_case_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("test_case.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    rule_key: str = Field(sa_column=Column(String(64), nullable=False, index=True))
    outcome: RuleOutcome = Field(sa_type=enum_type(RuleOutcome))
    reason: str | None = Field(default=None, sa_column=Column("reason", Text))
    turns: list[int] | None = Field(
        default=None, sa_column=Column("turns", JSONB, nullable=True)
    )
    # Whether the rule was critical in the spec version the run judged.
    critical: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"server_default": text("now()")},
    )


class SimulatedFinding(BaseModel):
    """What one code check found in a simulated call. Stored on the call's
    ``test_case_result.check_findings``; never a production finding."""

    check_type: str
    check_version: int
    kind: CheckKind
    mode: CheckMode
    key: str | None = None
    event_ids: list[str]
    detail: dict[str, Any] | None = None


# ── Answers ───────────────────────────────────────────────────────


class RuleTotalPublic(BaseModel):
    key: str
    text: str | None = PydanticField(
        default=None, description="The rule in the spec version the run judged"
    )
    critical: bool = False
    passed: int = 0
    failed: int = 0
    did_not_come_up: int = 0
    flaky: bool = PydanticField(
        default=False, description="It both passed and failed across repeats"
    )


class CheckTotalPublic(BaseModel):
    check_type: str
    title: str
    found: int = PydanticField(description="Simulated calls where it found something")


class VerdictPublic(BaseModel):
    key: str
    outcome: RuleOutcome
    reason: str | None = None
    turns: list[int] = PydanticField(default_factory=list)


class SimulatedCallPublic(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID
    scenario_name: str
    repeat: int = PydanticField(description="Which repeat, from 1")
    finished: bool
    error: str | None = None
    turns: int | None = None
    verdicts: list[VerdictPublic] = PydanticField(default_factory=list)
    findings: list[SimulatedFinding] = PydanticField(default_factory=list)
    default_fakes: list[str] = PydanticField(default_factory=list)
    cost_usd: float | None = None


class TestRunCountsPublic(BaseModel):
    calls: int = PydanticField(description="Simulated calls the run makes")
    finished: int = 0
    errors: int = 0
    rules_failed: int = 0
    critical_failed: int = 0
    flaky: int = 0
    findings: int = 0


class TestRunPublic(BaseModel):
    id: uuid.UUID
    status: RunStatus
    status_detail: str | None = None
    scope: RunScope
    set_name: str | None = None
    repeats: int
    spec_version: int | None = None
    platform_version: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    counts: TestRunCountsPublic
    cost_usd: float | None = None


class TestRunDetailPublic(TestRunPublic):
    rules: list[RuleTotalPublic] = PydanticField(
        default_factory=list, description="Failed rules first, critical first"
    )
    dropped_rules: list[str] = PydanticField(
        default_factory=list,
        description="Rule keys scenarios list that the run's spec no longer has",
    )
    checks: list[CheckTotalPublic] = PydanticField(default_factory=list)
    calls: list[SimulatedCallPublic] = PydanticField(default_factory=list)
