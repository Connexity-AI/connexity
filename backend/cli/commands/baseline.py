"""Manage baseline runs — set and show the current baseline."""

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.resolvers import resolve_agent, resolve_eval_config


@click.group("baseline")
def baseline_group() -> None:
    """Manage baseline runs for agent + eval config pairs."""


@baseline_group.command("set")
@click.argument("run_id")
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Override output format",
)
@click.pass_context
def baseline_set(
    ctx: click.Context,
    run_id: str,
    output_override: str | None,
) -> None:
    """Mark a completed run as the baseline for its agent + eval config."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)

    with open_client(ctx) as client:
        # Validate the run is completed before attempting to set baseline
        existing = client.runs.get(run_id)
        if str(existing.get("status", "")).lower() != "completed":
            raise click.ClickException(
                f"Only completed runs can be set as baseline "
                f"(run {run_id} status={existing.get('status')})"
            )

        run = client.runs.update(run_id, {"is_baseline": True})
        if fmt == "json":
            output.emit(run, output_format="json")
        else:
            output.progress(
                f"Baseline set: run {run['id']} "
                f"(agent={run.get('agent_id')}, "
                f"eval_config={run.get('eval_config_id')})"
            )


@baseline_group.command("show")
@click.option(
    "--agent",
    "agent_ref",
    required=True,
    help="Agent UUID, name, or endpoint URL",
)
@click.option(
    "--eval-config",
    "eval_config_ref",
    required=True,
    help="Eval config name or UUID",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Override output format",
)
@click.pass_context
def baseline_show(
    ctx: click.Context,
    agent_ref: str,
    eval_config_ref: str,
    output_override: str | None,
) -> None:
    """Show the current baseline run for an agent + eval config."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)

    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        eval_config = resolve_eval_config(client, eval_config_ref)
        run = client.runs.get_baseline(
            agent_id=str(agent["id"]),
            eval_config_id=str(eval_config["id"]),
        )
        if fmt == "json":
            output.emit(run, output_format="json")
        else:
            click.echo(output.format_run_detail(run))
