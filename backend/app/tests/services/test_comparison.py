"""Unit tests for app.services.comparison (CS-27)."""

import uuid
from types import SimpleNamespace

import pytest

from app.models.comparison import (
    AggregateComparison,
    MetricDelta,
    RegressionThresholds,
    TestCaseComparison,
)
from app.models.schemas import AggregateMetrics, JudgeVerdict, MetricScore
from app.services.comparison import (
    _build_metric_deltas,
    _compare_test_case,
    _compute_aggregate,
    _compute_per_metric_aggregate_deltas,
    _compute_verdict,
    _metric_status,
    _test_case_status,
)

# ── Helpers ──────────────────────────────────────────────────────

# Fields accessed by comparison.py on TestCaseResult objects.
_TEST_CASE_RESULT_DEFAULTS: dict[str, object] = {
    "passed": None,
    "error_message": None,
    "verdict": None,
    "total_latency_ms": None,
}


def _make_result(**overrides: object) -> SimpleNamespace:
    return SimpleNamespace(**{**_TEST_CASE_RESULT_DEFAULTS, **overrides})


def _make_verdict(
    passed: bool,
    overall_score: float,
    metric_scores: list[MetricScore] | None = None,
) -> dict:
    v = JudgeVerdict(
        passed=passed,
        overall_score=overall_score,
        metric_scores=metric_scores or [],
        summary=None,
        raw_judge_output=None,
        judge_model="gpt-4o",
        judge_provider="openai",
    )
    return v.model_dump(mode="json")


def _scored_metric(
    metric: str, score: int, label: str, is_binary: bool = False
) -> MetricScore:
    return MetricScore(
        metric=metric,
        score=score,
        label=label,
        weight=1.0,
        justification="test",
        is_binary=is_binary,
    )


# ── _metric_status ───────────────────────────────────────────────


class TestMetricStatus:
    def test_binary_pass_to_fail(self) -> None:
        assert _metric_status(True, "pass", "fail", 5, 0) == "regression"

    def test_binary_fail_to_pass(self) -> None:
        assert _metric_status(True, "fail", "pass", 0, 5) == "improvement"

    def test_binary_unchanged(self) -> None:
        assert _metric_status(True, "pass", "pass", 5, 5) == "unchanged"

    def test_scored_regression(self) -> None:
        assert _metric_status(False, None, None, 4, 2) == "regression"

    def test_scored_improvement(self) -> None:
        assert _metric_status(False, None, None, 2, 4) == "improvement"

    def test_scored_unchanged(self) -> None:
        assert _metric_status(False, None, None, 3, 3) == "unchanged"


# ── _build_metric_deltas ────────────────────────────────────────


