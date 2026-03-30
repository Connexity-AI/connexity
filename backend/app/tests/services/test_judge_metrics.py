import pytest

from app.models.schemas import JudgeConfig, MetricSelection
from app.services.judge import build_judge_response_format
from app.services.judge_metrics import (
    METRIC_REGISTRY,
    ScoreType,
    get_default_metrics,
    resolve_metrics,
)


def test_get_default_metrics_excludes_task_completion() -> None:
    names = {m.name for m in get_default_metrics()}
    assert "task_completion" not in names
    assert len(names) == 8
    assert all(m.score_type == ScoreType.SCORED for m in get_default_metrics())


def test_resolve_metrics_defaults_sum_to_one() -> None:
    resolved = resolve_metrics(None)
    assert len(resolved) == 8
    total = sum(w for _, w in resolved)
    assert abs(total - 1.0) < 1e-9


def test_resolve_metrics_custom_list_renormalizes() -> None:
    cfg = JudgeConfig(
        metrics=[
            MetricSelection(metric="tool_routing", weight=1.0),
            MetricSelection(metric="response_delivery", weight=1.0),
        ]
    )
    resolved = resolve_metrics(cfg)
    assert len(resolved) == 2
    assert abs(sum(w for _, w in resolved) - 1.0) < 1e-9


def test_task_completion_requires_explicit_weight() -> None:
    cfg = JudgeConfig(metrics=[MetricSelection(metric="task_completion", weight=None)])
    with pytest.raises(ValueError, match="task_completion requires"):
        resolve_metrics(cfg)


def test_build_judge_response_format_keys() -> None:
    metrics = [METRIC_REGISTRY["tool_routing"], METRIC_REGISTRY["task_completion"]]
    fmt = build_judge_response_format(metrics)
    assert fmt["type"] == "json_schema"
    js = fmt["json_schema"]
    schema = js["schema"]
    props = schema["properties"]
    assert set(props.keys()) == {"task_completion", "tool_routing"}
