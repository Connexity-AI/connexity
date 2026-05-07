from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from app.models.agent import Agent
from app.models.agent_version import AgentVersion
from app.models.environment import Environment
from app.models.webhook_payload import (
    WebhookAgent,
    WebhookDeployPayload,
    WebhookEval,
    WebhookLlm,
    WebhookToolCall,
    WebhookToolCallParameter,
)


class WebhookDeployResult(BaseModel):
    success: bool
    error_message: str | None = None


def _extract_tool_parameters(
    parameters_block: dict[str, Any] | None,
) -> list[WebhookToolCallParameter]:
    if not isinstance(parameters_block, dict):
        return []

    raw_required = parameters_block.get("required")
    required_names: set[str] = set()
    if isinstance(raw_required, list):
        required_names = {item for item in raw_required if isinstance(item, str)}

    raw_properties = parameters_block.get("properties")
    if not isinstance(raw_properties, dict):
        return []

    parameters: list[WebhookToolCallParameter] = []
    for param_name, param_schema in raw_properties.items():
        if not isinstance(param_name, str):
            continue
        if not isinstance(param_schema, dict):
            continue

        raw_type = param_schema.get("type")
        param_type = raw_type if isinstance(raw_type, str) else None

        raw_description = param_schema.get("description")
        description = raw_description if isinstance(raw_description, str) else None

        parameters.append(
            WebhookToolCallParameter(
                name=param_name,
                type=param_type,
                required=param_name in required_names,
                description=description,
            )
        )

    return parameters


def _extract_tool_calls(tools: list[dict[str, Any]] | None) -> list[WebhookToolCall]:
    if not tools:
        return []

    tool_calls: list[WebhookToolCall] = []
    for tool in tools:
        function_block = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function_block, dict):
            continue

        raw_name = function_block.get("name")
        name = raw_name if isinstance(raw_name, str) else None
        raw_description = function_block.get("description")
        description = raw_description if isinstance(raw_description, str) else None
        parameters = _extract_tool_parameters(function_block.get("parameters"))

        method: str | None = None
        url: str | None = None
        headers: dict[str, str] = {}

        platform_config = (
            tool.get("platform_config") if isinstance(tool, dict) else None
        )
        implementation = (
            platform_config.get("implementation")
            if isinstance(platform_config, dict)
            else None
        )
        if isinstance(implementation, dict):
            raw_method = implementation.get("method")
            if isinstance(raw_method, str):
                method = raw_method.upper()
            raw_url = implementation.get("url")
            if isinstance(raw_url, str):
                url = raw_url
            raw_headers = implementation.get("headers")
            if isinstance(raw_headers, dict):
                headers = {
                    str(key): str(value)
                    for key, value in raw_headers.items()
                    if isinstance(key, str | int | float | bool)
                    and isinstance(value, str | int | float | bool)
                }

        tool_calls.append(
            WebhookToolCall(
                name=name,
                description=description,
                method=method,
                url=url,
                headers=headers,
                parameters=parameters,
            )
        )
    return tool_calls


def build_webhook_payload(
    *,
    agent: Agent,
    environment: Environment,
    version_row: AgentVersion,
    deployed_by: str | None,
    eval_gate: WebhookEval,
) -> WebhookDeployPayload:
    return WebhookDeployPayload(
        event="agent.deploy",
        agent=WebhookAgent(
            id=str(agent.id),
            name=agent.name,
            version=version_row.version,
            version_name=version_row.version_name,
            version_description=version_row.version_description,
            prompt=version_row.system_prompt,
            llm=WebhookLlm(
                provider=version_row.agent_provider,
                model=version_row.agent_model,
                temperature=version_row.agent_temperature,
            ),
            tool_calls=_extract_tool_calls(version_row.tools),
        ),
        environment=environment.name,
        deployed_at=datetime.now(UTC),
        deployed_by=deployed_by,
        eval=eval_gate,
    )


async def deliver_webhook_deployment(
    *,
    endpoint_url: str,
    payload: WebhookDeployPayload | dict[str, Any],
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
