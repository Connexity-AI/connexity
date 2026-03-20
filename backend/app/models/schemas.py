"""Pure Pydantic v2 models for JSONB nested entities.

These are NOT database tables — they serialize into JSONB columns
on the ORM table models (Run, ScenarioResult, Scenario).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import ErrorCategory, SimulationMode, TurnRole

# ── Scenario nested types ──────────────────────────────────────────


class ScriptedStep(BaseModel):
    user_message: str
    expected_agent_behavior: str | None = None
    max_response_time_ms: int | None = None


class ExpectedOutcome(BaseModel):
    criterion: str
    weight: float = 1.0
    evaluation_hint: str | None = None


# ── Run nested types ───────────────────────────────────────────────


class RunConfig(BaseModel):
    judge_model: str | None = None
    judge_provider: str | None = None
    simulator_model: str | None = None
    simulator_provider: str | None = None
    concurrency: int = 5
    timeout_per_scenario_ms: int = 120_000
    simulation_mode_override: SimulationMode | None = None


# ── Conversation nested types ──────────────────────────────────────


class ToolCall(BaseModel):
    tool_name: str
    tool_input: dict[str, Any]
    tool_result: Any | None = None


class ConversationTurn(BaseModel):
    index: int
    role: TurnRole
    content: str
    tool_calls: list[ToolCall] | None = None
    latency_ms: int | None = None
    token_count: int | None = None
    timestamp: datetime


# ── Judge nested types ─────────────────────────────────────────────


class CriterionScore(BaseModel):
    criterion: str
    score: float  # 1.0–5.0
    label: str  # fail | poor | acceptable | good | excellent
    weight: float = 1.0
    justification: str


class JudgeVerdict(BaseModel):
    passed: bool
    overall_score: float
    criterion_scores: list[CriterionScore]
    error_category: ErrorCategory = ErrorCategory.NONE
    summary: str
    raw_judge_output: str | None = None
    judge_model: str
    judge_provider: str
    judge_latency_ms: int | None = None
    judge_token_usage: dict[str, int] | None = None


# ── Aggregate metrics nested types ─────────────────────────────────


class ErrorCategoryCount(BaseModel):
    category: ErrorCategory
    count: int


class AggregateMetrics(BaseModel):
    total_scenarios: int
    passed_count: int
    failed_count: int
    error_count: int
    pass_rate: float
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_max_ms: float | None = None
    latency_avg_ms: float | None = None
    total_agent_token_usage: dict[str, int] | None = None
    total_platform_token_usage: dict[str, int] | None = None
    total_estimated_cost_usd: float | None = None
    error_category_distribution: list[ErrorCategoryCount] = []
    avg_overall_score: float | None = None
