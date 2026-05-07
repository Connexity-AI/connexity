from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.environment import Environment


class WebhookDeployResult(BaseModel):
    success: bool
    error_message: str | None = None


def _extract_tool_calls(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not tools:
        return []

    tool_calls: list[dict[str, Any]] = []
    for tool in tools:
        function_block = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function_block, dict):
            continue

        entry: dict[str, Any] = {
            "name": function_block.get("name"),
            "description": function_block.get("description"),
            "parameters": function_block.get("parameters"),
        }

        platform_config = (
            tool.get("platform_config") if isinstance(tool, dict) else None
        )
        implementation = (
            platform_config.get("implementation")
            if isinstance(platform_config, dict)
            else None
        )
        if isinstance(implementation, dict):
            method = implementation.get("method")
            url = implementation.get("url")
            headers = implementation.get("headers")
            if isinstance(method, str):
                entry["method"] = method.upper()
            if isinstance(url, str):
                entry["url"] = url
            if isinstance(headers, dict):
                entry["headers"] = headers

        tool_calls.append(entry)
    return tool_calls


def build_webhook_payload(
    *,
    agent: Agent,
    environment: Environment,
    version_row: AgentVersion,
    deployed_by: str | None,
    eval_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": "agent.deploy",
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "version": version_row.version,
            "version_name": version_row.version_name,
            "version_description": version_row.version_description,
            "prompt": version_row.system_prompt,
            "llm": {
                "provider": version_row.agent_provider,
                "model": version_row.agent_model,
                "temperature": version_row.agent_temperature,
            },
            "tool_calls": _extract_tool_calls(version_row.tools),
        },
        "environment": environment.name,
        "platform": "webhook",
        "deployed_at": datetime.now(UTC).isoformat(),
        "deployed_by": deployed_by,
        "event_type": "agent.deployed",
    }
    if eval_gate is not None:
        payload["eval"] = eval_gate
    return payload


async def deliver_webhook_deployment(
    *,
    endpoint_url: str,
    payload: dict[str, Any],
) -> WebhookDeployResult:
    encoded_payload = jsonable_encoder(payload)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint_url,
                json=encoded_payload,
                headers={"Content-Type": "application/json"},
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        return WebhookDeployResult(
            success=False,
            error_message=f"Webhook request failed: {exc}",
        )

    if 200 <= response.status_code < 300:
        return WebhookDeployResult(success=True)

    body_preview = response.text.strip()
    if len(body_preview) > 500:
        body_preview = f"{body_preview[:500]}..."
    message = (
        f"Webhook responded with {response.status_code}. "
        f"Response body: {body_preview or '<empty>'}"
    )
    return WebhookDeployResult(success=False, error_message=message)
