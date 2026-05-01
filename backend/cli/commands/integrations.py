"""Third-party integration management (Retell etc.)."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client


@click.group("integrations")
def integrations_group() -> None:
    """Manage third-party integrations (e.g. Retell)."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


@integrations_group.command("list")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def integrations_list(
    ctx: click.Context, limit: int, skip: int, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        data = client.integrations.list(params={"limit": limit, "skip": skip})
    _emit(ctx, data, output_override)


@integrations_group.command("create")
@click.option("--provider", required=True, help="Provider identifier (e.g. retell)")
@click.option("--api-key", "api_key", required=True, help="API key for the provider")
@click.option("--name", default=None, help="Optional friendly name")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def integrations_create(
    ctx: click.Context,
    provider: str,
    api_key: str,
    name: str | None,
    output_override: str | None,
) -> None:
    """Create an integration; the API tests the connection before persisting."""
    ensure_auth(ctx)
    body: dict[str, Any] = {"provider": provider, "api_key": api_key}
    if name:
        body["name"] = name
    with open_client(ctx) as client:
        result = client.integrations.create(body)
    _emit(ctx, result, output_override)


@integrations_group.command("delete")
@click.argument("integration_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def integrations_delete(ctx: click.Context, integration_id: str, yes: bool) -> None:
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete integration {integration_id}?", abort=True)
    with open_client(ctx) as client:
        result = client.integrations.delete(integration_id)
    output.progress(str(result.get("message", "Deleted.")))


@integrations_group.command("test")
@click.argument("integration_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def integrations_test(
    ctx: click.Context, integration_id: str, output_override: str | None
) -> None:
    """Validate the integration's credentials against the provider."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        result = client.integrations.test(integration_id)
    _emit(ctx, result, output_override)


@integrations_group.command("agents")
@click.argument("integration_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def integrations_agents(
    ctx: click.Context, integration_id: str, output_override: str | None
) -> None:
    """List provider-side agents available through this integration."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.integrations.list_agents(integration_id)
    output.emit({"data": data, "count": len(data)}, output_format=fmt)
