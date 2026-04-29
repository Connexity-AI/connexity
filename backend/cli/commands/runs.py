"""Runs group: full lifecycle, baselines, comparison, SSE streaming."""

from __future__ import annotations

import json
import sys
from typing import Any

import click
import httpx

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload
from cli.resolvers import resolve_agent, resolve_eval_config


@click.group("runs")
def runs_group() -> None:
    """Manage runs (CRUD, execute, cancel, stream, baselines, compare)."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    fmt = get_output_format(ctx, output_override)
    if fmt == "json" or not isinstance(data, dict) or "id" not in data:
        output.emit(data, output_format=fmt)
        return
    click.echo(output.format_run_detail(data))


# ---------------------------------------------------------------------------
# CRUD / lifecycle
# ---------------------------------------------------------------------------


@runs_group.command("list")
@click.option("--agent", "agent_id", default=None)
@click.option("--agent-version", type=int, default=None)
@click.option("--eval-config", "eval_config_id", default=None)
@click.option("--status", default=None)
@click.option("--created-after", default=None, help="ISO 8601 timestamp")
@click.option("--created-before", default=None, help="ISO 8601 timestamp")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_list(
    ctx: click.Context,
    agent_id: str | None,
    agent_version: int | None,
    eval_config_id: str | None,
    status: str | None,
    created_after: str | None,
    created_before: str | None,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    """List runs with optional filters."""
    ensure_auth(ctx)
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    if agent_id:
        params["agent_id"] = agent_id
    if agent_version is not None:
        params["agent_version"] = agent_version
    if eval_config_id:
        params["eval_config_id"] = eval_config_id
    if status:
        params["status"] = status
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before

    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.runs.list(params=params)
    output.emit(data, output_format=fmt)


@runs_group.command("show")
@click.argument("run_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_show(ctx: click.Context, run_id: str, output_override: str | None) -> None:
    """Show one run."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        run = client.runs.get(run_id)
    _emit(ctx, run, output_override)
    final = str(run.get("status", "")).lower()
    if final in ("failed", "cancelled"):
        sys.exit(1)


