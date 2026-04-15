"""Build structured eval context for the prompt editor agent (CS-64)."""

import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import cast

from pydantic import BaseModel
from sqlmodel import Session

from app import crud
from app.models import Agent, Run, RunStatus, TestCaseResult
from app.models.comparison import RunComparison
from app.models.schemas import AggregateMetrics, JudgeVerdict, MetricScore
from app.services.comparison import compare_runs

_MAX_FAILING_TEST_CASES = 10
_MAX_TRANSCRIPT_TURNS = 30
_MAX_RESULTS_PER_RUN = 2000

# Scored metrics at or below this point count as "failing" for summaries.
_SCORE_FAIL_THRESHOLD = 2


class FailingTestCaseSummary(BaseModel):
    """Compact summary for aggregate context (Mode 1)."""

    test_case_id: uuid.UUID
    test_case_name: str | None
    overall_score: float
    passed: bool
    failing_metrics: list[str]
    judge_summary: str | None
    turn_count: int | None


class DetailedMetricScore(BaseModel):
    """Full metric score detail for specific test case context (Mode 2)."""

    metric: str
    display_name: str
    score: int
    label: str
    justification: str
    is_binary: bool
    tier: str | None
    failure_code: str | None
    turns: list[int]


class DetailedTestCaseResult(BaseModel):
    """Full detail for a specific user-selected test case result (Mode 2)."""

    test_case_result_id: uuid.UUID
    test_case_id: uuid.UUID
    test_case_name: str | None
    run_id: uuid.UUID
    run_name: str | None
    passed: bool | None
    overall_score: float | None
    metric_scores: list[DetailedMetricScore]
    transcript: list[dict[str, object]] | None
    turn_count: int | None
    total_latency_ms: int | None
    error_message: str | None


class MetricBreakdown(BaseModel):
    """Per-metric aggregate for run-level context."""

    metric: str
    display_name: str
    avg_score: float
    pass_count: int
    fail_count: int
    tier: str


class ComparisonSummary(BaseModel):
    """Baseline comparison summary."""

    baseline_run_name: str | None
    candidate_run_name: str | None
    pass_rate_delta: float
    avg_score_delta: float
    total_regressions: int
    total_improvements: int
    regressed_metrics: list[str]
    improved_metrics: list[str]
    verdict: str


class EditorEvalContext(BaseModel):
    """Structured context for the editor agent. Serialized to text for injection."""

    agent_name: str
    agent_mode: str
    agent_model: str | None
    tool_count: int
    tool_names: list[str]
    run_id: uuid.UUID | None = None
    run_name: str | None = None
    eval_set_name: str | None = None
    total_test_cases: int | None = None
    pass_rate: float | None = None
    avg_overall_score: float | None = None
    metric_breakdown: list[MetricBreakdown] | None = None
    failing_test_cases: list[FailingTestCaseSummary] | None = None
    comparison: ComparisonSummary | None = None
    improvement_suggestions: list[dict[str, object]] | None = None
    detailed_results: list[DetailedTestCaseResult] | None = None


def _extract_agent_tool_names(agent: Agent) -> list[str]:
    tool_names: list[str] = []
    if agent.tools:
        for t in agent.tools:
            if isinstance(t, dict) and "function" in t:
                fn = t.get("function")
                if isinstance(fn, dict) and "name" in fn:
                    tool_names.append(str(fn["name"]))
            elif isinstance(t, dict) and "name" in t:
                tool_names.append(str(t["name"]))
    return tool_names


def _metric_display_name(metric_id: str) -> str:
    return metric_id.replace("_", " ").title()


def _parse_verdict(raw: dict[str, object] | None) -> JudgeVerdict | None:
    if not raw:
        return None
    try:
        return JudgeVerdict.model_validate(raw)
    except Exception:
        return None


def _parse_aggregate_metrics(
    raw: Mapping[str, object] | None,
) -> AggregateMetrics | None:
    if not raw:
        return None
    try:
        return AggregateMetrics.model_validate(dict(raw))
    except Exception:
        return None


