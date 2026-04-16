"""Tests for the judge evaluation pipeline.

Covers score parsing, weighted scoring, summary generation, failure_code/turns
per metric, and graceful error handling.
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.enums import TurnRole
from app.models.schemas import (
    ConversationTurn,
    JudgeConfig,
    JudgeVerdict,
    MetricSelection,
)
from app.models.test_case import TestCase
from app.services.judge import (
    JudgeInput,
    evaluate_transcript,
)
from app.services.llm import LLMResponse

# ── Helpers ───────────────────────────────────────────────────────────


def _make_test_case(**overrides: object) -> TestCase:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "Sample test case",
        "description": "A sample test case for judge tests",
        "expected_outcomes": ["Agent MUST book appointment"],
        "expected_tool_calls": [{"tool": "book_appointment"}],
        "evaluation_criteria_override": None,
        "persona_context": None,
        "first_message": "Hi",
        "user_context": None,
        "tags": [],
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return TestCase(**defaults)  # type: ignore[arg-type]


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
        "tool_routing": {
            "score": 5,
            "justification": "All tools correct (turn 1).",
            "failure_code": None,
            "turns": [],
        },
        "parameter_extraction": {
            "score": 4,
            "justification": "Params mostly correct.",
            "failure_code": None,
            "turns": [],
        },
        "result_interpretation": {
            "score": 5,
            "justification": "Accurate reflection.",
            "failure_code": None,
            "turns": [],
        },
        "grounding_fidelity": {
            "score": 4,
            "justification": "Claims grounded.",
            "failure_code": None,
            "turns": [],
        },
        "instruction_compliance": {
            "score": 5,
            "justification": "Instructions followed.",
            "failure_code": None,
            "turns": [],
        },
        "information_gathering": {
            "score": 4,
            "justification": "Info collected.",
            "failure_code": None,
            "turns": [],
        },
        "conversation_management": {
            "score": 4,
            "justification": "Good flow.",
            "failure_code": None,
            "turns": [],
        },
        "response_delivery": {
            "score": 4,
            "justification": "Concise and natural.",
            "failure_code": None,
            "turns": [],
        },
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
        test_case=_make_test_case(),
        agent_system_prompt="You are a helpful assistant.",
        agent_tools=[{"type": "function", "function": {"name": "book_appointment"}}],
        judge_config=judge_config,
    )


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
        assert len(verdict.metric_scores) == 8
        assert verdict.judge_model == "gpt-4o"
        assert verdict.judge_provider == "openai"
        assert verdict.judge_latency_ms == 1200
        assert verdict.raw_judge_output is not None
        assert verdict.summary is not None

    @pytest.mark.asyncio
    async def test_low_scores_produce_failing_verdict(self) -> None:
        payload = _default_judge_llm_response()
        for key in payload:
            payload[key] = {
                "score": 1,
                "justification": "Poor performance.",
                "failure_code": "poor_performance",
                "turns": [1, 3],
            }

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert verdict.passed is False
        assert verdict.overall_score < 75.0

    @pytest.mark.asyncio
    async def test_failure_code_and_turns_captured(self) -> None:
        """Per-metric failure_code and turns are passed through from judge output."""
        payload = _default_judge_llm_response()
        payload["tool_routing"] = {
            "score": 1,
            "justification": "Wrong tool called at turn 1.",
            "failure_code": "wrong_tool_selected",
            "turns": [1],
        }

        mock_response = _mock_llm_response(payload)

        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        by_name = {ms.metric: ms for ms in verdict.metric_scores}
        tr = by_name["tool_routing"]
        assert tr.failure_code == "wrong_tool_selected"
        assert tr.turns == [1]

        # High-scoring metric should have no failure_code
        pe = by_name["parameter_extraction"]
        assert pe.failure_code is None
        assert pe.turns == []

    @pytest.mark.asyncio
    async def test_custom_pass_threshold(self) -> None:
        payload = _default_judge_llm_response()
        for key in payload:
            payload[key] = {
                "score": 3,
                "justification": "Acceptable.",
                "failure_code": None,
                "turns": [],
            }

        mock_response = _mock_llm_response(payload)
        cfg = JudgeConfig(pass_threshold=50.0)

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
            "tool_routing": {
                "score": 5,
                "justification": "Perfect routing.",
                "failure_code": None,
                "turns": [],
            },
            "response_delivery": {
                "score": 3,
                "justification": "Verbose.",
                "failure_code": "verbose_response",
                "turns": [3],
            },
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
            "tool_routing": {
                "score": 4,
                "justification": "Good.",
                "failure_code": None,
                "turns": [],
            },
            "task_completion": {
                "passed": True,
                "justification": "Task completed.",
                "failure_code": None,
                "turns": [],
            },
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
            "tool_routing": {
                "score": 4,
                "justification": "Good.",
                "failure_code": None,
                "turns": [],
            },
            "task_completion": {
                "passed": False,
                "justification": "Failed.",
                "failure_code": "task_not_completed",
                "turns": [3],
            },
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
        assert tc.failure_code == "task_not_completed"
        assert tc.turns == [3]

    @pytest.mark.asyncio
    async def test_score_labels_assigned_correctly(self) -> None:
        payload = _default_judge_llm_response()
        payload["tool_routing"] = {
            "score": 0,
            "justification": "No tools.",
            "failure_code": "no_tools_called",
            "turns": [0, 1, 2, 3],
        }
        payload["parameter_extraction"] = {
            "score": 1,
            "justification": "Bad.",
            "failure_code": "bad_params",
            "turns": [1],
        }
        payload["result_interpretation"] = {
            "score": 2,
            "justification": "Poor.",
            "failure_code": "poor_interpretation",
            "turns": [3],
        }
        payload["grounding_fidelity"] = {
            "score": 3,
            "justification": "OK.",
            "failure_code": None,
            "turns": [],
        }
        payload["instruction_compliance"] = {
            "score": 4,
            "justification": "Good.",
            "failure_code": None,
            "turns": [],
        }
        payload["information_gathering"] = {
            "score": 5,
            "justification": "Excellent.",
            "failure_code": None,
            "turns": [],
        }

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
        payload["tool_routing"] = {
            "score": 10,
            "justification": "Over max.",
            "failure_code": None,
            "turns": [],
        }

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
        )
        payload = {
            "tool_routing": {
                "score": 5,
                "justification": "Perfect.",
                "failure_code": None,
                "turns": [],
            },
            "grounding_fidelity": {
                "score": 3,
                "justification": "OK.",
                "failure_code": None,
                "turns": [],
            },
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

    @pytest.mark.asyncio
    async def test_llm_exception_returns_error_verdict(self) -> None:
        """Unrecoverable LLM error should produce a failed verdict."""
        with patch("app.services.judge.call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = RuntimeError("LLM service unavailable")
            inp = _make_judge_input()
            verdict = await evaluate_transcript(inp)

        assert isinstance(verdict, JudgeVerdict)
        assert verdict.passed is False
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
