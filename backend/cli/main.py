"""Connexity Evals CLI — command-line tooling for running evals, seeding data, etc."""

import asyncio
import json
import os
import sys
from pathlib import Path

import click


@click.group()
def app() -> None:
    """Connexity Evals CLI."""


@app.command()
def hello() -> None:
    """Smoke test — confirm the CLI is working."""
    click.echo("connexity-evals cli is working")


@app.group()
def scenarios() -> None:
    """Scenario management commands."""


@scenarios.command()
@click.option(
    "--prompt",
    "prompt_file",
    required=True,
    type=click.Path(exists=True),
    help="Path to agent system prompt file (text)",
)
@click.option(
    "--tools",
    "tools_file",
    required=False,
    type=click.Path(exists=True),
    help="Path to tool definitions file (JSON array)",
)
@click.option(
    "--count",
    default=10,
    type=click.IntRange(1, 50),
    help="Number of scenarios to generate",
)
@click.option("--model", default=None, help="Override LLM model (e.g. gpt-4o-mini)")
@click.option(
    "--output",
    "output_file",
    default=None,
    type=click.Path(),
    help="Write scenarios to JSON file instead of DB",
)
@click.option(
    "--no-persist",
    is_flag=True,
    default=False,
    help="Do not save scenarios to database",
)
def generate(
    prompt_file: str,
    tools_file: str | None,
    count: int,
    model: str | None,
    output_file: str | None,
    no_persist: bool,
) -> None:
    """Generate evaluation scenarios from an agent prompt."""
    from app.generator.core import generate_scenarios
    from app.generator.schemas import GenerateRequest, ToolDefinition

    agent_prompt = Path(prompt_file).read_text(encoding="utf-8")

    tools: list[ToolDefinition] = []
    if tools_file:
        tools_data = json.loads(Path(tools_file).read_text(encoding="utf-8"))
        tools = [ToolDefinition.model_validate(t) for t in tools_data]

    request = GenerateRequest(
        agent_prompt=agent_prompt,
        tools=tools,
        count=count,
        model=model,
        persist=False,  # CLI handles persistence separately
    )

    # Sync API keys into process env so LiteLLM can find them
    from app.core.config import settings as _settings

    if _settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", _settings.OPENAI_API_KEY)
    if _settings.ANTHROPIC_API_KEY:
        os.environ.setdefault("ANTHROPIC_API_KEY", _settings.ANTHROPIC_API_KEY)

    try:
        generated, model_used, latency_ms = asyncio.run(generate_scenarios(request))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(
        f"Generated {len(generated)} scenarios using {model_used} ({latency_ms}ms)"
    )

    if output_file:
        output = [s.model_dump(mode="json") for s in generated]
        Path(output_file).write_text(json.dumps(output, indent=2), encoding="utf-8")
        click.echo(f"Written to {output_file}")

    if not no_persist and not output_file:
        from sqlmodel import Session

        from app.core.db import engine
        from app.models.scenario import Scenario

        with Session(engine) as session:
            for sc in generated:
                db_obj = Scenario.model_validate(sc.model_dump())
                session.add(db_obj)
            session.commit()
        click.echo(f"Persisted {len(generated)} draft scenarios to database")
