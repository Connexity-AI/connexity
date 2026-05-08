from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.vapi import deploy_vapi_assistant


@pytest.mark.asyncio
async def test_deploy_vapi_assistant_sends_model_provider() -> None:
    response = httpx.Response(
        status_code=200,
        request=httpx.Request("PATCH", "https://api.vapi.ai/assistant/assistant-id"),
    )
    with patch("app.services.vapi.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.patch.return_value = response
        mock_client_cls.return_value = mock_client

        result = await deploy_vapi_assistant(
            api_key="vapi-key",
            assistant_id="assistant-id",
            system_prompt="You are helpful.",
            agent_model="gpt-4o-mini",
            agent_provider="openai",
            agent_temperature=0.2,
            tools=None,
            version_description="Connexity Agent v1",
        )

    assert result.success is True
    patched_json = mock_client.patch.call_args.kwargs["json"]
    assert patched_json["model"]["model"] == "gpt-4o-mini"
    assert patched_json["model"]["provider"] == "openai"


@pytest.mark.asyncio
async def test_deploy_vapi_assistant_omits_tool_server_method() -> None:
    response = httpx.Response(
        status_code=200,
        request=httpx.Request("PATCH", "https://api.vapi.ai/assistant/assistant-id"),
    )
    with patch("app.services.vapi.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.patch.return_value = response
        mock_client_cls.return_value = mock_client

        result = await deploy_vapi_assistant(
            api_key="vapi-key",
            assistant_id="assistant-id",
            system_prompt=None,
            agent_model="gpt-4o-mini",
            agent_provider="openai",
            agent_temperature=None,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "create_service_ticket",
                        "description": "Creates a service ticket.",
                        "parameters": {
                            "type": "object",
                            "required": [],
                            "properties": {},
                        },
                    },
                    "platform_config": {
                        "implementation": {
                            "type": "http_webhook",
                            "url": "https://example.com/tools/create-service-ticket",
                            "method": "POST",
                        },
                    },
                },
            ],
            version_description="Connexity Agent v1",
        )

    assert result.success is True
    patched_json = mock_client.patch.call_args.kwargs["json"]
    server = patched_json["model"]["tools"][0]["server"]
    assert server == {"url": "https://example.com/tools/create-service-ticket"}
