"""Connexity CLI — thin wrapper over the REST API."""

from __future__ import annotations

import os

import click

from cli import credentials
from cli.api import DEFAULT_BASE_URL
from cli.commands.agents import agents_group
from cli.commands.auth import login_command, logout_command, whoami_command
from cli.commands.baseline import baseline_group
from cli.commands.calls import calls_group
from cli.commands.compare import compare_command
from cli.commands.config_cmd import config_group
from cli.commands.custom_metrics import custom_metrics_group
from cli.commands.environments import environments_group
from cli.commands.eval_configs import eval_configs_group
from cli.commands.health import health_command
from cli.commands.integrations import integrations_group
from cli.commands.prompt_editor import prompt_editor_group
from cli.commands.run import run_command
from cli.commands.runs import runs_group
from cli.commands.test_case_results import test_case_results_group
from cli.commands.test_cases import test_cases_group


@click.group()
@click.option(
    "--api-url",
    envvar="CONNEXITY_CLI_API_URL",
    default=DEFAULT_BASE_URL,
    show_default=True,
    help="API base URL (without /api/v1)",
)
@click.option(
    "--token",
    envvar="CONNEXITY_CLI_API_TOKEN",
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
    """Connexity CLI."""
    stored = credentials.load()

    # Token: explicit flag/env wins; otherwise fall back to the stored token.
    if not token:
        token = stored.get("token", "")

    # API URL: only fall back to stored value when the user did not override
    # via flag or env. Click cannot tell us whether the default was used, so
    # we infer from the env var being unset and the flag matching the default
    # literal.
    if api_url == DEFAULT_BASE_URL and not os.environ.get("CONNEXITY_CLI_API_URL"):
        stored_url = stored.get("api_url")
        if stored_url:
            api_url = stored_url

    ctx.obj = {
        "api_url": api_url,
        "token": token,
        "output_format": output_format,
    }


# Auth & session
app.add_command(login_command)
app.add_command(logout_command)
app.add_command(whoami_command)
app.add_command(health_command)

# Resources
app.add_command(agents_group)
app.add_command(eval_configs_group)
app.add_command(test_cases_group)
app.add_command(test_case_results_group)
app.add_command(custom_metrics_group)
app.add_command(runs_group)
app.add_command(integrations_group)
app.add_command(environments_group)
app.add_command(calls_group)
app.add_command(prompt_editor_group)
app.add_command(config_group)

# Convenience top-level wrappers
app.add_command(run_command)
app.add_command(compare_command)
app.add_command(baseline_group)
