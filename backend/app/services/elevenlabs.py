import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from app.models.imported_platform_config import ImportedPlatformConfig

logger = logging.getLogger(__name__)

_ELEVENLABS_API_BASE_URL = "https://api.elevenlabs.io"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }


class ElevenLabsAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = True
    version: int | None = None


class ElevenLabsVoiceSummary(BaseModel):
    voice_id: str
    name: str | None = None
    preview_url: str | None = None


class ElevenLabsDeployResult(BaseModel):
    success: bool
    elevenlabs_version_id: str | None = None
    error_message: str | None = None


class ElevenLabsConversationSummary(BaseModel):
    conversation_id: str
    agent_id: str
    start_time_unix_secs: int
    call_duration_secs: int
    status: str | None = None
    transcript_summary: str | None = None
    raw: dict[str, Any] | None = None


class ElevenLabsConversationDetails(BaseModel):
    conversation_id: str
    agent_id: str
    start_time_unix_secs: int
    call_duration_secs: int
    status: str | None = None
    transcript: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


async def check_elevenlabs_connection(api_key: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_ELEVENLABS_API_BASE_URL}/v1/user",
                headers=_headers(api_key),
                timeout=10.0,
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def _extract_list_payload(payload: Any, *, items_key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if not isinstance(payload, dict):
        return []
    raw_items = payload.get(items_key)
    if isinstance(raw_items, list):
        return [p for p in raw_items if isinstance(p, dict)]
    data_items = payload.get("data")
    if isinstance(data_items, list):
        return [p for p in data_items if isinstance(p, dict)]
    return []


def list_elevenlabs_voices(api_key: str) -> list[ElevenLabsVoiceSummary]:
    """List TTS voices for catalog UI (sync; does not raise HTTPException)."""
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{_ELEVENLABS_API_BASE_URL}/v1/voices",
                headers=_headers(api_key),
            )
        if response.status_code != 200:
            logger.warning(
                "ElevenLabs voices API returned %s",
                response.status_code,
            )
            return []
        payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Failed to reach ElevenLabs voices API: %s", exc)
        return []

    items = _extract_list_payload(payload, items_key="voices")
    voices: list[ElevenLabsVoiceSummary] = []
    for item in items:
        voice_id = item.get("voice_id") or item.get("id")
        if not voice_id:
            continue
        preview = item.get("preview_url")
        voices.append(
            ElevenLabsVoiceSummary(
                voice_id=str(voice_id),
                name=item.get("name") if isinstance(item.get("name"), str) else None,
                preview_url=preview if isinstance(preview, str) else None,
            )
        )
    return voices


async def list_elevenlabs_agents(api_key: str) -> list[ElevenLabsAgentSummary]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_ELEVENLABS_API_BASE_URL}/v1/convai/agents",
                headers=_headers(api_key),
                params={"page_size": 100},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach ElevenLabs API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="ElevenLabs API returned an error")

    payload = response.json()
    items = _extract_list_payload(payload, items_key="agents")
    agents: list[ElevenLabsAgentSummary] = []
    for item in items:
        agent_id = item.get("agent_id") or item.get("id")
        if not agent_id:
            continue
        agents.append(
            ElevenLabsAgentSummary(
                agent_id=str(agent_id),
                agent_name=item.get("name"),
                is_published=bool(item.get("is_published", True)),
            )
        )
    return agents


