"""Connexity Evals CLI — thin wrapper over the REST API."""

import os

import click

from cli.api_client import DEFAULT_BASE_URL
from cli.commands.baseline import baseline_group
from cli.commands.compare import compare_command
from cli.commands.results import results_group
from cli.commands.run import run_command
from cli.commands.scenarios import scenarios_group


@click.group()
@click.option(
    "--api-url",
    envvar="CONNEXITY_EVALS_API_URL",
    default=DEFAULT_BASE_URL,
    show_default=True,
    help="API base URL (without /api/v1)",
)
@click.option(
    "--token",
    envvar="CONNEXITY_EVALS_API_TOKEN",
    default="",
    show_default=False,
    help="Bearer JWT (same as login access token)",
)
@click.option(
    "--output",
    "output_format",
    type=click.Choice(["json", "table"]),
    default="table",
    show_default=True,
    help="Default output format for commands",
)
@click.pass_context
def app(
    ctx: click.Context,
    api_url: str,
    token: str,
    output_format: str,
) -> None:
    """Connexity Evals CLI."""
    ctx.obj = {
        "api_url": api_url,
        "token": token or os.environ.get("CONNEXITY_EVALS_API_TOKEN", ""),
        "output_format": output_format,
    }


app.add_command(baseline_group)
app.add_command(compare_command)
app.add_command(run_command)
app.add_command(results_group)
app.add_command(scenarios_group)
