"""Custom metric resolution needs a real DB session.

``app/tests/services/conftest.py`` overrides ``db`` for service unit tests; these
integration-style checks live at the ``tests`` package root next to the session
``db`` fixture.
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from app import crud
from app.models import CustomMetricCreate, MetricTier, ScoreType
from app.models.enums import TestCaseStatus, TurnRole
from app.models.schemas import ConversationTurn, JudgeConfig, MetricSelection
from app.models.test_case import TestCase
from app.services.judge import JudgeInput, evaluate_transcript
from app.services.judge_metrics import (
    custom_metric_row_to_definition,
    resolve_metrics,
)
from app.tests.utils.user import create_random_user


def test_custom_metric_row_to_definition_matches_shape(db: Session) -> None:
    owner = create_random_user(db)
    name = f"judge_shape_{uuid.uuid4().hex[:10]}"
    row = crud.create_custom_metric(
        session=db,
        metric_in=CustomMetricCreate(
            name=name,
            display_name="Shape",
            description="d",
            tier=MetricTier.EXECUTION,
            default_weight=0.3,
            score_type=ScoreType.SCORED,
            rubric="Measures: x.\n5: y.",
            include_in_defaults=True,
        ),
        owner_id=owner.id,
    )
    d = custom_metric_row_to_definition(row)
    assert d.name == name
    assert d.display_name == "Shape"
    assert d.tier == MetricTier.EXECUTION
    assert d.include_in_defaults is True


def test_resolve_metrics_custom_from_db(db: Session) -> None:
    owner = create_random_user(db)
    name = f"custom_res_{uuid.uuid4().hex[:10]}"
    crud.create_custom_metric(
        session=db,
        metric_in=CustomMetricCreate(
            name=name,
            display_name="Custom",
            description="Custom desc",
            tier=MetricTier.PROCESS,
            default_weight=0.4,
            score_type=ScoreType.SCORED,
            rubric="Measures: flow.\n5: Smooth.\n   Example: Agent recovered.",
            include_in_defaults=False,
        ),
        owner_id=owner.id,
    )
    cfg = JudgeConfig(metrics=[MetricSelection(metric=name, weight=2.0)])
    resolved = resolve_metrics(cfg, session=db)
    assert len(resolved) == 1
    assert resolved[0][0].name == name
    assert abs(resolved[0][1] - 1.0) < 1e-9


def test_resolve_metrics_mixed_builtin_and_custom(db: Session) -> None:
    owner = create_random_user(db)
    name = f"mixed_{uuid.uuid4().hex[:10]}"
    crud.create_custom_metric(
        session=db,
        metric_in=CustomMetricCreate(
            name=name,
            display_name="Mixed",
            description="d",
            tier=MetricTier.DELIVERY,
            default_weight=0.5,
            score_type=ScoreType.SCORED,
            rubric="Measures: tone.\n5: Good.\n   Example: Brief reply.",
            include_in_defaults=False,
        ),
        owner_id=owner.id,
    )
    cfg = JudgeConfig(
        metrics=[
            MetricSelection(metric="tool_routing", weight=1.0),
            MetricSelection(metric=name, weight=1.0),
        ]
    )
    resolved = resolve_metrics(cfg, session=db)
    names = {m.name for m, _ in resolved}
    assert names == {"tool_routing", name}
    assert abs(sum(w for _, w in resolved) - 1.0) < 1e-9


def _minimal_transcript() -> list[ConversationTurn]:
    return [
        ConversationTurn(
            index=0, role=TurnRole.USER, content="Hi", timestamp=datetime.now(UTC)
        ),
        ConversationTurn(
            index=1,
            role=TurnRole.ASSISTANT,
            content="Hello!",
            timestamp=datetime.now(UTC),
        ),
    ]


def _minimal_test_case() -> TestCase:
    return TestCase(
        id=uuid.uuid4(),
        name="test-custom-metric",
        status=TestCaseStatus.ACTIVE,
        first_message="Hi",
        tags=[],
    )


@pytest.mark.asyncio
async def test_evaluate_transcript_with_custom_metric(db: Session) -> None:
    """Full judge pipeline resolves a DB-backed custom metric and scores it."""
    owner = create_random_user(db)

    name = f"e2e_judge_{uuid.uuid4().hex[:8]}"
    crud.create_custom_metric(
        session=db,
        metric_in=CustomMetricCreate(
            name=name,
            display_name="E2E Judge Metric",
            description="Test metric for judge integration",
            tier=MetricTier.DELIVERY,
            default_weight=1.0,
            score_type=ScoreType.SCORED,
            rubric=(
                "Scored 0-5 integer. Measures: greeting quality.\n"
                "5: Perfect greeting.\n   Example: Agent greets warmly.\n"
                "0: No greeting.\n   Example: Agent ignores user."
            ),
            include_in_defaults=False,
        ),
        owner_id=owner.id,
    )

    judge_output = json.dumps(
        {
            name: {
                "score": 4,
                "justification": "Agent greeted the user warmly.",
                "failure_code": None,
                "turns": [],
            }
        }
    )

    mock_llm_response = AsyncMock()
    mock_llm_response.return_value.content = judge_output
    mock_llm_response.return_value.model = "test-model"
    mock_llm_response.return_value.usage = {"prompt_tokens": 10, "completion_tokens": 5}
    mock_llm_response.return_value.latency_ms = 100
    mock_llm_response.return_value.response_cost_usd = 0.001

    inp = JudgeInput(
        transcript=_minimal_transcript(),
        test_case=_minimal_test_case(),
        agent_system_prompt=None,
        agent_tools=None,
        judge_config=JudgeConfig(metrics=[MetricSelection(metric=name, weight=1.0)]),
    )

    with patch("app.services.judge.call_llm", mock_llm_response):
        verdict = await evaluate_transcript(inp)

    assert verdict.passed is True
    assert len(verdict.metric_scores) == 1
    assert verdict.metric_scores[0].metric == name
    assert verdict.metric_scores[0].score == 4


@pytest.mark.asyncio
async def test_evaluate_transcript_unknown_metric_returns_failed_verdict() -> None:
    """When a non-existent metric name is requested, return a failed verdict
    instead of raising."""
    inp = JudgeInput(
        transcript=_minimal_transcript(),
        test_case=_minimal_test_case(),
        agent_system_prompt=None,
        agent_tools=None,
        judge_config=JudgeConfig(
            metrics=[MetricSelection(metric="nonexistent_metric", weight=1.0)]
        ),
    )
    verdict = await evaluate_transcript(inp)
    assert verdict.passed is False
    assert verdict.overall_score == 0.0
    assert "Metric resolution failed" in verdict.summary
