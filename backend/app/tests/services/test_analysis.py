"""Unit tests for app.services.analysis (CS-29)."""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.comparison import (
    AggregateComparison,
    CauseAnalysisItem,
    EvalSetDiff,
    FieldChange,
    ImprovementSuggestion,
    ImprovementSuggestions,
    MetricAggregateDelta,
    PromptDiff,
    RegressionAnalysis,
    RegressionThresholds,
    RegressionVerdict,
    RunComparison,
    RunConfigDiff,
    SuggestionsRequest,
    TestCaseComparison,
    ToolDiff,
)
from app.models.schemas import AggregateMetrics
from app.services.analysis import (
    _build_analysis_prompt,
    _build_tool_diff_summary,
    _extract_simulator_change,
    _format_field_change,
    _format_metric_deltas,
    _format_top_regressed_test_cases,
    _parse_analysis_json,
    compute_improvement_suggestions,
    compute_prompt_semantic_summary,
    compute_regression_analysis_with_prompts,
)

# ── Helpers ──────────────────────────────────────────────────────


def _make_aggregate_metrics(**overrides: object) -> AggregateMetrics:
    defaults = {
        "unique_test_case_count": 10,
        "total_executions": 10,
        "passed_count": 8,
        "failed_count": 2,
        "error_count": 0,
        "pass_rate": 0.8,
        "avg_overall_score": 75.0,
        "latency_avg_ms": 500.0,
    }
    defaults.update(overrides)
    return AggregateMetrics(**defaults)


def _make_config_diff(**overrides: object) -> RunConfigDiff:
    defaults = {
        "prompt_diff": PromptDiff(changed=False, change_ratio=0.0),
        "tool_diff": ToolDiff(),
        "eval_set_diff": EvalSetDiff(
            same_set=True,
            version_changed=False,
            common_test_case_ids=[uuid.uuid4()],
        ),
    }
    defaults.update(overrides)
    return RunConfigDiff(**defaults)


def _make_comparison(
    *,
    pass_rate_delta: float = -0.1,
    avg_score_delta: float = -10.0,
    total_regressions: int = 2,
    total_improvements: int = 0,
    test_case_comparisons: list[TestCaseComparison] | None = None,
    config_diff: RunConfigDiff | None = None,
    per_metric_aggregate_deltas: list[MetricAggregateDelta] | None = None,
) -> RunComparison:
    b_metrics = _make_aggregate_metrics(pass_rate=0.9, avg_overall_score=85.0)
    c_metrics = _make_aggregate_metrics(
        pass_rate=0.9 + pass_rate_delta,
        avg_overall_score=85.0 + (avg_score_delta or 0),
    )
    agg = AggregateComparison(
        baseline_metrics=b_metrics,
        candidate_metrics=c_metrics,
        pass_rate_delta=pass_rate_delta,
        avg_score_delta=avg_score_delta,
        total_regressions=total_regressions,
        total_improvements=total_improvements,
        total_unchanged=8,
        total_errors=0,
        per_metric_aggregate_deltas=per_metric_aggregate_deltas or [],
    )
    return RunComparison(
        baseline_run_id=uuid.uuid4(),
        candidate_run_id=uuid.uuid4(),
        aggregate=agg,
        test_case_comparisons=test_case_comparisons or [],
        baseline_only_test_cases=[],
        candidate_only_test_cases=[],
        config_diff=config_diff or _make_config_diff(),
        verdict=RegressionVerdict(
            regression_detected=True,
            reasons=["pass_rate dropped"],
            thresholds_used=RegressionThresholds(),
        ),
        warnings=[],
    )