class TestBuildMetricDeltas:
    def test_matching_metrics(self) -> None:
        b_verdict = JudgeVerdict(
            passed=True,
            overall_score=80.0,
            metric_scores=[_scored_metric("accuracy", 4, "good")],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        c_verdict = JudgeVerdict(
            passed=True,
            overall_score=90.0,
            metric_scores=[_scored_metric("accuracy", 5, "excellent")],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        deltas = _build_metric_deltas(b_verdict, c_verdict)
        assert len(deltas) == 1
        d = deltas[0]
        assert d.metric == "accuracy"
        assert d.baseline_score == 4
        assert d.candidate_score == 5
        assert d.delta == 1
        assert d.status == "improvement"

    def test_binary_metric_no_numeric_delta(self) -> None:
        b_verdict = JudgeVerdict(
            passed=True,
            overall_score=80.0,
            metric_scores=[_scored_metric("safety", 5, "pass", is_binary=True)],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        c_verdict = JudgeVerdict(
            passed=False,
            overall_score=40.0,
            metric_scores=[_scored_metric("safety", 0, "fail", is_binary=True)],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        deltas = _build_metric_deltas(b_verdict, c_verdict)
        assert len(deltas) == 1
        d = deltas[0]
        assert d.is_binary is True
        assert d.delta is None
        assert d.status == "regression"

    def test_missing_baseline_verdict(self) -> None:
        c_verdict = JudgeVerdict(
            passed=True,
            overall_score=80.0,
            metric_scores=[_scored_metric("accuracy", 4, "good")],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        deltas = _build_metric_deltas(None, c_verdict)
        assert len(deltas) == 1
        assert deltas[0].baseline_score is None
        assert deltas[0].candidate_score == 4


# ── _test_case_status ────────────────────────────────────────────


class TestTestCaseStatus:
    def test_error(self) -> None:
        b = _make_result(error_message="boom")
        c = _make_result(passed=True)
        assert _test_case_status(b, c, None, None) == "error"

    def test_pass_to_fail(self) -> None:
        b = _make_result(passed=True)
        c = _make_result(passed=False)
        assert _test_case_status(b, c, None, None) == "regression"

    def test_fail_to_pass(self) -> None:
        b = _make_result(passed=False)
        c = _make_result(passed=True)
        assert _test_case_status(b, c, None, None) == "improvement"

    def test_score_regression_above_threshold(self) -> None:
        b = _make_result(passed=True)
        c = _make_result(passed=True)
        b_v = JudgeVerdict(
            passed=True,
            overall_score=85.0,
            metric_scores=[],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        c_v = JudgeVerdict(
            passed=True,
            overall_score=70.0,
            metric_scores=[],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        assert _test_case_status(b, c, b_v, c_v) == "regression"

    def test_score_improvement_above_threshold(self) -> None:
        b = _make_result(passed=True)
        c = _make_result(passed=True)
        b_v = JudgeVerdict(
            passed=True,
            overall_score=70.0,
            metric_scores=[],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        c_v = JudgeVerdict(
            passed=True,
            overall_score=85.0,
            metric_scores=[],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        assert _test_case_status(b, c, b_v, c_v) == "improvement"

    def test_score_within_threshold(self) -> None:
        b = _make_result(passed=True)
        c = _make_result(passed=True)
        b_v = JudgeVerdict(
            passed=True,
            overall_score=80.0,
            metric_scores=[],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        c_v = JudgeVerdict(
            passed=True,
            overall_score=82.0,
            metric_scores=[],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        assert _test_case_status(b, c, b_v, c_v) == "unchanged"


# ── _compare_test_case ───────────────────────────────────────────


class TestCompareTestCase:
    def test_full_comparison(self) -> None:
        sid = uuid.uuid4()
        b = _make_result(
            test_case_id=sid,
            passed=True,
            verdict=_make_verdict(True, 85.0, [_scored_metric("accuracy", 4, "good")]),
            total_latency_ms=500,
        )
        c = _make_result(
            test_case_id=sid,
            passed=True,
            verdict=_make_verdict(
                True, 92.0, [_scored_metric("accuracy", 5, "excellent")]
            ),
            total_latency_ms=450,
        )
        result = _compare_test_case(sid, "Named test case", b, c)
        assert result.test_case_id == sid
        assert result.status == "improvement"
        assert result.score_delta == 7.0
        assert result.latency_delta_ms == -50
        assert len(result.metric_deltas) == 1
        assert result.metric_deltas[0].status == "improvement"


# ── _compute_per_metric_aggregate_deltas ────────────────────────


class TestPerMetricAggregateDeltas:
    def test_scored_metric_average(self) -> None:
        comparisons = [
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s1",
                status="improvement",
                metric_deltas=[
                    MetricDelta(
                        metric="accuracy",
                        is_binary=False,
                        baseline_score=3,
                        candidate_score=5,
                        delta=2,
                        status="improvement",
                    )
                ],
            ),
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s2",
                status="unchanged",
                metric_deltas=[
                    MetricDelta(
                        metric="accuracy",
                        is_binary=False,
                        baseline_score=4,
                        candidate_score=4,
                        delta=0,
                        status="unchanged",
                    )
                ],
            ),
        ]
        deltas = _compute_per_metric_aggregate_deltas(comparisons)
        assert len(deltas) == 1
        d = deltas[0]
        assert d.metric == "accuracy"
        assert d.baseline_avg == 3.5
        assert d.candidate_avg == 4.5
        assert d.delta == 1.0

    def test_binary_metric_pass_rate(self) -> None:
        comparisons = [
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s1",
                status="unchanged",
                metric_deltas=[
                    MetricDelta(
                        metric="safety",
                        is_binary=True,
                        baseline_score=5,
                        candidate_score=5,
                        delta=None,
                        baseline_label="pass",
                        candidate_label="pass",
                        status="unchanged",
                    )
                ],
            ),
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s2",
                status="regression",
                metric_deltas=[
                    MetricDelta(
                        metric="safety",
                        is_binary=True,
                        baseline_score=5,
                        candidate_score=0,
                        delta=None,
                        baseline_label="pass",
                        candidate_label="fail",
                        status="regression",
                    )
                ],
            ),
        ]
        deltas = _compute_per_metric_aggregate_deltas(comparisons)
        assert len(deltas) == 1
        d = deltas[0]
        assert d.is_binary is True
        assert d.baseline_avg == 1.0  # both pass
        assert d.candidate_avg == 0.5  # one pass, one fail
        assert d.delta == -0.5


# ── _compute_aggregate ──────────────────────────────────────────


class TestComputeAggregate:
    def test_aggregate_deltas(self) -> None:
        b_metrics = AggregateMetrics(
            unique_test_case_count=3,
            total_executions=3,
            passed_count=2,
            failed_count=1,
            error_count=0,
            pass_rate=0.6667,
            latency_avg_ms=500.0,
            latency_p95_ms=800.0,
            avg_overall_score=75.0,
            total_estimated_cost_usd=0.10,
        )
        c_metrics = AggregateMetrics(
            unique_test_case_count=3,
            total_executions=3,
            passed_count=3,
            failed_count=0,
            error_count=0,
            pass_rate=1.0,
            latency_avg_ms=450.0,
            latency_p95_ms=700.0,
            avg_overall_score=88.0,
            total_estimated_cost_usd=0.12,
        )
        comparisons = [
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s1",
                status="improvement",
                metric_deltas=[],
            ),
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s2",
                status="unchanged",
                metric_deltas=[],
            ),
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="s3",
                status="regression",
                metric_deltas=[],
            ),
        ]
        result = _compute_aggregate(b_metrics, c_metrics, comparisons)
        assert result.pass_rate_delta == pytest.approx(0.3333, abs=0.001)
        assert result.avg_score_delta == 13.0
        assert result.latency_avg_delta_ms == -50.0
        assert result.latency_p95_delta_ms == -100.0
        assert result.cost_delta_usd == pytest.approx(0.02, abs=0.001)
        assert result.total_regressions == 1
        assert result.total_improvements == 1
        assert result.total_unchanged == 1
        assert result.total_errors == 0


# ── _compute_verdict ───────────────────────────────────────────


class TestComputeVerdict:
    def _make_aggregate(
        self,
        *,
        pass_rate_delta: float = 0.0,
        avg_score_delta: float | None = 0.0,
        latency_avg_delta_ms: float | None = 0.0,
        b_pass_rate: float = 1.0,
        c_pass_rate: float = 1.0,
        b_avg_score: float | None = 80.0,
        c_avg_score: float | None = 80.0,
        b_latency_avg: float | None = 500.0,
        c_latency_avg: float | None = 500.0,
    ) -> AggregateComparison:
        b_metrics = AggregateMetrics(
            unique_test_case_count=10,
            total_executions=10,
            passed_count=int(b_pass_rate * 10),
            failed_count=10 - int(b_pass_rate * 10),
            error_count=0,
            pass_rate=b_pass_rate,
            avg_overall_score=b_avg_score,
            latency_avg_ms=b_latency_avg,
        )
        c_metrics = AggregateMetrics(
            unique_test_case_count=10,
            total_executions=10,
            passed_count=int(c_pass_rate * 10),
            failed_count=10 - int(c_pass_rate * 10),
            error_count=0,
            pass_rate=c_pass_rate,
            avg_overall_score=c_avg_score,
            latency_avg_ms=c_latency_avg,
        )
        return AggregateComparison(
            baseline_metrics=b_metrics,
            candidate_metrics=c_metrics,
            pass_rate_delta=pass_rate_delta,
            avg_score_delta=avg_score_delta,
            latency_avg_delta_ms=latency_avg_delta_ms,
            total_regressions=0,
            total_improvements=0,
            total_unchanged=10,
            total_errors=0,
            per_metric_aggregate_deltas=[],
        )

    def test_no_regression_default_thresholds(self) -> None:
        agg = self._make_aggregate()
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is False
        assert verdict.reasons == []

    def test_pass_rate_drop_strict(self) -> None:
        """Default threshold: any drop flags regression."""
        agg = self._make_aggregate(
            pass_rate_delta=-0.1,
            b_pass_rate=1.0,
            c_pass_rate=0.9,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is True
        assert any("pass_rate" in r for r in verdict.reasons)

    def test_pass_rate_drop_within_custom_threshold(self) -> None:
        agg = self._make_aggregate(
            pass_rate_delta=-0.02,
            b_pass_rate=1.0,
            c_pass_rate=0.98,
        )
        verdict = _compute_verdict(agg, RegressionThresholds(max_pass_rate_drop=0.05))
        assert verdict.regression_detected is False

    def test_avg_score_drop_within_default_threshold(self) -> None:
        """5-point tolerance: 3pt drop should not flag."""
        agg = self._make_aggregate(
            avg_score_delta=-3.0,
            b_avg_score=80.0,
            c_avg_score=77.0,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is False

    def test_avg_score_drop_exceeds_threshold(self) -> None:
        agg = self._make_aggregate(
            avg_score_delta=-10.0,
            b_avg_score=80.0,
            c_avg_score=70.0,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is True
        assert any("avg_score" in r for r in verdict.reasons)

    def test_latency_increase_within_threshold(self) -> None:
        """20% increase tolerance: 10% should not flag."""
        agg = self._make_aggregate(
            latency_avg_delta_ms=50.0,
            b_latency_avg=500.0,
            c_latency_avg=550.0,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is False

    def test_latency_increase_exceeds_threshold(self) -> None:
        agg = self._make_aggregate(
            latency_avg_delta_ms=200.0,
            b_latency_avg=500.0,
            c_latency_avg=700.0,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is True
        assert any("latency" in r for r in verdict.reasons)

    def test_multiple_regressions(self) -> None:
        """All three thresholds can fire simultaneously."""
        agg = self._make_aggregate(
            pass_rate_delta=-0.2,
            b_pass_rate=1.0,
            c_pass_rate=0.8,
            avg_score_delta=-15.0,
            b_avg_score=90.0,
            c_avg_score=75.0,
            latency_avg_delta_ms=500.0,
            b_latency_avg=500.0,
            c_latency_avg=1000.0,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is True
        assert len(verdict.reasons) == 3

    def test_thresholds_recorded(self) -> None:
        thresholds = RegressionThresholds(
            max_pass_rate_drop=0.1,
            max_avg_score_drop=10.0,
            max_latency_increase_pct=0.5,
        )
        agg = self._make_aggregate()
        verdict = _compute_verdict(agg, thresholds)
        assert verdict.thresholds_used == thresholds

    def test_none_latency_no_crash(self) -> None:
        """None latency values should not trigger regression."""
        agg = self._make_aggregate(
            b_latency_avg=None,
            c_latency_avg=None,
            latency_avg_delta_ms=None,
        )
        verdict = _compute_verdict(agg, RegressionThresholds())
        assert verdict.regression_detected is False
