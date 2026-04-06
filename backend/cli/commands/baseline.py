"""Manage baseline runs — set and show the current baseline."""

import click

from cli import output
from cli.commands.run import _resolve_agent, _resolve_eval_set
from cli.context import get_output_format, open_client, root_obj


@click.group("baseline")
def baseline_group() -> None:
    """Manage baseline runs for agent + eval set pairs."""


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
    """Mark a completed run as the baseline for its agent + eval set."""
    root = root_obj(ctx)
    if not root.get("token"):
        raise click.ClickException(
            "Authentication required: set CONNEXITY_EVALS_API_TOKEN or pass --token."
        )
    fmt = get_output_format(ctx, output_override)

    with open_client(ctx) as client:
        # Validate the run is completed before attempting to set baseline
        existing = client.get_run(run_id)
        if str(existing.get("status", "")).lower() != "completed":
            raise click.ClickException(
                f"Only completed runs can be set as baseline "
                f"(run {run_id} status={existing.get('status')})"
            )

        run = client.update_run(run_id, {"is_baseline": True})
        if fmt == "json":
            output.emit(run, output_format="json")
        else:
            output.progress(
                f"Baseline set: run {run['id']} "
                f"(agent={run.get('agent_id')}, "
                f"eval_set={run.get('eval_set_id')})"
            )


@baseline_group.command("show")
@click.option(
    "--agent",
    "agent_ref",
    required=True,
    help="Agent UUID, name, or endpoint URL",
)
@click.option(
    "--eval-set",
    "eval_set_ref",
    required=True,
    help="Eval set name or UUID",
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
    eval_set_ref: str,
    output_override: str | None,
) -> None:
    """Show the current baseline run for an agent + eval set."""
    fmt = get_output_format(ctx, output_override)

    with open_client(ctx) as client:
        agent = _resolve_agent(client, agent_ref)
        eval_set = _resolve_eval_set(client, eval_set_ref)
        run = client.get_baseline_run(str(agent["id"]), str(eval_set["id"]))
        if fmt == "json":
            output.emit(run, output_format="json")
        else:
            click.echo(output.format_run_detail(run))