def _make_fake_run(**overrides: object) -> SimpleNamespace:
    defaults = {
        "id": uuid.uuid4(),
        "agent_system_prompt": "You are a helpful assistant.",
        "agent_tools": None,
        "tools_snapshot": [
            {
                "type": "function",
                "function": {"name": "search", "description": "Search the web"},
            },
        ],
        "config": {"judge": {"model": "gpt-4o", "provider": "openai"}},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_llm_response(
    content: str, model: str = "anthropic/claude-sonnet-4-20250514"
) -> object:
    return SimpleNamespace(
        content=content,
        model=model,
        usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        latency_ms=500,
        response_cost_usd=0.01,
        tool_calls=None,
    )


# ── _parse_analysis_json ─────────────────────────────────────────


class TestParseAnalysisJson:
    def test_plain_json(self) -> None:
        raw = '{"analysis": [], "summary": "test"}'
        result = _parse_analysis_json(raw)
        assert result["summary"] == "test"

    def test_json_in_code_fence(self) -> None:
        raw = '```json\n{"analysis": [], "summary": "fenced"}\n```'
        result = _parse_analysis_json(raw)
        assert result["summary"] == "fenced"

    def test_code_fence_no_lang(self) -> None:
        raw = '```\n{"analysis": [], "summary": "nolang"}\n```'
        result = _parse_analysis_json(raw)
        assert result["summary"] == "nolang"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_analysis_json("not json")


# ── _format helpers ──────────────────────────────────────────────


class TestFormatHelpers:
    def test_format_field_change_none(self) -> None:
        result = _format_field_change("Model", None)
        assert "unchanged" in result

    def test_format_field_change_with_values(self) -> None:
        fc = FieldChange(field="agent_model", old_value="gpt-4o", new_value="gpt-4.1")
        result = _format_field_change("Model", fc)
        assert "gpt-4o" in result
        assert "gpt-4.1" in result

    def test_format_metric_deltas_empty(self) -> None:
        result = _format_metric_deltas([])
        assert "none" in result

    def test_format_metric_deltas_with_data(self) -> None:
        deltas = [
            MetricAggregateDelta(
                metric="accuracy",
                is_binary=False,
                baseline_avg=4.0,
                candidate_avg=3.0,
                delta=-1.0,
            )
        ]
        result = _format_metric_deltas(deltas)
        assert "accuracy" in result
        assert "-1.00" in result

    def test_format_top_regressed_test_cases_empty(self) -> None:
        result = _format_top_regressed_test_cases([])
        assert "none" in result

    def test_format_top_regressed_test_cases_sorted(self) -> None:
        comparisons = [
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="Mild regression",
                status="regression",
                score_delta=-5.0,
                metric_deltas=[],
            ),
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="Severe regression",
                status="regression",
                score_delta=-20.0,
                metric_deltas=[],
            ),
            TestCaseComparison(
                test_case_id=uuid.uuid4(),
                test_case_name="Unchanged",
                status="unchanged",
                score_delta=0.0,
                metric_deltas=[],
            ),
        ]
        result = _format_top_regressed_test_cases(comparisons)
        # Severe comes first (most negative delta)
        assert result.index("Severe") < result.index("Mild")
        assert "Unchanged" not in result

    def test_build_tool_diff_summary_unchanged(self) -> None:
        diff = _make_config_diff(tool_diff=ToolDiff())
        result = _build_tool_diff_summary(diff)
        assert result == "unchanged"

    def test_build_tool_diff_summary_with_changes(self) -> None:
        diff = _make_config_diff(
            tool_diff=ToolDiff(added=["new_tool"], removed=["old_tool"])
        )
        result = _build_tool_diff_summary(diff)
        assert "new_tool" in result
        assert "old_tool" in result

    def test_build_tool_diff_summary_none(self) -> None:
        diff = _make_config_diff(tool_diff=None)
        result = _build_tool_diff_summary(diff)
        assert result == "unchanged"

    def test_extract_simulator_change_none(self) -> None:
        diff = _make_config_diff()
        result = _extract_simulator_change(diff)
        assert result == "unchanged"

    def test_extract_simulator_change_present(self) -> None:
        diff = _make_config_diff(
            config_changes=[
                FieldChange(
                    field="root['user_simulator']['model']",
                    old_value="gpt-4o",
                    new_value="gpt-4.1",
                )
            ]
        )
        result = _extract_simulator_change(diff)
        assert "user_simulator" in result


