"""Tests for cost_tracker module — token estimation, cost calculation, and aggregation."""

from unittest.mock import patch

import pytest

from app.models.agent_contract import ChatMessage
from app.models.enums import TurnRole
from app.services.cost_tracker import (
    TestCaseTokenAccumulator,
    _char_heuristic_token_estimate,
    _count_tokens,
    estimate_agent_cost,
    estimate_agent_tokens,
    sum_platform_usage_dicts,
    sum_usage_dicts,
)

# ── _char_heuristic_token_estimate ────────────────────────────────────


class TestCharHeuristic:
    def test_empty_string(self) -> None:
        assert _char_heuristic_token_estimate("") == 0

    def test_whitespace_only(self) -> None:
        assert _char_heuristic_token_estimate("   ") == 0

    def test_short_text_returns_at_least_one(self) -> None:
        assert _char_heuristic_token_estimate("hi") == 1

    def test_longer_text(self) -> None:
        text = "a" * 100
        assert _char_heuristic_token_estimate(text) == 25


# ── _count_tokens ─────────────────────────────────────────────────────


class TestCountTokens:
    def test_empty_messages(self) -> None:
        assert _count_tokens("gpt-4o", []) == 0

    def test_uses_litellm_when_available(self) -> None:
        msgs = [{"role": "user", "content": "hello world"}]
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.token_counter.return_value = 42
            result = _count_tokens("gpt-4o", msgs)
        assert result == 42
        mock_litellm.token_counter.assert_called_once_with(
            model="gpt-4o", messages=msgs
        )

    def test_falls_back_to_heuristic_on_error(self) -> None:
        msgs = [{"role": "user", "content": "hello world"}]
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.token_counter.side_effect = RuntimeError("no tokenizer")
            result = _count_tokens("unknown-model", msgs)
        assert result == _char_heuristic_token_estimate("hello world")


# ── estimate_agent_tokens ─────────────────────────────────────────────


class TestEstimateAgentTokens:
    def _msg(self, role: TurnRole, content: str) -> ChatMessage:
        return ChatMessage(role=role, content=content)

    def test_basic_estimation(self) -> None:
        prompt = [self._msg(TurnRole.USER, "What is 2+2?")]
        response = [self._msg(TurnRole.ASSISTANT, "4")]
        with patch("app.services.cost_tracker._count_tokens") as mock_count:
            mock_count.side_effect = [50, 5]  # prompt, completion
            result = estimate_agent_tokens(
                prompt_messages=prompt,
                response_messages=response,
                agent_system_prompt=None,
                agent_tools=None,
                model="gpt-4o",
                fallback_model=None,
            )
        assert result["prompt_tokens"] == 50
        assert result["completion_tokens"] == 5
        assert result["total_tokens"] == 55
        assert result["estimated"] is True

    def test_includes_system_prompt_and_tools(self) -> None:
        response = [self._msg(TurnRole.ASSISTANT, "ok")]
        with patch("app.services.cost_tracker._count_tokens") as mock_count:
            mock_count.side_effect = [100, 3]
            estimate_agent_tokens(
                prompt_messages=None,
                response_messages=response,
                agent_system_prompt="You are a helpful assistant.",
                agent_tools=[{"type": "function", "function": {"name": "get_time"}}],
                model="gpt-4o",
                fallback_model=None,
            )
        # prompt_dicts should have system prompt + tools = 2 entries
        call_args = mock_count.call_args_list[0]
        prompt_dicts = call_args[0][1]
        assert len(prompt_dicts) == 2
        assert prompt_dicts[0]["role"] == "system"
        assert prompt_dicts[1]["content"].startswith("[tools]")

    def test_fallback_model_used_when_model_empty(self) -> None:
        response = [self._msg(TurnRole.ASSISTANT, "ok")]
        with patch("app.services.cost_tracker._count_tokens") as mock_count:
            mock_count.side_effect = [10, 2]
            estimate_agent_tokens(
                prompt_messages=None,
                response_messages=response,
                agent_system_prompt=None,
                agent_tools=None,
                model="",
                fallback_model="claude-3-haiku",
            )
        assert mock_count.call_args_list[0][0][0] == "claude-3-haiku"

    def test_default_model_when_both_empty(self) -> None:
        response = [self._msg(TurnRole.ASSISTANT, "ok")]
        with patch("app.services.cost_tracker._count_tokens") as mock_count:
            mock_count.side_effect = [10, 2]
            estimate_agent_tokens(
                prompt_messages=None,
                response_messages=response,
                agent_system_prompt=None,
                agent_tools=None,
                model=None,
                fallback_model=None,
            )
        assert mock_count.call_args_list[0][0][0] == "gpt-4o"


