"""Tests for cost_tracker module — token estimation, cost calculation, and aggregation."""

import pytest

from app.models.agent_contract import ChatMessage
from app.models.enums import TurnRole
from app.services.cost_tracker import (
    TestCaseTokenAccumulator,
    sum_platform_usage_dicts,
    sum_usage_dicts,
)

# ── _char_heuristic_token_estimate ────────────────────────────────────


# ── _count_tokens ─────────────────────────────────────────────────────


# ── estimate_agent_tokens ─────────────────────────────────────────────


class TestEstimateAgentTokens:
    def _msg(self, role: TurnRole, content: str) -> ChatMessage:
        return ChatMessage(role=role, content=content)


# ── estimate_agent_cost ───────────────────────────────────────────────


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
