"""Compare two runs and report regression verdict."""

import sys
from typing import Any

import click
import httpx

from cli import output
from cli.api_client import ApiClient
from cli.context import get_output_format, open_client


def _resolve_baseline_for_candidate(
    client: ApiClient, candidate: dict[str, Any]
) -> dict[str, Any]:
    """Find the baseline run for the candidate's agent."""
    agent_id = candidate.get("agent_id")
    if not agent_id:
        raise click.ClickException(
            "Candidate run has no agent_id — cannot resolve baseline."
        )
    data = client.list_runs(
        params={
            "agent_id": agent_id,
            "status": "completed",
            "limit": 100,
        }
    )
    rows: list[dict[str, Any]] = data.get("data") or []
    baselines = [r for r in rows if r.get("is_baseline") is True]
    if not baselines:
        raise click.ClickException(
            f"No baseline run found for agent {agent_id}. "
            "Mark a completed run as baseline first (PATCH /runs/{{id}})."
        )
    # Pick the most recent baseline (list is ordered by created_at desc)
    return baselines[0]


def _format_comparison_table(data: dict[str, Any]) -> str:
    """Render a human-readable summary table for a RunComparison."""
    lines: list[str] = []

    verdict = data.get("verdict", {})
    regression = verdict.get("regression_detected", False)
    status_label = "REGRESSION DETECTED" if regression else "PASS — no regression"
    lines.append(f"Verdict: {status_label}")
    lines.append("")

    agg = data.get("aggregate", {})
    b_metrics = agg.get("baseline_metrics", {})
    c_metrics = agg.get("candidate_metrics", {})

    lines.append("  Metric               Baseline    Candidate   Delta")
    lines.append("  ───────────────────── ─────────── ─────────── ───────────")

    pr_b = b_metrics.get("pass_rate")
    pr_c = c_metrics.get("pass_rate")
    pr_d = agg.get("pass_rate_delta")
    lines.append(
        f"  pass_rate             {_fmt_pct(pr_b)}  {_fmt_pct(pr_c)}  {_fmt_delta_pct(pr_d)}"
    )

    sc_b = b_metrics.get("avg_overall_score")
    sc_c = c_metrics.get("avg_overall_score")
    sc_d = agg.get("avg_score_delta")
    lines.append(
        f"  avg_score             {_fmt_f(sc_b)}  {_fmt_f(sc_c)}  {_fmt_delta_f(sc_d)}"
    )

    la_b = b_metrics.get("latency_avg_ms")
    la_c = c_metrics.get("latency_avg_ms")
    la_d = agg.get("latency_avg_delta_ms")
    lines.append(
        f"  latency_avg_ms        {_fmt_f(la_b)}  {_fmt_f(la_c)}  {_fmt_delta_f(la_d)}"
    )

    lines.append("")
    lines.append(
        f"  Scenarios: {agg.get('total_regressions', 0)} regressed, "
        f"{agg.get('total_improvements', 0)} improved, "
        f"{agg.get('total_unchanged', 0)} unchanged, "
        f"{agg.get('total_errors', 0)} errors"
    )

    reasons = verdict.get("reasons", [])
    if reasons:
        lines.append("")
        lines.append("  Regression reasons:")
        for r in reasons:
            lines.append(f"    - {r}")

    warnings = data.get("warnings", [])
    if warnings:
        lines.append("")
        lines.append("  Warnings:")
        for w in warnings:
            lines.append(f"    - {w}")

    return "\n".join(lines)


def _fmt_pct(v: float | None) -> str:
    return f"{v:.1%}".ljust(11) if v is not None else "—".ljust(11)


def _fmt_f(v: float | None) -> str:
    return f"{v:.1f}".ljust(11) if v is not None else "—".ljust(11)


def _fmt_delta_pct(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1%}"


def _fmt_delta_f(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}"


@click.command("compare")
@click.option(
    "--baseline",
    "baseline_id",
    default=None,
    help="UUID of the baseline run",
)
@click.option(
    "--candidate",
    "candidate_id",
    required=True,
    help="UUID of the candidate run",
)
@click.option(
    "--against-baseline",
    "against_baseline",
    is_flag=True,
    default=False,
    help="Auto-resolve baseline from the candidate's agent",
)
@click.option(
    "--max-pass-rate-drop",
    type=float,
    default=None,
    help="Override max pass-rate drop threshold (default 0.0 = strict)",
)
@click.option(
    "--max-avg-score-drop",
    type=float,
    default=None,
    help="Override max avg score drop on 0-100 scale (default 5.0)",
)
@click.option(
    "--max-latency-increase-pct",
    type=float,
    default=None,
    help="Override max latency increase fraction (default 0.2 = 20%)",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Override output format",
)
@click.pass_context
def compare_command(
    ctx: click.Context,
    baseline_id: str | None,
    candidate_id: str,
    against_baseline: bool,
    max_pass_rate_drop: float | None,
    max_avg_score_drop: float | None,
    max_latency_increase_pct: float | None,
    output_override: str | None,
) -> None:
    """Compare two runs and exit 0 (pass), 1 (regression), or 2 (error)."""
    if not baseline_id and not against_baseline:
        click.echo(
            "Error: Provide --baseline <run-id> or use --against-baseline.", err=True
        )
        sys.exit(2)
    if baseline_id and against_baseline:
        click.echo(
            "Error: --baseline and --against-baseline are mutually exclusive.", err=True
        )
        sys.exit(2)

    fmt = get_output_format(ctx, output_override)

    try:
        with open_client(ctx) as client:
            # Resolve baseline
            if against_baseline:
                output.progress("Resolving baseline run for candidate's agent...")
                candidate_run = client.get_run(candidate_id)
                baseline_run = _resolve_baseline_for_candidate(client, candidate_run)
                resolved_baseline_id = str(baseline_run["id"])
                output.progress(f"Using baseline run: {resolved_baseline_id}")
            else:
                resolved_baseline_id = baseline_id  # type: ignore[assignment]

            # Build API params
            params: dict[str, str | float] = {
                "baseline_run_id": resolved_baseline_id,
                "candidate_run_id": candidate_id,
            }
            if max_pass_rate_drop is not None:
                params["max_pass_rate_drop"] = max_pass_rate_drop
            if max_avg_score_drop is not None:
                params["max_avg_score_drop"] = max_avg_score_drop
            if max_latency_increase_pct is not None:
                params["max_latency_increase_pct"] = max_latency_increase_pct

            comparison = client.compare_runs(params)
    except click.ClickException as exc:
        click.echo(f"Error: {exc.format_message()}", err=True)
        sys.exit(2)
    except httpx.HTTPStatusError as exc:
        click.echo(
            f"Error: API returned {exc.response.status_code}: {exc.response.text}",
            err=True,
        )
        sys.exit(2)
    except httpx.HTTPError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)

    if fmt == "json":
        output.emit(comparison, output_format="json")
    else:
        click.echo(_format_comparison_table(comparison))

    verdict = comparison.get("verdict", {})
    if verdict.get("regression_detected"):
        sys.exit(1)
    ctx.exit(0)