async def import_elevenlabs_agent_config(
    *, api_key: str, agent_id: str
) -> ImportedPlatformConfig:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_ELEVENLABS_API_BASE_URL}/v1/convai/agents/{agent_id}",
                headers=_headers(api_key),
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach ElevenLabs API: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"ElevenLabs get agent failed with status {response.status_code}",
        )

    body = response.json()
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=422, detail="ElevenLabs agent response was not an object"
        )

    conv = body.get("conversation_config")
    if not isinstance(conv, dict):
        conv = {}
    agent_cfg = conv.get("agent")
    if not isinstance(agent_cfg, dict):
        agent_cfg = {}
    prompt_cfg = agent_cfg.get("prompt")
    if not isinstance(prompt_cfg, dict):
        prompt_cfg = {}

    system_prompt = (prompt_cfg.get("prompt") or "").strip()
    llm_raw = prompt_cfg.get("llm")
    agent_model = ""
    if isinstance(llm_raw, str):
        agent_model = _coerce_elevenlabs_llm(llm_raw) or ""
    elif llm_raw is not None:
        agent_model = _coerce_elevenlabs_llm(str(llm_raw)) or ""

    raw_temp = prompt_cfg.get("temperature")
    agent_temperature: float | None
    if raw_temp is None:
        agent_temperature = None
    else:
        try:
            agent_temperature = float(raw_temp)
        except (TypeError, ValueError):
            agent_temperature = None

    if not system_prompt or not agent_model:
        raise HTTPException(
            status_code=422,
            detail="ElevenLabs agent is missing prompt text or llm — cannot import",
        )

    return ImportedPlatformConfig(
        system_prompt=system_prompt,
        agent_model=agent_model,
        agent_provider=None,
        agent_temperature=agent_temperature,
        tools=None,
    )


def _coerce_elevenlabs_llm(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _map_tools_for_elevenlabs(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapped_tools: list[dict[str, Any]] = []
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
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            method = "POST"

        func = tool.get("function") or {}
        parameters = func.get("parameters")

        tool_config: dict[str, Any] = {
            "type": "webhook",
            "name": func.get("name", ""),
            "description": func.get("description", ""),
            "api_schema": {
                "url": url,
                "method": method,
            },
        }
        if isinstance(parameters, dict) and parameters:
            tool_config["api_schema"]["request_body_schema"] = parameters
        mapped_tools.append(tool_config)
    return mapped_tools


def _extract_elevenlabs_tool_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("tool_id", "id"):
        value = payload.get(key)
        if value:
            return str(value)
    nested = payload.get("tool")
    if isinstance(nested, dict):
        for key in ("tool_id", "id"):
            value = nested.get(key)
            if value:
                return str(value)
    return None


async def deploy_elevenlabs_agent(
    *,
    api_key: str,
    agent_id: str,
    system_prompt: str | None,
    agent_model: str | None,
    agent_temperature: float | None,
    tools: list[dict[str, Any]] | None,
    version_description: str | None,
) -> ElevenLabsDeployResult:
    mapped_tools = _map_tools_for_elevenlabs(tools or [])
    created_tool_ids: list[str] = []

    if mapped_tools:
        try:
            async with httpx.AsyncClient() as client:
                for tool_config in mapped_tools:
                    response = await client.post(
                        f"{_ELEVENLABS_API_BASE_URL}/v1/convai/tools",
                        headers=_headers(api_key),
                        json={"tool_config": tool_config},
                        timeout=30.0,
                    )
                    if response.status_code >= 400:
                        try:
                            detail = response.json()
                        except ValueError:
                            detail = response.text
                        return ElevenLabsDeployResult(
                            success=False,
                            error_message=f"ElevenLabs create tool returned {response.status_code}: {detail}",
                        )
                    try:
                        body = response.json()
                    except ValueError:
                        body = None
                    tool_id = _extract_elevenlabs_tool_id(body)
                    if tool_id is None:
                        return ElevenLabsDeployResult(
                            success=False,
                            error_message="ElevenLabs create tool returned no tool id",
                        )
                    created_tool_ids.append(tool_id)
        except httpx.HTTPError as exc:
            return ElevenLabsDeployResult(
                success=False,
                error_message=f"Failed to reach ElevenLabs API: {exc}",
            )

    llm = _coerce_elevenlabs_llm(agent_model)
    payload: dict[str, Any] = {
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": system_prompt or "",
                    **({"llm": llm} if llm is not None else {}),
                    **(
                        {"temperature": agent_temperature}
                        if agent_temperature is not None
                        else {}
                    ),
                    **({"tool_ids": created_tool_ids} if tools else {}),
                }
            }
        }
    }
    if version_description is not None:
        payload["version_description"] = version_description

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{_ELEVENLABS_API_BASE_URL}/v1/convai/agents/{agent_id}",
                headers=_headers(api_key),
                json=payload,
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        return ElevenLabsDeployResult(
            success=False,
            error_message=f"Failed to reach ElevenLabs API: {exc}",
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return ElevenLabsDeployResult(
            success=False,
            error_message=f"ElevenLabs update agent returned {response.status_code}: {detail}",
        )

    body: Any
    try:
        body = response.json()
    except ValueError:
        body = None

    version_id: str | None = None
    if isinstance(body, dict):
        version_id_value = body.get("version_id") or body.get("versionId")
        if version_id_value is not None:
            version_id = str(version_id_value)

    return ElevenLabsDeployResult(success=True, elevenlabs_version_id=version_id)


def _unix_seconds(dt: datetime) -> int:
    value = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return int(value.timestamp())


async def list_elevenlabs_conversations(
    api_key: str,
    *,
    agent_id: str,
    start_after: datetime | None = None,
    page_size: int = 100,
    max_pages: int = 20,
) -> list[ElevenLabsConversationSummary]:
    conversations: list[ElevenLabsConversationSummary] = []
    cursor: str | None = None

    for _ in range(max_pages):
        params: dict[str, Any] = {
            "agent_id": agent_id,
            "page_size": page_size,
            "summary_mode": "exclude",
            "exclude_statuses": ["initiated", "in-progress", "processing"],
        }
        if cursor is not None:
            params["cursor"] = cursor
        if start_after is not None:
            params["call_start_after_unix"] = _unix_seconds(start_after) + 1

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{_ELEVENLABS_API_BASE_URL}/v1/convai/conversations",
                    headers=_headers(api_key),
                    params=params,
                    timeout=15.0,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail="Failed to reach ElevenLabs API"
            ) from exc

        if response.status_code != 200:
            raise HTTPException(
                status_code=502, detail="ElevenLabs API returned an error"
            )

        payload = response.json()
        if not isinstance(payload, dict):
            break
        items = payload.get("conversations")
        if not isinstance(items, list) or not items:
            break

        for item in items:
            if not isinstance(item, dict):
                continue
            conversation_id = item.get("conversation_id")
            item_agent_id = item.get("agent_id")
            start_time_unix_secs = item.get("start_time_unix_secs")
            call_duration_secs = item.get("call_duration_secs")
            if (
                not conversation_id
                or not item_agent_id
                or start_time_unix_secs is None
                or call_duration_secs is None
            ):
                continue
            conversations.append(
                ElevenLabsConversationSummary(
                    conversation_id=str(conversation_id),
                    agent_id=str(item_agent_id),
                    start_time_unix_secs=int(start_time_unix_secs),
                    call_duration_secs=int(call_duration_secs),
                    status=item.get("status"),
                    transcript_summary=item.get("transcript_summary"),
                    raw=item,
                )
            )

        cursor_value = payload.get("next_cursor")
        has_more = payload.get("has_more")
        cursor = str(cursor_value) if cursor_value else None
        if not cursor or not has_more:
            break

    return conversations