def _metric_passes(m: MetricScore) -> bool:
    if m.is_binary:
        return m.score >= 5 or m.label.lower() == "pass"
    return m.score > _SCORE_FAIL_THRESHOLD


def _failing_metric_names(v: JudgeVerdict) -> list[str]:
    return [m.metric for m in v.metric_scores if not _metric_passes(m)]


def _judge_summary_from_verdict(v: JudgeVerdict) -> str | None:
    if v.summary and v.summary.strip():
        return v.summary.strip()
    worst: MetricScore | None = None
    worst_key: tuple[int, int] | None = None
    for m in v.metric_scores:
        key = (0 if m.is_binary else 1, m.score)
        if worst_key is None or key < worst_key:
            worst_key = key
            worst = m
    if worst is not None and worst.justification.strip():
        return worst.justification.strip()
    return None


def _comparison_summary_from_run(comparison: RunComparison) -> ComparisonSummary:
    agg = comparison.aggregate
    avg_delta = agg.avg_score_delta if agg.avg_score_delta is not None else 0.0
    regressed: list[str] = []
    improved: list[str] = []
    for m in agg.per_metric_aggregate_deltas:
        if m.delta is None:
            continue
        if m.delta < 0:
            regressed.append(m.metric)
        elif m.delta > 0:
            improved.append(m.metric)
    v = comparison.verdict
    verdict_text = (
        "regression_detected: " + "; ".join(v.reasons)
        if v.regression_detected
        else "no_regression_detected"
    )
    return ComparisonSummary(
        baseline_run_name=comparison.baseline_run_name,
        candidate_run_name=comparison.candidate_run_name,
        pass_rate_delta=agg.pass_rate_delta,
        avg_score_delta=avg_delta,
        total_regressions=agg.total_regressions,
        total_improvements=agg.total_improvements,
        regressed_metrics=regressed,
        improved_metrics=improved,
        verdict=verdict_text,
    )


def _build_metric_breakdowns(
    results: Sequence[TestCaseResult],
) -> list[MetricBreakdown]:
    """Aggregate per-metric stats from test case results."""
    by_metric: dict[str, list[MetricScore]] = defaultdict(list)
    for row in results:
        v = _parse_verdict(cast(dict[str, object] | None, row.verdict))
        if v is None:
            continue
        for m in v.metric_scores:
            by_metric[m.metric].append(m)

    breakdowns: list[MetricBreakdown] = []
    for metric_id, scores in sorted(by_metric.items()):
        n = len(scores)
        pass_count = sum(1 for m in scores if _metric_passes(m))
        fail_count = n - pass_count
        avg = sum(m.score for m in scores) / n if n else 0.0
        tier = next((m.tier for m in scores if m.tier), None) or "unknown"
        breakdowns.append(
            MetricBreakdown(
                metric=metric_id,
                display_name=_metric_display_name(metric_id),
                avg_score=avg,
                pass_count=pass_count,
                fail_count=fail_count,
                tier=tier,
            )
        )
    return breakdowns


def _build_failing_summaries(
    results: Sequence[TestCaseResult],
    db_session: Session,
) -> list[FailingTestCaseSummary]:
    candidates: list[tuple[float, TestCaseResult, JudgeVerdict | None]] = []
    for row in results:
        v = _parse_verdict(cast(dict[str, object] | None, row.verdict))
        failed = row.passed is False or (
            row.passed is None and v is not None and not v.passed
        )
        if not failed:
            continue
        score = v.overall_score if v else 0.0
        candidates.append((score, row, v))

    candidates.sort(key=lambda x: x[0])

    out: list[FailingTestCaseSummary] = []
    for _score, row, v in candidates[:_MAX_FAILING_TEST_CASES]:
        tc = crud.get_test_case(session=db_session, test_case_id=row.test_case_id)
        name = tc.name if tc else None
        failing_metrics: list[str] = _failing_metric_names(v) if v else []
        judge_summary: str | None = None
        if v is not None:
            judge_summary = _judge_summary_from_verdict(v)
        if not judge_summary and row.error_message:
            judge_summary = row.error_message
        out.append(
            FailingTestCaseSummary(
                test_case_id=row.test_case_id,
                test_case_name=name,
                overall_score=v.overall_score if v else 0.0,
                passed=False,
                failing_metrics=failing_metrics,
                judge_summary=judge_summary,
                turn_count=row.turn_count,
            )
        )
    return out


