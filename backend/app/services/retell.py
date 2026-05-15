import copy
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.models.imported_platform_config import ImportedPlatformConfig

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


class RetellChatMessage(BaseModel):
    role: str
    content: str | None = None
    message_id: str | None = None
    created_timestamp: int | None = None
    tool_call_id: str | None = None
    name: str | None = None
    arguments: str | None = None
    raw: dict[str, Any] | None = None


class RetellCreateChatResult(BaseModel):
    success: bool
    chat_id: str | None = None
    chat_status: str | None = None
    version: int | None = None
    messages: list[RetellChatMessage] = Field(default_factory=list)
    latency_ms: int | None = None
    error_message: str | None = None


class RetellChatCompletionResult(BaseModel):
    success: bool
    messages: list[RetellChatMessage] = Field(default_factory=list)
    latency_ms: int | None = None
    error_message: str | None = None


class RetellCreateChatAgentResult(BaseModel):
    success: bool
    agent_id: str | None = None
    error_message: str | None = None


class RetellCall(BaseModel):
    call_id: str
    agent_id: str | None = None
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    call_status: str | None = None
    transcript_object: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


class RetellBatchTest(BaseModel):
    test_case_batch_job_id: str
    status: str
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    total_count: int = 0
    raw: dict[str, Any] | None = None


class RetellTestCaseJob(BaseModel):
    test_case_job_id: str
    status: str
    test_case_definition_id: str
    transcript_snapshot: dict[str, Any] | None = None
    result_explanation: str | None = None
    raw: dict[str, Any] | None = None


def _retell_response_detail(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    return str(detail)


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
                params={"is_latest": "true"},
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


async def get_retell_agent_response_engine(
    *, api_key: str, retell_agent_id: str
) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.retellai.com/get-agent/{retell_agent_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Retell get-agent returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    body = response.json()
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=502, detail="Retell get-agent returned invalid JSON"
        )

    response_engine = body.get("response_engine")
    if not isinstance(response_engine, dict):
        raise HTTPException(
            status_code=422,
            detail="Retell agent is missing response_engine for simulation testing",
        )

    engine_type = response_engine.get("type")
    if engine_type == "retell-llm" and response_engine.get("llm_id"):
        out: dict[str, Any] = {
            "type": "retell-llm",
            "llm_id": str(response_engine["llm_id"]),
        }
        if response_engine.get("version") is not None:
            out["version"] = response_engine["version"]
        return out

    if engine_type == "conversation-flow" and response_engine.get(
        "conversation_flow_id"
    ):
        out = {
            "type": "conversation-flow",
            "conversation_flow_id": str(response_engine["conversation_flow_id"]),
        }
        if response_engine.get("version") is not None:
            out["version"] = response_engine["version"]
        return out

    raise HTTPException(
        status_code=422,
        detail="Retell agent response_engine is not supported for simulation testing",
    )


async def create_retell_test_case_definition(
    *,
    api_key: str,
    response_engine: dict[str, Any],
    name: str,
    user_prompt: str,
    metrics: list[str],
    dynamic_variables: dict[str, str],
) -> str:
    body: dict[str, Any] = {
        "name": name,
        "response_engine": response_engine,
        "user_prompt": user_prompt,
        "metrics": metrics,
        "dynamic_variables": dynamic_variables,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/create-test-case-definition",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                "Retell create-test-case-definition returned "
                f"{response.status_code}: {_retell_response_detail(response)}"
            ),
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail="Retell create-test-case-definition returned invalid JSON",
        )
    test_case_definition_id = payload.get("test_case_definition_id")
    if not test_case_definition_id:
        raise HTTPException(
            status_code=502,
            detail="Retell create-test-case-definition response did not contain test_case_definition_id",
        )
    return str(test_case_definition_id)


async def create_retell_batch_test(
    *,
    api_key: str,
    response_engine: dict[str, Any],
    test_case_definition_ids: list[str],
) -> str:
    body = {
        "response_engine": response_engine,
        "test_case_definition_ids": test_case_definition_ids,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/create-batch-test",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Retell create-batch-test returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502, detail="Retell create-batch-test returned invalid JSON"
        )
    batch_id = payload.get("test_case_batch_job_id")
    if not batch_id:
        raise HTTPException(
            status_code=502,
            detail="Retell create-batch-test response did not contain test_case_batch_job_id",
        )
    return str(batch_id)


