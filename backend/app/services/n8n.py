"""Read-only client for one n8n instance's public API.

Connexity only ever reads from n8n. Every function takes the instance's address and API
key; nothing here is configured server-wide.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.services.outbound_url import (
    OutboundTarget,
    OutboundUrlError,
    resolve_outbound_target,
)

_API_PREFIX = "/api/v1"
_TIMEOUT_SECONDS = 15.0
_PAGE_SIZE = 250


class N8nError(Exception):
    """n8n could not be read: unreachable, refused, or an answer that makes no sense."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class N8nWorkflow(BaseModel):
    id: str
    name: str
    active: bool = False


class N8nExecutionSummary(BaseModel):
    id: str
    workflow_id: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None


class N8nConnectionProblem(StrEnum):
    ADDRESS_NOT_ALLOWED = "address_not_allowed"
    UNREACHABLE = "unreachable"
    WRONG_KEY = "wrong_key"
    NOT_N8N = "not_n8n"


class N8nConnectionResult(BaseModel):
    ok: bool
    base_url: str | None = None
    problem: N8nConnectionProblem | None = None
    message: str | None = None


def n8n_api_root(base_url: str) -> str:
    """The API root for an instance address, with or without ``/api/v1`` already on it."""
    root = base_url.rstrip("/")
    return root if root.endswith(_API_PREFIX) else f"{root}{_API_PREFIX}"


async def _request(
    target: OutboundTarget,
    api_key: str,
    path: str,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    """One GET, sent to the address that was checked. Redirects are never followed."""
    async with httpx.AsyncClient(follow_redirects=False) as client:
        return await client.get(
            f"{n8n_api_root(target.connect_url)}{path}",
            headers={
                "X-N8N-API-KEY": api_key,
                "Accept": "application/json",
                **target.headers,
            },
            params=params,
            timeout=_TIMEOUT_SECONDS,
            extensions=target.extensions,
        )


async def check_n8n_connection(base_url: str, api_key: str) -> N8nConnectionResult:
    """Make one read call to confirm the address is an n8n and the key works."""
    try:
        target = await resolve_outbound_target(base_url)
    except OutboundUrlError as exc:
        return N8nConnectionResult(
            ok=False,
            problem=N8nConnectionProblem.ADDRESS_NOT_ALLOWED,
            message=str(exc),
        )

    try:
        response = await _request(target, api_key, "/executions", {"limit": 1})
    except httpx.HTTPError:
        return N8nConnectionResult(
            ok=False,
            problem=N8nConnectionProblem.UNREACHABLE,
            message="Could not reach n8n at that address",
        )

    if response.status_code in (401, 403):
        return N8nConnectionResult(
            ok=False,
            problem=N8nConnectionProblem.WRONG_KEY,
            message="n8n refused the API key",
        )
    if response.status_code == 200:
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict) and isinstance(body.get("data"), list):
            return N8nConnectionResult(ok=True, base_url=target.base_url)
    return N8nConnectionResult(
        ok=False,
        problem=N8nConnectionProblem.NOT_N8N,
        message="That address did not answer like an n8n API. "
        "Use the instance address, for example https://your-name.app.n8n.cloud",
    )


