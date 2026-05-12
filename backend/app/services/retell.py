import logging
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RetellAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = False
    version: int | None = None


class RetellAgentVersion(BaseModel):
    version: int
    version_title: str | None = None
    is_published: bool = False


class RetellDeployResult(BaseModel):
    success: bool
    retell_version_name: str | None = None
    error_message: str | None = None


class RetellCall(BaseModel):
    call_id: str
    agent_id: str | None = None
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    call_status: str | None = None
    transcript_object: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


def _retell_duration_seconds(
    *, start_timestamp: int | None, end_timestamp: int | None
) -> int | None:
    if start_timestamp is None or end_timestamp is None:
        return None
    return (end_timestamp - start_timestamp) // 1000


def _is_finished_retell_call(
    *,
    status: str | None,
    start_timestamp: int | None,
    end_timestamp: int | None,
) -> bool:
    duration_seconds = _retell_duration_seconds(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    if duration_seconds is None or duration_seconds <= 0:
        return False
    normalized_status = (status or "").lower()
    return normalized_status in {"ended", "completed", "finished"}


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


async def list_retell_agent_versions(
    *, api_key: str, retell_agent_id: str
) -> list[RetellAgentVersion]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.retellai.com/get-agent-versions/{retell_agent_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Retell API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Retell API returned an error")

    body = response.json()
    items = body if isinstance(body, list) else body.get("versions", [])

    versions: list[RetellAgentVersion] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_version = item.get("version")
        if raw_version is None:
            continue
        versions.append(
            RetellAgentVersion(
                version=int(raw_version),
                version_title=item.get("version_title"),
                is_published=bool(item.get("is_published", False)),
            )
        )
    return versions


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
        status = item.get("call_status")
        start_timestamp = item.get("start_timestamp")
        end_timestamp = item.get("end_timestamp")
        if not _is_finished_retell_call(
            status=status,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        ):
            continue
        calls.append(
            RetellCall(
                call_id=item.get("call_id", ""),
                agent_id=item.get("agent_id"),
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                call_status=status,
                transcript_object=item.get("transcript_object"),
                raw=item,
            )
        )
    return calls


_RETELL_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _map_tools_for_retell(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Connexity tools to Retell ``general_tools`` (type=custom).

    Only HTTP webhook tools are forwarded — Retell cannot execute Python or
    mock-mode tools, so they're dropped silently. Predefined tools
    (``end_call``, ``transfer_call``) are also skipped: Retell handles them
    natively via its own tool types and would mis-treat them as generic
    custom webhooks if forwarded.
    """
    retell_tools: list[dict[str, Any]] = []
    for tool in tools:
        platform_config = tool.get("platform_config") or {}
        if platform_config.get("predefined"):
            continue
        impl = platform_config.get("implementation") or {}
        if impl.get("type") != "http_webhook":
            continue

        url = impl.get("url") or ""
        if not url:
            continue

        method = str(impl.get("method") or "POST").upper()
        if method not in _RETELL_ALLOWED_METHODS:
            method = "POST"

        func = tool.get("function") or {}
        retell_tool: dict[str, Any] = {
            "type": "custom",
            "name": func.get("name", ""),
            "description": func.get("description", ""),
            "url": url,
            "method": method,
        }
        params = func.get("parameters")
        if isinstance(params, dict) and params:
            retell_tool["parameters"] = params
        retell_tools.append(retell_tool)
    return retell_tools


async def deploy_retell_agent(
    *,
    api_key: str,
    retell_agent_id: str,
    system_prompt: str | None,
    agent_model: str | None,
    agent_temperature: float | None,
    tools: list[dict[str, Any]] | None,
    version_description: str | None,
) -> RetellDeployResult:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        # Step 1: fetch the agent to get llm_id
        try:
            resp = await client.get(
                f"https://api.retellai.com/get-agent/{retell_agent_id}",
                headers=headers,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            return RetellDeployResult(
                success=False,
                error_message=f"Failed to reach Retell API: {exc}",
            )

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            return RetellDeployResult(
                success=False,
                error_message=f"Retell get-agent returned {resp.status_code}: {detail}",
            )

        agent_data = resp.json()
        llm_id: str | None = (
            agent_data.get("response_engine", {}).get("llm_id")
            if isinstance(agent_data, dict)
            else None
        )
        if not llm_id:
            return RetellDeployResult(
                success=False,
                error_message="Retell agent has no associated LLM (response_engine.llm_id missing)",
            )

        # Step 2: patch the LLM with agent version data
        llm_payload: dict[str, Any] = {}
        if system_prompt is not None:
            llm_payload["general_prompt"] = system_prompt
        if agent_model is not None:
            llm_payload["model"] = agent_model
        if agent_temperature is not None:
            llm_payload["model_temperature"] = agent_temperature
        if tools:
            llm_payload["general_tools"] = _map_tools_for_retell(tools)

        logger.info(
            "Retell deploy payload prepared for update-retell-llm: retell_agent_id=%s llm_id=%s payload=%s",
            retell_agent_id,
            llm_id,
            llm_payload,
        )

        try:
            resp = await client.patch(
                f"https://api.retellai.com/update-retell-llm/{llm_id}",
                headers=headers,
                json=llm_payload,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            return RetellDeployResult(
                success=False,
                error_message=f"Failed to reach Retell API: {exc}",
            )

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            return RetellDeployResult(
                success=False,
                error_message=f"Retell update-retell-llm returned {resp.status_code}: {detail}",
            )

        logger.info(
            "Retell update-retell-llm succeeded: retell_agent_id=%s llm_id=%s status_code=%s",
            retell_agent_id,
            llm_id,
            resp.status_code,
        )

        # Step 3: patch the agent with version description
        try:
            resp = await client.patch(
                f"https://api.retellai.com/update-agent/{retell_agent_id}",
                headers=headers,
                json={"version_description": version_description},
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            return RetellDeployResult(
                success=False,
                error_message=f"Failed to reach Retell API: {exc}",
            )

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            return RetellDeployResult(
                success=False,
                error_message=f"Retell update-agent returned {resp.status_code}: {detail}",
            )

        # Step 4: publish the agent
        try:
            resp = await client.post(
                f"https://api.retellai.com/publish-agent/{retell_agent_id}",
                headers=headers,
                timeout=30.0,
            )
        except httpx.HTTPError as exc:
            return RetellDeployResult(
                success=False,
                error_message=f"Failed to reach Retell API: {exc}",
            )

        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            return RetellDeployResult(
                success=False,
                error_message=f"Retell publish-agent returned {resp.status_code}: {detail}",
            )

        try:
            body = resp.json()
        except ValueError:
            body = {}

    version_title = body.get("version_title") if isinstance(body, dict) else None
    version_number = body.get("version") if isinstance(body, dict) else None
    if version_title:
        retell_version_name: str | None = str(version_title)
    elif version_number is not None:
        retell_version_name = f"v{version_number}"
    else:
        retell_version_name = None

    return RetellDeployResult(success=True, retell_version_name=retell_version_name)