async def get_retell_batch_test(*, api_key: str, batch_test_id: str) -> RetellBatchTest:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.retellai.com/get-batch-test/{batch_test_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Retell get-batch-test returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502, detail="Retell get-batch-test returned invalid JSON"
        )
    return RetellBatchTest(
        test_case_batch_job_id=str(
            payload.get("test_case_batch_job_id") or batch_test_id
        ),
        status=str(payload.get("status") or ""),
        pass_count=int(payload.get("pass_count") or 0),
        fail_count=int(payload.get("fail_count") or 0),
        error_count=int(payload.get("error_count") or 0),
        total_count=int(payload.get("total_count") or 0),
        raw=payload,
    )


async def list_retell_test_runs(
    *, api_key: str, batch_test_id: str
) -> list[RetellTestCaseJob]:
    items: list[dict[str, Any]] = []
    pagination_key: str | None = None

    while True:
        params: dict[str, Any] = {"limit": 1000}
        if pagination_key:
            params["pagination_key"] = pagination_key
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.retellai.com/v2/list-test-runs/{batch_test_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    params=params,
                    timeout=10.0,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"Failed to reach Retell API: {exc}"
            ) from exc

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Retell list-test-runs returned {response.status_code}: "
                    f"{_retell_response_detail(response)}"
                ),
            )

        payload = response.json()
        if isinstance(payload, list):
            raw_items = payload
            has_more = False
            next_key = None
        elif isinstance(payload, dict):
            raw_items = payload.get("items") or []
            has_more = bool(payload.get("has_more"))
            next_key = payload.get("pagination_key")
        else:
            raise HTTPException(
                status_code=502, detail="Retell list-test-runs returned invalid JSON"
            )

        items.extend(item for item in raw_items if isinstance(item, dict))
        if not has_more or not isinstance(next_key, str) or not next_key:
            break
        pagination_key = next_key

    jobs: list[RetellTestCaseJob] = []
    for item in items:
        transcript_snapshot = item.get("transcript_snapshot")
        if not isinstance(transcript_snapshot, dict):
            transcript_snapshot = None
        jobs.append(
            RetellTestCaseJob(
                test_case_job_id=str(item.get("test_case_job_id") or ""),
                status=str(item.get("status") or ""),
                test_case_definition_id=str(item.get("test_case_definition_id") or ""),
                transcript_snapshot=transcript_snapshot,
                result_explanation=(
                    str(item["result_explanation"])
                    if item.get("result_explanation") is not None
                    else None
                ),
                raw=item,
            )
        )
    return jobs


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


def _map_tool_for_retell(tool: dict[str, Any]) -> dict[str, Any] | None:
    """Map one Connexity tool to a Retell ``general_tools`` entry."""
    platform_config = tool.get("platform_config") or {}
    func = tool.get("function") or {}
    name = str(func.get("name") or "").strip()
    if not name:
        return None

    if platform_config.get("predefined"):
        if name == "end_call":
            return {
                "type": "end_call",
                "name": name,
                "description": func.get("description", ""),
            }
        return None

    impl = platform_config.get("implementation") or {}
    if impl.get("type") != "http_webhook":
        return None

    url = impl.get("url") or ""
    if not url:
        return None

    method = str(impl.get("method") or "POST").upper()
    if method not in _RETELL_ALLOWED_METHODS:
        method = "POST"

    retell_tool: dict[str, Any] = {
        "type": "custom",
        "name": name,
        "description": func.get("description", ""),
        "url": url,
        "method": method,
    }
    params = func.get("parameters")
    if isinstance(params, dict) and params:
        retell_tool["parameters"] = params
    return retell_tool


