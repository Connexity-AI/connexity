"""Observed external calls (Retell call logs)."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.resolvers import resolve_agent


@click.group("calls")
def calls_group() -> None:
    """Manage agent calls (sync from Retell, inspect transcripts)."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


@calls_group.command("list")
@click.argument("agent_ref")
@click.option("--from", "date_from", default=None, help="ISO 8601 timestamp")
@click.option("--to", "date_to", default=None, help="ISO 8601 timestamp")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def calls_list(
    ctx: click.Context,
    agent_ref: str,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    """List calls for an agent (auto-syncs from Retell if stale)."""
    ensure_auth(ctx)
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.calls.list_for_agent(str(agent["id"]), params=params)
    _emit(ctx, data, output_override)


@calls_group.command("show")
@click.argument("call_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def calls_show(ctx: click.Context, call_id: str, output_override: str | None) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        call = client.calls.get(call_id)
    _emit(ctx, call, output_override)


@calls_group.command("refresh")
@click.argument("agent_ref")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def calls_refresh(
    ctx: click.Context, agent_ref: str, output_override: str | None
) -> None:
    """Force a Retell sync for the agent and return the count."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        result = client.calls.refresh(str(agent["id"]))
    _emit(ctx, result, output_override)


@calls_group.command("mark-seen")
@click.argument("call_id")
@click.pass_context
def calls_mark_seen(ctx: click.Context, call_id: str) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        result = client.calls.mark_seen(call_id)
    output.progress(str(result.get("message", "OK.")))
