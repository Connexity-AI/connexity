"""Connexity Evals CLI — command-line tooling for running evals, seeding data, etc."""

import click


@click.group()
def app() -> None:
    """Connexity Evals CLI."""


@app.command()
def hello() -> None:
    """Smoke test — confirm the CLI is working."""
    click.echo("connexity-evals cli is working")