def _map_tools_for_retell(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Connexity tools to Retell ``general_tools`` entries.

    Only HTTP webhook tools are forwarded — Retell cannot execute Python or
    mock-mode tools, so they're dropped silently. Predefined tools
    (``end_call``, ``transfer_call``) are also skipped: Retell handles them
    natively via its own tool types and would mis-treat them as generic
    custom webhooks if forwarded.
    """
    retell_tools: list[dict[str, Any]] = []
    for tool in tools:
        mapped = _map_tool_for_retell(tool)
        if mapped is None:
            continue
        retell_tools.append(mapped)
    return retell_tools


def _retell_tool_name(raw: Any) -> str | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    return name or None


def _merge_retell_general_tools(
    *,
    existing_general_tools: Any,
    tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge Connexity tools into existing Retell tools by tool name.

    Retell stores tool-specific flags that Connexity does not model. When a
    Retell tool already exists, preserve those extra fields and only overwrite
    the Connexity-owned fields from the latest deploy payload.
    """
    desired_tools = _map_tools_for_retell(tools)
    desired_by_name: dict[str, dict[str, Any]] = {}
    for tool in desired_tools:
        name = _retell_tool_name(tool)
        if name:
            desired_by_name[name] = tool

    merged_tools: list[dict[str, Any]] = []
    consumed_names: set[str] = set()

    if isinstance(existing_general_tools, list):
        for raw in existing_general_tools:
            if not isinstance(raw, dict):
                continue
            name = _retell_tool_name(raw)
            if not name or name not in desired_by_name:
                merged_tools.append(copy.deepcopy(raw))
                continue

            merged = copy.deepcopy(raw)
            merged.update(copy.deepcopy(desired_by_name[name]))
            merged_tools.append(merged)
            consumed_names.add(name)

    for tool in desired_tools:
        name = _retell_tool_name(tool)
        if name and name in consumed_names:
            continue
        merged_tools.append(copy.deepcopy(tool))

    return merged_tools


def _map_retell_general_tools_to_openai(
    general_tools: list[Any],
) -> list[dict[str, Any]]:
    """Best-effort reverse of ``_map_tools_for_retell`` for imports."""
    out: list[dict[str, Any]] = []
    for raw in general_tools:
        if not isinstance(raw, dict):
            continue
        if raw.get("type") != "custom":
            continue
        url = raw.get("url") or ""
        if not url:
            continue
        method = str(raw.get("method") or "POST").upper()
        if method not in _RETELL_ALLOWED_METHODS:
            method = "POST"
        name = str(raw.get("name") or "")
        desc = str(raw.get("description") or "")
        params = raw.get("parameters")
        if not isinstance(params, dict):
            params = {}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": params,
                },
                "platform_config": {
                    "implementation": {
                        "type": "http_webhook",
                        "url": url,
                        "method": method,
                    },
                },
            }
        )
    return out


