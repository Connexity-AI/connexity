"""Create a run, wait for completion, print results."""

import json
import sys
import time
import uuid
from typing import Any

import click
import httpx

from cli import output
from cli.api_client import ApiClient
from cli.context import get_output_format, open_client, root_obj

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def _try_uuid(value: str) -> str | None:
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError:
        return None


def _resolve_scenario_set(client: ApiClient, ref: str) -> dict[str, Any]:
    uid = _try_uuid(ref)
    if uid:
        return client.get_scenario_set(uid)
    data = client.list_scenario_sets(params={"limit": 1000})
    raw = data.get("data")
    rows: list[dict[str, Any]] = (
        [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    )
    ref_l = ref.strip().casefold()
    matches = [s for s in rows if str(s.get("name", "")).casefold() == ref_l]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise click.ClickException(
            f"No scenario set found with name {ref!r}. Use a UUID or exact name."
        )
    names = ", ".join(str(m.get("name")) for m in matches[:5])
    raise click.ClickException(
        f"Multiple scenario sets match {ref!r}: {names}. Use a UUID."
    )


def _resolve_agent(client: ApiClient, ref: str) -> dict[str, Any]:
    """Return the full agent dict from the API."""
    uid = _try_uuid(ref)
    if uid:
        return client.get_agent(uid)

    ref_stripped = ref.strip()
    if ref_stripped.lower().startswith(("http://", "https://")):
        data = client.list_agents(params={"limit": 1000})
        rows = data.get("data") or []
        for a in rows:
            if not isinstance(a, dict):
                continue
            if str(a.get("endpoint_url", "")).rstrip("/") == ref_stripped.rstrip("/"):
                return a
        raise click.ClickException(
            f"No agent registered with endpoint_url matching {ref_stripped!r}. "
            "Create an agent in the UI/API first, or pass an agent UUID."
        )

    data = client.list_agents(params={"limit": 1000})
    rows = data.get("data") or []
    ref_l = ref_stripped.casefold()
    matches = [
        a
        for a in rows
        if isinstance(a, dict) and str(a.get("name", "")).casefold() == ref_l
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise click.ClickException(
            f"No agent found with name {ref!r}. Use a UUID, exact name, or agent URL."
        )
    names = ", ".join(str(m.get("name")) for m in matches[:5])
    raise click.ClickException(
        f"Multiple agents match {ref!r}: {names}. Use a UUID or endpoint URL."
    )


@click.command("run")
@click.option(
    "--scenarios",
    "scenario_ref",
    required=True,
    help="Scenario set name or UUID",
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
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Override output format from global default",
)
@click.pass_context
def run_command(
    ctx: click.Context,
    scenario_ref: str,
    agent_ref: str,
    run_name: str | None,
    timeout: float,
    poll_interval: float,
    stream: bool,
    output_override: str | None,
) -> None:
    """Trigger an eval run and wait until it finishes."""
    root = root_obj(ctx)
    if not root.get("token"):
        raise click.ClickException(
            "Authentication required: set CONNEXITY_EVALS_API_TOKEN or pass --token."
        )
    fmt = get_output_format(ctx, output_override)

    with open_client(ctx) as client:
        scenario_set = _resolve_scenario_set(client, scenario_ref)
        agent = _resolve_agent(client, agent_ref)
        agent_id = str(agent["id"])

        body: dict[str, Any] = {
            "agent_id": agent_id,
            "scenario_set_id": str(scenario_set["id"]),
            "scenario_set_version": int(scenario_set.get("version", 1)),
        }
        endpoint_url = agent.get("endpoint_url")
        if endpoint_url:
            body["agent_endpoint_url"] = endpoint_url
        if run_name:
            body["name"] = run_name

        output.progress("Creating run and starting execution...")
        run = client.create_run(body, auto_execute=True)
        run_id = str(run["id"])
        output.progress(f"Run ID: {run_id}")

        deadline = time.monotonic() + timeout

        if stream:
            output.progress("Streaming events (SSE)...")
            try:
                for sse in client.iter_run_sse(run_id):
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
            run = client.get_run(run_id)
            status = str(run.get("status", "")).lower()
            if status in TERMINAL_STATUSES:
                break
            output.progress(f"Status: {status} …")
            time.sleep(poll_interval)
        else:
            output.progress("Timed out waiting for run to finish.")
            sys.exit(2)

        if fmt == "json":
            output.emit(run, output_format="json")
        else:
            click.echo(output.format_run_detail(run))

        final = str(run.get("status", "")).lower()
        if final == "completed":
            ctx.exit(0)
        if final in ("failed", "cancelled"):
            sys.exit(1)
        sys.exit(1)
