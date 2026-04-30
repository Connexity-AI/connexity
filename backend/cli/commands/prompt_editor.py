"""Prompt-editor sessions, messages, presets, and SSE chat."""

from __future__ import annotations

import json
import sys
from typing import Any

import click
import httpx

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload
from cli.resolvers import resolve_agent


@click.group("prompt-editor")
def prompt_editor_group() -> None:
    """AI-assisted prompt editing — sessions, messages, presets, chat."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------


@prompt_editor_group.group("sessions")
def sessions_group() -> None:
    """Manage prompt-editor sessions."""


@sessions_group.command("list")
@click.option(
    "--agent", "agent_ref", default=None, help="Filter by agent UUID/name/URL"
)
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def sessions_list(
    ctx: click.Context,
    agent_ref: str | None,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    with open_client(ctx) as client:
        if agent_ref:
            params["agent_id"] = str(resolve_agent(client, agent_ref)["id"])
        data = client.prompt_editor.list_sessions(params=params)
    _emit(ctx, data, output_override)


@sessions_group.command("show")
@click.argument("session_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def sessions_show(
    ctx: click.Context, session_id: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        session = client.prompt_editor.get_session(session_id)
    _emit(ctx, session, output_override)


@sessions_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to PromptEditorSessionCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def sessions_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        session = client.prompt_editor.create_session(body)
    _emit(ctx, session, output_override)


@sessions_group.command("update")
@click.argument("session_id")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to PromptEditorSessionUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def sessions_update(
    ctx: click.Context,
    session_id: str,
    from_file: str,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        session = client.prompt_editor.update_session(session_id, body)
    _emit(ctx, session, output_override)


@sessions_group.command("set-base-prompt")
@click.argument("session_id")
@click.option(
    "--text", default=None, help="New base prompt (use --from-file for files)"
)
@click.option(
    "--from-file",
    "from_file",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Read base prompt text from file",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def sessions_set_base_prompt(
    ctx: click.Context,
    session_id: str,
    text: str | None,
    from_file: str | None,
    output_override: str | None,
) -> None:
    """Update the session's baseline prompt for diff calculation."""
    ensure_auth(ctx)
    if (text is None) == (from_file is None):
        raise click.ClickException("Provide exactly one of --text or --from-file.")
    if from_file:
        from pathlib import Path

        base_prompt = Path(from_file).read_text(encoding="utf-8")
    else:
        assert text is not None
        base_prompt = text
    with open_client(ctx) as client:
        session = client.prompt_editor.update_session_base_prompt(
            session_id, base_prompt=base_prompt
        )
    _emit(ctx, session, output_override)


@sessions_group.command("delete")
@click.argument("session_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def sessions_delete(ctx: click.Context, session_id: str, yes: bool) -> None:
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete session {session_id}?", abort=True)
    with open_client(ctx) as client:
        result = client.prompt_editor.delete_session(session_id)
    output.progress(str(result.get("message", "Deleted.")))


# ---------------------------------------------------------------------------
# messages + chat
# ---------------------------------------------------------------------------


@prompt_editor_group.group("messages")
def messages_group() -> None:
    """Inspect chat messages within a session."""


@messages_group.command("list")
@click.argument("session_id")
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def messages_list(
    ctx: click.Context,
    session_id: str,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        data = client.prompt_editor.list_messages(
            session_id, params={"limit": limit, "skip": skip}
        )
    _emit(ctx, data, output_override)


def _render_event(event: str, data: dict[str, Any]) -> None:
    """Render one SSE event for the prompt-editor chat to a TTY."""
    if event == "reasoning":
        text = str(data.get("text", "")).strip()
        if text:
            click.secho(f"  → {text}", fg="cyan", err=True)
    elif event == "status":
        msg = str(data.get("message") or data.get("status") or "")
        if msg:
            click.secho(f"  · {msg}", fg="yellow", err=True)
    elif event == "edit":
        prompt = data.get("edited_prompt")
        if isinstance(prompt, str):
            click.secho("  ⌫ edit snapshot:", fg="magenta", err=True)
            click.echo(prompt)
    elif event == "done":
        click.secho("  ✓ done", fg="green", err=True)
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(f"[{event}] {json.dumps(data, default=str)}", err=True)


@prompt_editor_group.command("chat")
@click.argument("session_id")
@click.option(
    "--message",
    required=True,
    help="User message to send",
)
@click.option(
    "--preset",
    "preset_id",
    default=None,
    help="Optional preset id to apply",
)
@click.option(
    "--stream/--no-stream",
    default=None,
    help="Force streaming mode (default: stream if stdout is a TTY)",
)
@click.pass_context
def chat_command(
    ctx: click.Context,
    session_id: str,
    message: str,
    preset_id: str | None,
    stream: bool | None,
) -> None:
    """Send a single chat message; SSE events render to stderr, final to stdout."""
    ensure_auth(ctx)
    body: dict[str, Any] = {"content": message}
    if preset_id:
        body["preset_id"] = preset_id

    should_stream = sys.stdout.isatty() if stream is None else stream

    with open_client(ctx) as client:
        try:
            collected: list[dict[str, Any]] = []
            for sse in client.prompt_editor.chat_stream(session_id, body):
                data = json.loads(sse.data) if sse.data else {}
                collected.append({"event": sse.event, "data": data})
                if should_stream:
                    _render_event(sse.event or "message", data)
                if sse.event == "done":
                    break
        except (httpx.HTTPError, OSError) as exc:
            raise click.ClickException(f"SSE chat failed: {exc}") from exc

    if not should_stream:
        # Non-streaming: emit the full event sequence as JSON for piping.
        output.emit(
            {"events": collected, "count": len(collected)},
            output_format="json",
        )


# ---------------------------------------------------------------------------
# presets
# ---------------------------------------------------------------------------


@prompt_editor_group.command("presets")
@click.option("--agent", "agent_ref", default=None, help="Filter presets by agent")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def presets_command(
    ctx: click.Context, agent_ref: str | None, output_override: str | None
) -> None:
    """List available editing presets (optionally scoped to an agent)."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    params: dict[str, Any] = {}
    with open_client(ctx) as client:
        if agent_ref:
            params["agent_id"] = str(resolve_agent(client, agent_ref)["id"])
        data = client.prompt_editor.get_presets(params=params)
    output.emit({"data": data, "count": len(data)}, output_format=fmt)
