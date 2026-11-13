import pytest
from connexity_mcp_server.app import build_application
from connexity_mcp_server.config import Settings
from connexity_mcp_server.guides import GUIDES


def _server():
    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )
    return build_application(settings).state.mcp_server


@pytest.mark.asyncio
async def test_server_lists_only_the_workspace_tools() -> None:
    tools = await _server().list_tools()

    assert sorted(tool.name for tool in tools) == [
        "add_agents",
        "connect_voice_platform",
        "create_workspace",
        "get_readiness",
        "list_agents",
        "list_categories",
        "list_issues",
        "list_workspaces",
        "scan_calls",
    ]
    list_agents = next(tool for tool in tools if tool.name == "list_agents")
    assert list_agents.inputSchema["required"] == ["workspace_id"]


def test_server_sends_connect_instructions() -> None:
    instructions = _server().instructions

    assert instructions is not None
    assert "list_workspaces" in instructions
    assert "workspace_id" in instructions


@pytest.mark.asyncio
async def test_every_guide_is_served_as_a_resource() -> None:
    server = _server()

    resources = await server.list_resources()

    assert sorted(str(r.uri) for r in resources) == sorted(
        f"connexity://guides/{name}" for name in GUIDES
    )
    for name in GUIDES:
        contents = list(await server.read_resource(f"connexity://guides/{name}"))
        assert contents[0].content.startswith("# ")
        assert contents[0].mime_type == "text/markdown"


@pytest.mark.asyncio
async def test_tools_say_whether_they_change_anything() -> None:
    tools = {tool.name: tool.annotations for tool in await _server().list_tools()}

    for name in ("list_workspaces", "list_agents", "list_categories", "list_issues", "get_readiness"):
        assert tools[name] is not None
        assert tools[name].readOnlyHint is True
        assert tools[name].openWorldHint is False
    assert tools["create_workspace"] is not None
    assert tools["create_workspace"].readOnlyHint is False
    assert tools["create_workspace"].destructiveHint is False
    assert tools["connect_voice_platform"] is not None
    assert tools["connect_voice_platform"].readOnlyHint is False
    assert tools["connect_voice_platform"].destructiveHint is False
    assert tools["scan_calls"] is not None
    assert tools["scan_calls"].readOnlyHint is False
    assert tools["scan_calls"].destructiveHint is False
    assert tools["scan_calls"].idempotentHint is True