async def _get(
    base_url: str, api_key: str, path: str, params: dict[str, Any] | None = None
) -> Any:
    """One read from n8n's API, as parsed JSON.

    Raises:
        N8nError: The address is not allowed, n8n is unreachable or slow, it answered
            with an error, or the answer is not JSON.
    """
    try:
        target = await resolve_outbound_target(base_url)
    except OutboundUrlError as exc:
        raise N8nError(str(exc)) from exc
    try:
        response = await _request(target, api_key, path, params)
    except httpx.HTTPError as exc:
        msg = "Could not reach n8n"
        raise N8nError(msg) from exc
    if response.status_code != 200:
        msg = f"n8n answered {response.status_code}"
        raise N8nError(msg, status_code=response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        msg = "n8n did not answer with JSON"
        raise N8nError(msg) from exc


def _page(body: Any) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(body, dict) or not isinstance(body.get("data"), list):
        msg = "n8n answered in an unexpected shape"
        raise N8nError(msg)
    cursor = body.get("nextCursor")
    items = [item for item in body["data"] if isinstance(item, dict)]
    return items, cursor if isinstance(cursor, str) and cursor else None


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


async def list_n8n_workflows(
    base_url: str, api_key: str, *, max_items: int = 1000
) -> list[N8nWorkflow]:
    """Names and ids of the instance's workflows, for choosing one. Archived left out."""
    workflows: list[N8nWorkflow] = []
    cursor: str | None = None
    while len(workflows) < max_items:
        params: dict[str, Any] = {"limit": _PAGE_SIZE, "excludePinnedData": "true"}
        if cursor:
            params["cursor"] = cursor
        items, cursor = _page(await _get(base_url, api_key, "/workflows", params))
        workflows.extend(
            N8nWorkflow(
                id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                active=bool(item.get("active")),
            )
            for item in items
            if item.get("id") is not None and not item.get("isArchived")
        )
        if cursor is None:
            break
    return sorted(workflows, key=lambda workflow: workflow.name.lower())


async def get_n8n_workflow(
    base_url: str, api_key: str, workflow_id: str
) -> N8nWorkflow | None:
    """One workflow's name, or ``None`` when the instance has no such workflow."""
    try:
        body = await _get(
            base_url, api_key, f"/workflows/{quote(workflow_id, safe='')}"
        )
    except N8nError as exc:
        if exc.status_code == 404:
            return None
        raise
    if not isinstance(body, dict) or body.get("id") is None:
        msg = "n8n answered in an unexpected shape"
        raise N8nError(msg)
    return N8nWorkflow(
        id=str(body["id"]),
        name=str(body.get("name") or body["id"]),
        active=bool(body.get("active")),
    )


async def list_n8n_executions(
    base_url: str,
    api_key: str,
    *,
    workflow_id: str,
    started_after: datetime,
    started_before: datetime,
    max_items: int,
) -> list[N8nExecutionSummary]:
    """A workflow's executions that started inside a time window, without node data.

    The window is also applied here, because the time filter is not in n8n's
    documentation and an instance that ignores it returns everything. Reading stops at
    ``max_items`` executions read, whether or not they are in the window.
    """
    found: list[N8nExecutionSummary] = []
    cursor: str | None = None
    read = 0
    time_filter: dict[str, Any] = {
        "startedAfter": _iso(started_after),
        "startedBefore": _iso(started_before),
    }
    while read < max_items:
        params: dict[str, Any] = {
            "limit": _PAGE_SIZE,
            "workflowId": workflow_id,
            **time_filter,
        }
        if cursor:
            params["cursor"] = cursor
        try:
            body = await _get(base_url, api_key, "/executions", params)
        except N8nError as exc:
            if exc.status_code != 400 or not time_filter:
                raise
            # An n8n that refuses the time filter: read newest first without it. The
            # window is still applied below, and ``max_items`` bounds the reading.
            time_filter = {}
            continue
        items, cursor = _page(body)
        read += len(items)
        for item in items:
            started_at = _timestamp(item.get("startedAt"))
            if item.get("id") is None or started_at is None:
                continue
            if not started_after <= started_at <= started_before:
                continue
            workflow = item.get("workflowId")
            found.append(
                N8nExecutionSummary(
                    id=str(item["id"]),
                    workflow_id=str(workflow) if workflow is not None else None,
                    started_at=started_at,
                    stopped_at=_timestamp(item.get("stoppedAt")),
                )
            )
        if cursor is None or not items:
            break
    return found


async def get_n8n_execution(
    base_url: str, api_key: str, execution_id: str
) -> dict[str, Any]:
    """One execution with every node's data, as n8n returns it."""
    body = await _get(
        base_url,
        api_key,
        f"/executions/{quote(execution_id, safe='')}",
        {"includeData": "true"},
    )
    if not isinstance(body, dict) or body.get("id") is None:
        msg = "n8n answered in an unexpected shape"
        raise N8nError(msg)
    return body
