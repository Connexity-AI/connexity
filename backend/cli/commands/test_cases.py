"""TestCase list, import, export, and generate via the API."""

import json
import sys
from pathlib import Path
from typing import Any

import click

from cli import output
from cli.context import get_output_format, open_client, root_obj


@click.group("test-cases")
def test_cases_group() -> None:
    """Manage test cases."""


@test_cases_group.command("list")
@click.option(
    "--tag",
    "--tags",
    multiple=True,
    help="Filter by tag (repeatable; one API call per tag, merged)",
)
@click.option("--difficulty", default=None)
@click.option("--status", default=None)
@click.option("--search", default=None)
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
)
@click.pass_context
def test_cases_list(
    ctx: click.Context,
    tag: tuple[str, ...],
    difficulty: str | None,
    status: str | None,
    search: str | None,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    """List test cases with optional filters."""
    if not root_obj(ctx).get("token"):
        raise click.ClickException(
            "Authentication required: set CONNEXITY_EVALS_API_TOKEN or pass --token."
        )
    fmt = get_output_format(ctx, output_override)

    with open_client(ctx) as client:
        if not tag:
            params: dict[str, Any] = {
                "limit": limit,
                "skip": skip,
            }
            if difficulty:
                params["difficulty"] = difficulty
            if status:
                params["status"] = status
            if search:
                params["search"] = search
            data = client.list_test_cases(params=params)
        else:
            merged: dict[str, dict[str, Any]] = {}
            total = 0
            for t in tag:
                params = {
                    "limit": limit,
                    "skip": skip,
                    "tag": t,
                }
                if difficulty:
                    params["difficulty"] = difficulty
                if status:
                    params["status"] = status
                if search:
                    params["search"] = search
                chunk = client.list_test_cases(params=params)
                total += int(chunk.get("count") or 0)
                for row in chunk.get("data") or []:
                    if isinstance(row, dict) and "id" in row:
                        merged[str(row["id"])] = row
            data = {"data": list(merged.values()), "count": len(merged)}

    output.emit(data, output_format=fmt)


def _load_import_payload(raw: str) -> list[dict[str, Any]]:
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        inner = parsed.get("test_cases")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    raise click.ClickException(
        "Import file must be a JSON array of test cases or an object with a "
        "'test_cases' array."
    )


@test_cases_group.command("import")
@click.argument("file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite existing test cases on id conflict (maps to on_conflict=overwrite)",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
)
@click.pass_context
def test_cases_import(
    ctx: click.Context,
    file: str,
    overwrite: bool,
    output_override: str | None,
) -> None:
    """Bulk-import test cases from JSON."""
    if not root_obj(ctx).get("token"):
        raise click.ClickException(
            "Authentication required: set CONNEXITY_EVALS_API_TOKEN or pass --token."
        )
    fmt = get_output_format(ctx, output_override)
    raw = Path(file).read_text(encoding="utf-8")
    items = _load_import_payload(raw)
    if not items:
        raise click.ClickException("No test case objects found in file.")

    on_conflict = "overwrite" if overwrite else "skip"
    with open_client(ctx) as client:
        result = client.import_test_cases(items, on_conflict=on_conflict)

    output.emit(result, output_format=fmt)
    if result.get("errors"):
        sys.exit(1)


@test_cases_group.command("export")
@click.option("--tag", default=None)
@click.option("--difficulty", default=None)
@click.option("--status", default=None)
@click.option(
    "--file",
    "out_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write JSON to this file instead of stdout",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
)
@click.pass_context
def test_cases_export(
    ctx: click.Context,
    tag: str | None,
    difficulty: str | None,
    status: str | None,
    out_path: str | None,
    output_override: str | None,
) -> None:
    """Export test cases as JSON."""
    if not root_obj(ctx).get("token"):
        raise click.ClickException(
            "Authentication required: set CONNEXITY_EVALS_API_TOKEN or pass --token."
        )
    params: dict[str, Any] = {}
    if tag:
        params["tag"] = tag
    if difficulty:
        params["difficulty"] = difficulty
    if status:
        params["status"] = status

    with open_client(ctx) as client:
        data = client.export_test_cases(params=params)

    if out_path:
        Path(out_path).write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
        click.echo(f"Wrote {out_path}", err=True)
        return

    fmt = get_output_format(ctx, output_override)
    output.emit(data, output_format=fmt)


@test_cases_group.command("generate")
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
    help="Number of test cases to generate",
)
@click.option("--model", default=None, help="Override LLM model")
@click.option(
    "--write",
    "write_file",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write generated test cases JSON to this file",
)
@click.option(
    "--no-persist",
    is_flag=True,
    default=False,
    help="Do not persist test cases in the database",
)
@click.option(
    "--output",
    "output_override",
    type=click.Choice(["json", "table"]),
    default=None,
)
@click.pass_context
def test_cases_generate(
    ctx: click.Context,
    prompt_file: str,
    tools_file: str | None,
    count: int,
    model: str | None,
    write_file: str | None,
    no_persist: bool,
    output_override: str | None,
) -> None:
    """Generate test cases via the API (POST /test-cases/generate)."""
    if not root_obj(ctx).get("token"):
        raise click.ClickException(
            "Authentication required: set CONNEXITY_EVALS_API_TOKEN or pass --token."
        )
    fmt = get_output_format(ctx, output_override)

    agent_prompt = Path(prompt_file).read_text(encoding="utf-8")
    tools: list[dict[str, Any]] = []
    if tools_file:
        tools_data = json.loads(Path(tools_file).read_text(encoding="utf-8"))
        if not isinstance(tools_data, list):
            raise click.ClickException("Tools file must contain a JSON array.")
        tools = [t for t in tools_data if isinstance(t, dict)]

    body: dict[str, Any] = {
        "agent_prompt": agent_prompt,
        "tools": tools,
        "count": count,
        "persist": not no_persist,
    }
    if model:
        body["model"] = model

    with open_client(ctx) as client:
        result = client.generate_test_cases(body)

    if write_file:
        test_cases = result.get("test_cases") or []
        Path(write_file).write_text(
            json.dumps(test_cases, indent=2, default=str),
            encoding="utf-8",
        )
        click.echo(f"Written {len(test_cases)} test case(s) to {write_file}", err=True)

    if fmt == "json":
        output.emit(result, output_format="json")
        return

    click.echo(
        f"Generated {result.get('count')} test case(s) using "
        f"{result.get('model_used')} ({result.get('generation_time_ms')}ms)"
    )
    test_cases = result.get("test_cases") or []
    if test_cases:
        rows = [
            {
                "name": s.get("name"),
                "id": str(s.get("id", "")),
                "status": s.get("status"),
            }
            for s in test_cases
            if isinstance(s, dict)
        ]
        click.echo(output.format_dict_rows(rows))