# ── estimate_agent_cost ───────────────────────────────────────────────


class TestEstimateAgentCost:
    def test_returns_none_for_empty_model(self) -> None:
        assert estimate_agent_cost(model="", provider=None, usage={}) is None
        assert estimate_agent_cost(model=None, provider=None, usage={}) is None

    def test_calls_litellm_with_correct_shape(self) -> None:
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.completion_cost.return_value = 0.0042
            result = estimate_agent_cost(
                model="gpt-4o",
                provider=None,
                usage={"prompt_tokens": 100, "completion_tokens": 50},
            )
        assert result == pytest.approx(0.0042)
        call_kwargs = mock_litellm.completion_cost.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        resp = call_kwargs["completion_response"]
        assert resp["usage"]["prompt_tokens"] == 100
        assert resp["usage"]["completion_tokens"] == 50

    def test_prepends_provider(self) -> None:
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.completion_cost.return_value = 0.001
            estimate_agent_cost(
                model="claude-3-haiku",
                provider="anthropic",
                usage={"prompt_tokens": 10, "completion_tokens": 5},
            )
        call_kwargs = mock_litellm.completion_cost.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-3-haiku"

    def test_skips_provider_if_model_has_slash(self) -> None:
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.completion_cost.return_value = 0.001
            estimate_agent_cost(
                model="anthropic/claude-3-haiku",
                provider="should-be-ignored",
                usage={"prompt_tokens": 10, "completion_tokens": 5},
            )
        call_kwargs = mock_litellm.completion_cost.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-3-haiku"

    def test_passes_cache_tokens(self) -> None:
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.completion_cost.return_value = 0.001
            estimate_agent_cost(
                model="gpt-4o",
                provider=None,
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "cache_creation_input_tokens": 80,
                    "cache_read_input_tokens": 20,
                },
            )
        resp = mock_litellm.completion_cost.call_args[1]["completion_response"]
        assert resp["usage"]["cache_creation_input_tokens"] == 80
        assert resp["usage"]["cache_read_input_tokens"] == 20

    def test_returns_none_on_litellm_error(self) -> None:
        with patch("app.services.cost_tracker.litellm") as mock_litellm:
            mock_litellm.completion_cost.side_effect = Exception("unknown model")
            result = estimate_agent_cost(
                model="some-custom-model",
                provider=None,
                usage={"prompt_tokens": 10, "completion_tokens": 5},
            )
        assert result is None


# ── sum_usage_dicts ───────────────────────────────────────────────────


