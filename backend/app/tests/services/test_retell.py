from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.retell import _map_tools_for_retell, deploy_retell_agent


def _response(
    method: str, url: str, *, status_code: int = 200, json=None
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json,
        request=httpx.Request(method, url),
    )


@pytest.mark.asyncio
async def test_deploy_retell_agent_merges_tools_and_preserves_retell_fields() -> None:
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [
            _response(
                "GET",
                "https://api.retellai.com/get-agent/agent_123",
                json={"response_engine": {"llm_id": "llm_123"}},
            ),
            _response(
                "GET",
                "https://api.retellai.com/get-retell-llm/llm_123",
                json={
                    "general_tools": [
                        {
                            "type": "custom",
                            "name": "lookup_customer",
                            "description": "Old lookup description",
                            "url": "https://retell.example.com/old-lookup",
                            "method": "GET",
                            "parameters": {"type": "object", "properties": {}},
                            "speak_during_execution": True,
                        },
                        {
                            "type": "end_call",
                            "name": "end_call",
                            "description": "Old end call description",
                            "speak_during_execution": True,
                        },
                        {
                            "type": "custom",
                            "name": "manual_retell_only",
                            "description": "Keep this manual tool",
                            "url": "https://retell.example.com/manual",
                            "method": "POST",
                        },
                    ]
                },
            ),
        ]
        mock_client.patch.side_effect = [
            _response("PATCH", "https://api.retellai.com/update-retell-llm/llm_123"),
            _response("PATCH", "https://api.retellai.com/update-agent/agent_123"),
        ]
        mock_client.post.return_value = _response(
            "POST",
            "https://api.retellai.com/publish-agent/agent_123",
            json={"version": 9},
        )
        mock_client_cls.return_value = mock_client

        result = await deploy_retell_agent(
            api_key="retell-key",
            retell_agent_id="agent_123",
            system_prompt="You are helpful.",
            agent_model="gpt-4.1",
            agent_temperature=0.2,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_customer",
                        "description": "Fresh lookup description",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_id": {"type": "string"},
                            },
                            "required": ["customer_id"],
                        },
                    },
                    "platform_config": {
                        "implementation": {
                            "type": "http_webhook",
                            "url": "https://connexity.example.com/lookup-customer",
                            "method": "POST",
                        }
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "new_tool",
                        "description": "Brand new tool",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                    "platform_config": {
                        "implementation": {
                            "type": "http_webhook",
                            "url": "https://connexity.example.com/new-tool",
                            "method": "PATCH",
                        }
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "end_call",
                        "description": "End the call when the user's need is resolved.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        },
                    },
                    "platform_config": {
                        "predefined": True,
                        "terminating": True,
                    },
                },
            ],
            version_description="Connexity Agent v9",
        )

    assert result.success is True
    update_llm_payload = mock_client.patch.call_args_list[0].kwargs["json"]
    assert update_llm_payload["general_tools"] == [
        {
            "type": "custom",
            "name": "lookup_customer",
            "description": "Fresh lookup description",
            "url": "https://connexity.example.com/lookup-customer",
            "method": "POST",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                },
                "required": ["customer_id"],
            },
            "speak_during_execution": True,
        },
        {
            "type": "end_call",
            "name": "end_call",
            "description": "End the call when the user's need is resolved.",
            "speak_during_execution": True,
        },
        {
            "type": "custom",
            "name": "manual_retell_only",
            "description": "Keep this manual tool",
            "url": "https://retell.example.com/manual",
            "method": "POST",
        },
        {
            "type": "custom",
            "name": "new_tool",
            "description": "Brand new tool",
            "url": "https://connexity.example.com/new-tool",
            "method": "PATCH",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]


def test_map_tools_for_retell_includes_native_end_call() -> None:
    mapped = _map_tools_for_retell(
        [
            {
                "type": "function",
                "function": {
                    "name": "end_call",
                    "description": "End the call cleanly.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
                "platform_config": {
                    "predefined": True,
                    "terminating": True,
                },
            }
        ]
    )

    assert mapped == [
        {
            "type": "end_call",
            "name": "end_call",
            "description": "End the call cleanly.",
        }
    ]