def _truncate_transcript(
    transcript: list[dict[str, object]] | None,
) -> list[dict[str, object]] | None:
    if transcript is None:
        return None
    if len(transcript) <= _MAX_TRANSCRIPT_TURNS:
        return list(transcript)
    return list(transcript[:_MAX_TRANSCRIPT_TURNS])


def _detailed_metric_scores(v: JudgeVerdict) -> list[DetailedMetricScore]:
    return [
        DetailedMetricScore(
            metric=m.metric,
            display_name=_metric_display_name(m.metric),
            score=m.score,
            label=m.label,
            justification=m.justification,
            is_binary=m.is_binary,
            tier=m.tier,
            failure_code=m.failure_code,
            turns=list(m.turns),
        )
        for m in v.metric_scores
    ]


def _build_detailed_result(
    *,
    db_session: Session,
    row: TestCaseResult,
) -> DetailedTestCaseResult | None:
    run = crud.get_run(session=db_session, run_id=row.run_id)
    if run is None:
        return None
    tc = crud.get_test_case(session=db_session, test_case_id=row.test_case_id)
    v = _parse_verdict(cast(dict[str, object] | None, row.verdict))
    raw_tr = row.transcript
    transcript_dicts: list[dict[str, object]] | None
    if raw_tr is None:
        transcript_dicts = None
    else:
        transcript_dicts = [dict(cast(Mapping[str, object], t)) for t in raw_tr]
    transcript_dicts = _truncate_transcript(transcript_dicts)
    return DetailedTestCaseResult(
        test_case_result_id=row.id,
        test_case_id=row.test_case_id,
        test_case_name=tc.name if tc else None,
        run_id=row.run_id,
        run_name=run.name,
        passed=row.passed if row.passed is not None else (v.passed if v else None),
        overall_score=v.overall_score if v else None,
        metric_scores=_detailed_metric_scores(v) if v else [],
        transcript=transcript_dicts,
        turn_count=row.turn_count,
        total_latency_ms=row.total_latency_ms,
        error_message=row.error_message,
    )


