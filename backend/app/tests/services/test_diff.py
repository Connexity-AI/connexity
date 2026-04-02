"""Unit tests for app.services.diff (CS-47)."""

import uuid
from types import SimpleNamespace

from app.services.diff import (
    compute_config_diff,
    compute_prompt_diff,
    compute_run_config_diff,
    compute_scenario_set_diff,
    compute_tool_diff,
)

# Fields accessed by diff.py on Run objects.
_RUN_DEFAULTS: dict[str, object] = {
    "id": None,  # overridden per call
    "scenario_set_id": None,
    "scenario_set_version": 1,
    "agent_system_prompt": None,
    "agent_tools": None,
    "tools_snapshot": None,
    "agent_model": None,
    "agent_provider": None,
    "config": None,
}


def _make_run(**overrides: object) -> SimpleNamespace:
    defaults = {**_RUN_DEFAULTS, "id": uuid.uuid4(), "scenario_set_id": uuid.uuid4()}
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── Prompt diff ──────────────────────────────────────────────────


class TestComputePromptDiff:
    def test_identical_prompts(self) -> None:
        result = compute_prompt_diff("Hello world", "Hello world")
        assert result.changed is False
        assert result.change_ratio == 0.0

    def test_both_none(self) -> None:
        result = compute_prompt_diff(None, None)
        assert result.changed is False
        assert result.change_ratio == 0.0

    def test_minor_edit(self) -> None:
        old = "You are a helpful assistant.\nBe concise.\nAnswer accurately."
        new = "You are a helpful assistant.\nBe very concise.\nAnswer accurately."
        result = compute_prompt_diff(old, new)
        assert result.changed is True
        assert 0.0 < result.change_ratio < 1.0
        assert result.added_line_count >= 1
        assert result.removed_line_count >= 1
        assert result.unified_diff is not None

    def test_completely_different(self) -> None:
        result = compute_prompt_diff("Old prompt", "Completely new prompt text")
        assert result.changed is True
        assert result.change_ratio > 0.0

    def test_none_to_value(self) -> None:
        result = compute_prompt_diff(None, "New prompt")
        assert result.changed is True
        assert result.added_line_count >= 1

    def test_value_to_none(self) -> None:
        result = compute_prompt_diff("Old prompt", None)
        assert result.changed is True
        assert result.removed_line_count >= 1


# ── Tool diff ────────────────────────────────────────────────────


def _tool(name: str, desc: str = "A tool", params: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": params or {"type": "object", "properties": {}},
        },
    }


class TestComputeToolDiff:
    def test_no_change(self) -> None:
        tools = [_tool("search"), _tool("calculate")]
        result = compute_tool_diff(tools, tools)
        assert result.added == []
        assert result.removed == []
        assert result.modified == []

    def test_tool_added(self) -> None:
        old = [_tool("search")]
        new = [_tool("search"), _tool("weather")]
        result = compute_tool_diff(old, new)
        assert result.added == ["weather"]
        assert result.removed == []

    def test_tool_removed(self) -> None:
        old = [_tool("search"), _tool("weather")]
        new = [_tool("search")]
        result = compute_tool_diff(old, new)
        assert result.removed == ["weather"]
        assert result.added == []

    def test_tool_modified(self) -> None:
        old = [_tool("search", desc="Search the web")]
        new = [_tool("search", desc="Search the internet")]
        result = compute_tool_diff(old, new)
        assert result.added == []
        assert result.removed == []
        assert len(result.modified) == 1
        assert result.modified[0].field == "search"

    def test_both_none(self) -> None:
        result = compute_tool_diff(None, None)
        assert result.added == []
        assert result.removed == []
        assert result.modified == []


# ── Config diff ──────────────────────────────────────────────────


class TestComputeConfigDiff:
    def test_identical_config(self) -> None:
        cfg = {"concurrency": 5, "judge": {"pass_threshold": 75}}
        r1 = _make_run(config=cfg)
        r2 = _make_run(config=cfg)
        result = compute_config_diff(r1, r2)
        assert result == []

    def test_changed_config(self) -> None:
        r1 = _make_run(config={"concurrency": 5})
        r2 = _make_run(config={"concurrency": 10})
        result = compute_config_diff(r1, r2)
        assert len(result) == 1
        assert result[0].old_value == 5
        assert result[0].new_value == 10

    def test_both_none_config(self) -> None:
        r1 = _make_run(config=None)
        r2 = _make_run(config=None)
        result = compute_config_diff(r1, r2)
        assert result == []


