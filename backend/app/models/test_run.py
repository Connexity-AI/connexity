"""Runs of scenarios: a spec rule's verdict in each simulated call, and what code checks
found there (`plans/2026-11-17-text-runner.md`, `docs-internal/testing.md`).

A run is a `run` and each simulated call a `test_case_result`.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import Column, ForeignKey, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.columns import enum_type
from app.models.enums import (
    CheckKind,
    CheckMode,
    RuleOutcome,
    RunScope,
    RunStatus,
    VerdictMark,
    VersionVerdict,
)


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
    # Set when the verdict is not evidence; it then counts in no column.
    mark: VerdictMark | None = Field(default=None, sa_type=enum_type(VerdictMark))
    # For a default fake: the tools that answered with it.
    mark_detail: list[str] | None = Field(
        default=None, sa_column=Column("mark_detail", JSONB, nullable=True)
    )
    # The clarifications of the rule in force when the run started, which the judge
    # read with it (plan `plans/2026-11-26-clarification-on-rule.md`).
    clarification_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(
            "clarification_ids",
            JSONB,
            nullable=False,
            server_default=text("'[]'::jsonb"),
        ),
    )
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
    default_fake: int = PydanticField(
        default=0,
        description="Verdicts not counted, because they rest on a default fake",
    )
    flaky: bool = PydanticField(
        default=False, description="It both passed and failed across repeats"
    )


class CheckTotalPublic(BaseModel):
    check_type: str
    title: str
    found: int = PydanticField(description="Simulated calls where it found something")
    critical: bool = PydanticField(
        default=False, description="It fails calls, rather than only flagging them"
    )


class VerdictPublic(BaseModel):
    key: str
    outcome: RuleOutcome
    reason: str | None = None
    turns: list[int] = PydanticField(default_factory=list)
    mark: VerdictMark | None = PydanticField(
        default=None,
        description="Set when the verdict is not evidence and is not counted: "
        "default_fake when it rests on a tool the scenario did not fake",
    )
    mark_detail: list[str] = PydanticField(
        default_factory=list, description="For default_fake: the tools' names"
    )


class SchemaViolationPublic(BaseModel):
    """One argument of one tool call that breaks the tool's own schema."""

    tool: str
    field: str
    problem: str = PydanticField(description="What is wrong, in plain words")
    turn: int = PydanticField(description="The turn of the tool call")


class SchemaViolationTotalPublic(BaseModel):
    tool: str
    field: str
    problem: str
    calls: int = PydanticField(description="Simulated calls where it happened")


class RunSchemaCheckPublic(BaseModel):
    """A run's tool calls checked against the tools' schemas. A violation is a fact
    about what the agent sent; nothing refused it, and it never changes the verdict."""

    tools_checked: int = PydanticField(
        description="Tools of the tested version that declare a schema"
    )
    tools_unreadable: list[str] = PydanticField(
        default_factory=list,
        description="Tools whose schema could not be read, so were not checked",
    )
    calls_with_violations: int = 0
    violations: list[SchemaViolationTotalPublic] = PydanticField(
        default_factory=list, description="Each tool and field, most calls first"
    )


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
    schema_violations: list[SchemaViolationPublic] = PydanticField(
        default_factory=list,
        description="Tool arguments that break the tool's own schema",
    )
    caller_messages: int = PydanticField(
        default=0, description="Messages the simulated caller sent: what is counted"
    )
    cost_usd: float | None = PydanticField(
        default=None,
        description="caller_messages at the list price, once the call has finished; "
        "nothing is billed",
    )
    timing: "CallTimingPublic | None" = PydanticField(
        default=None, description="Where its time went, once finished"
    )
    throttled: int = PydanticField(
        default=0,
        description="Times the platform answered 'too many requests' during the call",
    )
    url: str = PydanticField(description="The simulated call in the app")


class RunProgressPublic(BaseModel):
    """How far a run is, by simulated call."""

    calls: int = PydanticField(description="Simulated calls the run makes")
    queued: int = PydanticField(default=0, description="Not started yet")
    running: int = PydanticField(default=0, description="Started and not finished")
    started: int = PydanticField(default=0, description="Started, finished or not")
    finished: int = 0
    errors: int = PydanticField(
        default=0, description="Finished without verdicts: stopped, or a judge error"
    )
    judge_errors: int = PydanticField(
        default=0,
        description="Of those: the conversation is there, the judge gave no usable "
        "answer. The rest stopped",
    )


class CallTimingPublic(BaseModel):
    """Where a simulated call's time went, in seconds."""

    total_s: float
    agent_s: float = PydanticField(description="Waiting for the agent's platform")
    caller_s: float = PydanticField(description="Waiting for the simulated caller")
    judge_s: float | None = PydanticField(
        default=None, description="Waiting for the judge; none for older calls"
    )
    server_s: float = PydanticField(
        description="The rest: Connexity's own server, mostly waiting for its turn"
    )


