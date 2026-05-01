"""Agent CRUD, draft/publish/rollback, versions, and guidelines."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload
from cli.resolvers import resolve_agent

# ---------------------------------------------------------------------------
# group + helpers
# ---------------------------------------------------------------------------


@click.group("agents")
def agents_group() -> None:
    """Manage agents (create, edit, draft/publish, versions, guidelines)."""


def _output_choice() -> click.Option:
    return click.Option(
        ["--output", "output_override"],
        type=click.Choice(["json", "table"]),
        default=None,
        help="Override output format",
    )


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    fmt = get_output_format(ctx, output_override)
    output.emit(data, output_format=fmt)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@agents_group.command("list")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_list(
    ctx: click.Context, limit: int, skip: int, output_override: str | None
) -> None:
    """List agents."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        data = client.agents.list(params={"limit": limit, "skip": skip})
    _emit(ctx, data, output_override)


@agents_group.command("show")
@click.argument("agent_ref")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_show(
    ctx: click.Context, agent_ref: str, output_override: str | None
) -> None:
    """Show one agent (UUID, name, or endpoint URL)."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
    _emit(ctx, agent, output_override)


@agents_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to AgentCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    """Create an agent from a JSON AgentCreate body."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        agent = client.agents.create(body)
    _emit(ctx, agent, output_override)


@agents_group.command("create-draft")
@click.option("--name", required=True, help="Display name for the new draft agent")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_create_draft(
    ctx: click.Context, name: str, output_override: str | None
) -> None:
    """Create an empty draft agent (no prompt or tools yet)."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = client.agents.create_draft(name=name)
    _emit(ctx, agent, output_override)


@agents_group.command("update")
@click.argument("agent_ref")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to AgentUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_update(
    ctx: click.Context,
    agent_ref: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Patch agent fields (name, description, etc.). Bumps version on changes."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        updated = client.agents.update(str(agent["id"]), body)
    _emit(ctx, updated, output_override)


@agents_group.command("delete")
@click.argument("agent_ref")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation")
@click.pass_context
def agents_delete(ctx: click.Context, agent_ref: str, yes: bool) -> None:
    """Delete an agent."""
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete agent {agent_ref}?", abort=True)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        result = client.agents.delete(str(agent["id"]))
    output.progress(str(result.get("message", "Deleted.")))


# ---------------------------------------------------------------------------
# draft & publish
# ---------------------------------------------------------------------------


@agents_group.group("draft")
def agents_draft_group() -> None:
    """Inspect or modify the unpublished draft of an agent."""


@agents_draft_group.command("get")
@click.argument("agent_ref")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_draft_get(
    ctx: click.Context, agent_ref: str, output_override: str | None
) -> None:
    """Fetch the current draft (system_prompt, tools, model, etc.)."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        draft = client.agents.get_draft(str(agent["id"]))
    _emit(ctx, draft, output_override)


@agents_draft_group.command("set")
@click.argument("agent_ref")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to AgentDraftUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_draft_set(
    ctx: click.Context,
    agent_ref: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Create or replace the draft for an agent."""
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        draft = client.agents.upsert_draft(str(agent["id"]), body)
    _emit(ctx, draft, output_override)


@agents_draft_group.command("discard")
@click.argument("agent_ref")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation")
@click.pass_context
def agents_draft_discard(ctx: click.Context, agent_ref: str, yes: bool) -> None:
    """Discard the current draft."""
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Discard draft for {agent_ref}?", abort=True)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        client.agents.discard_draft(str(agent["id"]))
    output.progress("Draft discarded.")


@agents_group.command("publish")
@click.argument("agent_ref")
@click.option(
    "--description",
    "change_description",
    default=None,
    help="Optional changelog entry for this version",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_publish(
    ctx: click.Context,
    agent_ref: str,
    change_description: str | None,
    output_override: str | None,
) -> None:
    """Promote the draft to a new published version."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        version = client.agents.publish(
            str(agent["id"]), change_description=change_description
        )
    _emit(ctx, version, output_override)


@agents_group.command("rollback")
@click.argument("agent_ref")
@click.option(
    "--version", "version", required=True, type=int, help="Version to revert to"
)
@click.option(
    "--description", "change_description", default=None, help="Optional changelog"
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_rollback(
    ctx: click.Context,
    agent_ref: str,
    version: int,
    change_description: str | None,
    output_override: str | None,
) -> None:
    """Roll back to a prior version (creates a new version snapshot)."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        result = client.agents.rollback(
            str(agent["id"]),
            version=version,
            change_description=change_description,
        )
    _emit(ctx, result, output_override)


# ---------------------------------------------------------------------------
# versions
# ---------------------------------------------------------------------------


@agents_group.group("versions")
def agents_versions_group() -> None:
    """Inspect agent version history."""


@agents_versions_group.command("list")
@click.argument("agent_ref")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_versions_list(
    ctx: click.Context,
    agent_ref: str,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    """List published versions for an agent."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.agents.list_versions(
            str(agent["id"]), params={"limit": limit, "skip": skip}
        )
    _emit(ctx, data, output_override)


@agents_versions_group.command("show")
@click.argument("agent_ref")
@click.argument("version", type=int)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_versions_show(
    ctx: click.Context,
    agent_ref: str,
    version: int,
    output_override: str | None,
) -> None:
    """Show one version's snapshot."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.agents.get_version(str(agent["id"]), version)
    _emit(ctx, data, output_override)


@agents_versions_group.command("diff")
@click.argument("agent_ref")
@click.option("--from", "from_version", type=int, required=True, help="Older version")
@click.option("--to", "to_version", type=int, required=True, help="Newer version")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_versions_diff(
    ctx: click.Context,
    agent_ref: str,
    from_version: int,
    to_version: int,
    output_override: str | None,
) -> None:
    """Diff system_prompt / tools / model between two versions."""
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.agents.diff_versions(
            str(agent["id"]),
            from_version=from_version,
            to_version=to_version,
        )
    _emit(ctx, data, output_override)


# ---------------------------------------------------------------------------
# guidelines
# ---------------------------------------------------------------------------


@agents_group.group("guidelines")
def agents_guidelines_group() -> None:
    """Read or write the agent's system guidelines."""


@agents_guidelines_group.command("get")
@click.argument("agent_ref")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_guidelines_get(
    ctx: click.Context, agent_ref: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.agents.get_guidelines(str(agent["id"]))
    _emit(ctx, data, output_override)


@agents_guidelines_group.command("set")
@click.argument("agent_ref")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to AgentGuidelinesUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def agents_guidelines_set(
    ctx: click.Context,
    agent_ref: str,
    from_file: str,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        data = client.agents.put_guidelines(str(agent["id"]), body)
    _emit(ctx, data, output_override)