# ── Scenario set diff ────────────────────────────────────────────


class TestComputeScenarioSetDiff:
    def test_same_set_same_version(self) -> None:
        set_id = uuid.uuid4()
        s1, s2, s3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        r1 = _make_run(scenario_set_id=set_id, scenario_set_version=1)
        r2 = _make_run(scenario_set_id=set_id, scenario_set_version=1)
        result = compute_scenario_set_diff(r1, r2, {s1, s2, s3}, {s1, s2, s3})
        assert result.same_set is True
        assert result.version_changed is False
        assert len(result.common_scenario_ids) == 3
        assert result.added_scenario_ids == []
        assert result.removed_scenario_ids == []

    def test_same_set_version_bump_with_changes(self) -> None:
        set_id = uuid.uuid4()
        common = uuid.uuid4()
        removed = uuid.uuid4()
        added = uuid.uuid4()
        r1 = _make_run(scenario_set_id=set_id, scenario_set_version=1)
        r2 = _make_run(scenario_set_id=set_id, scenario_set_version=2)
        result = compute_scenario_set_diff(r1, r2, {common, removed}, {common, added})
        assert result.same_set is True
        assert result.version_changed is True
        assert common in result.common_scenario_ids
        assert added in result.added_scenario_ids
        assert removed in result.removed_scenario_ids

    def test_different_sets(self) -> None:
        s1 = uuid.uuid4()
        r1 = _make_run(scenario_set_id=uuid.uuid4(), scenario_set_version=1)
        r2 = _make_run(scenario_set_id=uuid.uuid4(), scenario_set_version=1)
        result = compute_scenario_set_diff(r1, r2, {s1}, {s1})
        assert result.same_set is False
        assert result.version_changed is False


# ── Full orchestrator ────────────────────────────────────────────


class TestComputeRunConfigDiff:
    def test_no_changes(self) -> None:
        set_id = uuid.uuid4()
        sids = {uuid.uuid4()}
        r1 = _make_run(
            scenario_set_id=set_id,
            agent_system_prompt="Hello",
            agent_model="gpt-4o",
            agent_provider="openai",
        )
        r2 = _make_run(
            scenario_set_id=set_id,
            agent_system_prompt="Hello",
            agent_model="gpt-4o",
            agent_provider="openai",
        )
        result = compute_run_config_diff(r1, r2, sids, sids)
        assert result.prompt_diff is not None
        assert result.prompt_diff.changed is False
        assert result.model_changed is None
        assert result.provider_changed is None

    def test_model_swap(self) -> None:
        set_id = uuid.uuid4()
        sids = {uuid.uuid4()}
        r1 = _make_run(scenario_set_id=set_id, agent_model="gpt-4o")
        r2 = _make_run(scenario_set_id=set_id, agent_model="gpt-4o-mini")
        result = compute_run_config_diff(r1, r2, sids, sids)
        assert result.model_changed is not None
        assert result.model_changed.old_value == "gpt-4o"
        assert result.model_changed.new_value == "gpt-4o-mini"

    def test_prompt_and_tool_change(self) -> None:
        set_id = uuid.uuid4()
        sids = {uuid.uuid4()}
        r1 = _make_run(
            scenario_set_id=set_id,
            agent_system_prompt="V1 prompt",
            tools_snapshot=[_tool("search")],
        )
        r2 = _make_run(
            scenario_set_id=set_id,
            agent_system_prompt="V2 prompt completely rewritten",
            tools_snapshot=[_tool("search"), _tool("weather")],
        )
        result = compute_run_config_diff(r1, r2, sids, sids)
        assert result.prompt_diff is not None
        assert result.prompt_diff.changed is True
        assert result.tool_diff is not None
        assert result.tool_diff.added == ["weather"]

    def test_judge_model_change(self) -> None:
        set_id = uuid.uuid4()
        sids = {uuid.uuid4()}
        r1 = _make_run(
            scenario_set_id=set_id,
            config={"judge": {"model": "gpt-4o", "provider": "openai"}},
        )
        r2 = _make_run(
            scenario_set_id=set_id,
            config={"judge": {"model": "claude-3-5-sonnet", "provider": "anthropic"}},
        )
        result = compute_run_config_diff(r1, r2, sids, sids)
        assert result.judge_model_changed is not None
        assert result.judge_model_changed.old_value == "gpt-4o"
        assert result.judge_model_changed.new_value == "claude-3-5-sonnet"
        assert result.judge_provider_changed is not None
