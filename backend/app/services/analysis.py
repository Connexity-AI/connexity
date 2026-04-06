"""AI-powered regression analysis and improvement suggestions (CS-29).

Uses LiteLLM (via ``call_llm``) to:
1. Summarize semantic prompt changes between two runs.
2. Analyze which config changes likely caused which metric movements.
3. Generate actionable improvement suggestions (on-demand).
"""

import json
import logging

from app.core.config import settings
from app.models.comparison import (
    CauseAnalysisItem,
    ImprovementSuggestion,
    ImprovementSuggestions,
    MetricAggregateDelta,
    RegressionAnalysis,
    RunComparison,
    RunConfigDiff,
    TestCaseComparison,
)
from app.models.run import Run
from app.services.llm import LLMCallConfig, LLMMessage, call_llm

logger = logging.getLogger(__name__)

_TOP_TEST_CASES_LIMIT = 10


def _analysis_llm_config(max_tokens: int | None = None) -> LLMCallConfig:
    return LLMCallConfig(
        model=settings.ANALYSIS_MODEL or settings.LLM_DEFAULT_MODEL,
        provider=settings.ANALYSIS_PROVIDER or settings.LLM_DEFAULT_PROVIDER,
        temperature=settings.ANALYSIS_TEMPERATURE,
        max_tokens=max_tokens or settings.ANALYSIS_MAX_TOKENS,
    )


# ── Operation 0: Prompt semantic summary ──────────────────────────


def _build_prompt_summary_messages(prompt_a: str, prompt_b: str) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content=(
                "You are a concise technical writer. Given two versions of a "
                "system prompt, produce a short summary of what changed "
                "semantically. Focus on behavioral changes, not formatting. "
                "Reply with ONLY the summary text, no JSON."
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                f"## Version A\n{prompt_a}\n\n"
                f"## Version B\n{prompt_b}\n\n"
                "Summarize the semantic changes from A to B in 2-4 sentences."
            ),
        ),
    ]


async def compute_prompt_semantic_summary(
    prompt_a: str | None, prompt_b: str | None
) -> tuple[str | None, float | None]:
    """Produce a semantic summary of prompt changes via LLM.

    Returns (summary_text, cost_usd). Returns (None, None) if prompts
    are identical or both absent.
    """
    if prompt_a == prompt_b or (not prompt_a and not prompt_b):
        return None, None

    messages = _build_prompt_summary_messages(prompt_a or "", prompt_b or "")
    config = _analysis_llm_config(max_tokens=512)

    response = await call_llm(messages, config=config)
    return response.content.strip(), response.response_cost_usd


# ── Operation 1: Regression cause analysis ────────────────────────


def _format_field_change(label: str, field_change: object) -> str:
    if field_change is None:
        return f"- {label}: unchanged"
    return f"- {label}: {getattr(field_change, 'old_value', '?')} → {getattr(field_change, 'new_value', '?')}"


def _format_metric_deltas(
    deltas: list[MetricAggregateDelta],
) -> str:
    if not deltas:
        return "  (none)"
    lines: list[str] = []
    for d in deltas:
        b = f"{d.baseline_avg:.2f}" if d.baseline_avg is not None else "N/A"
        c = f"{d.candidate_avg:.2f}" if d.candidate_avg is not None else "N/A"
        delta = f"{d.delta:+.2f}" if d.delta is not None else "N/A"
        lines.append(f"  - {d.metric}: {delta} ({b} → {c})")
    return "\n".join(lines)


def _format_top_regressed_test_cases(
    test_cases: list[TestCaseComparison],
) -> str:
    regressed = [s for s in test_cases if s.status == "regression"]
    regressed.sort(key=lambda s: s.score_delta or 0)
    top = regressed[:_TOP_TEST_CASES_LIMIT]
    if not top:
        return "(none)"
    lines: list[str] = []
    for s in top:
        delta_str = f"{s.score_delta:+.1f}" if s.score_delta is not None else "N/A"
        metric_details = ", ".join(
            f"{m.metric}: {m.status}"
            for m in s.metric_deltas
            if m.status != "unchanged"
        )
        lines.append(
            f"- {s.test_case_name}: score delta {delta_str}"
            + (f" [{metric_details}]" if metric_details else "")
        )
    return "\n".join(lines)


def _build_tool_diff_summary(config_diff: RunConfigDiff) -> str:
    td = config_diff.tool_diff
    if td is None:
        return "unchanged"
    parts: list[str] = []
    if td.added:
        parts.append(f"Added: {', '.join(td.added)}")
    if td.removed:
        parts.append(f"Removed: {', '.join(td.removed)}")
    if td.modified:
        parts.append(f"Modified: {', '.join(m.field for m in td.modified)}")
    return "; ".join(parts) if parts else "unchanged"


def _extract_simulator_change(config_diff: RunConfigDiff) -> str:
    sim_changes = [
        c
        for c in config_diff.config_changes
        if "user_simulator" in c.field or "agent_simulator" in c.field
    ]
    if not sim_changes:
        return "unchanged"
    return "; ".join(f"{c.field}: {c.old_value} → {c.new_value}" for c in sim_changes)


