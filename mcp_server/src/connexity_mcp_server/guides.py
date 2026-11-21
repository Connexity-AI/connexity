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
    "connect": "Connect an assistant to Connexity",
    "categories": "Categories",
    "issues": "Issues",
    "calls": "Calls",
    "spec": "Writing an agent's spec",
    "scenarios": "Writing and running scenarios",
    "usage": "Usage and list prices",
    "feedback": "Reporting a problem in Connexity",
}
# Written and reviewed, but not served until the tools they name exist.
NOT_YET_SERVED: set[str] = set()

INSTRUCTIONS = (
    "Connexity records and checks every call of a team's conversational AI agents. "
    "You do the operational work through these tools; people approve where a decision "
    "is theirs. Start with `list_workspaces`: every other tool needs a `workspace_id`. "
    "Then call `get_next_task`, at the start of a session and after each task: "
    "Connexity sorts the work and hands you the single most important task, with its "
    "steps. Do not pick your own order. "
    "Behaviour an agent's spec does not settle is a question for the person: raise it "
    "with `raise_clarifications`, never decide it. "
    "Every answer has `data`, the `rules` that apply (follow them), numbered "
    "`next_steps` and a `guide`; read the guide at that URI when you need more. "
    "Connexity never edits, deploys or calls an agent. "
    "When a Connexity tool fails, contradicts another answer, or cannot do what the "
    "work needs, report it with `send_feedback` after one retry, without asking the "
    "person, then tell them in a sentence."
)


def read_guide(name: str) -> str:
    return (
        resources.files("connexity_mcp_server")
        .joinpath(f"guides/{name}.md")
        .read_text(encoding="utf-8")
    )