# ── _build_analysis_prompt ───────────────────────────────────────


class TestBuildAnalysisPrompt:
    def test_produces_system_and_user_messages(self) -> None:
        comparison = _make_comparison()
        config_diff = _make_config_diff()
        messages = _build_analysis_prompt(
            comparison, config_diff, "Prompt changed to be more formal"
        )
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert "more formal" in messages[1].content
        assert "JSON" in messages[0].content

    def test_includes_infrastructure_notes(self) -> None:
        config_diff = _make_config_diff(
            judge_model_changed=FieldChange(
                field="judge.model", old_value="gpt-4o", new_value="gpt-4.1"
            )
        )
        comparison = _make_comparison(config_diff=config_diff)
        messages = _build_analysis_prompt(comparison, config_diff, None)
        assert "gpt-4.1" in messages[1].content

    def test_no_prompt_change_says_unchanged(self) -> None:
        comparison = _make_comparison()
        config_diff = _make_config_diff()
        messages = _build_analysis_prompt(comparison, config_diff, None)
        assert "Prompt: unchanged" in messages[1].content


# ── compute_prompt_semantic_summary ──────────────────────────────


class TestComputePromptSemanticSummary:
    @pytest.mark.asyncio
    async def test_identical_prompts_return_none(self) -> None:
        result, cost = await compute_prompt_semantic_summary("hello", "hello")
        assert result is None
        assert cost is None

    @pytest.mark.asyncio
    async def test_both_none_return_none(self) -> None:
        result, cost = await compute_prompt_semantic_summary(None, None)
        assert result is None
        assert cost is None

    @pytest.mark.asyncio
    async def test_different_prompts_call_llm(self) -> None:
        fake_resp = _fake_llm_response("Added formality constraints.")
        with patch(
            "app.services.analysis.call_llm",
            new_callable=AsyncMock,
            return_value=fake_resp,
        ) as mock_llm:
            result, cost = await compute_prompt_semantic_summary(
                "Be helpful.", "Be helpful and formal."
            )
        assert result == "Added formality constraints."
        assert cost == 0.01
        mock_llm.assert_called_once()


# ── compute_regression_analysis_with_prompts ─────────────────────


