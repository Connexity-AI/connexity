"""The MCP contract: every tool has a registry entry and every input a description,
and `GET /manifest` serves it publicly for the /mcp-docs page."""

import pytest
from fastapi.testclient import TestClient

from connexity_mcp_server.app import build_application
from connexity_mcp_server.config import Settings
from connexity_mcp_server.contract import TOOLS
from connexity_mcp_server.guides import GUIDES
from connexity_mcp_server.manifest import build_manifest


def _app():
    settings = Settings(
        mcp_public_base_url="https://mcp.example.com",
        mcp_oauth_issuer_url="https://tenant.example.com",
    )
    return build_application(settings)


async def _manifest():
    app = _app()
    return await build_manifest(app.state.mcp_server, server_url=None)


def _tools(manifest):
    return {tool.name: tool for group in manifest.groups for tool in group.tools}


@pytest.mark.asyncio
async def test_every_tool_has_a_registry_entry_and_no_entry_is_stale() -> None:
    # build_manifest raises when the registry and the tools disagree.
    manifest = await _manifest()
    assert set(_tools(manifest)) == set(TOOLS)
    assert manifest.tool_count == len(TOOLS)


@pytest.mark.asyncio
async def test_every_tool_input_has_a_description() -> None:
    manifest = await _manifest()
    missing = [
        f"{tool.name}.{field.name}"
        for tool in _tools(manifest).values()
        for field in tool.inputs
        if not (field.description or "").strip()
    ]
    assert missing == [], f"inputs without a description: {missing}"


@pytest.mark.asyncio
async def test_only_three_tools_need_the_persons_yes() -> None:
    tools = _tools(await _manifest())
    assert sorted(name for name, tool in tools.items() if tool.needs_yes) == [
        "answer_clarifications",
        "archive_issue",
        "unarchive_issue",
    ]
    assert [name for name, tool in tools.items() if tool.only_when_asked] == [
        "move_task"
    ]


@pytest.mark.asyncio
async def test_effects_come_from_the_annotations() -> None:
    tools = _tools(await _manifest())
    assert tools["list_calls"].effect == "reads"
    assert tools["write_scenario_set"].effect == "writes"
    assert tools["mark_issue_fixed"].effect == "writes"
    assert tools["scan_calls"].effect == "reads_platform"
    assert tools["connect_voice_platform"].effect == "reads_platform"
    assert tools["run_scenarios"].effect == "talks_to_agent"


@pytest.mark.asyncio
async def test_inputs_carry_type_and_whether_required() -> None:
    tools = _tools(await _manifest())
    inputs = {field.name: field for field in tools["archive_issue"].inputs}
    assert inputs["issue_id"].required and inputs["issue_id"].type == "string"
    assert not inputs["duration"].required
    assert inputs["duration"].type == "one of until_spike | forever"
    limit = {field.name: field for field in tools["list_calls"].inputs}["limit"]
    assert limit.type == "integer" and not limit.required


def test_the_manifest_is_public_and_has_no_workspace_data() -> None:
    client = TestClient(_app())
    response = client.get("/manifest")

    assert response.status_code == 200
    body = response.json()
    assert body["server_url"] == "https://mcp.example.com/mcp"
    assert body["guide_count"] == len(GUIDES)
    assert [g["uri"] for g in body["guides"]] == [
        f"connexity://guides/{name}" for name in GUIDES
    ]
    assert all(g["text"].startswith("#") for g in body["guides"])
    assert [a["key"] for a in body["answer_shape"]] == [
        "data",
        "rules",
        "next_steps",
        "guide",
    ]
    assert [g["key"] for g in body["groups"]] == [
        "start",
        "connect",
        "calls_and_issues",
        "agents_and_spec",
        "testing",
    ]
    assert "workspace" not in {k for k in body if k != "groups"}
