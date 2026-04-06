"""Config diff engine (CS-47).

Computes structured diffs between two run snapshots:
- System prompt: difflib unified diff + change_ratio
- Tools: keyed by function.name, deepdiff per tool schema
- Model/provider: simple equality
- RunConfig JSONB: deepdiff on the full config dict
- Eval set membership: set intersection/difference on test case IDs
"""

import difflib
import uuid

from deepdiff import DeepDiff

from app.models.comparison import (
    EvalSetDiff,
    FieldChange,
    PromptDiff,
    RunConfigDiff,
    ToolDiff,
)
from app.models.run import Run

_UNIFIED_DIFF_MAX_CHARS = 5_000


def compute_prompt_diff(old_prompt: str | None, new_prompt: str | None) -> PromptDiff:
    if old_prompt == new_prompt:
        return PromptDiff(changed=False, change_ratio=0.0)

    old_lines = (old_prompt or "").splitlines(keepends=True)
    new_lines = (new_prompt or "").splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=3))

    added = sum(
        1 for line in diff_lines if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in diff_lines if line.startswith("-") and not line.startswith("---")
    )

    total = max(len(old_lines), len(new_lines), 1)
    ratio = min((added + removed) / total, 1.0)

    raw_diff = "\n".join(diff_lines)
    if len(raw_diff) > _UNIFIED_DIFF_MAX_CHARS:
        raw_diff = raw_diff[:_UNIFIED_DIFF_MAX_CHARS] + "\n... (truncated)"

    return PromptDiff(
        changed=True,
        unified_diff=raw_diff or None,
        change_ratio=round(ratio, 4),
        added_line_count=added,
        removed_line_count=removed,
    )


def _tools_by_name(tools: list[dict] | None) -> dict[str, dict]:
    """Index tool definitions by function.name for stable comparison."""
    if not tools:
        return {}
    result: dict[str, dict] = {}
    for tool in tools:
        fn = tool.get("function", {})
        name = fn.get("name") if isinstance(fn, dict) else None
        if name:
            result[name] = tool
        else:
            result[str(tool)] = tool
    return result


def compute_tool_diff(
    old_tools: list[dict] | None, new_tools: list[dict] | None
) -> ToolDiff:
    old_map = _tools_by_name(old_tools)
    new_map = _tools_by_name(new_tools)

    old_names = set(old_map)
    new_names = set(new_map)

    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    common = old_names & new_names

    modified: list[FieldChange] = []
    for name in sorted(common):
        dd = DeepDiff(old_map[name], new_map[name], ignore_order=True)
        if dd:
            modified.append(
                FieldChange(
                    field=name,
                    old_value=_summarize_deepdiff(dd, "old"),
                    new_value=_summarize_deepdiff(dd, "new"),
                )
            )

    return ToolDiff(added=added, removed=removed, modified=modified)


def _summarize_deepdiff(dd: DeepDiff, side: str) -> dict:
    """Condense DeepDiff output into a readable summary dict."""
    summary: dict = {}
    tree = dd.to_dict()

    if "values_changed" in tree:
        changes = {}
        for path, change in tree["values_changed"].items():
            key = "old_value" if side == "old" else "new_value"
            changes[path] = change[key]
        summary["values_changed"] = changes

    for key in ("iterable_item_added", "dictionary_item_added"):
        if key in tree and side == "new":
            summary[key] = tree[key]

    for key in ("iterable_item_removed", "dictionary_item_removed"):
        if key in tree and side == "old":
            summary[key] = tree[key]

    return summary


def _extract_judge_config(run: Run) -> dict | None:
    """Extract judge config dict from run's config JSONB."""
    if not run.config:
        return None
    cfg = run.config
    return cfg.get("judge")


def compute_config_diff(old_run: Run, new_run: Run) -> list[FieldChange]:
    """Diff the RunConfig JSONB between two runs, excluding judge model/provider."""
    old_cfg = old_run.config or {}
    new_cfg = new_run.config or {}

    if old_cfg == new_cfg:
        return []

    dd = DeepDiff(old_cfg, new_cfg, ignore_order=True)
    if not dd:
        return []

    changes: list[FieldChange] = []
    tree = dd.to_dict()

    if "values_changed" in tree:
        for path, change in tree["values_changed"].items():
            changes.append(
                FieldChange(
                    field=path,
                    old_value=change["old_value"],
                    new_value=change["new_value"],
                )
            )

    for key in ("dictionary_item_added",):
        if key in tree:
            for path in tree[key]:
                changes.append(
                    FieldChange(field=path, old_value=None, new_value=tree[key][path])
                )

    for key in ("dictionary_item_removed",):
        if key in tree:
            for path in tree[key]:
                changes.append(
                    FieldChange(field=path, old_value=tree[key][path], new_value=None)
                )

    return changes


def compute_eval_set_diff(
    old_run: Run,
    new_run: Run,
    baseline_test_case_ids: set[uuid.UUID],
    candidate_test_case_ids: set[uuid.UUID],
) -> EvalSetDiff:
    same_set = old_run.eval_set_id == new_run.eval_set_id
    version_changed = same_set and old_run.eval_set_version != new_run.eval_set_version

    common = baseline_test_case_ids & candidate_test_case_ids
    added = candidate_test_case_ids - baseline_test_case_ids
    removed = baseline_test_case_ids - candidate_test_case_ids

    return EvalSetDiff(
        same_set=same_set,
        version_changed=version_changed,
        added_test_case_ids=sorted(added),
        removed_test_case_ids=sorted(removed),
        common_test_case_ids=sorted(common),
    )


def _field_change_or_none(
    field: str, old_val: str | None, new_val: str | None
) -> FieldChange | None:
    if old_val == new_val:
        return None
    return FieldChange(field=field, old_value=old_val, new_value=new_val)


def compute_run_config_diff(
    baseline: Run,
    candidate: Run,
    baseline_test_case_ids: set[uuid.UUID],
    candidate_test_case_ids: set[uuid.UUID],
) -> RunConfigDiff:
    """Orchestrator: computes the full structured diff between two runs."""
    prompt_diff = compute_prompt_diff(
        baseline.agent_system_prompt, candidate.agent_system_prompt
    )

    tool_diff = compute_tool_diff(
        baseline.tools_snapshot or baseline.agent_tools,
        candidate.tools_snapshot or candidate.agent_tools,
    )

    model_changed = _field_change_or_none(
        "agent_model", baseline.agent_model, candidate.agent_model
    )
    provider_changed = _field_change_or_none(
        "agent_provider", baseline.agent_provider, candidate.agent_provider
    )

    old_judge = _extract_judge_config(baseline) or {}
    new_judge = _extract_judge_config(candidate) or {}
    judge_model_changed = _field_change_or_none(
        "judge.model", old_judge.get("model"), new_judge.get("model")
    )
    judge_provider_changed = _field_change_or_none(
        "judge.provider", old_judge.get("provider"), new_judge.get("provider")
    )

    config_changes = compute_config_diff(baseline, candidate)

    eval_set_diff = compute_eval_set_diff(
        baseline, candidate, baseline_test_case_ids, candidate_test_case_ids
    )

    return RunConfigDiff(
        prompt_diff=prompt_diff,
        tool_diff=tool_diff,
        model_changed=model_changed,
        provider_changed=provider_changed,
        judge_model_changed=judge_model_changed,
        judge_provider_changed=judge_provider_changed,
        config_changes=config_changes,
        eval_set_diff=eval_set_diff,
    )
