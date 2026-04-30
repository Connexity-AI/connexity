"""Custom metric CRUD plus LLM-backed metric preview generation."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload


@click.group("custom-metrics")
def custom_metrics_group() -> None:
    """Manage user-defined custom metrics."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


@custom_metrics_group.command("list")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def custom_metrics_list(
    ctx: click.Context, limit: int, skip: int, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        data = client.custom_metrics.list(params={"limit": limit, "skip": skip})
    _emit(ctx, data, output_override)


@custom_metrics_group.command("show")
@click.argument("metric_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def custom_metrics_show(
    ctx: click.Context, metric_id: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        metric = client.custom_metrics.get(metric_id)
    _emit(ctx, metric, output_override)


@custom_metrics_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to CustomMetricCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def custom_metrics_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        metric = client.custom_metrics.create(body)
    _emit(ctx, metric, output_override)


@custom_metrics_group.command("update")
@click.argument("metric_id")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to CustomMetricUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def custom_metrics_update(
    ctx: click.Context,
    metric_id: str,
    from_file: str,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        metric = client.custom_metrics.update(metric_id, body)
    _emit(ctx, metric, output_override)


@custom_metrics_group.command("delete")
@click.argument("metric_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def custom_metrics_delete(ctx: click.Context, metric_id: str, yes: bool) -> None:
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete metric {metric_id}?", abort=True)
    with open_client(ctx) as client:
        result = client.custom_metrics.delete(metric_id)
    output.progress(str(result.get("message", "Deleted.")))


@custom_metrics_group.command("generate")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to MetricGenerateRequest JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def custom_metrics_generate(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    """Generate a metric definition preview via LLM (does not save)."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        result = client.custom_metrics.generate(body)
    _emit(ctx, result, output_override)
