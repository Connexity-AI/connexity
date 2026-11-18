"""`GET /manifest`: the MCP contract the public `/mcp-docs` page is built from.

Joins the contract registry (`contract.py`) with what the running server really has:
each tool's annotations and input schema, and the guides it serves. Public and read
only: no workspace data, no auth.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from connexity_mcp_server.contract import GROUPS, TOOLS, effect_of, guide_uri
from connexity_mcp_server.guides import GUIDE_URI_PREFIX, GUIDES, read_guide

ANSWER_SHAPE = [
    ("data", "The facts: records, ids and what the checks found."),
    ("rules", "What the assistant must follow while it works on this."),
    ("next_steps", "Numbered, each naming the tool to call next."),
    ("guide", "A link to the guide that explains this part."),
]

EFFECTS = [
    ("reads", "Reads", "Reads Connexity only."),
    ("writes", "Writes", "Writes inside Connexity."),
    ("reads_platform", "Reads your platform", "Reaches Retell to read agents and calls."),
    ("talks_to_agent", "Talks to your agent", "Simulated calls only, every tool faked."),
    ("decision", "Your decision", "The assistant calls it only after you say yes."),
]


class ManifestInput(BaseModel):
    name: str
    type: str
    required: bool
    description: str | None = None


class ManifestTool(BaseModel):
    name: str
    effect: str
    needs_yes: bool
    only_when_asked: bool
    line: str
    guide: str
    inputs: list[ManifestInput]


class ManifestGroup(BaseModel):
    key: str
    name: str
    purpose: str
    tools: list[ManifestTool]


class ManifestText(BaseModel):
    key: str
    text: str
    label: str | None = None


class ManifestGuide(BaseModel):
    uri: str
    name: str
    title: str
    # The guide's markdown, as the server serves it to the assistant.
    text: str


class Manifest(BaseModel):
    version: str
    server_url: str | None
    tool_count: int
    guide_count: int
    answer_shape: list[ManifestText]
    effects: list[ManifestText]
    groups: list[ManifestGroup]
    guides: list[ManifestGuide]


class ContractError(Exception):
    """A tool and the contract registry disagree."""


def _server_version() -> str:
    try:
        return version("connexity-mcp-server")
    except PackageNotFoundError:
        return "unknown"


def _type(schema: dict[str, Any], defs: dict[str, Any]) -> str:
    """A short type name for a person: string, integer, string[], one of a | b."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return "object" if name in defs else name
    if "enum" in schema:
        return "one of " + " | ".join(str(value) for value in schema["enum"])
    options = schema.get("anyOf") or schema.get("oneOf")
    if options:
        kinds = [_type(option, defs) for option in options if option.get("type") != "null"]
        return " or ".join(dict.fromkeys(kinds)) or "null"
    kind = schema.get("type", "object")
    if kind == "array":
        return f"{_type(schema.get('items', {}), defs)}[]"
    return str(kind)


def tool_inputs(input_schema: dict[str, Any]) -> list[ManifestInput]:
    properties: dict[str, Any] = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    defs = input_schema.get("$defs", {})
    return [
        ManifestInput(
            name=name,
            type=_type(schema, defs),
            required=name in required,
            description=schema.get("description"),
        )
        for name, schema in properties.items()
    ]


async def build_manifest(mcp_server: FastMCP, *, server_url: str | None) -> Manifest:
    """The contract as the running server has it.

    Raises:
        ContractError: a tool has no entry in the registry, or an entry names no tool.
    """
    tools = {tool.name: tool for tool in await mcp_server.list_tools()}
    missing = sorted(set(tools) - set(TOOLS))
    unknown = sorted(set(TOOLS) - set(tools))
    if missing or unknown:
        msg = f"contract registry out of date: missing {missing}, unknown {unknown}"
        raise ContractError(msg)
    groups = []
    for group in GROUPS:
        entries = [
            (name, entry) for name, entry in TOOLS.items() if entry.group == group.key
        ]
        groups.append(
            ManifestGroup(
                key=group.key,
                name=group.name,
                purpose=group.purpose,
                tools=[
                    ManifestTool(
                        name=name,
                        effect=effect_of(tools[name].annotations),
                        needs_yes=entry.needs_yes,
                        only_when_asked=entry.only_when_asked,
                        line=entry.line,
                        guide=guide_uri(entry.guide),
                        inputs=tool_inputs(tools[name].inputSchema),
                    )
                    for name, entry in entries
                ],
            )
        )
    return Manifest(
        version=_server_version(),
        server_url=server_url,
        tool_count=len(tools),
        guide_count=len(GUIDES),
        answer_shape=[ManifestText(key=k, text=t) for k, t in ANSWER_SHAPE],
        effects=[ManifestText(key=k, label=label, text=t) for k, label, t in EFFECTS],
        groups=groups,
        guides=[
            ManifestGuide(
                uri=f"{GUIDE_URI_PREFIX}{name}",
                name=name,
                title=title,
                text=read_guide(name),
            )
            for name, title in GUIDES.items()
        ],
    )
