"""Pure Pydantic v2 models for JSONB nested entities.

These are NOT database tables — they serialize into JSONB columns
on the ORM table models (Run, ScenarioResult, Scenario).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ErrorCategory, SimulationMode, TurnRole

# ── Scenario nested types ──────────────────────────────────────────


class ScriptedStep(BaseModel):
    user_message: str = Field(description="The scripted user message to send")
    expected_agent_behavior: str | None = Field(
        default=None,
        description="Description of expected agent behavior for this step",
    )
    max_response_time_ms: int | None = Field(
        default=None,
        description="Maximum allowed agent response time in milliseconds",
    )


class ExpectedOutcome(BaseModel):
    criterion: str = Field(description="Descriptive label for the success criterion")
    weight: float = Field(
        default=1.0, description="Relative weight for scoring (default 1.0)"
    )
    evaluation_hint: str | None = Field(
        default=None,
        description="Hint for the judge on how to evaluate this criterion",
    )


# ── Run nested types ───────────────────────────────────────────────


class RunConfig(BaseModel):
    judge_model: str | None = Field(
        default=None, description="Model ID for the judge LLM"
    )
    judge_provider: str | None = Field(
        default=None, description="Provider for the judge LLM (e.g. anthropic, openai)"
    )
    simulator_model: str | None = Field(
        default=None, description="Model ID for the user simulator LLM"
    )
    simulator_provider: str | None = Field(
        default=None, description="Provider for the simulator LLM"
    )
    concurrency: int = Field(default=5, description="Max parallel scenario executions")
    timeout_per_scenario_ms: int = Field(
        default=120_000,
        description="Timeout per scenario in milliseconds before forced stop",
    )
    simulation_mode_override: SimulationMode | None = Field(
        default=None,
        description="Override the simulation mode defined on individual scenarios",
    )


# ── Conversation nested types ──────────────────────────────────────


class ToolCall(BaseModel):
    tool_name: str = Field(description="Name of the tool/function called")
    tool_input: dict[str, Any] = Field(
        description="Input parameters passed to the tool"
    )
    tool_result: Any | None = Field(
        default=None, description="Result returned by the tool"
    )


class ConversationTurn(BaseModel):
    index: int = Field(description="Zero-based turn index in the conversation")
    role: TurnRole = Field(description="Who produced this turn (user, agent, system)")
    content: str = Field(description="Text content of the turn")
    tool_calls: list[ToolCall] | None = Field(
        default=None, description="Tool calls made during this turn"
    )
    latency_ms: int | None = Field(
        default=None, description="Response latency in milliseconds"
    )
    token_count: int | None = Field(
        default=None, description="Token count for this turn"
    )
    timestamp: datetime = Field(description="When this turn occurred")


# ── Judge nested types ─────────────────────────────────────────────


class CriterionScore(BaseModel):
    criterion: str = Field(description="Name of the evaluated criterion")
    score: float = Field(description="Score from 1.0 to 5.0")
    label: str = Field(
        description="Human-readable label (fail, poor, acceptable, good, excellent)"
    )
    weight: float = Field(default=1.0, description="Relative weight of this criterion")
    justification: str = Field(description="Judge's reasoning for the assigned score")


class JudgeVerdict(BaseModel):
    passed: bool = Field(description="Whether the scenario passed overall")
    overall_score: float = Field(
        description="Weighted overall score across all criteria"
    )
    criterion_scores: list[CriterionScore] = Field(
        description="Per-criterion score breakdown"
    )
    error_category: ErrorCategory = Field(
        default=ErrorCategory.NONE,
        description="Classified error category if failed",
    )
    summary: str = Field(description="Judge's overall reasoning summary")
    raw_judge_output: str | None = Field(
        default=None, description="Raw unprocessed judge LLM output"
    )
    judge_model: str = Field(description="Model ID used for judging")
    judge_provider: str = Field(description="Provider of the judge model")
    judge_latency_ms: int | None = Field(
        default=None, description="Judge evaluation latency in milliseconds"
    )
    judge_token_usage: dict[str, int] | None = Field(
        default=None, description="Token usage for the judge call"
    )


# ── Aggregate metrics nested types ─────────────────────────────────


class ErrorCategoryCount(BaseModel):
    category: ErrorCategory = Field(description="The error category")
    count: int = Field(description="Number of results in this category")


class AggregateMetrics(BaseModel):
    total_scenarios: int = Field(
        description="Total number of scenarios executed in the run"
    )
    passed_count: int = Field(description="Number of scenarios that passed")
    failed_count: int = Field(description="Number of scenarios that failed")
    error_count: int = Field(
        description="Number of scenarios that errored during execution"
    )
    pass_rate: float = Field(description="Fraction of scenarios that passed (0.0–1.0)")
    latency_p50_ms: float | None = Field(
        default=None, description="Median agent latency across scenarios"
    )
    latency_p95_ms: float | None = Field(
        default=None, description="95th percentile agent latency"
    )
    latency_max_ms: float | None = Field(
        default=None, description="Maximum agent latency across scenarios"
    )
    latency_avg_ms: float | None = Field(
        default=None, description="Mean agent latency across scenarios"
    )
    total_agent_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Summed token usage from the agent across all scenarios",
    )
    total_platform_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Summed token usage from the platform (simulator + judge)",
    )
    total_estimated_cost_usd: float | None = Field(
        default=None, description="Total estimated cost in USD for the entire run"
    )
    error_category_distribution: list[ErrorCategoryCount] = Field(
        default_factory=list,
        description="Breakdown of error counts by category",
    )
    avg_overall_score: float | None = Field(
        default=None,
        description="Mean judge overall score across all scenarios",
    )
