"""Run-to-run comparison engine (CS-27).

Computes structured diffs between two completed runs: per-test-case verdict
changes, per-metric score deltas, and suite-level aggregate metric deltas.
"""

import uuid
from statistics import mean
from typing import Literal

from sqlmodel import Session, select

from app.models.comparison import (
    AggregateComparison,
    MetricAggregateDelta,
    MetricDelta,
    RegressionThresholds,
    RegressionVerdict,
    RunComparison,
    TestCaseComparison,
)
from app.models.run import Run
from app.models.schemas import AggregateMetrics, JudgeVerdict, MetricScore
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.services.diff import compute_run_config_diff

# Score threshold on the 0-100 overall_score scale for classifying
# a test case as regression/improvement (when pass/fail didn't flip).
_SCORE_THRESHOLD = 5.0


def compare_runs(
    session: Session,
    baseline: Run,
    candidate: Run,
    thresholds: RegressionThresholds | None = None,
) -> RunComparison:
    """Compare two completed runs and return a structured RunComparison."""
    warnings: list[str] = []

    # Load test case results for both runs in bulk
    baseline_results = _load_results_by_test_case(session, baseline.id)
    candidate_results = _load_results_by_test_case(session, candidate.id)

    baseline_tc_ids = set(baseline_results)
    candidate_tc_ids = set(candidate_results)

    # Determine test case matching
    if baseline.eval_config_id != candidate.eval_config_id:
        warnings.append(
            "Runs use different eval configs — comparison is based on "
            "overlapping test case IDs only."
        )

    matched_ids = baseline_tc_ids & candidate_tc_ids
    baseline_only = sorted(baseline_tc_ids - candidate_tc_ids)
    candidate_only = sorted(candidate_tc_ids - baseline_tc_ids)

    if baseline_only or candidate_only:
        if baseline.eval_config_id == candidate.eval_config_id:
            warnings.append(
                f"Eval config versions differ ({baseline.eval_config_version} vs "
                f"{candidate.eval_config_version}): {len(baseline_only)} removed, "
                f"{len(candidate_only)} added."
            )

    # Load test case names for matched test cases
    test_case_names = _load_test_case_names(session, matched_ids)

    # Per-test-case comparisons
    test_case_comparisons: list[TestCaseComparison] = []
    for sid in sorted(matched_ids):
        b_result = baseline_results[sid]
        c_result = candidate_results[sid]
        sc = _compare_test_case(
            sid, test_case_names.get(sid, "Unknown"), b_result, c_result
        )
        test_case_comparisons.append(sc)

    # Aggregate comparison
    baseline_metrics = _parse_aggregate_metrics(baseline)
    candidate_metrics = _parse_aggregate_metrics(candidate)
    aggregate = _compute_aggregate(
        baseline_metrics, candidate_metrics, test_case_comparisons
    )

    # Config diff (CS-47)
    config_diff = compute_run_config_diff(
        baseline,
        candidate,
        baseline_tc_ids,
        candidate_tc_ids,
        session=session,
    )

    # Regression verdict (CS-28)
    effective_thresholds = thresholds or RegressionThresholds()
    verdict = _compute_verdict(aggregate, effective_thresholds)

    return RunComparison(
        baseline_run_id=baseline.id,
        candidate_run_id=candidate.id,
        baseline_agent_version=baseline.agent_version,
        candidate_agent_version=candidate.agent_version,
        baseline_run_name=baseline.name,
        candidate_run_name=candidate.name,
        aggregate=aggregate,
        test_case_comparisons=test_case_comparisons,
        baseline_only_test_cases=baseline_only,
        candidate_only_test_cases=candidate_only,
        config_diff=config_diff,
        verdict=verdict,
        warnings=warnings,
    )


# ── Internal helpers ─────────────────────────────────────────────


def _load_results_by_test_case(
    session: Session, run_id: uuid.UUID
) -> dict[uuid.UUID, TestCaseResult]:
    """Load all TestCaseResults for a run, keyed by test_case_id."""
    stmt = select(TestCaseResult).where(TestCaseResult.run_id == run_id)
    results = session.exec(stmt).all()
    return {r.test_case_id: r for r in results}