def _build_analysis_prompt(
    comparison: RunComparison,
    config_diff: RunConfigDiff,
    prompt_semantic_summary: str | None,
) -> list[LLMMessage]:
    agg = comparison.aggregate

    pass_rate_b = agg.baseline_metrics.pass_rate
    pass_rate_c = agg.candidate_metrics.pass_rate
    pass_rate_delta = agg.pass_rate_delta

    avg_score_b = agg.baseline_metrics.avg_overall_score
    avg_score_c = agg.candidate_metrics.avg_overall_score
    avg_score_delta = agg.avg_score_delta

    regressed_count = agg.total_regressions
    improved_count = agg.total_improvements

    system_msg = (
        "You are an AI agent evaluation analyst. Given the changes made between two "
        "evaluation runs and the resulting metric shifts, determine which changes "
        "likely caused which metric movements.\n\n"
        "IMPORTANT RULES:\n"
        "- Judge/simulator model changes are infrastructure observations, NOT causes. "
        "Never say a regression was caused by a judge or simulator model change. "
        "Instead note it may affect scoring consistency.\n"
        "- If nothing changed in agent config but metrics moved, note that this is "
        "likely LLM non-determinism.\n"
        "- Be specific. If you cannot determine a cause, say so rather than speculating.\n\n"
        "Output ONLY valid JSON matching this schema:\n"
        '{"analysis": [{"metric": "...", "direction": "regressed|improved", '
        '"likely_cause": "...", "confidence": "high|medium|low", "reasoning": "..."}], '
        '"infrastructure_notes": ["..."], '
        '"summary": "One paragraph executive summary"}'
    )

    user_content = f"""## Changes made
- Prompt: {prompt_semantic_summary or "unchanged"}
- Tools: {_build_tool_diff_summary(config_diff)}
{_format_field_change("Model", config_diff.model_changed)}
{_format_field_change("Provider", config_diff.provider_changed)}

## Infrastructure notes (do not attribute causation, just note for user awareness)
{_format_field_change("Judge model", config_diff.judge_model_changed)}
{_format_field_change("Judge provider", config_diff.judge_provider_changed)}
- Simulator settings: {_extract_simulator_change(config_diff)}

## Metric changes
- Pass rate: {pass_rate_delta:+.2%} ({pass_rate_b:.2f} → {pass_rate_c:.2f})
- Average score: {f"{avg_score_delta:+.1f}" if avg_score_delta is not None else "N/A"} ({f"{avg_score_b:.1f}" if avg_score_b is not None else "N/A"} → {f"{avg_score_c:.1f}" if avg_score_c is not None else "N/A"})
- Per-metric:
{_format_metric_deltas(agg.per_metric_aggregate_deltas)}
- Test cases regressed: {regressed_count} | improved: {improved_count}

## Top regressed test cases
{_format_top_regressed_test_cases(comparison.test_case_comparisons)}

## Task
For each significant metric change, identify the most likely cause from the changes listed above."""

    return [
        LLMMessage(role="system", content=system_msg),
        LLMMessage(role="user", content=user_content),
    ]


