"""Pure Pydantic v2 models for JSONB nested entities.

These are NOT database tables — they serialize into JSONB columns
on the ORM table models (Run, TestCaseResult, TestCase). Run execution
helpers (:class:`RunConfig`, :class:`UserSimulatorConfig`, :class:`JudgeConfig`)
live here so API and services share one definition.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import SimulatorMode, TurnRole

if TYPE_CHECKING:
    from app.models.test_case import TestCase

# ── Test case nested types ──────────────────────────────────────────


class Persona(BaseModel):
    type: str = Field(description="Short persona archetype label")
    description: str = Field(description="Detailed persona description")
    instructions: str = Field(description="Behavioral directives for the LLM simulator")


class MockResponse(BaseModel):
    expected_params: dict[str, Any] | None = Field(
        default=None,
        description="Partial-match filter on tool arguments; null = match any call",
    )
    response: dict[str, Any] = Field(
        description="Canned return value sent back to the LLM as the tool result",
    )


class ExpectedToolCall(BaseModel):
    tool: str = Field(description="Tool/function name the agent should invoke")
    expected_params: dict[str, Any] | None = Field(
        default=None,
        description="Key parameters the judge verifies; null = any params acceptable",
    )
    mock_responses: list[MockResponse] | None = Field(
        default=None,
        description=(
            "Ordered mock responses consumed sequentially during platform agent "
            "simulation. First entry whose expected_params partially matches is "
            "popped and returned."
        ),
    )


# ── Tool platform config (lives inside Agent.tools JSONB) ─────────


class PythonImplementation(BaseModel):
    type: Literal["python"] = "python"
    code: str = Field(
        description="Python source defining: async def execute(args, context) -> dict"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Static config available as context.config inside the tool code",
    )
    timeout_s: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="Max seconds before the tool execution is cancelled",
    )


class HttpWebhookImplementation(BaseModel):
    type: Literal["http_webhook"] = "http_webhook"
    url: str = Field(description="Webhook URL; supports ${VAR} env interpolation")
    method: str = Field(
        default="POST", description="HTTP method (POST, GET, PUT, etc.)"
    )
    headers: dict[str, str] | None = Field(
        default=None,
        description="HTTP headers; values support ${VAR} env interpolation",
    )
    timeout_ms: int = Field(
        default=10000,
        ge=1000,
        le=60000,
        description="Request timeout in milliseconds",
    )


ToolImplementation = PythonImplementation | HttpWebhookImplementation


class ToolPlatformConfig(BaseModel):
    mode: Literal["mock", "live"] = Field(
        default="mock",
        description="mock: use test-case mock_responses; live: execute real implementation",
    )
    implementation: ToolImplementation | None = Field(
        default=None,
        description="Required when mode=live. Null for mock tools.",
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
    model: str | None = Field(
        default=None,
        description="Judge LLM model override",
    )
    provider: str | None = Field(
        default=None,
        description="Judge LLM provider override",
    )


class UserSimulatorConfig(BaseModel):
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

    @model_validator(mode="after")
    def scripted_mode_requires_messages(self) -> UserSimulatorConfig:
        if self.mode == SimulatorMode.SCRIPTED and not self.scripted_messages:
            msg = "scripted_messages must be non-empty when mode is 'scripted'"
            raise ValueError(msg)
        return self


class AgentSimulatorConfig(BaseModel):
    """Agent simulator LLM overrides (only used when agent mode is platform)."""

    model: str | None = Field(
        default=None,
        description="Override agent_model for this run",
    )
    provider: str | None = Field(
        default=None,
        description="Override agent agent_provider for this run",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for agent simulator LLM",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Max completion tokens for agent simulator LLM",
    )


class RunConfig(BaseModel):
    concurrency: int = Field(default=5, description="Max parallel test case executions")
    timeout_per_test_case_ms: int = Field(
        default=120_000,
        description="Timeout per test case in milliseconds before forced stop",
    )
    judge: JudgeConfig | None = Field(
        default=None,
        description="Judge metric selection, weights, pass threshold, and model overrides",
    )
    user_simulator: UserSimulatorConfig | None = Field(
        default=None,
        description=(
            "User simulator: LLM vs scripted replay, model/provider overrides, temperature. "
            "Omitted fields use app LLM defaults."
        ),
    )
    agent_simulator: AgentSimulatorConfig | None = Field(
        default=None,
        description=(
            "Agent simulator LLM overrides. Only applies when the agent mode is platform."
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
    failure_code: str | None = Field(
        default=None,
        description="Free-form failure code generated by the judge when this metric scored poorly",
    )
    turns: list[int] = Field(
        default_factory=list,
        description="Turn indices where the issue was observed",
    )


class JudgeVerdict(BaseModel):
    passed: bool = Field(description="Whether the test case passed overall")
    overall_score: float = Field(
        description="Weighted overall score across all criteria (0-100)"
    )
    metric_scores: list[MetricScore] = Field(description="Per-metric score breakdown")
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
    judge_cost_usd: float | None = Field(
        default=None,
        description="LiteLLM-estimated USD cost for the judge completion",
    )


# ── Aggregate metrics nested types ─────────────────────────────────


@dataclass(frozen=True)
class TestCaseExecution:
    """One row in an eval set execution plan (test case + member metadata)."""

    test_case: "TestCase"  # noqa: UP037 — avoid circular import with app.models.test_case
    repetitions: int
    position: int


class AggregateMetrics(BaseModel):
    unique_test_case_count: int = Field(
        description="Number of unique test cases represented in run results"
    )
    total_executions: int = Field(
        description="Total number of test case executions (result rows) in the run"
    )
    passed_count: int = Field(description="Number of test cases that passed")

    failed_count: int = Field(description="Number of test cases that failed")
    error_count: int = Field(
        description="Number of test cases that errored during execution"
    )
    pass_rate: float = Field(
        description="Fraction of executions that passed (0.0–1.0); denominator is total_executions"
    )
    latency_p50_ms: float | None = Field(
        default=None, description="Median agent latency across test cases"
    )
    latency_p95_ms: float | None = Field(
        default=None, description="95th percentile agent latency"
    )
    latency_max_ms: float | None = Field(
        default=None, description="Maximum agent latency across test cases"
    )
    latency_avg_ms: float | None = Field(
        default=None, description="Mean agent latency across test cases"
    )
    total_agent_token_usage: dict[str, int | bool] | None = Field(
        default=None,
        description="Summed token usage from the agent across all test cases",
    )
    total_platform_token_usage: dict[str, int] | None = Field(
        default=None,
        description="Summed token usage from the platform (simulator + judge)",
    )
    total_agent_cost_usd: float | None = Field(
        default=None, description="Total estimated agent cost in USD for the entire run"
    )
    total_platform_cost_usd: float | None = Field(
        default=None,
        description="Total estimated platform cost in USD (simulator + judge) for the entire run",
    )
    total_estimated_cost_usd: float | None = Field(
        default=None, description="Total estimated cost in USD for the entire run"
    )
    avg_overall_score: float | None = Field(
        default=None,
        description="Mean judge overall score across all test cases",
    )


# ── SSE Event nested types ─────────────────────────────────────────


class RunStreamEvent(BaseModel):
    event: str
    data: dict[str, Any]


class TestCaseProgressData(BaseModel):
    run_id: uuid.UUID
    test_case_id: uuid.UUID
    test_case_name: str
    completed_count: int
    total_count: int
    passed: bool | None = None
    overall_score: float | None = None
    error_message: str | None = None
