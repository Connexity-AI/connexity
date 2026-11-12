"""Connect instructions and the guides served as MCP resources.

Each guide is a markdown file in `guides/`, served at `connexity://guides/<name>`, the
link the backend puts in every answer's `guide` field.
"""

from __future__ import annotations

from importlib import resources

GUIDE_URI_PREFIX = "connexity://guides/"
GUIDES = {
    "getting-started": "Getting started with Connexity",
    "workspaces": "Workspaces",
    "readiness": "Readiness",
}

INSTRUCTIONS = (
    "Connexity records and checks every call of a team's conversational AI agents. "
    "You do the operational work through these tools; people approve where a decision "
    "is theirs. Start with `list_workspaces`: every other tool needs a `workspace_id`. "
    "Then call `get_readiness` to see what is left to set up in that workspace. "
    "Every answer has `data`, the `rules` that apply (follow them), numbered "
    "`next_steps` and a `guide`; read the guide at that URI when you need more. "
    "Connexity never edits, deploys or calls an agent."
)


def read_guide(name: str) -> str:
    return (
        resources.files("connexity_mcp_server")
        .joinpath(f"guides/{name}.md")
        .read_text(encoding="utf-8")
    )
