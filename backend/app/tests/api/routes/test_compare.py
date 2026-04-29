"""Integration tests for GET /api/v1/runs/compare (CS-27)."""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import RunStatus, RunUpdate
from app.models.schemas import JudgeVerdict, MetricScore
from app.models.test_case_result import TestCaseResultUpdate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_case_result_fixture,
    create_test_eval_config,
    create_test_run,
    eval_config_members,
)

_PREFIX = f"{settings.API_V1_STR}/runs/compare"


def _completed_run_with_results(
    db: Session,
    passed: bool = True,
    overall_score: float = 80.0,
    metric_scores: list[MetricScore] | None = None,
) -> tuple:
    """Create a completed run with one test case result that has a verdict."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)

    # Mark as completed with aggregate metrics
    crud.update_run(
        session=db,
        db_run=run,
        run_in=RunUpdate(
            status=RunStatus.COMPLETED,
            aggregate_metrics={
                "unique_test_case_count": 1,
                "total_executions": 1,
                "passed_count": 1 if passed else 0,
                "failed_count": 0 if passed else 1,
                "error_count": 0,
                "pass_rate": 1.0 if passed else 0.0,
                "avg_overall_score": overall_score,
                "latency_avg_ms": 500.0,
                "latency_p95_ms": 800.0,
                "total_estimated_cost_usd": 0.05,
            },
        ),
    )

    # Create test case result with verdict
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    verdict = JudgeVerdict(
        passed=passed,
        overall_score=overall_score,
        metric_scores=metric_scores
        or [
            MetricScore(
                metric="accuracy",
                score=4 if passed else 2,
                label="good" if passed else "poor",
                weight=1.0,
                justification="test",
            )
        ],
        summary=None,
        raw_judge_output=None,
        judge_model="gpt-4o",
        judge_provider="openai",
    )
    crud.update_test_case_result(
        session=db,
        db_result=result,
        result_in=TestCaseResultUpdate(
            passed=passed,
            verdict=verdict,
            total_latency_ms=500,
        ),
    )

    return run, test_case, eval_config


def _completed_run_pair_same_set(db: Session) -> tuple:
    """Create two completed runs sharing the same eval set."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )

    run_b = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    run_c = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)

    for run, passed, score in [(run_b, True, 80.0), (run_c, True, 90.0)]:
        crud.update_run(
            session=db,
            db_run=run,
            run_in=RunUpdate(
                status=RunStatus.COMPLETED,
                aggregate_metrics={
                    "unique_test_case_count": 1,
                    "total_executions": 1,
                    "passed_count": 1,
                    "failed_count": 0,
                    "error_count": 0,
                    "pass_rate": 1.0,
                    "avg_overall_score": score,
                    "latency_avg_ms": 500.0,
                    "latency_p95_ms": 800.0,
                },
            ),
        )
        result = create_test_case_result_fixture(
            db, run_id=run.id, test_case_id=test_case.id
        )
        verdict = JudgeVerdict(
            passed=passed,
            overall_score=score,
            metric_scores=[
                MetricScore(
                    metric="accuracy",
                    score=4 if score < 85 else 5,
                    label="good" if score < 85 else "excellent",
                    weight=1.0,
                    justification="test",
                )
            ],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        crud.update_test_case_result(
            session=db,
            db_result=result,
            result_in=TestCaseResultUpdate(
                passed=passed,
                verdict=verdict,
                total_latency_ms=500,
            ),
        )

    return run_b, run_c


# ── Tests ────────────────────────────────────────────────────────


def test_compare_runs_success(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["baseline_run_id"] == str(run_b.id)
    assert body["candidate_run_id"] == str(run_c.id)
    assert "aggregate" in body
    assert "test_case_comparisons" in body
    assert "config_diff" in body
    assert isinstance(body["warnings"], list)


def test_compare_runs_aggregate_deltas(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    agg = r.json()["aggregate"]
    assert agg["avg_score_delta"] == 10.0  # 90 - 80
    assert agg["pass_rate_delta"] == 0.0  # both 100%


def test_compare_runs_test_case_comparisons(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    test_cases = r.json()["test_case_comparisons"]
    assert len(test_cases) == 1
    sc = test_cases[0]
    assert sc["status"] == "improvement"
    assert sc["baseline_score"] == 80.0
    assert sc["candidate_score"] == 90.0
    assert len(sc["metric_deltas"]) == 1


def test_compare_runs_baseline_not_completed(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )
    pending_run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    completed_run, _, _ = _completed_run_with_results(db)

    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(pending_run.id),
            "candidate_run_id": str(completed_run.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 400
    assert "not completed" in r.json()["detail"]


def test_compare_runs_candidate_not_completed(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    completed_run, _, _ = _completed_run_with_results(db)
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )
    running_run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    crud.update_run(
        session=db,
        db_run=running_run,
        run_in=RunUpdate(status=RunStatus.RUNNING),
    )

    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(completed_run.id),
            "candidate_run_id": str(running_run.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 400
    assert "not completed" in r.json()["detail"]


def test_compare_runs_not_found(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(uuid.uuid4()),
            "candidate_run_id": str(uuid.uuid4()),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 404


def test_compare_runs_different_eval_configs_warning(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    run_b, _, _ = _completed_run_with_results(db)
    run_c, _, _ = _completed_run_with_results(db)

    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert any("different eval configs" in w for w in body["warnings"])


def test_compare_runs_config_diff_present(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    config_diff = r.json()["config_diff"]
    assert "eval_config_diff" in config_diff
    assert config_diff["eval_config_diff"]["same_set"] is True


def test_compare_runs_includes_agent_versions(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["baseline_agent_version"] == run_b.agent_version
    assert body["candidate_agent_version"] == run_c.agent_version
    assert body["config_diff"]["baseline_agent_version"] == run_b.agent_version
    assert body["config_diff"]["candidate_agent_version"] == run_c.agent_version


def test_compare_runs_binary_metric_handling(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Binary metrics should have delta=None and status based on label transition."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )

    runs = []
    for passed, score, binary_label, binary_score in [
        (True, 80.0, "pass", 5),
        (False, 40.0, "fail", 0),
    ]:
        run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
        crud.update_run(
            session=db,
            db_run=run,
            run_in=RunUpdate(
                status=RunStatus.COMPLETED,
                aggregate_metrics={
                    "unique_test_case_count": 1,
                    "total_executions": 1,
                    "passed_count": 1 if passed else 0,
                    "failed_count": 0 if passed else 1,
                    "error_count": 0,
                    "pass_rate": 1.0 if passed else 0.0,
                    "avg_overall_score": score,
                },
            ),
        )
        result = create_test_case_result_fixture(
            db, run_id=run.id, test_case_id=test_case.id
        )
        verdict = JudgeVerdict(
            passed=passed,
            overall_score=score,
            metric_scores=[
                MetricScore(
                    metric="safety",
                    score=binary_score,
                    label=binary_label,
                    weight=1.0,
                    justification="test",
                    is_binary=True,
                )
            ],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        crud.update_test_case_result(
            session=db,
            db_result=result,
            result_in=TestCaseResultUpdate(passed=passed, verdict=verdict),
        )
        runs.append(run)

    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(runs[0].id),
            "candidate_run_id": str(runs[1].id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    sc = r.json()["test_case_comparisons"][0]
    md = sc["metric_deltas"][0]
    assert md["is_binary"] is True
    assert md["delta"] is None
    assert md["status"] == "regression"
    assert md["baseline_label"] == "pass"
    assert md["candidate_label"] == "fail"


# ── CS-28: Regression verdict tests ────────────────────────────


def test_compare_runs_verdict_present(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """RunComparison response includes a verdict with default thresholds."""
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert "verdict" in body
    verdict = body["verdict"]
    assert "regression_detected" in verdict
    assert "reasons" in verdict
    assert "thresholds_used" in verdict
    # Both runs pass, candidate is better — no regression
    assert verdict["regression_detected"] is False


def test_compare_runs_verdict_detects_regression(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Regression detected when pass_rate drops."""
    # baseline: passed, candidate: failed
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )

    runs = []
    for passed, score, pass_rate in [(True, 80.0, 1.0), (False, 40.0, 0.0)]:
        run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
        crud.update_run(
            session=db,
            db_run=run,
            run_in=RunUpdate(
                status=RunStatus.COMPLETED,
                aggregate_metrics={
                    "unique_test_case_count": 1,
                    "total_executions": 1,
                    "passed_count": 1 if passed else 0,
                    "failed_count": 0 if passed else 1,
                    "error_count": 0,
                    "pass_rate": pass_rate,
                    "avg_overall_score": score,
                    "latency_avg_ms": 500.0,
                    "latency_p95_ms": 800.0,
                },
            ),
        )
        result = create_test_case_result_fixture(
            db, run_id=run.id, test_case_id=test_case.id
        )
        verdict = JudgeVerdict(
            passed=passed,
            overall_score=score,
            metric_scores=[
                MetricScore(
                    metric="accuracy",
                    score=4 if passed else 1,
                    label="good" if passed else "critical_fail",
                    weight=1.0,
                    justification="test",
                )
            ],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        crud.update_test_case_result(
            session=db,
            db_result=result,
            result_in=TestCaseResultUpdate(passed=passed, verdict=verdict),
        )
        runs.append(run)

    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(runs[0].id),
            "candidate_run_id": str(runs[1].id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    verdict = r.json()["verdict"]
    assert verdict["regression_detected"] is True
    assert any("pass_rate" in reason for reason in verdict["reasons"])


def test_compare_runs_custom_thresholds(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Custom threshold can suppress a regression that default would catch."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(test_case.id)
    )

    runs = []
    for passed, score, pass_rate in [(True, 80.0, 1.0), (False, 40.0, 0.0)]:
        run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
        crud.update_run(
            session=db,
            db_run=run,
            run_in=RunUpdate(
                status=RunStatus.COMPLETED,
                aggregate_metrics={
                    "unique_test_case_count": 1,
                    "total_executions": 1,
                    "passed_count": 1 if passed else 0,
                    "failed_count": 0 if passed else 1,
                    "error_count": 0,
                    "pass_rate": pass_rate,
                    "avg_overall_score": score,
                    "latency_avg_ms": 500.0,
                },
            ),
        )
        result = create_test_case_result_fixture(
            db, run_id=run.id, test_case_id=test_case.id
        )
        verdict = JudgeVerdict(
            passed=passed,
            overall_score=score,
            metric_scores=[
                MetricScore(
                    metric="accuracy",
                    score=4 if passed else 1,
                    label="good" if passed else "critical_fail",
                    weight=1.0,
                    justification="test",
                )
            ],
            summary=None,
            raw_judge_output=None,
            judge_model="gpt-4o",
            judge_provider="openai",
        )
        crud.update_test_case_result(
            session=db,
            db_result=result,
            result_in=TestCaseResultUpdate(passed=passed, verdict=verdict),
        )
        runs.append(run)

    # With a generous threshold, the pass-rate drop should not flag
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(runs[0].id),
            "candidate_run_id": str(runs[1].id),
            "max_pass_rate_drop": 1.0,  # allow 100% drop
            "max_avg_score_drop": 100.0,  # allow full score drop
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    verdict = r.json()["verdict"]
    assert verdict["regression_detected"] is False
    assert verdict["thresholds_used"]["max_pass_rate_drop"] == 1.0
    assert verdict["thresholds_used"]["max_avg_score_drop"] == 100.0


def test_compare_runs_default_thresholds_in_response(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """When no threshold overrides, defaults appear in the response."""
    run_b, run_c = _completed_run_pair_same_set(db)
    r = client.get(
        _PREFIX,
        params={
            "baseline_run_id": str(run_b.id),
            "candidate_run_id": str(run_c.id),
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    thresholds = r.json()["verdict"]["thresholds_used"]
    assert thresholds["max_pass_rate_drop"] == 0.0
    assert thresholds["max_avg_score_drop"] == 5.0
    assert thresholds["max_latency_increase_pct"] == 0.2