class TestSumUsageDicts:
    def test_empty_input(self) -> None:
        assert sum_usage_dicts() == {}

    def test_single_dict(self) -> None:
        result = sum_usage_dicts({"prompt_tokens": 10, "completion_tokens": 5})
        assert result == {"prompt_tokens": 10, "completion_tokens": 5}

    def test_multiple_dicts(self) -> None:
        result = sum_usage_dicts(
            {"prompt_tokens": 10, "completion_tokens": 5},
            {"prompt_tokens": 20, "completion_tokens": 10},
        )
        assert result == {"prompt_tokens": 30, "completion_tokens": 15}

    def test_none_skipped(self) -> None:
        result = sum_usage_dicts(
            {"prompt_tokens": 10},
            None,
            {"prompt_tokens": 5},
        )
        assert result == {"prompt_tokens": 15}

    def test_estimated_flag_propagated(self) -> None:
        result = sum_usage_dicts(
            {"prompt_tokens": 10, "estimated": True},
            {"prompt_tokens": 20},
        )
        assert result["estimated"] is True
        assert result["prompt_tokens"] == 30

    def test_estimated_flag_absent_when_not_set(self) -> None:
        result = sum_usage_dicts(
            {"prompt_tokens": 10},
            {"prompt_tokens": 20},
        )
        assert "estimated" not in result

    def test_all_none_returns_empty(self) -> None:
        assert sum_usage_dicts(None, None) == {}


# ── sum_platform_usage_dicts ──────────────────────────────────────────


class TestSumPlatformUsageDicts:
    def test_basic_sum(self) -> None:
        result = sum_platform_usage_dicts(
            {"prompt_tokens": 100, "completion_tokens": 20},
            {"prompt_tokens": 50, "completion_tokens": 10},
        )
        assert result == {"prompt_tokens": 150, "completion_tokens": 30}

    def test_none_skipped(self) -> None:
        result = sum_platform_usage_dicts(None, {"prompt_tokens": 50})
        assert result == {"prompt_tokens": 50}

    def test_empty_returns_empty(self) -> None:
        assert sum_platform_usage_dicts() == {}


# ── TestCaseTokenAccumulator ─────────────────────────────────────────


class TestTestCaseTokenAccumulator:
    def test_empty_accumulator(self) -> None:
        acc = TestCaseTokenAccumulator()
        assert acc.agent_token_usage == {}
        assert acc.platform_token_usage == {}
        assert acc.agent_cost_usd == 0.0
        assert acc.platform_cost_usd == 0.0

    def test_agent_usage_accumulation(self) -> None:
        acc = TestCaseTokenAccumulator()
        acc.add_agent_usage({"prompt_tokens": 10, "completion_tokens": 5})
        acc.add_agent_usage({"prompt_tokens": 20, "completion_tokens": 10})
        assert acc.agent_token_usage == {"prompt_tokens": 30, "completion_tokens": 15}

    def test_platform_usage_accumulation(self) -> None:
        acc = TestCaseTokenAccumulator()
        acc.add_platform_usage({"prompt_tokens": 100, "completion_tokens": 20})
        acc.add_platform_usage({"prompt_tokens": 50, "completion_tokens": 10})
        assert acc.platform_token_usage == {
            "prompt_tokens": 150,
            "completion_tokens": 30,
        }

    def test_cost_accumulation(self) -> None:
        acc = TestCaseTokenAccumulator()
        acc.add_agent_cost(0.01)
        acc.add_agent_cost(0.02)
        acc.add_platform_cost(0.005)
        assert acc.agent_cost_usd == pytest.approx(0.03)
        assert acc.platform_cost_usd == pytest.approx(0.005)

    def test_none_cost_ignored(self) -> None:
        acc = TestCaseTokenAccumulator()
        acc.add_agent_cost(None)
        acc.add_platform_cost(None)
        assert acc.agent_cost_usd == 0.0
        assert acc.platform_cost_usd == 0.0

    def test_none_usage_ignored(self) -> None:
        acc = TestCaseTokenAccumulator()
        acc.add_agent_usage(None)
        acc.add_platform_usage(None)
        assert acc.agent_token_usage == {}
        assert acc.platform_token_usage == {}

    def test_estimated_flag_preserved(self) -> None:
        acc = TestCaseTokenAccumulator()
        acc.add_agent_usage({"prompt_tokens": 10, "estimated": True})
        acc.add_agent_usage({"prompt_tokens": 20})
        result = acc.agent_token_usage
        assert result["estimated"] is True
        assert result["prompt_tokens"] == 30
