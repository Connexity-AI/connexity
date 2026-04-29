"""Create a run, wait for completion, print results.

Top-level convenience command — equivalent to ``runs create --auto-execute``
plus polling/streaming and an optional ``--set-baseline`` step.
"""

import json
import sys
import time
from typing import Any

import click
import httpx

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_optional_dict
from cli.resolvers import resolve_agent, resolve_eval_config

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


@click.command("run")
@click.option(
    "--eval-config",
    "eval_config_ref",
    required=True,
    help="Eval config name or UUID",
)
@click.option(
    "--agent",
    "agent_ref",
    required=True,
    help="Agent UUID, name, or endpoint URL registered in the platform",
)
@click.option(
    "--name",
    "run_name",
    default=None,
    help="Optional run label",
)
@click.option(
    "--config-file",
    "config_file",
    default=None,
    help="Path (or '-' for stdin) to JSON RunConfig — judge_config, simulator_config, etc.",
)
@click.option(
    "--timeout",
    default=600.0,
    type=float,
    show_default=True,
    help="Seconds to wait for run completion",
)
@click.option(
    "--poll-interval",
    default=2.5,
    type=float,
    show_default=True,
    help="Seconds between status polls when not streaming",
)
@click.option(
    "--stream/--no-stream",
    default=False,
    help="Stream SSE progress from GET /runs/{id}/stream",
)
@click.option(
    "--set-baseline",
    "set_baseline",
    is_flag=True,
    default=False,
    help="Mark this run as baseline after completion",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Override output format from global default",
)
@click.pass_context
def run_command(
    ctx: click.Context,
    eval_config_ref: str,
    agent_ref: str,
    run_name: str | None,
    config_file: str | None,
    timeout: float,
    poll_interval: float,
    stream: bool,
    set_baseline: bool,
    output_override: str | None,
) -> None:
    """Trigger an eval run and wait until it finishes."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    run_config = load_optional_dict(config_file)

    with open_client(ctx) as client:
        eval_config = resolve_eval_config(client, eval_config_ref)
        agent = resolve_agent(client, agent_ref)
        agent_id = str(agent["id"])

        body: dict[str, Any] = {
            "agent_id": agent_id,
            "eval_config_id": str(eval_config["id"]),
            "eval_config_version": int(eval_config.get("version", 1)),
        }
        endpoint_url = agent.get("endpoint_url")
        if endpoint_url:
            body["agent_endpoint_url"] = endpoint_url
        if run_name:
            body["name"] = run_name
        if run_config is not None:
            body["config"] = run_config

        output.progress("Creating run and starting execution...")
        run = client.runs.create(body, auto_execute=True)
        run_id = str(run["id"])
        output.progress(f"Run ID: {run_id}")

        deadline = time.monotonic() + timeout

        if stream:
            output.progress("Streaming events (SSE)...")
            try:
                for sse in client.runs.stream(run_id):
                    data = json.loads(sse.data) if sse.data else {}
                    output.progress(f"  [{sse.event}] {json.dumps(data, default=str)}")
                    if sse.event in (
                        "stream_closed",
                        "run_completed",
                        "run_failed",
                        "run_cancelled",
                    ):
                        break
                    if time.monotonic() > deadline:
                        output.progress("Timed out waiting for SSE.")
                        sys.exit(2)
            except (httpx.HTTPError, OSError) as e:
                raise click.ClickException(f"SSE stream failed: {e}") from e

        while time.monotonic() <= deadline:
            run = client.runs.get(run_id)
            status = str(run.get("status", "")).lower()
            if status in TERMINAL_STATUSES:
                break
            output.progress(f"Status: {status} …")
            time.sleep(poll_interval)
        else:
            output.progress("Timed out waiting for run to finish.")
            sys.exit(2)

        final = str(run.get("status", "")).lower()

        if set_baseline and final == "completed":
            output.progress("Marking run as baseline...")
            run = client.runs.update(run_id, {"is_baseline": True})

        if fmt == "json":
            output.emit(run, output_format="json")
        else:
            click.echo(output.format_run_detail(run))

        if final == "completed":
            ctx.exit(0)
        if final in ("failed", "cancelled"):
            sys.exit(1)
        sys.exit(1)
