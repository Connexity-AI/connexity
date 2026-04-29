from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel


class RetellAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = False
    version: int | None = None


class RetellCall(BaseModel):
    call_id: str
    agent_id: str | None = None
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    call_status: str | None = None
    transcript_object: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


async def test_retell_connection(api_key: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.retellai.com/list-agents",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def list_retell_agents(api_key: str) -> list[RetellAgentSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.retellai.com/list-agents",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Retell API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Retell API returned an error")

    agents: list[RetellAgentSummary] = []
    for item in response.json():
        agents.append(
            RetellAgentSummary(
                agent_id=item.get("agent_id", ""),
                agent_name=item.get("agent_name"),
                is_published=bool(item.get("is_published", False)),
                version=item.get("version"),
            )
        )
    return agents


async def list_retell_calls(
    api_key: str,
    *,
    agent_id: str,
    start_after: datetime | None = None,
    limit: int = 100,
) -> list[RetellCall]:
    """Fetch calls for a given Retell agent via POST /v2/list-calls.

    If ``start_after`` is provided, only calls with ``start_timestamp`` strictly
    greater than it are returned (used by the refresh flow to skip already-stored
    rows).
    """
    filter_criteria: dict[str, Any] = {"agent_id": [agent_id]}
    if start_after is not None:
        # Retell timestamps are epoch milliseconds; use exclusive lower threshold
        filter_criteria["start_timestamp"] = {
            "lower_threshold": int(start_after.timestamp() * 1000) + 1,
        }

    body = {
        "filter_criteria": filter_criteria,
        "limit": limit,
        "sort_order": "ascending",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/v2/list-calls",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Retell API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Retell API returned an error")

    payload = response.json()
    # Retell may return the list directly or wrap it in {"calls": [...]} depending
    # on version; handle both defensively.
    items = payload if isinstance(payload, list) else payload.get("calls", [])

    calls: list[RetellCall] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        calls.append(
            RetellCall(
                call_id=item.get("call_id", ""),
                agent_id=item.get("agent_id"),
                start_timestamp=item.get("start_timestamp"),
                end_timestamp=item.get("end_timestamp"),
                call_status=item.get("call_status"),
                transcript_object=item.get("transcript_object"),
                raw=item,
            )
        )
    return calls
