"""Authentication commands: login, logout, whoami."""

from __future__ import annotations

from datetime import UTC, datetime

import click

from cli import credentials, output
from cli.api import ApiClient
from cli.context import ensure_auth, get_output_format, root_obj


@click.command("login")
@click.option(
    "--email",
    required=True,
    help="Email address registered with the platform",
)
@click.option(
    "--password",
    default=None,
    help="Password (omit to be prompted securely)",
)
@click.option(
    "--save",
    is_flag=True,
    default=False,
    help="Persist token + API URL to ~/.config/connexity-cli/credentials.json (mode 0600)",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Override output format",
)
@click.pass_context
def login_command(
    ctx: click.Context,
    email: str,
    password: str | None,
    save: bool,
    output_override: str | None,
) -> None:
    """Exchange email + password for a JWT access token."""
    fmt = get_output_format(ctx, output_override)
    if password is None:
        password = click.prompt("Password", hide_input=True)
    if not password:
        raise click.ClickException("Password cannot be empty.")

    root = root_obj(ctx)
    api_url = root["api_url"]

    # Login does not require an existing token; build a bare client.
    with ApiClient(base_url=api_url, token="") as client:
        token_response = client.auth.login(email=email, password=password)

    access_token = token_response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise click.ClickException("Login response missing access_token.")
    expires = token_response.get("expires")

    if save:
        payload: credentials.StoredCredentials = {
            "api_url": api_url,
            "token": access_token,
            "email": email,
        }
        if isinstance(expires, int):
            payload["expires"] = int(expires)
        path = credentials.save(payload)
        output.progress(f"Saved credentials to {path} (mode 0600).")
    else:
        output.progress(
            "Credentials NOT saved. Pass --save to persist, or export the token:\n"
            f"  export CONNEXITY_CLI_API_TOKEN={access_token}"
        )

    if fmt == "json":
        output.emit(token_response, output_format="json")
        return

    expires_str = (
        datetime.fromtimestamp(expires, tz=UTC).isoformat()
        if isinstance(expires, int)
        else "unknown"
    )
    click.echo(f"Logged in as {email}.")
    click.echo(f"  token expires: {expires_str}")


@click.command("logout")
@click.pass_context
def logout_command(ctx: click.Context) -> None:
    """Clear local credentials and best-effort revoke server-side cookie."""
    token = root_obj(ctx).get("token")
    # Best effort: only call /logout if we have a token; otherwise skip silently.
    if token:
        try:
            with ApiClient(base_url=root_obj(ctx)["api_url"], token=token) as client:
                client.auth.logout()
        except click.ClickException as exc:
            # Server-side errors here are non-fatal — local cleanup still proceeds.
            output.progress(f"Server logout call failed (continuing): {exc.message}")

    if credentials.clear():
        output.progress(f"Removed {credentials.credentials_path()}.")
    else:
        output.progress("No saved credentials to remove.")


@click.command("whoami")
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
)
@click.pass_context
def whoami_command(ctx: click.Context, output_override: str | None) -> None:
    """Show the user that owns the current token."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with ApiClient(
        base_url=root_obj(ctx)["api_url"],
        token=root_obj(ctx)["token"],
    ) as client:
        me = client.users.me()
    if fmt == "json":
        output.emit(me, output_format="json")
    else:
        click.echo(f"id:        {me.get('id')}")
        click.echo(f"email:     {me.get('email')}")
        click.echo(f"full_name: {me.get('full_name') or '—'}")
        click.echo(f"is_active: {me.get('is_active')}")
