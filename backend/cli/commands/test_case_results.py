"""Per-test-case run result CRUD."""

from __future__ import annotations

from typing import Any

import click

from cli import output
from cli.context import ensure_auth, get_output_format, open_client
from cli.payload import load_dict_payload


@click.group("test-case-results")
def test_case_results_group() -> None:
    """Inspect or mutate per-test-case results within a run."""


def _emit(ctx: click.Context, data: Any, output_override: str | None) -> None:
    output.emit(data, output_format=get_output_format(ctx, output_override))


@test_case_results_group.command("list")
@click.option("--run", "run_id", default=None, help="Filter by run UUID")
@click.option(
    "--test-case", "test_case_id", default=None, help="Filter by test case UUID"
)
@click.option("--repetition", "repetition_index", type=int, default=None)
@click.option(
    "--passed",
    type=click.Choice(["true", "false"]),
    default=None,
    help="Filter by pass/fail",
)
@click.option("--limit", default=100, type=int, show_default=True)
@click.option("--skip", default=0, type=int, show_default=True)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_case_results_list(
    ctx: click.Context,
    run_id: str | None,
    test_case_id: str | None,
    repetition_index: int | None,
    passed: str | None,
    limit: int,
    skip: int,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    params: dict[str, Any] = {"limit": limit, "skip": skip}
    if run_id:
        params["run_id"] = run_id
    if test_case_id:
        params["test_case_id"] = test_case_id
    if repetition_index is not None:
        params["repetition_index"] = repetition_index
    if passed is not None:
        params["passed"] = passed == "true"
    with open_client(ctx) as client:
        data = client.test_case_results.list(params=params)
    _emit(ctx, data, output_override)


@test_case_results_group.command("show")
@click.argument("result_id")
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_case_results_show(
    ctx: click.Context, result_id: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    with open_client(ctx) as client:
        result = client.test_case_results.get(result_id)
    _emit(ctx, result, output_override)


@test_case_results_group.command("create")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to TestCaseResultCreate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_case_results_create(
    ctx: click.Context, from_file: str, output_override: str | None
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        result = client.test_case_results.create(body)
    _emit(ctx, result, output_override)


@test_case_results_group.command("update")
@click.argument("result_id")
@click.option(
    "--from-file",
    "from_file",
    required=True,
    help="Path to TestCaseResultUpdate JSON ('-' for stdin)",
)
@click.option(
    "--output", "output_override", type=click.Choice(["json", "table"]), default=None
)
@click.pass_context
def test_case_results_update(
    ctx: click.Context,
    result_id: str,
    from_file: str,
    output_override: str | None,
) -> None:
    ensure_auth(ctx)
    body = load_dict_payload(from_file)
    with open_client(ctx) as client:
        result = client.test_case_results.update(result_id, body)
    _emit(ctx, result, output_override)


@test_case_results_group.command("delete")
@click.argument("result_id")
@click.option("--yes", "-y", is_flag=True, default=False)
@click.pass_context
def test_case_results_delete(ctx: click.Context, result_id: str, yes: bool) -> None:
    ensure_auth(ctx)
    if not yes:
        click.confirm(f"Delete result {result_id}?", abort=True)
    with open_client(ctx) as client:
        result = client.test_case_results.delete(result_id)
    output.progress(str(result.get("message", "Deleted.")))
