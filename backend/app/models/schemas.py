"""Pure Pydantic v2 models for JSONB nested entities.

These are NOT database tables — they serialize into JSONB columns
on the ORM table models (Run, ScenarioResult, Scenario). Run execution
helpers (:class:`RunConfig`, :class:`SimulatorConfig`, :class:`JudgeConfig`)
live here so API and services share one definition.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import ErrorCategory, SimulatorMode, TurnRole

# ── Scenario nested types ──────────────────────────────────────────


class Persona(BaseModel):
    type: str = Field(description="Short persona archetype label")
    description: str = Field(description="Detailed persona description")
    instructions: str = Field(description="Behavioral directives for the LLM simulator")


class ExpectedToolCall(BaseModel):
    tool: str = Field(description="Tool/function name the agent should invoke")
    expected_params: dict[str, Any] | None = Field(
        default=None,
        description="Key parameters the judge verifies; null = any params acceptable",
    )


# ── Run nested types ───────────────────────────────────────────────


class MetricSelection(BaseModel):
    metric: str = Field(description="Metric id from the platform registry (snake_case)")
    weight: float | None = Field(
        default=None,
        description="Override weight before renormalization; None = metric default",
    )


class JudgeConfig(BaseModel):
    """Judge behavior and LLM overrides."""

    metrics: list[MetricSelection] | None = Field(
        default=None,
        description="Selected metrics; null = platform default scored metric set",
    )
    pass_threshold: float = Field(
        default=75.0,
        ge=0.0,
        le=100.0,
        description="Minimum overall score (0-100) to pass",
    )
    critical_failure_threshold: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Execution-tier scored metric at or below this value triggers critical failure",
    )
    model: str | None = Field(
        default=None,
        description="Judge LLM model override",
    )
    provider: str | None = Field(
        default=None,
        description="Judge LLM provider override",
    )


class SimulatorConfig(BaseModel):
    """User simulator behavior (LLM persona vs scripted replay) and LLM overrides."""

    mode: SimulatorMode = Field(
        default=SimulatorMode.LLM,
        description="llm: generate via LLM; scripted: replay fixed messages",
    )
    scripted_messages: list[str] = Field(
        default_factory=list,
        description="User lines after initial_message, in order (scripted mode only)",
    )
    model: str | None = Field(
        default=None,
        description="Simulator LLM model override",
    )
    provider: str | None = Field(
        default=None,
        description="Simulator LLM provider override",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for simulator LLM",
    )


class RunConfig(BaseModel):
    concurrency: int = Field(default=5, description="Max parallel scenario executions")
    timeout_per_scenario_ms: int = Field(
        default=120_000,
        description="Timeout per scenario in milliseconds before forced stop",
    )
    judge: JudgeConfig | None = Field(
        default=None,
        description="Judge metric selection, weights, pass threshold, and model overrides",
    )
    simulator: SimulatorConfig | None = Field(
        default=None,
        description=(
            "User simulator: LLM vs scripted replay, model/provider overrides, temperature. "
            "Omitted fields use app LLM defaults."
        ),
    )


# ── Conversation nested types ──────────────────────────────────────


class ToolCallFunction(BaseModel):
    name: str = Field(description="Tool/function name")
    arguments: str = Field(
        description="JSON-encoded arguments string (OpenAI chat completions convention)"
    )


class ToolCall(BaseModel):
    id: str = Field(
        description="Unique tool call identifier (e.g. call_abc123), OpenAI-compatible"
    )
    type: Literal["function"] = Field(
        default="function", description="Tool call type; only function is supported"
    )
    function: ToolCallFunction = Field(description="Function name and arguments")
    tool_result: Any | None = Field(
        default=None,
        description="Result returned by the tool (platform extension, not in agent wire format)",
    )


class ConversationTurn(BaseModel):
    index: int = Field(description="Zero-based turn index in the conversation")
    role: TurnRole = Field(
        description="Who produced this turn (user, assistant, system, tool)"
    )
    content: str | None = Field(
        default=None,
        description="Text content of the turn; null for tool-call-only assistant turns",
    )
    tool_calls: list[ToolCall] | None = Field(
        default=None, description="Tool calls made during this turn"
    )
    tool_call_id: str | None = Field(
        default=None,
        description="For role=tool turns, references the id of the tool call this message answers",
    )
    latency_ms: int | None = Field(
        default=None, description="Response latency in milliseconds"
    )
    token_count: int | None = Field(
        default=None, description="Token count for this turn"
    )
    timestamp: datetime = Field(description="When this turn occurred")


# ── Judge nested types ─────────────────────────────────────────────


class MetricScore(BaseModel):
    metric: str = Field(description="Metric id from the registry (snake_case)")
    score: int = Field(
        description="0-5 for scored metrics; 0 or 5 for binary (fail/pass)"
    )
    label: str = Field(
        description=(
            "Scored: critical_fail, fail, poor, acceptable, good, excellent. "
            "Binary: pass or fail"
        )
    )
    weight: float = Field(default=1.0, description="Relative weight of this metric")
    justification: str = Field(description="Judge's reasoning for the assigned score")
    is_binary: bool = Field(
        default=False,
        description="True if this metric uses pass/fail instead of 0-5",
    )
    tier: str | None = Field(
        default=None,
        description="Metric tier: execution, knowledge, process, delivery",
    )


class JudgeVerdict(BaseModel):
    passed: bool = Field(description="Whether the scenario passed overall")
    overall_score: float = Field(
        description="Weighted overall score across all criteria (0-100)"
    )
    critical_failure: bool = Field(
        default=False,
        description="True if an execution-tier scored metric is at or below the critical threshold",
    )
    metric_scores: list[MetricScore] = Field(description="Per-metric score breakdown")
    error_category: ErrorCategory = Field(
        default=ErrorCategory.NONE,
        description="Derived from the lowest-scoring metric when failed",
    )
    summary: str | None = Field(
        default=None,
        description="Optional summary; not produced by the judge LLM in the current pipeline",
    )
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
