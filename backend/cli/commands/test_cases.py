"""TestCase list, import, export, and generate via the API."""

import json
import sys
from pathlib import Path
from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload, load_list_payload
from cli.resolvers import resolve_agent


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
    ensure_auth(ctx)
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
            data = client.test_cases.list(params=params)
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
                chunk = client.test_cases.list(params=params)
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
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    raw = Path(file).read_text(encoding="utf-8")
    items = _load_import_payload(raw)
    if not items:
        raise click.ClickException("No test case objects found in file.")

    on_conflict = "overwrite" if overwrite else "skip"
    with open_client(ctx) as client:
        result = client.test_cases.import_(items, on_conflict=on_conflict)

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
    ensure_auth(ctx)
    params: dict[str, Any] = {}
    if tag:
        params["tag"] = tag
    if difficulty:
        params["difficulty"] = difficulty
    if status:
        params["status"] = status

    with open_client(ctx) as client:
        data = client.test_cases.export(params=params)

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
    ensure_auth(ctx)
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
        result = client.test_cases.generate(body)

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


# ---------------------------------------------------------------------------
# CRUD (single test cases)
# ---------------------------------------------------------------------------


@test_cases_group.command("show")
@click.argument("test_case_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_cases_show(
    ctx: click.Context, test_case_id: str, output_override: str | None
) -> None:
    """Show one test case by UUID."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    with open_client(ctx) as client:
        tc = client.test_cases.get(test_case_id)
    output.emit(tc, output_format=fmt)


@test_cases_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to TestCaseCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_cases_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    """Create a single test case from JSON."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        tc = client.test_cases.create(body)
    output.emit(tc, output_format=fmt)


@test_cases_group.command("update")
@click.argument("test_case_id")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to TestCaseUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_cases_update(
    ctx: click.Context,
    test_case_id: str,
    from_file: str,
    output_override: str | None,
) -> None:
    """Patch a test case by UUID."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        tc = client.test_cases.update(test_case_id, body)
    output.emit(tc, output_format=fmt)


@test_cases_group.command("delete")
@click.argument("test_case_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def test_cases_delete(ctx: click.Context, test_case_id: str, yes: bool) -> None:
    """Delete a test case by UUID."""
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete test case {test_case_id}?", abort=True)
    with open_client(ctx) as client:
        result = client.test_cases.delete(test_case_id)
    output.progress(str(result.get("message", "Deleted.")))


# ---------------------------------------------------------------------------
# AI agent (POST /test-cases/ai)
# ---------------------------------------------------------------------------


@test_cases_group.command("ai")
@click.option(
    "--mode",
    type=click.Choice(["create", "from_transcript", "edit"]),
    required=True,
    help="AI agent mode",
)
@click.option(
    "--message",
    "user_message",
    required=True,
    help="Instruction for the AI agent",
)
@click.option("--agent", "agent_ref", required=True, help="Agent UUID, name, or URL")
@click.option(
    "--agent-version", type=int, default=None, help="Pin to a specific agent version"
)
@click.option(
    "--transcript-file",
    "transcript_file",
    default=None,
    help="JSON file with ConversationTurn list (required for mode=from_transcript)",
)
@click.option(
    "--test-case",
    "test_case_id",
    default=None,
    help="Test case UUID to edit (required for mode=edit)",
)
@click.option(
    "--source-call",
    "source_call_id",
    default=None,
    help="Call UUID this test case derives from (links the persisted row)",
)
@click.option(
    "--persist/--no-persist",
    default=None,
    help="Override the default persist behavior (true for create/from_transcript, false for edit)",
)
@click.option("--model", default=None)
@click.option("--provider", default=None)
@click.option("--temperature", type=click.FloatRange(0.0, 2.0), default=None)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_cases_ai(
    ctx: click.Context,
    mode: str,
    user_message: str,
    agent_ref: str,
    agent_version: int | None,
    transcript_file: str | None,
    test_case_id: str | None,
    source_call_id: str | None,
    persist: bool | None,
    model: str | None,
    provider: str | None,
    temperature: float | None,
    output_override: str | None,
) -> None:
    """Run the test-case AI agent (single tool-calling turn)."""
    ensure_auth(ctx)
    fmt = get_output_format(ctx, output_override)

    transcript: list[Any] | None = None
    if mode == "from_transcript":
        if not transcript_file:
            raise click.ClickException(
                "--transcript-file is required when --mode=from_transcript"
            )
        transcript = load_list_payload(transcript_file)

    if mode == "edit" and not test_case_id:
        raise click.ClickException("--test-case is required when --mode=edit")

    with open_client(ctx) as client:
        agent = resolve_agent(client, agent_ref)
        body: dict[str, Any] = {
            "mode": mode,
            "user_message": user_message,
            "agent_id": str(agent["id"]),
        }
        if agent_version is not None:
            body["agent_version"] = agent_version
        if transcript is not None:
            body["transcript"] = transcript
        if test_case_id:
            body["test_case_id"] = test_case_id
        if source_call_id:
            body["source_call_id"] = source_call_id
        if persist is not None:
            body["persist"] = persist
        if model:
            body["model"] = model
        if provider:
            body["provider"] = provider
        if temperature is not None:
            body["temperature"] = temperature

        result = client.test_cases.ai(body)

    output.emit(result, output_format=fmt)
