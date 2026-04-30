"""Agent deployment environments."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload
from cli.resolvers import resolve_agent


@click.group("environments")
def environments_group() -> None:
    """Manage deployment environments (Retell agent bindings, etc.)."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


@environments_group.command("list")
@click.option("--agent", "agent_ref", required=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def environments_list(
    ctx: click.Context, agent_ref: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.environments.list(agent_id=str(agent["id"]))
    _emit(ctx, data, output_override)


@environments_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to EnvironmentCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def environments_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        env = client.environments.create(body)
    _emit(ctx, env, output_override)


@environments_group.command("delete")
@click.argument("environment_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def environments_delete(ctx: click.Context, environment_id: str, yes: bool) -> None:
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete environment {environment_id}?", abort=True)
    with open_client(ctx) as client:
        result = client.environments.delete(environment_id)
    output.progress(str(result.get("message", "Deleted.")))