def _load_test_case_names(
    session: Session, test_case_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not test_case_ids:
        return {}
    stmt = select(TestCase.id, TestCase.name).where(
        TestCase.id.in_(test_case_ids)  # type: ignore[union-attr]
    )
    rows = session.exec(stmt).all()
    return {row[0]: row[1] for row in rows}


def _parse_verdict(result: TestCaseResult) -> JudgeVerdict | None:
    if not result.verdict:
        return None
    return JudgeVerdict.model_validate(result.verdict)


def _parse_aggregate_metrics(run: Run) -> AggregateMetrics:
    if run.aggregate_metrics:
        return AggregateMetrics.model_validate(dict(run.aggregate_metrics))
    return AggregateMetrics(
        unique_test_case_count=0,
        total_executions=0,
        passed_count=0,
        failed_count=0,
        error_count=0,
        pass_rate=0.0,
    )


def _metric_status(
    is_binary: bool,
    baseline_label: str | None,
    candidate_label: str | None,
    baseline_score: int | None,
    candidate_score: int | None,
) -> Literal["regression", "improvement", "unchanged"]:
    """Determine metric-level status."""
    if is_binary:
        if baseline_label == candidate_label:
            return "unchanged"
        if baseline_label == "pass" and candidate_label == "fail":
            return "regression"
        if baseline_label == "fail" and candidate_label == "pass":
            return "improvement"
        return "unchanged"

    if baseline_score is not None and candidate_score is not None:
        if candidate_score < baseline_score:
            return "regression"
        if candidate_score > baseline_score:
            return "improvement"
    return "unchanged"


def _build_metric_deltas(
    baseline_verdict: JudgeVerdict | None,
    candidate_verdict: JudgeVerdict | None,
) -> list[MetricDelta]:
    """Build per-metric deltas by matching on metric id."""
    b_scores: dict[str, MetricScore] = {}
    c_scores: dict[str, MetricScore] = {}

    if baseline_verdict:
        b_scores = {ms.metric: ms for ms in baseline_verdict.metric_scores}
    if candidate_verdict:
        c_scores = {ms.metric: ms for ms in candidate_verdict.metric_scores}

    all_metrics = sorted(set(b_scores) | set(c_scores))
    deltas: list[MetricDelta] = []

    for metric_id in all_metrics:
        b = b_scores.get(metric_id)
        c = c_scores.get(metric_id)

        is_binary = (b.is_binary if b else False) or (c.is_binary if c else False)
        b_score = b.score if b else None
        c_score = c.score if c else None
        b_label = b.label if b else None
        c_label = c.label if c else None

        if is_binary:
            delta_val = None
        elif b_score is not None and c_score is not None:
            delta_val = c_score - b_score
        else:
            delta_val = None

        status = _metric_status(is_binary, b_label, c_label, b_score, c_score)

        deltas.append(
            MetricDelta(
                metric=metric_id,
                is_binary=is_binary,
                baseline_score=b_score,
                candidate_score=c_score,
                delta=delta_val,
                baseline_label=b_label,
                candidate_label=c_label,
                status=status,
            )
        )

    return deltas


def _test_case_status(
    b_result: TestCaseResult,
    c_result: TestCaseResult,
    b_verdict: JudgeVerdict | None,
    c_verdict: JudgeVerdict | None,
) -> Literal["regression", "improvement", "unchanged", "error"]:
    """Determine overall test case comparison status."""
    if b_result.error_message or c_result.error_message:
        return "error"

    # Pass/fail transition takes priority
    if b_result.passed is True and c_result.passed is False:
        return "regression"
    if b_result.passed is False and c_result.passed is True:
        return "improvement"

    # Score-based threshold check
    b_score = b_verdict.overall_score if b_verdict else None
    c_score = c_verdict.overall_score if c_verdict else None

    if b_score is not None and c_score is not None:
        delta = c_score - b_score
        if delta < -_SCORE_THRESHOLD:
            return "regression"
        if delta > _SCORE_THRESHOLD:
            return "improvement"

    return "unchanged"


def _compare_test_case(
    test_case_id: uuid.UUID,
    test_case_name: str,
    b_result: TestCaseResult,
    c_result: TestCaseResult,
) -> TestCaseComparison:
    b_verdict = _parse_verdict(b_result)
    c_verdict = _parse_verdict(c_result)

    b_score = b_verdict.overall_score if b_verdict else None
    c_score = c_verdict.overall_score if c_verdict else None

    score_delta: float | None = None
    if b_score is not None and c_score is not None:
        score_delta = round(c_score - b_score, 2)

    latency_delta: int | None = None
    if b_result.total_latency_ms is not None and c_result.total_latency_ms is not None:
        latency_delta = c_result.total_latency_ms - b_result.total_latency_ms

    return TestCaseComparison(
        test_case_id=test_case_id,
        test_case_name=test_case_name,
        status=_test_case_status(b_result, c_result, b_verdict, c_verdict),
        baseline_passed=b_result.passed,
        candidate_passed=c_result.passed,
        baseline_score=b_score,
        candidate_score=c_score,
        score_delta=score_delta,
        metric_deltas=_build_metric_deltas(b_verdict, c_verdict),
        baseline_latency_ms=b_result.total_latency_ms,
        candidate_latency_ms=c_result.total_latency_ms,
        latency_delta_ms=latency_delta,
    )


def _safe_delta(a: float | None, b: float | None) -> float | None:
    """Compute b - a, returning None if either is None."""
    if a is None or b is None:
        return None
    return round(b - a, 4)


def _compute_per_metric_aggregate_deltas(
    test_case_comparisons: list[TestCaseComparison],
) -> list[MetricAggregateDelta]:
    """Aggregate each metric across all matched test cases.

    For binary metrics: pass rate (fraction where label == 'pass').
    For scored metrics: mean 0-5 score.
    """
    # Collect per-metric scores from both sides
    baseline_scores: dict[str, list[int | str]] = {}
    candidate_scores: dict[str, list[int | str]] = {}
    is_binary_map: dict[str, bool] = {}

    for sc in test_case_comparisons:
        for md in sc.metric_deltas:
            is_binary_map[md.metric] = md.is_binary

            if md.is_binary:
                if md.baseline_label is not None:
                    baseline_scores.setdefault(md.metric, []).append(md.baseline_label)
                if md.candidate_label is not None:
                    candidate_scores.setdefault(md.metric, []).append(
                        md.candidate_label
                    )
            else:
                if md.baseline_score is not None:
                    baseline_scores.setdefault(md.metric, []).append(md.baseline_score)
                if md.candidate_score is not None:
                    candidate_scores.setdefault(md.metric, []).append(
                        md.candidate_score
                    )

    deltas: list[MetricAggregateDelta] = []
    for metric_id in sorted(is_binary_map):
        is_binary = is_binary_map[metric_id]
        b_vals = baseline_scores.get(metric_id, [])
        c_vals = candidate_scores.get(metric_id, [])

        if is_binary:
            b_avg = (
                mean(1.0 if v == "pass" else 0.0 for v in b_vals) if b_vals else None
            )
            c_avg = (
                mean(1.0 if v == "pass" else 0.0 for v in c_vals) if c_vals else None
            )
        else:
            b_avg = mean(float(v) for v in b_vals) if b_vals else None  # type: ignore[arg-type]
            c_avg = mean(float(v) for v in c_vals) if c_vals else None  # type: ignore[arg-type]

        b_avg_rounded = round(b_avg, 4) if b_avg is not None else None
        c_avg_rounded = round(c_avg, 4) if c_avg is not None else None

        deltas.append(
            MetricAggregateDelta(
                metric=metric_id,
                is_binary=is_binary,
                baseline_avg=b_avg_rounded,
                candidate_avg=c_avg_rounded,
                delta=_safe_delta(b_avg_rounded, c_avg_rounded),
            )
        )

    return deltas


def _compute_aggregate(
    baseline_metrics: AggregateMetrics,
    candidate_metrics: AggregateMetrics,
    test_case_comparisons: list[TestCaseComparison],
) -> AggregateComparison:
    total_regressions = sum(
        1 for sc in test_case_comparisons if sc.status == "regression"
    )
    total_improvements = sum(
        1 for sc in test_case_comparisons if sc.status == "improvement"
    )
    total_unchanged = sum(1 for sc in test_case_comparisons if sc.status == "unchanged")
    total_errors = sum(1 for sc in test_case_comparisons if sc.status == "error")

    return AggregateComparison(
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        pass_rate_delta=round(
            candidate_metrics.pass_rate - baseline_metrics.pass_rate, 4
        ),
        avg_score_delta=_safe_delta(
            baseline_metrics.avg_overall_score, candidate_metrics.avg_overall_score
        ),
        latency_avg_delta_ms=_safe_delta(
            baseline_metrics.latency_avg_ms, candidate_metrics.latency_avg_ms
        ),
        latency_p95_delta_ms=_safe_delta(
            baseline_metrics.latency_p95_ms, candidate_metrics.latency_p95_ms
        ),
        cost_delta_usd=_safe_delta(
            baseline_metrics.total_estimated_cost_usd,
            candidate_metrics.total_estimated_cost_usd,
        ),
        total_regressions=total_regressions,
        total_improvements=total_improvements,
        total_unchanged=total_unchanged,
        total_errors=total_errors,
        per_metric_aggregate_deltas=_compute_per_metric_aggregate_deltas(
            test_case_comparisons
        ),
    )


def _compute_verdict(
    aggregate: AggregateComparison,
    thresholds: RegressionThresholds,
) -> RegressionVerdict:
    """Evaluate aggregate deltas against thresholds to produce a verdict."""
    reasons: list[str] = []

    # Pass-rate check
    drop = -aggregate.pass_rate_delta  # positive = drop
    if drop > thresholds.max_pass_rate_drop:
        b = aggregate.baseline_metrics.pass_rate
        c = aggregate.candidate_metrics.pass_rate
        reasons.append(f"pass_rate dropped {drop:.0%} ({b:.2f} → {c:.2f})")

    # Average score check
    if aggregate.avg_score_delta is not None and aggregate.avg_score_delta < 0:
        score_drop = -aggregate.avg_score_delta
        if score_drop > thresholds.max_avg_score_drop:
            b = aggregate.baseline_metrics.avg_overall_score
            c = aggregate.candidate_metrics.avg_overall_score
            reasons.append(f"avg_score dropped {score_drop:.1f}pt ({b:.1f} → {c:.1f})")

    # Latency check (percentage-based)
    b_lat = aggregate.baseline_metrics.latency_avg_ms
    c_lat = aggregate.candidate_metrics.latency_avg_ms
    if b_lat is not None and c_lat is not None and b_lat > 0:
        increase_pct = (c_lat - b_lat) / b_lat
        if increase_pct > thresholds.max_latency_increase_pct:
            reasons.append(
                f"avg_latency increased {increase_pct:.0%} "
                f"({b_lat:.0f}ms → {c_lat:.0f}ms)"
            )

    return RegressionVerdict(
        regression_detected=len(reasons) > 0,
        reasons=reasons,
        thresholds_used=thresholds,
    )
