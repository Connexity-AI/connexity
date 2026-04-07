"""Pydantic models for config diff (CS-47) and run-to-run comparison (CS-27)."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field
from sqlmodel import SQLModel

from app.models.schemas import AggregateMetrics

# ── CS-47: Config diff schemas ───────────────────────────────────


class FieldChange(BaseModel):
    field: str
    old_value: str | int | float | bool | dict | list | None = None
    new_value: str | int | float | bool | dict | list | None = None


class ToolDiff(BaseModel):
    added: list[str] = Field(default_factory=list, description="Added tool names")
    removed: list[str] = Field(default_factory=list, description="Removed tool names")
    modified: list[FieldChange] = Field(
        default_factory=list, description="Per-tool deepdiff summary"
    )


class PromptDiff(BaseModel):
    changed: bool
    unified_diff: str | None = None  # raw unified diff (truncated if huge)
    change_ratio: float = Field(
        description="0.0 = identical, 1.0 = completely different"
    )
    added_line_count: int = 0
    removed_line_count: int = 0
    semantic_summary: str | None = None  # populated by future LLM call (CS-29)


class EvalSetDiff(BaseModel):
    same_set: bool
    version_changed: bool
    added_test_case_ids: list[uuid.UUID] = Field(default_factory=list)
    removed_test_case_ids: list[uuid.UUID] = Field(default_factory=list)
    common_test_case_ids: list[uuid.UUID] = Field(default_factory=list)


class RunConfigDiff(BaseModel):
    """Structured diff of snapshotted run configuration between two runs."""

    model_config = {"protected_namespaces": ()}

    prompt_diff: PromptDiff | None = None
    tool_diff: ToolDiff | None = None
    model_changed: FieldChange | None = None
    provider_changed: FieldChange | None = None
    judge_model_changed: FieldChange | None = None
    judge_provider_changed: FieldChange | None = None
    config_changes: list[FieldChange] = Field(default_factory=list)
    eval_set_diff: EvalSetDiff


class AgentVersionDiff(SQLModel):
    """Structured diff between two immutable agent_version snapshots."""

    model_config = {"protected_namespaces": ()}

    from_version: int
    to_version: int
    prompt_diff: PromptDiff | None = None
    tool_diff: ToolDiff | None = None
    mode_changed: bool = False
    model_changed: FieldChange | None = None
    provider_changed: FieldChange | None = None
    endpoint_url_changed: FieldChange | None = None


# ── CS-27: Per-metric delta ──────────────────────────────────────


class MetricDelta(BaseModel):
    metric: str
    is_binary: bool
    baseline_score: int | None = None
    candidate_score: int | None = None
    delta: int | None = None  # None for binary metrics
    baseline_label: str | None = None
    candidate_label: str | None = None
    status: Literal["regression", "improvement", "unchanged"]


# ── CS-27: Per-test-case comparison ───────────────────────────────


class TestCaseComparison(BaseModel):
    test_case_id: uuid.UUID
    test_case_name: str
    status: Literal["regression", "improvement", "unchanged", "error"]
    baseline_passed: bool | None = None
    candidate_passed: bool | None = None
    baseline_score: float | None = None  # overall_score from JudgeVerdict (0-100)
    candidate_score: float | None = None
    score_delta: float | None = None  # candidate - baseline
    metric_deltas: list[MetricDelta]
    baseline_latency_ms: int | None = None
    candidate_latency_ms: int | None = None
    latency_delta_ms: int | None = None


# ── CS-27: Suite-level aggregate deltas ──────────────────────────


class MetricAggregateDelta(BaseModel):
    metric: str
    is_binary: bool
    baseline_avg: float | None = None
    candidate_avg: float | None = None
    delta: float | None = None


class AggregateComparison(BaseModel):
    baseline_metrics: AggregateMetrics
    candidate_metrics: AggregateMetrics
    pass_rate_delta: float
    avg_score_delta: float | None = None
    latency_avg_delta_ms: float | None = None
    latency_p95_delta_ms: float | None = None
    cost_delta_usd: float | None = None
    total_regressions: int
    total_improvements: int
    total_unchanged: int
    total_errors: int
    per_metric_aggregate_deltas: list[MetricAggregateDelta]


# ── CS-28: Regression verdict ───────────────────────────────────


class RegressionThresholds(BaseModel):
    """Sensible defaults. Overridable via CLI flags or API query params."""

    max_pass_rate_drop: float = Field(
        default=0.0,
        description="Any pass-rate drop flags regression (default: strict)",
    )
    max_avg_score_drop: float = Field(
        default=5.0,
        description="Tolerance on 0-100 scale for avg score drop (LLM noise)",
    )
    max_latency_increase_pct: float = Field(
        default=0.2,
        description="Fraction of latency increase tolerated (0.2 = 20%)",
    )


class RegressionVerdict(BaseModel):
    regression_detected: bool
    reasons: list[str]
    thresholds_used: RegressionThresholds


# ── CS-27: Top-level response ────────────────────────────────────


class RunComparison(BaseModel):
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    baseline_run_name: str | None = None
    candidate_run_name: str | None = None
    aggregate: AggregateComparison
    test_case_comparisons: list[TestCaseComparison]
    baseline_only_test_cases: list[uuid.UUID]
    candidate_only_test_cases: list[uuid.UUID]
    config_diff: RunConfigDiff
    verdict: RegressionVerdict
    warnings: list[str]
    regression_analysis: "RegressionAnalysis | None" = None


# ── CS-29: AI-powered regression analysis ──────────────────────────


class CauseAnalysisItem(BaseModel):
    metric: str
    direction: Literal["regressed", "improved"]
    likely_cause: str
    confidence: Literal["high", "medium", "low"]
    reasoning: str


class RegressionAnalysis(BaseModel):
    model_config = {"protected_namespaces": ()}

    analysis: list[CauseAnalysisItem]
    infrastructure_notes: list[str]
    summary: str
    prompt_semantic_summary: str | None = None
    analysis_model: str
    analysis_cost_usd: float | None = None


class SuggestionsRequest(BaseModel):
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID


class ImprovementSuggestion(BaseModel):
    target: Literal[
        "system_prompt",
        "tool_definition",
        "model_selection",
        "test_case_design",
        "other",
    ]
    title: str
    description: str
    current_value: str | None = None
    suggested_value: str | None = None
    expected_metric_impact: list[str]
    priority: Literal["high", "medium", "low"]


class ImprovementSuggestions(BaseModel):
    model_config = {"protected_namespaces": ()}

    suggestions: list[ImprovementSuggestion]
    summary: str
    model: str
    cost_usd: float | None = None


# Resolve forward reference for RunComparison.regression_analysis
RunComparison.model_rebuild()
