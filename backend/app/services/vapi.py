from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel


class VapiAssistantSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = True
    version: int | None = None


class VapiDeployResult(BaseModel):
    success: bool
    vapi_version_name: str | None = None
    error_message: str | None = None


class VapiCall(BaseModel):
    call_id: str
    assistant_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    status: str | None = None
    transcript: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


_VAPI_API_BASE_URL = "https://api.vapi.ai"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def test_vapi_connection(api_key: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_VAPI_API_BASE_URL}/assistant",
                headers=_headers(api_key),
                params={"limit": 1},
                timeout=10.0,
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def list_vapi_assistants(api_key: str) -> list[VapiAssistantSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_VAPI_API_BASE_URL}/assistant",
                headers=_headers(api_key),
                params={"limit": 100},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to reach Vapi API") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Vapi API returned an error")

    payload = response.json()
    items = payload if isinstance(payload, list) else payload.get("data", [])
    assistants: list[VapiAssistantSummary] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        assistant_id = item.get("id")
        if not assistant_id:
            continue
        assistants.append(
            VapiAssistantSummary(
                agent_id=str(assistant_id),
                agent_name=item.get("name"),
            )
        )
    return assistants


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _map_tools_for_vapi(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    vapi_tools: list[dict[str, Any]] = []
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

        func = tool.get("function") or {}
        function_payload: dict[str, Any] = {
            "name": func.get("name", ""),
            "description": func.get("description", ""),
        }
        parameters = func.get("parameters")
        if isinstance(parameters, dict) and parameters:
            function_payload["parameters"] = parameters

        vapi_tools.append(
            {
                "type": "function",
                "function": function_payload,
                "server": {
                    "url": url,
                },
            }
        )
    return vapi_tools


async def deploy_vapi_assistant(
    *,
    api_key: str,
    assistant_id: str,
    system_prompt: str | None,
    agent_model: str | None,
    agent_provider: str | None,
    agent_temperature: float | None,
    tools: list[dict[str, Any]] | None,
    version_description: str | None,
) -> VapiDeployResult:
    model_payload: dict[str, Any] = {}
    if agent_model is not None:
        model_payload["model"] = agent_model
    if agent_provider is not None:
        model_payload["provider"] = agent_provider
    if agent_temperature is not None:
        model_payload["temperature"] = agent_temperature
    if system_prompt is not None:
        model_payload["messages"] = [{"role": "system", "content": system_prompt}]
    if tools:
        model_payload["tools"] = _map_tools_for_vapi(tools)

    payload: dict[str, Any] = {}
    if model_payload:
        payload["model"] = model_payload

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{_VAPI_API_BASE_URL}/assistant/{assistant_id}",
                headers=_headers(api_key),
                json=payload,
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        return VapiDeployResult(
            success=False,
            error_message=f"Failed to reach Vapi API: {exc}",
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return VapiDeployResult(
            success=False,
            error_message=f"Vapi update assistant returned {response.status_code}: {detail}",
        )

    return VapiDeployResult(success=True, vapi_version_name=version_description)


async def list_vapi_calls(
    api_key: str,
    *,
    assistant_id: str,
    start_after: datetime | None = None,
    limit: int = 100,
) -> list[VapiCall]:
    params: dict[str, Any] = {"assistantId": assistant_id, "limit": limit}
    if start_after is not None:
        params["createdAtGt"] = start_after.isoformat()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_VAPI_API_BASE_URL}/call",
                headers=_headers(api_key),
                params=params,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Failed to reach Vapi API") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Vapi API returned an error")

    payload = response.json()
    items = payload if isinstance(payload, list) else payload.get("data", [])
    calls: list[VapiCall] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        call_id = item.get("id")
        if not call_id:
            continue
        started_at = _parse_datetime(item.get("startedAt")) or _parse_datetime(
            item.get("createdAt")
        )
        ended_at = _parse_datetime(item.get("endedAt")) or _parse_datetime(
            item.get("ended_at")
        )
        transcript = item.get("messages")
        if not isinstance(transcript, list):
            transcript = None
        calls.append(
            VapiCall(
                call_id=str(call_id),
                assistant_id=item.get("assistantId"),
                created_at=_parse_datetime(item.get("createdAt")),
                started_at=started_at,
                ended_at=ended_at,
                status=item.get("status"),
                transcript=transcript,
                raw=item,
            )
        )
    calls.sort(key=lambda call: call.started_at or datetime.now(UTC))
    return calls