@runs_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to RunCreate JSON ('-' for stdin)",
)
@click.option(
    "--auto-execute/--no-auto-execute",
    default=False,
    help="Kick off execution immediately after creating the run",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_create(
    ctx: click.Context,
    from_file: str,
    auto_execute: bool,
    output_override: str | None,
) -> None:
    """Create a run from a full JSON RunCreate body."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        run = client.runs.create(body, auto_execute=auto_execute)
    _emit(ctx, run, output_override)


@runs_group.command("update")
@click.argument("run_id")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to RunUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_update(
    ctx: click.Context,
    run_id: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Patch run metadata (name, is_baseline, etc.)."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        run = client.runs.update(run_id, body)
    _emit(ctx, run, output_override)


@runs_group.command("delete")
@click.argument("run_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def runs_delete(ctx: click.Context, run_id: str, yes: bool) -> None:
    """Delete a run and cascade its results."""
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete run {run_id} and all its results?", abort=True)
    with open_client(ctx) as client:
        result = client.runs.delete(run_id)
    output.progress(str(result.get("message", "Deleted.")))


@runs_group.command("execute")
@click.argument("run_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_execute(ctx: click.Context, run_id: str, output_override: str | None) -> None:
    """Kick off execution for a PENDING / FAILED / CANCELLED run."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        run = client.runs.execute(run_id)
    _emit(ctx, run, output_override)


@runs_group.command("cancel")
@click.argument("run_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_cancel(ctx: click.Context, run_id: str, output_override: str | None) -> None:
    """Signal cancellation for an active run."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        run = client.runs.cancel(run_id)
    _emit(ctx, run, output_override)


@runs_group.command("stream")
@click.argument("run_id")
@click.pass_context
def runs_stream(ctx: click.Context, run_id: str) -> None:
    """Stream SSE events for a run until completion."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        try:
            for sse in client.runs.stream(run_id):
                data = json.loads(sse.data) if sse.data else {}
                click.echo(f"[{sse.event}] {json.dumps(data, default=str)}")
                if sse.event in (
                    "stream_closed",
                    "run_completed",
                    "run_failed",
                    "run_cancelled",
                ):
                    break
        except (httpx.HTTPError, OSError) as exc:
            raise click.ClickException(f"SSE stream failed: {exc}") from exc


# ---------------------------------------------------------------------------
# baselines
# ---------------------------------------------------------------------------


@runs_group.group("baseline")
def runs_baseline_group() -> None:
    """Inspect or set the baseline run."""


@runs_baseline_group.command("get")
@click.option("--agent", "agent_ref", required=True)
@click.option("--eval-config", "eval_config_ref", required=True)
@click.option(
    "--agent-version",
    type=int,
    default=None,
    help="Optional agent version scope (otherwise uses current)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_baseline_get(
    ctx: click.Context,
    agent_ref: str,
    eval_config_ref: str,
    agent_version: int | None,
    output_override: str | None,
) -> None:
    """Get the baseline run for an (agent, eval-config) pair."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        cfg = resolve_eval_config(client, eval_config_ref)
        run = client.runs.get_baseline(
            agent_id=str(agent["id"]),
            eval_config_id=str(cfg["id"]),
            agent_version=agent_version,
        )
    _emit(ctx, run, output_override)


@runs_baseline_group.command("set")
@click.argument("run_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_baseline_set(
    ctx: click.Context, run_id: str, output_override: str | None
) -> None:
    """Mark a completed run as baseline."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        existing = client.runs.get(run_id)
        if str(existing.get("status", "")).lower() != "completed":
            raise click.ClickException(
                f"Only completed runs can be set as baseline "
                f"(run {run_id} status={existing.get('status')})"
            )
        run = client.runs.update(run_id, {"is_baseline": True})
    _emit(ctx, run, output_override)


# ---------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------


@runs_group.command("compare")
@click.option("--baseline", "baseline_run_id", required=True)
@click.option("--candidate", "candidate_run_id", required=True)
@click.option("--max-pass-rate-drop", type=float, default=None)
@click.option("--max-avg-score-drop", type=float, default=None)
@click.option("--max-latency-increase-pct", type=float, default=None)
@click.option(
    "--include-analysis/--no-include-analysis",
    default=False,
    help="Compute LLM-backed regression analysis",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_compare(
    ctx: click.Context,
    baseline_run_id: str,
    candidate_run_id: str,
    max_pass_rate_drop: float | None,
    max_avg_score_drop: float | None,
    max_latency_increase_pct: float | None,
    include_analysis: bool,
    output_override: str | None,
) -> None:
    """Compare two runs (mirrors the convenience top-level `compare`)."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    params: dict[str, Any] = {
        "baseline_run_id": baseline_run_id,
        "candidate_run_id": candidate_run_id,
        "include_analysis": include_analysis,
    }
    if max_pass_rate_drop is not None:
        params["max_pass_rate_drop"] = max_pass_rate_drop
    if max_avg_score_drop is not None:
        params["max_avg_score_drop"] = max_avg_score_drop
    if max_latency_increase_pct is not None:
        params["max_latency_increase_pct"] = max_latency_increase_pct
    with open_client(ctx) as client:
        result = client.runs.compare(params)
    output.emit(result, output_format=fmt)
    if result.get("verdict", {}).get("regression_detected"):
        sys.exit(1)


@runs_group.command("compare-suggestions")
@click.option("--baseline", "baseline_run_id", required=True)
@click.option("--candidate", "candidate_run_id", required=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def runs_compare_suggestions(
    ctx: click.Context,
    baseline_run_id: str,
    candidate_run_id: str,
    output_override: str | None,
) -> None:
    """Generate AI improvement suggestions from a comparison."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        result = client.runs.compare_suggestions(
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
        )
    output.emit(result, output_format=fmt)
