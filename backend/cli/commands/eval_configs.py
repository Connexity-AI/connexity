"""Eval config CRUD plus member (test-case) management."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload
from cli.resolvers import resolve_eval_config


@click.group("eval-configs")
def eval_configs_group() -> None:
    """Manage eval configs (judge config, simulator config, test-case members)."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@eval_configs_group.command("list")
@click.option("--agent", "agent_id", default=None, help="Filter by agent UUID")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_list(
    ctx: click.Context,
    agent_id: str | None,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    """List eval configs."""
    ensure_auth(ctx)
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    if agent_id:
        params["agent_id"] = agent_id
    with open_client(ctx) as client:
        data = client.eval_configs.list(params=params)
    _emit(ctx, data, output_override)


@eval_configs_group.command("show")
@click.argument("eval_config_ref")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_show(
    ctx: click.Context, eval_config_ref: str, output_override: str | None
) -> None:
    """Show one eval config (UUID or name)."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
    _emit(ctx, cfg, output_override)


@eval_configs_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to EvalConfigCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    """Create an eval config from JSON."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        cfg = client.eval_configs.create(body)
    _emit(ctx, cfg, output_override)


@eval_configs_group.command("update")
@click.argument("eval_config_ref")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to EvalConfigUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_update(
    ctx: click.Context,
    eval_config_ref: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Patch eval config fields."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
        updated = client.eval_configs.update(str(cfg["id"]), body)
    _emit(ctx, updated, output_override)


@eval_configs_group.command("delete")
@click.argument("eval_config_ref")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def eval_configs_delete(ctx: click.Context, eval_config_ref: str, yes: bool) -> None:
    """Delete an eval config."""
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete eval config {eval_config_ref}?", abort=True)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
        result = client.eval_configs.delete(str(cfg["id"]))
    output.progress(str(result.get("message", "Deleted.")))


# ---------------------------------------------------------------------------
# member (test-case) management
# ---------------------------------------------------------------------------


@eval_configs_group.group("members")
def eval_configs_members_group() -> None:
    """Manage the test-cases attached to an eval config."""


@eval_configs_members_group.command("list")
@click.argument("eval_config_ref")
@click.option("--limit", default=1000, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_members_list(
    ctx: click.Context,
    eval_config_ref: str,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
        data = client.eval_configs.list_members(
            str(cfg["id"]), params={"limit": limit, "skip": skip}
        )
    _emit(ctx, data, output_override)


@eval_configs_members_group.command("add")
@click.argument("eval_config_ref")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to EvalConfigMembersUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_members_add(
    ctx: click.Context,
    eval_config_ref: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Append members to an eval config."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
        result = client.eval_configs.add_members(str(cfg["id"]), body)
    _emit(ctx, result, output_override)


@eval_configs_members_group.command("replace")
@click.argument("eval_config_ref")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to EvalConfigMembersUpdate JSON ('-' for stdin) — replaces ALL members",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_members_replace(
    ctx: click.Context,
    eval_config_ref: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Replace the entire member list (PUT)."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
        result = client.eval_configs.replace_members(str(cfg["id"]), body)
    _emit(ctx, result, output_override)


@eval_configs_members_group.command("remove")
@click.argument("eval_config_ref")
@click.argument("test_case_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def eval_configs_members_remove(
    ctx: click.Context,
    eval_config_ref: str,
    test_case_id: str,
    output_override: str | None,
) -> None:
    """Remove a single test case (by UUID) from the eval config."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        cfg = resolve_eval_config(client, eval_config_ref)
        result = client.eval_configs.remove_member(str(cfg["id"]), test_case_id)
    _emit(ctx, result, output_override)