def _parse_analysis_json(raw: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


async def compute_regression_analysis_with_prompts(
    comparison: RunComparison,
    config_diff: RunConfigDiff,
    baseline_prompt: str | None,
    candidate_prompt: str | None,
) -> RegressionAnalysis | None:
    """Full regression analysis including prompt semantic summary.

    This is the main entry point called by the route handler which has
    access to the actual run objects.
    """
    agg = comparison.aggregate
    has_shifts = agg.total_regressions > 0 or agg.total_improvements > 0
    has_score_shift = agg.avg_score_delta is not None and abs(agg.avg_score_delta) > 1.0
    has_pass_rate_shift = abs(agg.pass_rate_delta) > 0.0

    if not (has_shifts or has_score_shift or has_pass_rate_shift):
        return None

    total_cost: float = 0.0

    # Step 1: Prompt semantic summary
    prompt_semantic_summary: str | None = None
    if config_diff.prompt_diff and config_diff.prompt_diff.changed:
        prompt_semantic_summary, summary_cost = await compute_prompt_semantic_summary(
            baseline_prompt, candidate_prompt
        )
        if summary_cost:
            total_cost += summary_cost

    # Step 2: Analysis LLM call
    messages = _build_analysis_prompt(comparison, config_diff, prompt_semantic_summary)
    config = _analysis_llm_config()

    response = await call_llm(messages, config=config)
    if response.response_cost_usd:
        total_cost += response.response_cost_usd

    try:
        parsed = _parse_analysis_json(response.content)
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to parse analysis LLM response: %s", exc)
        return RegressionAnalysis(
            analysis=[],
            infrastructure_notes=[],
            summary=response.content[:500],
            prompt_semantic_summary=prompt_semantic_summary,
            analysis_model=response.model,
            analysis_cost_usd=total_cost or None,
        )

    analysis_items: list[CauseAnalysisItem] = []
    for item in parsed.get("analysis", []):
        try:
            analysis_items.append(CauseAnalysisItem(**item))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping malformed analysis item: %s", exc)

    return RegressionAnalysis(
        analysis=analysis_items,
        infrastructure_notes=parsed.get("infrastructure_notes", []),
        summary=parsed.get("summary", ""),
        prompt_semantic_summary=prompt_semantic_summary,
        analysis_model=response.model,
        analysis_cost_usd=total_cost or None,
    )


# ── Operation 2: Improvement suggestions (on-demand) ─────────────


def _format_metric_scores_for_suggestions(
    comparison: RunComparison,
) -> str:
    """Format scoring rubric from metric deltas."""
    metrics = comparison.aggregate.per_metric_aggregate_deltas
    if not metrics:
        return "(no metrics available)"
    lines: list[str] = []
    for m in metrics:
        b = f"{m.baseline_avg:.2f}" if m.baseline_avg is not None else "N/A"
        c = f"{m.candidate_avg:.2f}" if m.candidate_avg is not None else "N/A"
        delta = f"{m.delta:+.2f}" if m.delta is not None else "N/A"
        lines.append(
            f"- {m.metric} ({'binary' if m.is_binary else 'scored'}): {b} → {c} (delta: {delta})"
        )
    return "\n".join(lines)


def _format_tools_summary(candidate_run: Run) -> str:
    """Summarize tool definitions from the candidate run."""
    tools = candidate_run.tools_snapshot or candidate_run.agent_tools
    if not tools:
        return "(no tools defined)"
    names: list[str] = []
    for tool in tools:
        fn = tool.get("function", {})
        name = fn.get("name", "unknown") if isinstance(fn, dict) else "unknown"
        desc = fn.get("description", "")[:80] if isinstance(fn, dict) else ""
        names.append(f"- {name}: {desc}")
    return "\n".join(names)


def _build_suggestions_prompt(
    comparison: RunComparison,
    analysis: RegressionAnalysis,
    candidate_run: Run,
) -> list[LLMMessage]:
    system_prompt = candidate_run.agent_system_prompt or "(no system prompt)"

    system_msg = (
        "You are an expert AI prompt engineer. Based on the evaluation results and "
        "regression analysis, suggest specific, actionable improvements.\n\n"
        "For each suggestion:\n"
        "1. What to change (specific prompt section, tool definition, etc.)\n"
        "2. Why this should help (link to metric that regressed)\n"
        "3. Expected impact (which metrics should improve)\n\n"
        "Be specific — quote the exact section of the prompt to modify and "
        "suggest the replacement text where possible.\n\n"
        "Output ONLY valid JSON matching this schema:\n"
        '{"suggestions": [{"target": "system_prompt|tool_definition|model_selection|test_case_design|other", '
        '"title": "...", "description": "...", "current_value": "...", '
        '"suggested_value": "...", "expected_metric_impact": ["..."], '
        '"priority": "high|medium|low"}], '
        '"summary": "One paragraph summary of all suggestions"}'
    )

    analysis_summary = analysis.summary
    analysis_items = "\n".join(
        f"- {a.metric} ({a.direction}): {a.likely_cause} [{a.confidence}]"
        for a in analysis.analysis
    )

    user_content = f"""## Current system prompt
{system_prompt}

## Current tools
{_format_tools_summary(candidate_run)}

## Regression analysis
Summary: {analysis_summary}

Per-item analysis:
{analysis_items or "(no specific items)"}

Infrastructure notes:
{chr(10).join(f"- {n}" for n in analysis.infrastructure_notes) or "(none)"}

## Scoring metrics
{_format_metric_scores_for_suggestions(comparison)}

## Task
Generate concrete improvement suggestions based on the above analysis."""

    return [
        LLMMessage(role="system", content=system_msg),
        LLMMessage(role="user", content=user_content),
    ]


async def compute_improvement_suggestions(
    comparison: RunComparison,
    analysis: RegressionAnalysis,
    candidate_run: Run,
) -> ImprovementSuggestions:
    """Generate actionable improvement suggestions via LLM (on-demand)."""
    messages = _build_suggestions_prompt(comparison, analysis, candidate_run)
    config = _analysis_llm_config(max_tokens=settings.ANALYSIS_MAX_TOKENS * 2)

    response = await call_llm(messages, config=config)

    try:
        parsed = _parse_analysis_json(response.content)
    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Failed to parse suggestions LLM response: %s", exc)
        return ImprovementSuggestions(
            suggestions=[],
            summary=response.content[:500],
            model=response.model,
            cost_usd=response.response_cost_usd,
        )

    suggestions: list[ImprovementSuggestion] = []
    for item in parsed.get("suggestions", []):
        try:
            suggestions.append(ImprovementSuggestion(**item))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping malformed suggestion item: %s", exc)

    return ImprovementSuggestions(
        suggestions=suggestions,
        summary=parsed.get("summary", ""),
        model=response.model,
        cost_usd=response.response_cost_usd,
    )
