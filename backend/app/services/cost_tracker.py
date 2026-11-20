"""Token usage aggregation and agent-side token estimation (no DB / I/O)."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

UsageDict = dict[str, int | bool]
AgentUsageDict = dict[str, int | bool]
PlatformUsageDict = dict[str, int]


def sum_usage_dicts(*dicts: dict[str, int | bool] | dict[str, int] | None) -> UsageDict:
    """Sum numeric usage keys across dicts; propagate ``estimated`` if any input had it."""
    merged: dict[str, int] = {}
    any_estimated = False
    for d in dicts:
        if not d:
            continue
        if d.get("estimated") is True:
            any_estimated = True
        for k, v in d.items():
            if k == "estimated" or isinstance(v, bool):
                continue
            merged[k] = merged.get(k, 0) + int(v)
    out: UsageDict = {**merged}
    if any_estimated:
        out["estimated"] = True
    return out


def sum_platform_usage_dicts(
    *dicts: dict[str, int] | None,
) -> PlatformUsageDict:
    """Sum platform LLM usage (ints only)."""
    merged: dict[str, int] = {}
    for d in dicts:
        if not d:
            continue
        for k, v in d.items():
            merged[k] = merged.get(k, 0) + int(v)
    return merged


@dataclass
class TestCaseTokenAccumulator:
    """Collects per-test-case agent/platform token dicts and USD costs."""

    _agent_parts: list[AgentUsageDict] = field(default_factory=list)
    _platform_parts: list[PlatformUsageDict] = field(default_factory=list)
    agent_cost_usd: float = 0.0
    platform_cost_usd: float = 0.0

    def add_agent_usage(self, usage: AgentUsageDict | None) -> None:
        if usage:
            self._agent_parts.append(usage)

    def add_agent_cost(self, cost_usd: float | None) -> None:
        if cost_usd is not None:
            self.agent_cost_usd += float(cost_usd)

    def add_platform_usage(self, usage: dict[str, int] | None) -> None:
        if usage:
            self._platform_parts.append(dict(usage))

    def add_platform_cost(self, cost_usd: float | None) -> None:
        if cost_usd is not None:
            self.platform_cost_usd += float(cost_usd)

    @property
    def agent_token_usage(self) -> AgentUsageDict:
        return sum_usage_dicts(*self._agent_parts)

    @property
    def platform_token_usage(self) -> PlatformUsageDict:
        return sum_platform_usage_dicts(*self._platform_parts)