async def import_retell_agent_config(
    *, api_key: str, retell_agent_id: str
) -> ImportedPlatformConfig:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.retellai.com/get-agent/{retell_agent_id}",
                headers=headers,
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"Retell get-agent failed with status {resp.status_code}",
        )

    agent_data = resp.json()
    if not isinstance(agent_data, dict):
        raise HTTPException(
            status_code=422, detail="Retell get-agent returned invalid JSON"
        )

    llm_id = (agent_data.get("response_engine") or {}).get("llm_id")
    if not llm_id:
        raise HTTPException(
            status_code=422,
            detail="Retell agent has no associated LLM (response_engine.llm_id missing)",
        )

    try:
        async with httpx.AsyncClient() as client:
            llm_resp = await client.get(
                f"https://api.retellai.com/get-retell-llm/{llm_id}",
                headers=headers,
                timeout=30.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if llm_resp.status_code >= 400:
        raise HTTPException(
            status_code=422,
            detail=f"Retell get-retell-llm failed with status {llm_resp.status_code}",
        )

    llm_body = llm_resp.json()
    if not isinstance(llm_body, dict):
        raise HTTPException(
            status_code=422, detail="Retell LLM response was not an object"
        )

    system_prompt = (llm_body.get("general_prompt") or "").strip()
    agent_model = (llm_body.get("model") or "").strip()
    if not system_prompt or not agent_model:
        raise HTTPException(
            status_code=422,
            detail="Retell LLM is missing general_prompt or model — cannot import",
        )

    raw_temp = llm_body.get("model_temperature")
    agent_temperature: float | None
    if raw_temp is None:
        agent_temperature = None
    else:
        try:
            agent_temperature = float(raw_temp)
        except (TypeError, ValueError):
            agent_temperature = None

    general_tools = llm_body.get("general_tools")
    tools: list[dict[str, Any]] | None = None
    if isinstance(general_tools, list) and general_tools:
        tools = _map_retell_general_tools_to_openai(general_tools)

    return ImportedPlatformConfig(
        system_prompt=system_prompt,
        agent_model=agent_model,
        agent_provider=None,
        agent_temperature=agent_temperature,
        tools=tools,
    )


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
        if tools is not None:
            try:
                llm_resp = await client.get(
                    f"https://api.retellai.com/get-retell-llm/{llm_id}",
                    headers=headers,
                    timeout=30.0,
                )
            except httpx.HTTPError as exc:
                return RetellDeployResult(
                    success=False,
                    error_message=f"Failed to reach Retell API: {exc}",
                )

            if llm_resp.status_code >= 400:
                try:
                    detail = llm_resp.json()
                except ValueError:
                    detail = llm_resp.text
                return RetellDeployResult(
                    success=False,
                    error_message=(
                        "Retell get-retell-llm returned "
                        f"{llm_resp.status_code}: {detail}"
                    ),
                )

            try:
                llm_body = llm_resp.json()
            except ValueError as exc:
                return RetellDeployResult(
                    success=False,
                    error_message=f"Retell get-retell-llm returned invalid JSON: {exc}",
                )

            existing_general_tools = (
                llm_body.get("general_tools") if isinstance(llm_body, dict) else None
            )
            llm_payload["general_tools"] = _merge_retell_general_tools(
                existing_general_tools=existing_general_tools,
                tools=tools,
            )

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


# ── Web call initiation (eval engine) ─────────────────────────────


def _parse_retell_chat_messages(raw_messages: Any) -> list[RetellChatMessage]:
    if not isinstance(raw_messages, list):
        return []

    out: list[RetellChatMessage] = []
    for item in raw_messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        if not role:
            continue
        out.append(
            RetellChatMessage(
                role=role,
                content=(
                    str(item["content"]) if item.get("content") is not None else None
                ),
                message_id=(
                    str(item["message_id"])
                    if item.get("message_id") is not None
                    else None
                ),
                created_timestamp=(
                    int(item["created_timestamp"])
                    if item.get("created_timestamp") is not None
                    else None
                ),
                tool_call_id=(
                    str(item["tool_call_id"])
                    if item.get("tool_call_id") is not None
                    else None
                ),
                name=str(item["name"]) if item.get("name") is not None else None,
                arguments=(
                    str(item["arguments"])
                    if item.get("arguments") is not None
                    else None
                ),
                raw=item,
            )
        )
    return out


async def get_retell_chat_agent(api_key: str, agent_id: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.retellai.com/get-chat-agent/{agent_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Retell get-chat-agent returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502, detail="Retell get-chat-agent returned invalid JSON"
        )
    return payload


async def create_retell_chat(
    *,
    api_key: str,
    retell_agent_id: str,
    agent_version: int | None = None,
    metadata: dict[str, Any] | None = None,
    dynamic_variables: dict[str, str] | None = None,
) -> RetellCreateChatResult:
    body: dict[str, Any] = {"agent_id": retell_agent_id}
    if agent_version is not None:
        body["agent_version"] = agent_version
    if metadata:
        body["metadata"] = metadata
    if dynamic_variables:
        body["retell_llm_dynamic_variables"] = dynamic_variables

    started = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/create-chat",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        return RetellCreateChatResult(
            success=False, error_message=f"Network error: {exc}"
        )
    latency_ms = int((time.perf_counter() - started) * 1000)

    if response.status_code >= 400:
        return RetellCreateChatResult(
            success=False,
            latency_ms=latency_ms,
            error_message=(
                f"Retell create-chat returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    try:
        payload = response.json()
    except ValueError as exc:
        return RetellCreateChatResult(
            success=False,
            latency_ms=latency_ms,
            error_message=f"Malformed Retell response: {exc}",
        )

    if not isinstance(payload, dict):
        return RetellCreateChatResult(
            success=False,
            latency_ms=latency_ms,
            error_message="Retell create-chat returned invalid JSON",
        )

    chat_id = payload.get("chat_id")
    if not chat_id:
        return RetellCreateChatResult(
            success=False,
            latency_ms=latency_ms,
            error_message="Retell create-chat response did not contain a chat_id",
        )

    return RetellCreateChatResult(
        success=True,
        chat_id=str(chat_id),
        chat_status=(
            str(payload["chat_status"])
            if payload.get("chat_status") is not None
            else None
        ),
        version=(
            int(payload["version"]) if payload.get("version") is not None else None
        ),
        messages=_parse_retell_chat_messages(payload.get("message_with_tool_calls")),
        latency_ms=latency_ms,
    )


def is_retell_invalid_agent_channel_error(detail: str) -> bool:
    return "invalid agent channel" in detail.strip().lower()


async def create_retell_chat_agent(
    *,
    api_key: str,
    response_engine: dict[str, Any],
    agent_name: str | None = None,
) -> RetellCreateChatAgentResult:
    # Retell rejects response-engine versions greater than 0 when creating a
    # brand-new chat agent. Reuse the same engine id/type and let Retell attach
    # the new chat agent to the engine's current draft.
    chat_response_engine = copy.deepcopy(response_engine)
    chat_response_engine.pop("version", None)

    body: dict[str, Any] = {"response_engine": chat_response_engine}
    if agent_name is not None:
        body["agent_name"] = agent_name

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/create-chat-agent",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        return RetellCreateChatAgentResult(
            success=False, error_message=f"Network error: {exc}"
        )

    if response.status_code >= 400:
        return RetellCreateChatAgentResult(
            success=False,
            error_message=(
                f"Retell create-chat-agent returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    try:
        payload = response.json()
    except ValueError as exc:
        return RetellCreateChatAgentResult(
            success=False,
            error_message=f"Malformed Retell response: {exc}",
        )

    if not isinstance(payload, dict):
        return RetellCreateChatAgentResult(
            success=False,
            error_message="Retell create-chat-agent returned invalid JSON",
        )

    chat_agent_id = payload.get("agent_id")
    if not chat_agent_id:
        return RetellCreateChatAgentResult(
            success=False,
            error_message="Retell create-chat-agent response did not contain an agent_id",
        )

    return RetellCreateChatAgentResult(success=True, agent_id=str(chat_agent_id))


async def create_retell_chat_agent_from_existing_agent(
    *,
    api_key: str,
    retell_agent_id: str,
    agent_name: str | None = None,
) -> RetellCreateChatAgentResult:
    try:
        response_engine = await get_retell_agent_response_engine(
            api_key=api_key,
            retell_agent_id=retell_agent_id,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return RetellCreateChatAgentResult(success=False, error_message=detail)

    return await create_retell_chat_agent(
        api_key=api_key,
        response_engine=response_engine,
        agent_name=agent_name,
    )


async def create_retell_chat_completion(
    *,
    api_key: str,
    chat_id: str,
    content: str,
) -> RetellChatCompletionResult:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/create-chat-completion",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"chat_id": chat_id, "content": content},
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        return RetellChatCompletionResult(
            success=False, error_message=f"Network error: {exc}"
        )
    latency_ms = int((time.perf_counter() - started) * 1000)

    if response.status_code >= 400:
        return RetellChatCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message=(
                f"Retell create-chat-completion returned {response.status_code}: "
                f"{_retell_response_detail(response)}"
            ),
        )

    try:
        payload = response.json()
    except ValueError as exc:
        return RetellChatCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message=f"Malformed Retell response: {exc}",
        )

    if not isinstance(payload, dict):
        return RetellChatCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message="Retell create-chat-completion returned invalid JSON",
        )

    return RetellChatCompletionResult(
        success=True,
        messages=_parse_retell_chat_messages(payload.get("messages")),
        latency_ms=latency_ms,
    )


async def end_retell_chat(*, api_key: str, chat_id: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.retellai.com/end-chat/{chat_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError:
        return False

    return response.status_code in {200, 204, 404}


async def delete_retell_chat_agent(*, api_key: str, agent_id: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.retellai.com/delete-chat-agent/{agent_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError:
        return False

    return response.status_code in {200, 204, 404}


class RetellCreateWebCallResult(BaseModel):
    success: bool
    call_id: str | None = None
    error_message: str | None = None


async def create_retell_web_call(
    *,
    api_key: str,
    retell_agent_id: str,
    dynamic_variables: dict[str, Any] | None = None,
) -> RetellCreateWebCallResult:
    """Create a Retell web call for the given agent. Returns the new ``call_id``."""
    body: dict[str, Any] = {"agent_id": retell_agent_id}
    if dynamic_variables:
        body["retell_llm_dynamic_variables"] = dynamic_variables

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.retellai.com/v2/create-web-call",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        return RetellCreateWebCallResult(
            success=False, error_message=f"Network error: {exc}"
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return RetellCreateWebCallResult(
            success=False,
            error_message=f"Retell create-web-call returned {response.status_code}: {detail}",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        return RetellCreateWebCallResult(
            success=False,
            error_message=f"Malformed Retell response: {exc}",
        )

    call_id = payload.get("call_id") if isinstance(payload, dict) else None
    if not call_id:
        return RetellCreateWebCallResult(
            success=False,
            error_message="Retell response did not contain a call_id",
        )
    return RetellCreateWebCallResult(success=True, call_id=str(call_id))


async def get_retell_call(api_key: str, call_id: str) -> RetellCall | None:
    """Fetch a single Retell call by id (used for polling). Returns ``None`` on 404."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.retellai.com/v2/get-call/{call_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Retell get-call returned {response.status_code}",
        )

    item = response.json()
    if not isinstance(item, dict):
        return None
    return RetellCall(
        call_id=item.get("call_id", call_id),
        agent_id=item.get("agent_id"),
        start_timestamp=item.get("start_timestamp"),
        end_timestamp=item.get("end_timestamp"),
        call_status=item.get("call_status"),
        transcript_object=item.get("transcript_object"),
        raw=item,
    )
