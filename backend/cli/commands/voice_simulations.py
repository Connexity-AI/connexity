"""Voice simulation job inspection."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client


@click.group("voice-simulations")
def voice_simulations_group() -> None:
    """Inspect voice simulation jobs (phone-call eval lifecycle)."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


@voice_simulations_group.group("jobs")
def voice_simulations_jobs_group() -> None:
    """Voice simulation jobs for a run."""


@voice_simulations_jobs_group.command("list")
@click.argument("run_id")
@click.option("--limit", default=500, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def voice_simulations_jobs_list(
    ctx: click.Context,
    run_id: str,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    """List voice simulation jobs for a run."""
    ensure_auth(ctx)
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    with open_client(ctx) as client:
        data = client.voice_simulations.list_jobs_for_run(run_id, params=params)
    _emit(ctx, data, output_override)


@voice_simulations_jobs_group.command("show")
@click.argument("job_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def voice_simulations_jobs_show(
    ctx: click.Context, job_id: str, output_override: str | None
) -> None:
    """Show one voice simulation job."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        job = client.voice_simulations.get_job(job_id)
    _emit(ctx, job, output_override)