class RunTimingPublic(BaseModel):
    """The median of the run's finished calls, in seconds."""

    calls: int = PydanticField(description="Finished calls the medians are over")
    total_s: float
    agent_s: float
    caller_s: float
    judge_s: float | None = None
    server_s: float
    server_share_pct: int = PydanticField(
        description="The server's share of a call's time; over a third means the run "
        "was slowed by Connexity's server, not by the agent"
    )


class RunStatusPublic(BaseModel):
    """A run's status alone, for polling."""

    id: uuid.UUID
    status: RunStatus
    status_detail: str | None = None
    progress: RunProgressPublic
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_progress_at: datetime | None = PydanticField(
        default=None, description="When a simulated call last started or finished"
    )
    stalled: bool = PydanticField(
        default=False,
        description="Running, but the server running it has given no sign of life",
    )
    stalled_since: datetime | None = PydanticField(
        default=None, description="Its last sign of life, when stalled"
    )


class TestRunCountsPublic(RunProgressPublic):
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
    spec_written_for: str | None = PydanticField(
        default=None,
        description="The agent version that spec's rules were written for",
    )
    spec_behind: bool = PydanticField(
        default=False,
        description="The run tested an agent version newer than the one its spec was "
        "written for",
    )
    platform_version: str | None = None
    content: Literal["same", "edited", "unknown"] = PydanticField(
        default="unknown",
        description="Whether the version still has the content this run tested: "
        "edited when its number now holds other content, unknown when that could not "
        "be read",
    )
    content_checked_at: datetime | None = PydanticField(
        default=None, description="When the version was read on the platform for it"
    )
    tool_schemas_checked: bool = PydanticField(
        default=False,
        description="Whether the agent's tool calls were checked against the tools' "
        "own schemas. False when the tested version could not be read, and for runs "
        "made before the check existed",
    )
    schema_check: "RunSchemaCheckPublic | None" = PydanticField(
        default=None, description="What that check found, when it ran"
    )
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    counts: TestRunCountsPublic
    caller_messages: int = PydanticField(
        default=0, description="Messages the simulated caller sent, over its calls"
    )
    cost_usd: float = PydanticField(
        default=0.0, description="caller_messages at the list price; nothing is billed"
    )
    full: bool = PydanticField(
        default=False,
        description="A run of every scenario: the only kind that decides the verdict",
    )
    verdict: VersionVerdict | None = PydanticField(
        default=None, description="A completed full run's verdict"
    )
    result: Literal["passed", "failed", "incomplete"] | None = PydanticField(
        default=None,
        description="A completed on-demand run's result; it never changes the "
        "verdict. Incomplete when nothing failed but some calls gave no verdicts",
    )
    last_progress_at: datetime | None = PydanticField(
        default=None, description="When a simulated call last started or finished"
    )
    stalled: bool = PydanticField(
        default=False,
        description="Running, but the server running it has given no sign of life",
    )
    stalled_since: datetime | None = PydanticField(
        default=None, description="Its last sign of life, when stalled"
    )
    timing: RunTimingPublic | None = PydanticField(
        default=None, description="Where a call's time went, as medians"
    )
    throttled: int = PydanticField(
        default=0,
        description="Times the platform answered 'too many requests' across the run",
    )
    totals: "RunTotalsPublic | None" = PydanticField(
        default=None, description="Rules by outcome, once a run has completed"
    )
    ran_by: str | None = PydanticField(default=None, description="The person")
    assistant_name: str | None = None
    session_name: str | None = None


class RunTotalsPublic(BaseModel):
    """A run's rules, each counted once: Failed when any repeat failed it, Didn't come up
    when no repeat reached it (Dmytro, 2026-11-19)."""

    rules: int = PydanticField(description="Rules in the run's spec")
    passed: int = 0
    failed: int = 0
    did_not_come_up: int = 0
    no_scenario: int = PydanticField(
        default=0, description="Rules of the spec that none of the run's scenarios list"
    )
    not_judged: int = PydanticField(
        default=0,
        description="Rules only calls that stopped listed; they count in no column",
    )
    default_fake: int = PydanticField(
        default=0,
        description="Rules whose every verdict rests on a default fake; they count in "
        "no column",
    )
    critical: int = PydanticField(
        default=0,
        description="Critical rules that failed, and critical code checks that found "
        "something",
    )
    judged_calls: int = PydanticField(
        default=0, description="Simulated calls a judge read; none means no result"
    )
    stopped: int = PydanticField(
        default=0, description="Simulated calls that ended in an error"
    )


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


class VerifiedVersionPublic(BaseModel):
    version: str
    at: datetime = PydanticField(description="When its full run completed")


