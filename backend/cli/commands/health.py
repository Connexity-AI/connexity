"""Top-level health probe."""

from __future__ import annotations

import sys

import click

from cli import output
from cli.context import get_output_format, open_client


@click.command("health")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def health_command(ctx: click.Context, output_override: str | None) -> None:
    """Ping the API root (no auth required)."""
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        try:
            data = client.health.check()
        except click.ClickException as exc:
            click.echo(f"Health check failed: {exc.format_message()}", err=True)
            sys.exit(1)
    output.emit(data, output_format=fmt)
