"""Tests for the judge evaluation pipeline.

Covers score parsing, weighted scoring, critical failure detection,
error category derivation, summary generation, and graceful error handling.
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import ErrorCategory, TurnRole
from app.models.scenario import Scenario
from app.models.schemas import (
    ConversationTurn,
    JudgeConfig,
    JudgeVerdict,
    MetricScore,
    MetricSelection,
)
from app.services.judge import (
    JudgeInput,
    _critical_failure,
    _derive_error_category,
    _effective_numeric_score,
    evaluate_transcript,
)
from app.services.llm import LLMResponse

# ── Helpers ───────────────────────────────────────────────────────────


def _make_scenario(**overrides: object) -> Scenario:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "Test scenario",
        "description": "A test scenario",
        "expected_outcomes": {"task": "book appointment"},
        "expected_tool_calls": [{"tool": "book_appointment"}],
        "evaluation_criteria_override": None,
        "persona": None,
        "initial_message": "Hi",
        "user_context": None,
        "max_turns": 10,
        "tags": [],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Scenario(**defaults)  # type: ignore[arg-type]


def _make_turn(
    index: int,
    role: TurnRole,
    content: str,
) -> ConversationTurn:
    return ConversationTurn(
        index=index,
        role=role,
        content=content,
        tool_calls=None,
        tool_call_id=None,
        latency_ms=100,
        token_count=10,
        timestamp=datetime.now(UTC),
    )


def _make_transcript() -> list[ConversationTurn]:
    return [
        _make_turn(0, TurnRole.USER, "I need to book an appointment"),
        _make_turn(1, TurnRole.ASSISTANT, "Sure, let me help you with that."),
        _make_turn(2, TurnRole.USER, "Tomorrow at 2pm please"),
        _make_turn(3, TurnRole.ASSISTANT, "Done! Your appointment is booked."),
    ]


def _default_judge_llm_response() -> dict[str, object]:
    """LLM JSON payload with all 8 default metrics scoring well."""
    return {
        "tool_routing": {"score": 5, "justification": "All tools correct (turn 1)."},
        "parameter_extraction": {"score": 4, "justification": "Params mostly correct."},
        "result_interpretation": {"score": 5, "justification": "Accurate reflection."},
        "grounding_fidelity": {"score": 4, "justification": "Claims grounded."},
        "instruction_compliance": {
            "score": 5,
            "justification": "Instructions followed.",
        },
        "information_gathering": {"score": 4, "justification": "Info collected."},
        "conversation_management": {"score": 4, "justification": "Good flow."},
        "response_delivery": {"score": 4, "justification": "Concise and natural."},
    }


def _mock_llm_response(payload: dict[str, object]) -> LLMResponse:
    return LLMResponse(
        content=json.dumps(payload),
        model="gpt-4o",
        usage={"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
        latency_ms=1200,
    )


def _make_judge_input(
    *,
    judge_config: JudgeConfig | None = None,
    transcript: list[ConversationTurn] | None = None,
) -> JudgeInput:
    return JudgeInput(
        transcript=transcript if transcript is not None else _make_transcript(),
        scenario=_make_scenario(),
        agent_system_prompt="You are a helpful assistant.",
        agent_tools=[{"type": "function", "function": {"name": "book_appointment"}}],
        judge_config=judge_config,
    )


# ── _effective_numeric_score ──────────────────────────────────────────


class TestEffectiveNumericScore:
    def test_scored_clamps_to_range(self) -> None:
        assert _effective_numeric_score(-1, is_binary=False) == 0
        assert _effective_numeric_score(3, is_binary=False) == 3
        assert _effective_numeric_score(7, is_binary=False) == 5

    def test_binary_pass(self) -> None:
        assert _effective_numeric_score(5, is_binary=True) == 5

    def test_binary_fail(self) -> None:
        assert _effective_numeric_score(0, is_binary=True) == 0
        assert _effective_numeric_score(4, is_binary=True) == 0


# ── _critical_failure ─────────────────────────────────────────────────


class TestCriticalFailure:
    def test_no_failure_when_execution_scores_above_threshold(self) -> None:
        scores = [
            MetricScore(
                metric="tool_routing",
                score=3,
                label="acceptable",
                weight=0.5,
                justification="ok",
                is_binary=False,
                tier="execution",
            ),
            MetricScore(
                metric="grounding_fidelity",
                score=1,
                label="fail",
                weight=0.5,
                justification="bad",
                is_binary=False,
                tier="knowledge",
            ),
        ]
        assert _critical_failure(scores, threshold=1) is False

    def test_failure_when_execution_score_at_threshold(self) -> None:
        scores = [
            MetricScore(
                metric="tool_routing",
                score=1,
                label="fail",
                weight=0.5,
                justification="bad",
                is_binary=False,
                tier="execution",
            ),
        ]
        assert _critical_failure(scores, threshold=1) is True

    def test_failure_when_execution_score_below_threshold(self) -> None:
        scores = [
            MetricScore(
                metric="parameter_extraction",
                score=0,
                label="critical_fail",
                weight=0.5,
                justification="terrible",
                is_binary=False,
                tier="execution",
            ),
        ]
        assert _critical_failure(scores, threshold=1) is True

    def test_binary_metrics_ignored(self) -> None:
        scores = [
            MetricScore(
                metric="task_completion",
                score=0,
                label="fail",
                weight=0.5,
                justification="failed",
                is_binary=True,
                tier="execution",
            ),
        ]
        assert _critical_failure(scores, threshold=1) is False

    def test_non_execution_tiers_ignored(self) -> None:
        scores = [
            MetricScore(
                metric="response_delivery",
                score=0,
                label="critical_fail",
                weight=0.5,
                justification="terrible",
                is_binary=False,
                tier="delivery",
            ),
        ]
        assert _critical_failure(scores, threshold=1) is False

    def test_empty_scores(self) -> None:
        assert _critical_failure([], threshold=1) is False


# ── _derive_error_category ────────────────────────────────────────────


class TestDeriveErrorCategory:
    def test_passed_returns_none(self) -> None:
        scores = [
            MetricScore(
                metric="tool_routing",
                score=1,
                label="fail",
                weight=1.0,
                justification="bad",
                is_binary=False,
                tier="execution",
            ),
        ]
        assert _derive_error_category(scores, passed=True) == ErrorCategory.NONE

    def test_empty_scores_returns_other(self) -> None:
        assert _derive_error_category([], passed=False) == ErrorCategory.OTHER

    def test_lowest_execution_metric_maps_to_tool_misuse(self) -> None:
        scores = [
            MetricScore(
                metric="tool_routing",
                score=1,
                label="fail",
                weight=0.5,
                justification="wrong tool",
                is_binary=False,
                tier="execution",
            ),
            MetricScore(
                metric="grounding_fidelity",
                score=4,
                label="good",
                weight=0.5,
                justification="fine",
                is_binary=False,
                tier="knowledge",
            ),
        ]
        assert _derive_error_category(scores, passed=False) == ErrorCategory.TOOL_MISUSE

    def test_lowest_result_interpretation_maps_to_hallucination(self) -> None:
        scores = [
            MetricScore(
                metric="tool_routing",
                score=4,
                label="good",
                weight=0.5,
                justification="fine",
                is_binary=False,
                tier="execution",
            ),
            MetricScore(
                metric="result_interpretation",
                score=0,
                label="critical_fail",
                weight=0.5,
                justification="fabricated",
                is_binary=False,
                tier="execution",
            ),
        ]
        assert (
            _derive_error_category(scores, passed=False) == ErrorCategory.HALLUCINATION
        )

    def test_lowest_instruction_compliance_maps_to_prompt_violation(self) -> None:
        scores = [
            MetricScore(
                metric="instruction_compliance",
                score=1,
                label="fail",
                weight=0.5,
                justification="violated",
                is_binary=False,
                tier="knowledge",
            ),
            MetricScore(
                metric="response_delivery",
                score=3,
                label="acceptable",
                weight=0.5,
                justification="ok",
                is_binary=False,
                tier="delivery",
            ),
        ]
        assert (
            _derive_error_category(scores, passed=False)
            == ErrorCategory.PROMPT_VIOLATION
        )

    def test_unknown_metric_returns_other(self) -> None:
        scores = [
            MetricScore(
                metric="nonexistent_metric",
                score=0,
                label="fail",
                weight=1.0,
                justification="bad",
                is_binary=False,
                tier="execution",
            ),
        ]
        assert _derive_error_category(scores, passed=False) == ErrorCategory.OTHER


# ── evaluate_transcript ───────────────────────────────────────────────


class TestEvaluateTranscript:
    @pytest.fixture()
    def _mock_settings(self) -> dict[str, object]:
        """Patch settings used by evaluate_transcript."""
        return {
            "JUDGE_TEMPERATURE": 0.0,
            "JUDGE_MAX_TOKENS": 4096,
            "LLM_DEFAULT_PROVIDER": "openai",
            "LLM_DEFAULT_MODEL": "gpt-4o",
            "LLM_RETRY_MAX_ATTEMPTS": 1,
            "LLM_RETRY_MIN_WAIT_SECONDS": 0.1,
            "LLM_RETRY_MAX_WAIT_SECONDS": 0.5,
        }

    @pytest.mark.asyncio
    async def test_all_high_scores_produces_passing_verdict(self) -> None:
        payload = _default_judge_llm_response()
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert isinstance(verdict, JudgeVerdict)
        assert verdict.passed is True
        assert verdict.overall_score > 75.0
        assert verdict.critical_failure is False
        assert verdict.error_category == ErrorCategory.NONE
        assert len(verdict.metric_scores) == 8
        assert verdict.judge_model == "gpt-4o"
        assert verdict.judge_provider == "openai"
        assert verdict.judge_latency_ms == 1200
        assert verdict.raw_judge_output is not None
        assert verdict.summary is not None  # summary now populated

    @pytest.mark.asyncio
    async def test_low_scores_produce_failing_verdict(self) -> None:
        payload = _default_judge_llm_response()
        # Make all scores low
        for key in payload:
            payload[key] = {"score": 1, "justification": "Poor performance."}

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert verdict.passed is False
        assert verdict.overall_score < 75.0
        assert verdict.critical_failure is True  # execution metrics at 1 ≤ threshold 1
        assert verdict.error_category != ErrorCategory.NONE

    @pytest.mark.asyncio
    async def test_critical_failure_overrides_high_overall_score(self) -> None:
        """Even if overall_score ≥ threshold, critical_failure forces failure."""
        payload = _default_judge_llm_response()
        # One execution metric at 0, rest very high
        payload["tool_routing"] = {"score": 0, "justification": "No tools called."}
        for key in payload:
            if key != "tool_routing":
                payload[key] = {"score": 5, "justification": "Perfect."}

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert verdict.critical_failure is True
        assert verdict.passed is False

    @pytest.mark.asyncio
    async def test_custom_pass_threshold(self) -> None:
        payload = _default_judge_llm_response()
        # Set all scores to 3 → overall ~60%
        for key in payload:
            payload[key] = {"score": 3, "justification": "Acceptable."}

        mock_response = _mock_llm_response(payload)
        cfg = JudgeConfig(pass_threshold=50.0, critical_failure_threshold=0)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input(judge_config=cfg)
            verdict = await evaluate_transcript(inp)

        assert verdict.overall_score == 60.0
        assert verdict.passed is True

    @pytest.mark.asyncio
    async def test_custom_metrics_subset(self) -> None:
        cfg = JudgeConfig(
            metrics=[
                MetricSelection(metric="tool_routing", weight=1.0),
                MetricSelection(metric="response_delivery", weight=1.0),
            ],
        )
        payload = {
            "tool_routing": {"score": 5, "justification": "Perfect routing."},
            "response_delivery": {"score": 3, "justification": "Verbose."},
        }
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input(judge_config=cfg)
            verdict = await evaluate_transcript(inp)

        assert len(verdict.metric_scores) == 2
        metrics_by_name = {ms.metric: ms for ms in verdict.metric_scores}
        assert metrics_by_name["tool_routing"].score == 5
        assert metrics_by_name["response_delivery"].score == 3
        # (5/5 * 0.5 + 3/5 * 0.5) * 100 = 80.0
        assert verdict.overall_score == 80.0

    @pytest.mark.asyncio
    async def test_binary_metric_scoring(self) -> None:
        cfg = JudgeConfig(
            metrics=[
                MetricSelection(metric="tool_routing", weight=1.0),
                MetricSelection(metric="task_completion", weight=1.0),
            ],
        )
        payload = {
            "tool_routing": {"score": 4, "justification": "Good."},
            "task_completion": {"passed": True, "justification": "Task completed."},
        }
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input(judge_config=cfg)
            verdict = await evaluate_transcript(inp)

        metrics_by_name = {ms.metric: ms for ms in verdict.metric_scores}
        tc = metrics_by_name["task_completion"]
        assert tc.is_binary is True
        assert tc.score == 5
        assert tc.label == "pass"

    @pytest.mark.asyncio
    async def test_binary_metric_fail(self) -> None:
        cfg = JudgeConfig(
            metrics=[
                MetricSelection(metric="tool_routing", weight=1.0),
                MetricSelection(metric="task_completion", weight=1.0),
            ],
        )
        payload = {
            "tool_routing": {"score": 4, "justification": "Good."},
            "task_completion": {"passed": False, "justification": "Failed."},
        }
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input(judge_config=cfg)
            verdict = await evaluate_transcript(inp)

        metrics_by_name = {ms.metric: ms for ms in verdict.metric_scores}
        tc = metrics_by_name["task_completion"]
        assert tc.score == 0
        assert tc.label == "fail"

    @pytest.mark.asyncio
    async def test_score_labels_assigned_correctly(self) -> None:
        payload = _default_judge_llm_response()
        payload["tool_routing"] = {"score": 0, "justification": "No tools."}
        payload["parameter_extraction"] = {"score": 1, "justification": "Bad."}
        payload["result_interpretation"] = {"score": 2, "justification": "Poor."}
        payload["grounding_fidelity"] = {"score": 3, "justification": "OK."}
        payload["instruction_compliance"] = {"score": 4, "justification": "Good."}
        payload["information_gathering"] = {"score": 5, "justification": "Excellent."}

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        by_name = {ms.metric: ms for ms in verdict.metric_scores}
        assert by_name["tool_routing"].label == "critical_fail"
        assert by_name["parameter_extraction"].label == "fail"
        assert by_name["result_interpretation"].label == "poor"
        assert by_name["grounding_fidelity"].label == "acceptable"
        assert by_name["instruction_compliance"].label == "good"
        assert by_name["information_gathering"].label == "excellent"

    @pytest.mark.asyncio
    async def test_score_clamped_to_0_5(self) -> None:
        payload = _default_judge_llm_response()
        payload["tool_routing"] = {"score": 10, "justification": "Over max."}

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        by_name = {ms.metric: ms for ms in verdict.metric_scores}
        assert by_name["tool_routing"].score == 5

    @pytest.mark.asyncio
    async def test_weighted_overall_score_calculation(self) -> None:
        """Two metrics with equal weight: score = (s1/5 * 0.5 + s2/5 * 0.5) * 100."""
        cfg = JudgeConfig(
            metrics=[
                MetricSelection(metric="tool_routing", weight=1.0),
                MetricSelection(metric="grounding_fidelity", weight=1.0),
            ],
            critical_failure_threshold=0,
        )
        payload = {
            "tool_routing": {"score": 5, "justification": "Perfect."},
            "grounding_fidelity": {"score": 3, "justification": "OK."},
        }
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input(judge_config=cfg)
            verdict = await evaluate_transcript(inp)

        # (5/5 * 0.5 + 3/5 * 0.5) * 100 = (0.5 + 0.3) * 100 = 80.0
        assert verdict.overall_score == 80.0

    @pytest.mark.asyncio
    async def test_empty_transcript_raises_value_error(self) -> None:
        inp = _make_judge_input(transcript=[])
        with pytest.raises(ValueError, match="Cannot evaluate an empty transcript"):
            await evaluate_transcript(inp)

    @pytest.mark.asyncio
    async def test_malformed_json_returns_error_verdict(self) -> None:
        """Malformed JSON from LLM should produce a failed verdict, not raise."""
        mock_response = LLMResponse(
            content="This is not JSON at all",
            model="gpt-4o",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            latency_ms=500,
        )

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert isinstance(verdict, JudgeVerdict)
        assert verdict.passed is False
        assert verdict.error_category == ErrorCategory.OTHER
        assert verdict.overall_score == 0.0
        assert verdict.raw_judge_output == "This is not JSON at all"

    @pytest.mark.asyncio
    async def test_missing_metric_block_returns_error_verdict(self) -> None:
        """If LLM omits a metric key, should produce a failed verdict."""
        payload = _default_judge_llm_response()
        del payload["tool_routing"]  # type: ignore[arg-type]

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert isinstance(verdict, JudgeVerdict)
        assert verdict.passed is False
        assert verdict.error_category == ErrorCategory.OTHER

    @pytest.mark.asyncio
    async def test_llm_exception_returns_error_verdict(self) -> None:
        """Unrecoverable LLM error should produce a failed verdict."""
        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = RuntimeError("LLM service unavailable")
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert isinstance(verdict, JudgeVerdict)
        assert verdict.passed is False
        assert verdict.error_category == ErrorCategory.OTHER
        assert verdict.overall_score == 0.0

    @pytest.mark.asyncio
    async def test_summary_is_populated(self) -> None:
        payload = _default_judge_llm_response()
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert verdict.summary is not None
        assert len(verdict.summary) > 0

    @pytest.mark.asyncio
    async def test_token_usage_recorded(self) -> None:
        payload = _default_judge_llm_response()
        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert verdict.judge_token_usage is not None
        assert verdict.judge_token_usage["prompt_tokens"] == 500
        assert verdict.judge_token_usage["total_tokens"] == 700