async def build_eval_context(
    *,
    db_session: Session,
    agent: Agent,
    run_id: uuid.UUID | None = None,
    test_case_result_ids: list[uuid.UUID] | None = None,
) -> EditorEvalContext | None:
    """Build structured eval context for the prompt editor agent."""
    ids = [x for x in (test_case_result_ids or []) if x]

    aggregate_run: Run | None = None
    if run_id is not None:
        loaded = crud.get_run(session=db_session, run_id=run_id)
        if loaded is not None and loaded.agent_id == agent.id:
            aggregate_run = loaded
        elif not ids:
            return None
    elif not ids:
        items, _total = crud.list_runs(
            session=db_session,
            agent_id=agent.id,
            status=RunStatus.COMPLETED,
            limit=1,
        )
        aggregate_run = items[0] if items else None
        if aggregate_run is None:
            return None

    tool_names = _extract_agent_tool_names(agent)

    metric_breakdown: list[MetricBreakdown] | None = None
    failing_test_cases: list[FailingTestCaseSummary] | None = None
    comparison_summary: ComparisonSummary | None = None
    total_test_cases: int | None = None
    pass_rate: float | None = None
    avg_overall_score: float | None = None
    run_name: str | None = None
    eval_set_name: str | None = None
    aggregate_run_id: uuid.UUID | None = None

    if aggregate_run is not None:
        aggregate_run_id = aggregate_run.id
        run_name = aggregate_run.name
        es = crud.get_eval_set(
            session=db_session, eval_set_id=aggregate_run.eval_set_id
        )
        eval_set_name = es.name if es else None

        results, _count = crud.list_test_case_results(
            session=db_session,
            run_id=aggregate_run.id,
            skip=0,
            limit=_MAX_RESULTS_PER_RUN,
        )
        agg = _parse_aggregate_metrics(
            cast(Mapping[str, object] | None, aggregate_run.aggregate_metrics)
        )
        if agg is not None:
            total_test_cases = agg.total_executions
            pass_rate = agg.pass_rate
            avg_overall_score = agg.avg_overall_score
        else:
            n = len(results)
            total_test_cases = n
            passed_n = sum(1 for r in results if r.passed is True)
            pass_rate = (passed_n / n) if n else 0.0
            scores: list[float] = []
            for r in results:
                v = _parse_verdict(cast(dict[str, object] | None, r.verdict))
                if v is not None:
                    scores.append(v.overall_score)
            avg_overall_score = sum(scores) / len(scores) if scores else None

        metric_breakdown = _build_metric_breakdowns(results)
        failing_test_cases = _build_failing_summaries(results, db_session)

        baseline = crud.get_baseline_run(
            session=db_session,
            agent_id=agent.id,
            eval_set_id=aggregate_run.eval_set_id,
        )
        if (
            baseline is not None
            and baseline.id != aggregate_run.id
            and baseline.status == RunStatus.COMPLETED
        ):
            comparison = compare_runs(
                db_session,
                baseline=baseline,
                candidate=aggregate_run,
            )
            comparison_summary = _comparison_summary_from_run(comparison)

    detailed: list[DetailedTestCaseResult] = []
    for result_id in ids:
        row = crud.get_test_case_result(session=db_session, result_id=result_id)
        if row is None:
            continue
        parent = crud.get_run(session=db_session, run_id=row.run_id)
        if parent is None or parent.agent_id != agent.id:
            continue
        built = _build_detailed_result(db_session=db_session, row=row)
        if built is not None:
            detailed.append(built)

    if aggregate_run_id is None and not detailed:
        return None

    return EditorEvalContext(
        agent_name=agent.name,
        agent_mode=str(agent.mode),
        agent_model=agent.agent_model,
        tool_count=len(tool_names),
        tool_names=tool_names,
        run_id=aggregate_run_id,
        run_name=run_name,
        eval_set_name=eval_set_name,
        total_test_cases=total_test_cases,
        pass_rate=pass_rate,
        avg_overall_score=avg_overall_score,
        metric_breakdown=metric_breakdown,
        failing_test_cases=failing_test_cases,
        comparison=comparison_summary,
        improvement_suggestions=None,
        detailed_results=detailed if detailed else None,
    )


