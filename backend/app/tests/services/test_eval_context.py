"""Tests for prompt editor eval context builder (CS-64)."""

import uuid

from app.models.enums import AgentMode
from app.services.prompt_editor.eval_context import (
    ComparisonSummary,
    DetailedMetricScore,
    DetailedTestCaseResult,
    EditorEvalContext,
    FailingTestCaseSummary,
    MetricBreakdown,
    format_eval_context_for_prompt,
)


def test_format_eval_context_minimal() -> None:
    ctx = EditorEvalContext(
        agent_name="Test Agent",
        agent_mode=AgentMode.PLATFORM.value,
        agent_model="gpt-4o",
        tool_count=0,
        tool_names=[],
        detailed_results=None,
    )
    text = format_eval_context_for_prompt(ctx)
    assert "<eval_context>" in text
    assert "</eval_context>" in text
    assert "Test Agent" in text
    assert "<config>" in text


def test_format_eval_context_with_aggregate_and_comparison() -> None:
    ctx = EditorEvalContext(
        agent_name="A",
        agent_mode="platform",
        agent_model="m",
        tool_count=1,
        tool_names=["lookup"],
        run_id=uuid.uuid4(),
        run_name="Run 1",
        eval_set_name="Suite",
        total_test_cases=10,
        pass_rate=0.7,
        avg_overall_score=72.5,
        metric_breakdown=[
            MetricBreakdown(
                metric="tone",
                display_name="Tone",
                avg_score=3.5,
                pass_count=7,
                fail_count=3,
                tier="delivery",
            )
        ],
        failing_test_cases=[
            FailingTestCaseSummary(
                test_case_id=uuid.uuid4(),
                test_case_name="Bad case",
                overall_score=40.0,
                passed=False,
                failing_metrics=["tone"],
                judge_summary="Too stiff",
                turn_count=4,
            )
        ],
        comparison=ComparisonSummary(
            baseline_run_name="Base",
            candidate_run_name="Run 1",
            pass_rate_delta=0.05,
            avg_score_delta=2.0,
            total_regressions=1,
            total_improvements=2,
            regressed_metrics=["x"],
            improved_metrics=["y"],
            verdict="no_regression_detected",
        ),
    )
    text = format_eval_context_for_prompt(ctx)
    assert "<eval_results" in text
    assert "70.0%" in text or "70" in text
    assert "<comparison" in text
    assert "Tone" in text
    assert "Bad case" in text


def test_format_eval_context_detailed_transcript() -> None:
    tid = uuid.uuid4()
    ctx = EditorEvalContext(
        agent_name="A",
        agent_mode="platform",
        agent_model=None,
        tool_count=0,
        tool_names=[],
        detailed_results=[
            DetailedTestCaseResult(
                test_case_result_id=uuid.uuid4(),
                test_case_id=tid,
                test_case_name="TC",
                run_id=uuid.uuid4(),
                run_name="R",
                passed=False,
                overall_score=50.0,
                metric_scores=[
                    DetailedMetricScore(
                        metric="m",
                        display_name="M",
                        score=2,
                        label="poor",
                        justification="bad",
                        is_binary=False,
                        tier=None,
                        failure_code=None,
                        turns=[1],
                    )
                ],
                transcript=[
                    {"index": 0, "role": "user", "content": "hi"},
                    {"index": 1, "role": "assistant", "content": "hello"},
                ],
                turn_count=2,
                total_latency_ms=100,
                error_message=None,
            )
        ],
    )
    text = format_eval_context_for_prompt(ctx)
    assert "<selected_test_cases>" in text
    assert "user: hi" in text
    assert "poor" in text