async def get_elevenlabs_conversation(
    api_key: str,
    *,
    conversation_id: str,
) -> ElevenLabsConversationDetails:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{_ELEVENLABS_API_BASE_URL}/v1/convai/conversations/{conversation_id}",
                headers=_headers(api_key),
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach ElevenLabs API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="ElevenLabs API returned an error")

    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502, detail="ElevenLabs API returned invalid JSON"
        )

    transcript = payload.get("transcript")
    transcript_value: list[dict[str, Any]] | None = (
        [t for t in transcript if isinstance(t, dict)]
        if isinstance(transcript, list)
        else None
    )

    metadata_raw = payload.get("metadata")
    metadata: dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    start_time_unix_secs = metadata.get("start_time_unix_secs") or payload.get(
        "start_time_unix_secs"
    )
    call_duration_secs = metadata.get("call_duration_secs") or payload.get(
        "call_duration_secs"
    )

    return ElevenLabsConversationDetails(
        conversation_id=str(payload.get("conversation_id") or conversation_id),
        agent_id=str(payload.get("agent_id") or ""),
        start_time_unix_secs=int(start_time_unix_secs)
        if start_time_unix_secs is not None
        else 0,
        call_duration_secs=int(call_duration_secs)
        if call_duration_secs is not None
        else 0,
        status=payload.get("status"),
        transcript=transcript_value,
        raw=payload,
    )