class LiveVersionPublic(BaseModel):
    version: str
    verdict: VersionVerdict = PydanticField(
        description="From the live version's latest full run"
    )
    at: datetime | None = PydanticField(
        default=None, description="When that full run completed"
    )


class SameContentPublic(BaseModel):
    version: str = PydanticField(description="The version number its full run tested")
    run_id: uuid.UUID
    at: datetime = PydanticField(description="When that full run completed")


class VersionResultsPublic(BaseModel):
    """One version's verdict, read from its latest completed full run (Dmytro,
    2026-11-19): runs of a set or a pick never change it."""

    version: str | None = PydanticField(
        default=None, description="The version number on the platform"
    )
    edited_since: datetime | None = PydanticField(
        default=None,
        description="When its last full run ran, when the version was edited after it: "
        "that run no longer counts",
    )
    same_content: SameContentPublic | None = PydanticField(
        default=None,
        description="When the verdict comes from another version with the same content",
    )
    live_version: str | None = PydanticField(
        default=None, description="The agent version of its most recent call"
    )
    live: LiveVersionPublic | None = PydanticField(
        default=None,
        description="The live version's state, when the version shown is not live",
    )
    verdict: VersionVerdict
    full_run: TestRunPublic | None = PydanticField(
        default=None, description="The full run that decided the verdict"
    )
    last_verified: VerifiedVersionPublic | None = PydanticField(
        default=None, description="The newest other version a full run verified"
    )
    critical_failed: list[str] = PydanticField(
        default_factory=list, description="Critical rules that failed, flaky included"
    )
    critical_checks: list[str] = PydanticField(
        default_factory=list, description="Critical code checks that found something"
    )
    rules: list[RuleTotalPublic] = PydanticField(
        default_factory=list,
        description="The full run's rules, failed first, critical first",
    )
    checks: list[CheckTotalPublic] = PydanticField(default_factory=list)
    unchecked: list["UncheckedRulePublic"] = PydanticField(
        default_factory=list,
        description="Rules of the full run's spec it did not check, critical first",
    )
    runs: list[TestRunPublic] = PydanticField(
        default_factory=list, description="Every run of this version, newest first"
    )
    coverage: "CoveragePublic | None" = PydanticField(
        default=None,
        description="Tests written: the latest spec's rules a scenario lists",
    )
    stopped: "StoppedCallsPublic | None" = PydanticField(
        default=None,
        description="The full run's simulated calls that ended in an error",
    )


class StoppedCallsPublic(BaseModel):
    calls: int = PydanticField(description="Simulated calls that ended in an error")
    reason: str = PydanticField(description="The most common error, in plain words")
    run_id: uuid.UUID = PydanticField(description="A run with one of those calls")


class UncheckedRulePublic(BaseModel):
    key: str
    text: str
    category: str
    critical: bool = False
    why: Literal["no_scenario", "did_not_come_up", "not_judged", "default_fake"] = (
        PydanticField(
            description="No scenario lists it, its scenarios never reached it, only "
            "calls that stopped listed it, or its verdicts rest on a default fake"
        )
    )


class CoveragePublic(BaseModel):
    """Tests written: a rule is covered when at least one active scenario lists it."""

    rules: int = PydanticField(description="Rules in the agent's latest spec")
    covered: int
    pct: int = PydanticField(description="Covered rules as a whole percentage")
    uncovered: list[UncheckedRulePublic] = PydanticField(
        default_factory=list, description="Rules no scenario lists, critical first"
    )


class ScenarioRowPublic(BaseModel):
    id: uuid.UUID
    name: str
    caller_goal: str | None = None
    rules: int
    sets: list[str] = PydanticField(default_factory=list)


class SetChipPublic(BaseModel):
    name: str
    scenarios: int


class TestsTabPublic(BaseModel):
    """The agent's Tests tab: the newest tested version's verdict, every run in one
    list, and the scenarios."""

    has_spec: bool
    results: VersionResultsPublic | None = PydanticField(
        default=None, description="The live version, or the newest tested one"
    )
    coverage: CoveragePublic | None = None
    runs: list[TestRunPublic] = PydanticField(
        default_factory=list,
        description="Every run of the agent newest first, or the picked version's",
    )
    live_version: str | None = PydanticField(
        default=None, description="For the Version column: 'live' or 'not live yet'"
    )
    running: bool = PydanticField(
        default=False, description="A run of this agent is in progress"
    )
    sets: list[SetChipPublic] = PydanticField(default_factory=list)
    scenarios: list[ScenarioRowPublic] = PydanticField(default_factory=list)


SimulatedCallPublic.model_rebuild()
TestRunPublic.model_rebuild()
VersionResultsPublic.model_rebuild()