def _escape_xml_text(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _format_turn_line(turn: Mapping[str, object]) -> str:
    role = turn.get("role", "unknown")
    content_obj = turn.get("content")
    content = content_obj if isinstance(content_obj, str) else ""
    return f"[Turn {turn.get('index', '?')}] {role}: {content}"


def format_eval_context_for_prompt(context: EditorEvalContext) -> str:
    """Format EditorEvalContext as structured text for the second system message."""
    tools_line = ", ".join(context.tool_names) if context.tool_names else "(none)"
    lines: list[str] = [
        "<eval_context>",
        "  <config>",
        f"    Agent: {_escape_xml_text(context.agent_name)} | Mode: {_escape_xml_text(context.agent_mode)} | Model: {_escape_xml_text(context.agent_model or '')}",
        f"    Tools ({context.tool_count}): {_escape_xml_text(tools_line)}",
        "  </config>",
    ]

    if context.run_id is not None and (
        context.pass_rate is not None or context.total_test_cases is not None
    ):
        run_label = _escape_xml_text(context.run_name or str(context.run_id))
        lines.append(f'  <eval_results run="{run_label}">')
        if context.eval_set_name:
            lines.append(f"    Eval set: {_escape_xml_text(context.eval_set_name)}")
        pr_pct = (context.pass_rate * 100.0) if context.pass_rate is not None else 0.0
        avg = (
            context.avg_overall_score if context.avg_overall_score is not None else 0.0
        )
        total = context.total_test_cases or 0
        passed = int(round(pr_pct / 100.0 * total)) if total else 0
        failed = max(0, total - passed)
        lines.append(f"    Pass rate: {pr_pct:.1f}% | Avg score: {avg:.1f}/100")
        lines.append(f"    Test cases: {total} | Passed: {passed} | Failed: {failed}")
        lines.append("")
        lines.append("    Metric breakdown:")
        if context.metric_breakdown:
            for m in context.metric_breakdown:
                tier = _escape_xml_text(m.tier)
                lines.append(
                    f"    - { _escape_xml_text(m.display_name)}: avg {m.avg_score:.2f}/5 "
                    f"({m.pass_count}/{m.pass_count + m.fail_count} passed) [{tier}]"
                )
        else:
            lines.append("    - (no per-metric data)")
        lines.append("")
        lines.append(f"    Failing test cases (top { _MAX_FAILING_TEST_CASES}):")
        if context.failing_test_cases:
            for ft in context.failing_test_cases:
                nm = _escape_xml_text(ft.test_case_name or str(ft.test_case_id))
                metrics = ", ".join(_escape_xml_text(x) for x in ft.failing_metrics)
                judge = ft.judge_summary or ""
                lines.append(
                    f"    - {nm}: score {ft.overall_score:.1f}/100, failed on [{metrics}]"
                )
                if judge:
                    lines.append(f'      Judge: "{_escape_xml_text(judge)}"')
        else:
            lines.append("    - (none listed)")
        lines.append("  </eval_results>")

    if context.comparison is not None:
        c = context.comparison
        base_name = _escape_xml_text(c.baseline_run_name or "")
        lines.append(f'  <comparison baseline="{base_name}">')
        lines.append(
            f"    Pass rate: {c.pass_rate_delta:+.1%} | Score: {c.avg_score_delta:+.1f}"
        )
        lines.append(
            f"    Regressions: {c.total_regressions} | Improvements: {c.total_improvements}"
        )
        reg = ", ".join(_escape_xml_text(x) for x in c.regressed_metrics)
        imp = ", ".join(_escape_xml_text(x) for x in c.improved_metrics)
        lines.append(f"    Regressed metrics: [{reg}]")
        lines.append(f"    Improved metrics: [{imp}]")
        lines.append(f"    Verdict: {_escape_xml_text(c.verdict)}")
        lines.append("  </comparison>")

    if context.detailed_results:
        lines.append("  <selected_test_cases>")
        for dr in context.detailed_results:
            nm = _escape_xml_text(dr.test_case_name or str(dr.test_case_id))
            score = dr.overall_score if dr.overall_score is not None else 0.0
            passed_s = str(dr.passed) if dr.passed is not None else "unknown"
            lines.append(
                f'    <test_case name="{nm}" score="{score:.1f}/100" passed="{passed_s}">'
            )
            lines.append("      <metrics>")
            for m in dr.metric_scores:
                lines.append(
                    f"        - {_escape_xml_text(m.display_name)}: {m.score}/5 "
                    f"({_escape_xml_text(m.label)}) - {_escape_xml_text(m.justification)}"
                )
            lines.append("      </metrics>")
            lines.append("      <conversation>")
            if dr.transcript:
                for t in dr.transcript:
                    lines.append(f"        {_escape_xml_text(_format_turn_line(t))}")
            else:
                lines.append("        (no transcript)")
            lines.append("      </conversation>")
            if dr.error_message:
                lines.append(
                    f"      <error>{_escape_xml_text(dr.error_message)}</error>"
                )
            lines.append("    </test_case>")
        lines.append("  </selected_test_cases>")

    lines.append("</eval_context>")
    return "\n".join(lines)
