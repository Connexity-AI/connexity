"""Read-only config / metrics / models endpoints."""

from __future__ import annotations

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client


@click.group("config")
def config_group() -> None:
    """Read API metadata: settings, available metrics, LLM models."""


@config_group.command("show")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def config_show(ctx: click.Context, output_override: str | None) -> None:
    """Show API metadata (project_name, api_version, environment, etc.)."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.config.show()
    output.emit(data, output_format=fmt)


@config_group.command("metrics")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def config_metrics(ctx: click.Context, output_override: str | None) -> None:
    """List available metrics (built-in + user's custom)."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.config.available_metrics()
    output.emit(data, output_format=fmt)


@config_group.command("llm-models")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def config_llm_models(ctx: click.Context, output_override: str | None) -> None:
    """List configured LLM models grouped by provider."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.config.llm_models()
    output.emit(data, output_format=fmt)


@config_group.command("stt-models")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def config_stt_models(ctx: click.Context, output_override: str | None) -> None:
    """List configured STT models grouped by provider."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.config.stt_models()
    output.emit(data, output_format=fmt)


@config_group.command("tts-models")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def config_tts_models(ctx: click.Context, output_override: str | None) -> None:
    """List configured TTS models grouped by provider."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.config.tts_models()
    output.emit(data, output_format=fmt)


@config_group.command("tts-voices")
@click.argument("provider")
@click.argument("model")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def config_tts_voices(
    ctx: click.Context,
    provider: str,
    model: str,
    output_override: str | None,
) -> None:
    """List TTS voices for a provider and model."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        data = client.config.tts_voices(provider=provider, model=model)
    output.emit(data, output_format=fmt)
