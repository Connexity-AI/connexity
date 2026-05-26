from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

TELNYX_API_BASE = "https://api.telnyx.com/v2"


class TelnyxAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None


class TelnyxAgentVersion(BaseModel):
    version: int
    is_published: bool = False


class TelnyxDeployResult(BaseModel):
    success: bool
    error_message: str | None = None


class TelnyxCall(BaseModel):
    call_id: str
    agent_id: str | None = None
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    call_status: str | None = None
    transcript_object: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


async def test_telnyx_connection(api_key: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELNYX_API_BASE}/call_control_applications",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"page[size]": 1},
                timeout=10.0,
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def list_telnyx_agents(api_key: str) -> list[TelnyxAgentSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELNYX_API_BASE}/call_control_applications",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Telnyx API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Telnyx API returned an error")

    agents: list[TelnyxAgentSummary] = []
    for item in response.json().get("data", []):
        agents.append(
            TelnyxAgentSummary(
                agent_id=item.get("id", ""),
                agent_name=item.get("application_name"),
            )
        )
    return agents


async def list_telnyx_agent_versions(
    *, api_key: str, telnyx_agent_id: str
) -> list[TelnyxAgentVersion]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELNYX_API_BASE}/call_control_applications/{telnyx_agent_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Telnyx API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Telnyx API returned an error")

    return [TelnyxAgentVersion(version=1, is_published=True)]


async def list_telnyx_calls(
    api_key: str,
    *,
    agent_id: str,
    start_after: datetime | None = None,
    limit: int = 100,
) -> list[TelnyxCall]:
    """Fetch voice detail records for a given Telnyx agent via GET /detail_records.

    If ``start_after`` is provided, only calls with ``start_timestamp`` strictly
    greater than it are returned (used by the refresh flow to skip already-stored
    rows).
    """
    params: dict[str, Any] = {
        "filter[record_type]": "voice",
        "sort": "-start_date",
        "page[size]": min(limit, 100),
    }
    if start_after is not None:
        params["filter[start_date][gt]"] = start_after.isoformat()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TELNYX_API_BASE}/detail_records",
                headers={"Authorization": f"Bearer {api_key}"},
                params=params,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Telnyx API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Telnyx API returned an error")

    payload = response.json()
    items = payload.get("data", []) if isinstance(payload, dict) else []

    calls: list[TelnyxCall] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record_type = item.get("record_type", "")
        if record_type != "voice":
            continue
        if item.get("connection_id") != agent_id:
            continue

        start_date = item.get("start_date")
        end_date = item.get("end_date")

        # Convert ISO date strings to epoch milliseconds
        start_epoch = None
        end_epoch = None
        if start_date:
            try:
                dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                start_epoch = int(dt.timestamp() * 1000)
            except (ValueError, TypeError):
                pass
        if end_date:
            try:
                dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                end_epoch = int(dt.timestamp() * 1000)
            except (ValueError, TypeError):
                pass

        calls.append(
            TelnyxCall(
                call_id=item.get("id", ""),
                agent_id=item.get("connection_id"),
                start_timestamp=start_epoch,
                end_timestamp=end_epoch,
                call_status=item.get("status"),
                transcript_object=item.get("transcript"),
                raw=item,
            )
        )
    return calls


async def deploy_telnyx_agent(
    *,
    api_key: str,
    telnyx_agent_id: str,
    system_prompt: str | None,
    agent_model: str | None,
    agent_temperature: float | None,
    tools: list[dict[str, Any]] | None,
    version_description: str | None,
) -> TelnyxDeployResult:
    """Placeholder for future API-driven Telnyx agent configuration.

    Telnyx Call Control Applications are currently configured through the
    Telnyx Mission Control Portal or API-driven provisioning (not yet
    available for agent configuration). When Telnyx exposes programmatic
    agent configuration, this function will implement the deploy pipeline.

    Makes zero API calls.
    """
    del (
        api_key,
        telnyx_agent_id,
        system_prompt,
        agent_model,
        agent_temperature,
        tools,
        version_description,
    )
    return TelnyxDeployResult(success=True)