class TestComputeRegressionAnalysis:
    @pytest.mark.asyncio
    async def test_no_shifts_returns_none(self) -> None:
        comparison = _make_comparison(
            pass_rate_delta=0.0,
            avg_score_delta=0.0,
            total_regressions=0,
            total_improvements=0,
        )
        result = await compute_regression_analysis_with_prompts(
            comparison, comparison.config_diff, "prompt a", "prompt a"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_analysis_with_prompt_change(self) -> None:
        config_diff = _make_config_diff(
            prompt_diff=PromptDiff(
                changed=True,
                change_ratio=0.3,
                added_line_count=5,
                removed_line_count=2,
            )
        )
        comparison = _make_comparison(config_diff=config_diff)

        analysis_json = json.dumps(
            {
                "analysis": [
                    {
                        "metric": "accuracy",
                        "direction": "regressed",
                        "likely_cause": "Prompt change removed helpful instructions",
                        "confidence": "high",
                        "reasoning": "The removed lines contained key accuracy guidance",
                    }
                ],
                "infrastructure_notes": [],
                "summary": "Prompt changes caused accuracy regression.",
            }
        )

        summary_resp = _fake_llm_response("Added formality, removed fallback greeting.")
        analysis_resp = _fake_llm_response(analysis_json)

        call_count = 0

        async def mock_call_llm(_messages, config=None, **_kwargs):  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return summary_resp
            return analysis_resp

        with patch("app.services.analysis.call_llm", side_effect=mock_call_llm):
            result = await compute_regression_analysis_with_prompts(
                comparison, config_diff, "Be helpful.", "Be formal."
            )

        assert result is not None
        assert (
            result.prompt_semantic_summary
            == "Added formality, removed fallback greeting."
        )
        assert len(result.analysis) == 1
        assert result.analysis[0].metric == "accuracy"
        assert result.analysis[0].direction == "regressed"
        assert result.analysis[0].confidence == "high"
        assert result.analysis_cost_usd == pytest.approx(0.02)

    @pytest.mark.asyncio
    async def test_analysis_without_prompt_change(self) -> None:
        comparison = _make_comparison()

        analysis_json = json.dumps(
            {
                "analysis": [
                    {
                        "metric": "pass_rate",
                        "direction": "regressed",
                        "likely_cause": "LLM non-determinism",
                        "confidence": "low",
                        "reasoning": "No config changes detected",
                    }
                ],
                "infrastructure_notes": ["Judge model unchanged"],
                "summary": "Likely LLM non-determinism.",
            }
        )
        analysis_resp = _fake_llm_response(analysis_json)

        with patch(
            "app.services.analysis.call_llm",
            new_callable=AsyncMock,
            return_value=analysis_resp,
        ):
            result = await compute_regression_analysis_with_prompts(
                comparison, comparison.config_diff, "prompt", "prompt"
            )

        assert result is not None
        assert result.prompt_semantic_summary is None  # no prompt change
        assert len(result.analysis) == 1
        assert result.infrastructure_notes == ["Judge model unchanged"]

    @pytest.mark.asyncio
    async def test_malformed_json_returns_fallback(self) -> None:
        comparison = _make_comparison()
        bad_resp = _fake_llm_response("This is not JSON at all, sorry.")

        with patch(
            "app.services.analysis.call_llm",
            new_callable=AsyncMock,
            return_value=bad_resp,
        ):
            result = await compute_regression_analysis_with_prompts(
                comparison, comparison.config_diff, "a", "a"
            )

        assert result is not None
        assert result.analysis == []
        assert "not JSON" in result.summary

    @pytest.mark.asyncio
    async def test_malformed_analysis_items_skipped(self) -> None:
        comparison = _make_comparison()

        analysis_json = json.dumps(
            {
                "analysis": [
                    {
                        "metric": "accuracy",
                        "direction": "regressed",
                        "likely_cause": "something",
                        "confidence": "high",
                        "reasoning": "valid",
                    },
                    {
                        "metric": "bad_metric",
                        "direction": "invalid_direction",  # not in Literal
                        "likely_cause": "x",
                        "confidence": "high",
                        "reasoning": "y",
                    },
                ],
                "infrastructure_notes": [],
                "summary": "Mixed results.",
            }
        )
        analysis_resp = _fake_llm_response(analysis_json)

        with patch(
            "app.services.analysis.call_llm",
            new_callable=AsyncMock,
            return_value=analysis_resp,
        ):
            result = await compute_regression_analysis_with_prompts(
                comparison, comparison.config_diff, "a", "a"
            )

        assert result is not None
        # Only the valid item should be included
        assert len(result.analysis) == 1
        assert result.analysis[0].metric == "accuracy"


# ── compute_improvement_suggestions ──────────────────────────────


class TestComputeImprovementSuggestions:
    @pytest.mark.asyncio
    async def test_returns_suggestions(self) -> None:
        comparison = _make_comparison()
        analysis = RegressionAnalysis(
            analysis=[
                CauseAnalysisItem(
                    metric="accuracy",
                    direction="regressed",
                    likely_cause="Prompt too vague",
                    confidence="high",
                    reasoning="test",
                )
            ],
            infrastructure_notes=[],
            summary="Accuracy regressed due to vague prompt.",
            analysis_model="anthropic/claude-sonnet-4-20250514",
        )
        candidate_run = _make_fake_run()

        suggestions_json = json.dumps(
            {
                "suggestions": [
                    {
                        "target": "system_prompt",
                        "title": "Add explicit accuracy instructions",
                        "description": "Add a section with specific accuracy requirements.",
                        "current_value": "You are a helpful assistant.",
                        "suggested_value": "You are a helpful and accurate assistant. Always verify facts.",
                        "expected_metric_impact": ["accuracy"],
                        "priority": "high",
                    },
                ],
                "summary": "One key prompt improvement suggested.",
            }
        )
        suggestions_resp = _fake_llm_response(suggestions_json)

        with patch(
            "app.services.analysis.call_llm",
            new_callable=AsyncMock,
            return_value=suggestions_resp,
        ):
            result = await compute_improvement_suggestions(
                comparison, analysis, candidate_run
            )

        assert isinstance(result, ImprovementSuggestions)
        assert len(result.suggestions) == 1
        assert result.suggestions[0].target == "system_prompt"
        assert result.suggestions[0].priority == "high"
        assert "accuracy" in result.suggestions[0].expected_metric_impact
        assert result.cost_usd == 0.01

    @pytest.mark.asyncio
    async def test_malformed_response_returns_empty(self) -> None:
        comparison = _make_comparison()
        analysis = RegressionAnalysis(
            analysis=[],
            infrastructure_notes=[],
            summary="test",
            analysis_model="gpt-4o",
        )
        candidate_run = _make_fake_run()
        bad_resp = _fake_llm_response("Not valid JSON response")

        with patch(
            "app.services.analysis.call_llm",
            new_callable=AsyncMock,
            return_value=bad_resp,
        ):
            result = await compute_improvement_suggestions(
                comparison, analysis, candidate_run
            )

        assert result.suggestions == []
        assert "Not valid" in result.summary


# ── Model validation ─────────────────────────────────────────────


class TestModelValidation:
    def test_cause_analysis_item_valid(self) -> None:
        item = CauseAnalysisItem(
            metric="accuracy",
            direction="regressed",
            likely_cause="Prompt change",
            confidence="high",
            reasoning="Clear correlation",
        )
        assert item.direction == "regressed"

    def test_cause_analysis_item_invalid_direction(self) -> None:
        with pytest.raises(ValueError):
            CauseAnalysisItem(
                metric="accuracy",
                direction="sideways",
                likely_cause="x",
                confidence="high",
                reasoning="y",
            )

    def test_improvement_suggestion_valid(self) -> None:
        s = ImprovementSuggestion(
            target="system_prompt",
            title="Test",
            description="Test desc",
            expected_metric_impact=["accuracy"],
            priority="high",
        )
        assert s.target == "system_prompt"

    def test_improvement_suggestion_invalid_target(self) -> None:
        with pytest.raises(ValueError):
            ImprovementSuggestion(
                target="invalid_target",
                title="Test",
                description="Test",
                expected_metric_impact=[],
                priority="high",
            )

    def test_suggestions_request(self) -> None:
        req = SuggestionsRequest(
            baseline_run_id=uuid.uuid4(),
            candidate_run_id=uuid.uuid4(),
        )
        assert req.baseline_run_id is not None

    def test_regression_analysis_model_config(self) -> None:
        """Verify model_config allows 'model' as a field name."""
        ra = RegressionAnalysis(
            analysis=[],
            infrastructure_notes=[],
            summary="test",
            analysis_model="gpt-4o",
            analysis_cost_usd=0.01,
        )
        assert ra.analysis_model == "gpt-4o"

    def test_run_comparison_with_analysis(self) -> None:
        """Verify RunComparison accepts regression_analysis field."""
        comparison = _make_comparison()
        analysis = RegressionAnalysis(
            analysis=[],
            infrastructure_notes=[],
            summary="test",
            analysis_model="gpt-4o",
        )
        comparison.regression_analysis = analysis
        assert comparison.regression_analysis is not None
        assert comparison.regression_analysis.analysis_model == "gpt-4o"
