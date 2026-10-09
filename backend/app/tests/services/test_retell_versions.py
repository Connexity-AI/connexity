"""Reading a Retell agent at a version. Every response here is invented."""

import httpx
import pytest
import respx

from app.services.retell_versions import (
    RetellReadError,
    get_retell_agent_at_version,
    get_retell_conversation_flow_at_version,
    get_retell_llm_at_version,
)

AGENT = "https://api.retellai.com/get-agent/agent_invented_1"
LLM = "https://api.retellai.com/get-retell-llm/llm_invented_1"
FLOW = "https://api.retellai.com/get-conversation-flow/flow_invented_1"


@respx.mock
async def test_reads_ask_for_the_version_with_the_key() -> None:
    agent = respx.get(AGENT).mock(
        return_value=httpx.Response(200, json={"agent_id": "a"})
    )
    llm = respx.get(LLM).mock(return_value=httpx.Response(200, json={"llm_id": "l"}))
    flow = respx.get(FLOW).mock(
        return_value=httpx.Response(200, json={"conversation_flow_id": "f"})
    )
    assert await get_retell_agent_at_version("key_invented", "agent_invented_1", "7")
    assert await get_retell_llm_at_version("key_invented", "llm_invented_1", 7)
    assert await get_retell_conversation_flow_at_version(
        "key_invented", "flow_invented_1", None
    )
    assert agent.calls.last.request.url.params["version"] == "7"
    assert agent.calls.last.request.headers["Authorization"] == "Bearer key_invented"
    assert llm.calls.last.request.url.params["version"] == "7"
    assert "version" not in flow.calls.last.request.url.params


@respx.mock
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, json={"message": "no such version"}),
        httpx.Response(500, text="boom"),
        httpx.Response(200, text=""),
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={}),
    ],
)
async def test_an_error_empty_or_malformed_answer_fails_cleanly(
    response: httpx.Response,
) -> None:
    respx.get(AGENT).mock(return_value=response)
    with pytest.raises(RetellReadError):
        await get_retell_agent_at_version("key_invented", "agent_invented_1", "7")


@respx.mock
async def test_a_timeout_fails_cleanly() -> None:
    respx.get(AGENT).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(RetellReadError, match="Could not reach"):
        await get_retell_agent_at_version("key_invented", "agent_invented_1", "7")
