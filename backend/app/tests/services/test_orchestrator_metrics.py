"""Tests for compute_aggregate_metrics — pure function, no DB or async required."""

import uuid

import pytest

from app.models.test_case_result import TestCaseResult
from app.services.orchestrator import compute_aggregate_metrics


def _make_result(
    *,
    passed: bool | None = None,
    error_message: str | None = None,
    agent_latency_p50_ms: int | None = None,
    verdict: dict | None = None,
    agent_token_usage: dict[str, int | bool] | None = None,
    platform_token_usage: dict[str, int] | None = None,
    agent_cost_usd: float | None = None,
    platform_cost_usd: float | None = None,
    estimated_cost_usd: float | None = None,
    test_case_id: uuid.UUID | None = None,
) -> TestCaseResult:
    return TestCaseResult(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        test_case_id=test_case_id or uuid.uuid4(),
        passed=passed,
        error_message=error_message,
        agent_latency_p50_ms=agent_latency_p50_ms,
        verdict=verdict,
        agent_token_usage=agent_token_usage,
        platform_token_usage=platform_token_usage,
        agent_cost_usd=agent_cost_usd,
        platform_cost_usd=platform_cost_usd,
        estimated_cost_usd=estimated_cost_usd,
    )


def test_empty_results() -> None:
    metrics = compute_aggregate_metrics([])
    assert metrics.unique_test_case_count == 0
    assert metrics.total_executions == 0
    assert metrics.passed_count == 0
    assert metrics.failed_count == 0
    assert metrics.error_count == 0
    assert metrics.pass_rate == 0.0


def test_all_passed() -> None:
    results = [
        _make_result(passed=True, agent_latency_p50_ms=100),
        _make_result(passed=True, agent_latency_p50_ms=200),
        _make_result(passed=True, agent_latency_p50_ms=300),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.total_executions == 3
    assert metrics.unique_test_case_count == 3
    assert metrics.passed_count == 3
    assert metrics.failed_count == 0
    assert metrics.error_count == 0
    assert metrics.pass_rate == 1.0


def test_all_failed() -> None:
    results = [
        _make_result(passed=False),
        _make_result(passed=False),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.total_executions == 2
    assert metrics.unique_test_case_count == 2
    assert metrics.passed_count == 0
    assert metrics.failed_count == 2
    assert metrics.pass_rate == 0.0


def test_mixed_results() -> None:
    results = [
        _make_result(passed=True, agent_latency_p50_ms=100),
        _make_result(passed=False),
        _make_result(
            passed=False,
            error_message="Agent timed out",
        ),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.total_executions == 3
    assert metrics.unique_test_case_count == 3
    assert metrics.passed_count == 1
    assert metrics.failed_count == 1
    assert metrics.error_count == 1
    assert abs(metrics.pass_rate - 1.0 / 3.0) < 1e-9


def test_latency_stats_with_data() -> None:
    results = [
        _make_result(passed=True, agent_latency_p50_ms=100),
        _make_result(passed=True, agent_latency_p50_ms=200),
        _make_result(passed=True, agent_latency_p50_ms=300),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.latency_p50_ms == 200.0
    assert metrics.latency_max_ms == 300
    assert metrics.latency_avg_ms is not None
    assert abs(metrics.latency_avg_ms - 200.0) < 1e-9


def test_latency_stats_without_data() -> None:
    results = [_make_result(passed=True)]
    metrics = compute_aggregate_metrics(results)
    assert metrics.latency_p50_ms is None
    assert metrics.latency_max_ms is None
    assert metrics.latency_avg_ms is None
    assert metrics.latency_p95_ms is None


def test_avg_overall_score() -> None:
    results = [
        _make_result(passed=True, verdict={"overall_score": 0.8}),
        _make_result(passed=True, verdict={"overall_score": 0.6}),
        _make_result(passed=True, verdict={"overall_score": 1.0}),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.avg_overall_score is not None
    assert abs(metrics.avg_overall_score - 0.8) < 1e-9


def test_avg_overall_score_skips_none() -> None:
    results = [
        _make_result(passed=True, verdict={"overall_score": 0.5}),
        _make_result(passed=True, verdict=None),
        _make_result(passed=True, verdict={"overall_score": None}),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.avg_overall_score is not None
    assert abs(metrics.avg_overall_score - 0.5) < 1e-9


def test_avg_overall_score_all_none() -> None:
    results = [
        _make_result(passed=True, verdict=None),
        _make_result(passed=True, verdict={"other_field": 1}),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.avg_overall_score is None


def test_token_and_cost_aggregation() -> None:
    results = [
        _make_result(
            passed=True,
            agent_token_usage={"prompt_tokens": 10, "completion_tokens": 5},
            platform_token_usage={"prompt_tokens": 100, "completion_tokens": 20},
            estimated_cost_usd=0.01,
        ),
        _make_result(
            passed=True,
            agent_token_usage={"prompt_tokens": 20, "completion_tokens": 10},
            platform_token_usage={"prompt_tokens": 50, "completion_tokens": 10},
            estimated_cost_usd=0.02,
        ),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.total_agent_token_usage == {
        "prompt_tokens": 30,
        "completion_tokens": 15,
    }
    assert metrics.total_platform_token_usage == {
        "prompt_tokens": 150,
        "completion_tokens": 30,
    }
    assert metrics.total_estimated_cost_usd == pytest.approx(0.03)
    assert metrics.total_agent_cost_usd is None
    assert metrics.total_platform_cost_usd is None


def test_cost_breakdown_aggregation() -> None:
    results = [
        _make_result(
            passed=True,
            agent_cost_usd=0.005,
            platform_cost_usd=0.003,
            estimated_cost_usd=0.008,
        ),
        _make_result(
            passed=True,
            agent_cost_usd=0.010,
            platform_cost_usd=0.002,
            estimated_cost_usd=0.012,
        ),
    ]
    metrics = compute_aggregate_metrics(results)
    assert metrics.total_agent_cost_usd == pytest.approx(0.015)
    assert metrics.total_platform_cost_usd == pytest.approx(0.005)
    assert metrics.total_estimated_cost_usd == pytest.approx(0.020)


def test_unique_test_case_count_vs_total_executions() -> None:
    sid = uuid.uuid4()
    results = [_make_result(passed=True, test_case_id=sid) for _ in range(4)]
    metrics = compute_aggregate_metrics(results)
    assert metrics.total_executions == 4
    assert metrics.unique_test_case_count == 1
    assert metrics.pass_rate == 1.0
