"""Shared Click context helpers.

The root ``app`` group stores ``api_url``, ``token``, and ``output_format``
on ``ctx.obj``. Subcommands look these values up via :func:`root_obj` /
:func:`get_output_format` and obtain a ready-to-use HTTP client via
:func:`open_client`. ``ensure_auth`` raises a uniform error if no token is
configured.
"""

from __future__ import annotations

from typing import Any

import click

from cli.api import ApiClient


def root_obj(ctx: click.Context) -> dict[str, Any]:
    while ctx.parent is not None:
        ctx = ctx.parent
    obj = ctx.obj
    if not isinstance(obj, dict):
        raise click.ClickException("CLI context was not initialized.")
    return obj


def get_output_format(ctx: click.Context, override: str | None) -> str:
    base = root_obj(ctx)["output_format"]
    if not isinstance(base, str):
        raise click.ClickException("Invalid default output format.")
    fmt = override if override is not None else base
    if fmt not in ("json", "table"):
        raise click.BadParameter("output must be json or table")
    return fmt


def ensure_auth(ctx: click.Context) -> None:
    """Raise unless a token is present in the resolved context."""
    if not root_obj(ctx).get("token"):
        raise click.ClickException(
            "Authentication required: run `connexity-cli login` or set "
            "CONNEXITY_CLI_API_TOKEN."
        )


def open_client(ctx: click.Context) -> ApiClient:
    o = root_obj(ctx)
    return ApiClient(base_url=o["api_url"], token=o["token"])
