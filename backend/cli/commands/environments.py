"""Agent deployment environments."""

from __future__ import annotations

import sys
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


@environments_group.command("deploy")
@click.argument("environment_id")
@click.option(
    "--agent-version",
    type=int,
    required=True,
    help="Agent version number to deploy (must be a published version)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def environments_deploy(
    ctx: click.Context,
    environment_id: str,
    agent_version: int,
    output_override: str | None,
) -> None:
    """Deploy an agent version to a configured environment.

    Triggers a Retell agent update on the bound platform integration. If the
    environment has an eval gate configured, the deploy is rejected unless the
    latest run for this agent version on the gated eval-config passed both
    metrics and cases thresholds.
    """
    ensure_auth(ctx)
    with open_client(ctx) as client:
        deployment = client.environments.deploy(
            environment_id, agent_version=agent_version
        )
    _emit(ctx, deployment, output_override)
    if str(deployment.get("status", "")).lower() == "failed":
        sys.exit(1)


@environments_group.command("retell-versions")
@click.argument("environment_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def environments_retell_versions(
    ctx: click.Context, environment_id: str, output_override: str | None
) -> None:
    """List published Retell agent versions for the bound integration."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        versions = client.environments.retell_versions(environment_id)
    _emit(ctx, versions, output_override)


@environments_group.group("deployments")
def environments_deployments_group() -> None:
    """Inspect deployment history."""


@environments_deployments_group.command("list")
@click.option(
    "--agent",
    "agent_ref",
    default=None,
    help="Agent UUID, name, or endpoint URL — list deployments across all environments for this agent",
)
@click.option(
    "--env-id",
    "environment_id",
    default=None,
    help="Environment UUID — list deployments for this environment only",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def environments_deployments_list(
    ctx: click.Context,
    agent_ref: str | None,
    environment_id: str | None,
    output_override: str | None,
) -> None:
    """List deployments scoped to an agent or to a single environment."""
    if (agent_ref is None) == (environment_id is None):
        raise click.UsageError("Provide exactly one of --agent or --env-id.")
    ensure_auth(ctx)
    with open_client(ctx) as client:
        if environment_id is not None:
            data = client.environments.list_environment_deployments(environment_id)
        else:
            assert agent_ref is not None
            agent = resolve_agent(client, agent_ref)
            data = client.environments.list_agent_deployments(agent_id=str(agent["id"]))
    _emit(ctx, data, output_override)
