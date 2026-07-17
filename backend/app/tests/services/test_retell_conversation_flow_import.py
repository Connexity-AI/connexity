from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.retell import (
    CONVERSATION_FLOW_AGENT_MODEL,
    import_retell_agent_config,
)


def _response(
    method: str, url: str, *, status_code: int = 200, json=None
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=json,
        request=httpx.Request(method, url),
    )


@pytest.mark.asyncio
async def test_import_conversation_flow_agent() -> None:
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [
            _response(
                "GET",
                "https://api.retellai.com/get-agent/agent_flow",
                json={
                    "response_engine": {
                        "type": "conversation-flow",
                        "conversation_flow_id": "flow_1",
                        "version": 3,
                    }
                },
            ),
            _response(
                "GET",
                "https://api.retellai.com/get-conversation-flow/flow_1",
                json={
                    "global_prompt": "Be helpful.",
                    "nodes": [
                        {
                            "id": "n1",
                            "type": "conversation",
                            "instruction": {"type": "prompt", "text": "Greet."},
                        }
                    ],
                    "edges": [],
                    "tools": [
                        {
                            "type": "custom",
                            "name": "lookup",
                            "description": "Lookup",
                            "url": "https://x.example.com/lookup",
                            "method": "POST",
                            "parameters": {"type": "object", "properties": {}},
                        }
                    ],
                },
            ),
        ]
        mock_client_cls.return_value = mock_client

        result = await import_retell_agent_config(
            api_key="key", retell_agent_id="agent_flow"
        )

    assert result.agent_model == CONVERSATION_FLOW_AGENT_MODEL
    assert "Be helpful." in result.system_prompt
    assert result.tools is not None and result.tools[0]["function"]["name"] == "lookup"
    assert result.agent_metadata is not None
    assert result.agent_metadata["conversation_flow_id"] == "flow_1"
    assert result.agent_metadata["conversation_flow_version"] == 3
    assert result.agent_metadata["conversation_flow_nodes"]


@pytest.mark.asyncio
async def test_import_retell_llm_agent_still_works() -> None:
    with patch("app.services.retell.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [
            _response(
                "GET",
                "https://api.retellai.com/get-agent/agent_llm",
                json={"response_engine": {"type": "retell-llm", "llm_id": "llm_1"}},
            ),
            _response(
                "GET",
                "https://api.retellai.com/get-retell-llm/llm_1",
                json={
                    "general_prompt": "You are helpful.",
                    "model": "gpt-4o",
                    "model_temperature": 0.4,
                },
            ),
        ]
        mock_client_cls.return_value = mock_client

        result = await import_retell_agent_config(
            api_key="key", retell_agent_id="agent_llm"
        )

    assert result.system_prompt == "You are helpful."
    assert result.agent_model == "gpt-4o"
    assert result.agent_temperature == 0.4
    assert result.agent_metadata is None
