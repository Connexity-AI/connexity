"""The MCP contract: what each tool is for, in words a person reads.

The public page `/mcp-docs` is built from `GET /manifest`, which joins this registry
with what the running server really has (each tool's annotations and input schema). A
test fails when a tool has no entry here, an entry names no tool, or an input has no
description, so the page cannot fall behind the tools.

Every change to a tool (added, removed, renamed, new inputs or behaviour) updates its
entry here and describes every input (Dmytro, 2026-11-18, CLAUDE.md rule 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mcp.types import ToolAnnotations

from connexity_mcp_server.guides import GUIDE_URI_PREFIX

Effect = Literal["reads", "writes", "reads_platform", "talks_to_agent"]


@dataclass(frozen=True)
class Group:
    key: str
    name: str
    purpose: str


GROUPS = (
    Group(
        "start",
        "Start and the task list",
        "Pick a workspace, see what is missing, and work the task list in order.",
    ),
    Group(
        "connect",
        "Connect",
        "Link the voice platform, then bring in agents and their calls.",
    ),
    Group(
        "calls_and_issues",
        "Calls and issues",
        "Read calls, see what went wrong, and close issues once they are fixed.",
    ),
    Group(
        "agents_and_spec",
        "Agents and the spec",
        "Write down what each agent must do, and ask you when it is unclear.",
    ),
    Group(
        "testing",
        "Testing",
        "Write scenarios and run them as simulated calls against your agent.",
    ),
)


@dataclass(frozen=True)
class ToolEntry:
    group: str
    # One plain line for a person, not the assistant's instructions.
    line: str
    guide: str
    # The assistant calls it only after the person says yes (Dmytro, 2026-11-18).
    needs_yes: bool = False
    # The assistant calls it only when the person asks for it.
    only_when_asked: bool = False


TOOLS: dict[str, ToolEntry] = {
    # Start and the task list
    "list_workspaces": ToolEntry(
        "start",
        "Lists the workspaces you can reach, one per client, with their score.",
        "workspaces",
    ),
    "create_workspace": ToolEntry(
        "start", "Creates a workspace for a new client.", "workspaces"
    ),
    "get_readiness": ToolEntry(
        "start", "Shows each setup step, whether it is done, and what is next.", "readiness"
    ),
    "get_next_task": ToolEntry(
        "start",
        "Takes the single most important task, with its facts, rules and steps.",
        "getting-started",
    ),
    "list_tasks": ToolEntry(
        "start",
        "Lists every task in order, with what waits on you and who is working on what.",
        "getting-started",
    ),
    "move_task": ToolEntry(
        "start",
        "Moves a task to sit before another in the list.",
        "getting-started",
        only_when_asked=True,
    ),
    # Connect
    "connect_voice_platform": ToolEntry(
        "connect",
        "Links the workspace to your voice platform with your API key.",
        "connect",
    ),
    "add_agents": ToolEntry(
        "connect", "Adds the client's agents, linked to their Retell agents.", "connect"
    ),
    "scan_calls": ToolEntry(
        "connect",
        "Brings the added agents' last 30 days of calls in, and checks each one.",
        "calls",
    ),
    # Calls and issues
    "list_calls": ToolEntry(
        "calls_and_issues",
        "Lists calls, newest first, with their result and what the checks found.",
        "calls",
    ),
    "get_call": ToolEntry(
        "calls_and_issues",
        "One call in full: every turn and tool call in order, and what was found.",
        "calls",
    ),
    "get_dashboard": ToolEntry(
        "calls_and_issues",
        "Where the workspace stands: score, failed calls, latency and every area.",
        "issues",
    ),
    "list_issues": ToolEntry(
        "calls_and_issues",
        "Lists issues, worst first, with how many calls each one touched.",
        "issues",
    ),
    "get_issue": ToolEntry(
        "calls_and_issues",
        "Everything about one issue: the check behind it, its size, versions and history.",
        "issues",
    ),
    "mark_issue_fixed": ToolEntry(
        "calls_and_issues",
        "Marks an issue fixed in a version; it reopens if it happens again.",
        "issues",
    ),
    "archive_issue": ToolEntry(
        "calls_and_issues",
        "Hides an issue nobody will fix.",
        "issues",
        needs_yes=True,
    ),
    "unarchive_issue": ToolEntry(
        "calls_and_issues",
        "Brings an archived issue back.",
        "issues",
        needs_yes=True,
    ),
    "list_categories": ToolEntry(
        "calls_and_issues",
        "Lists the fixed categories every issue and spec rule belongs to.",
        "categories",
    ),
    # Agents and the spec
    "list_agents": ToolEntry(
        "agents_and_spec",
        "Lists the workspace's agents with their calls, spec state and score.",
        "spec",
    ),
    "get_agent": ToolEntry(
        "agents_and_spec",
        "One agent at a glance: live version, calls, latency and its score.",
        "spec",
    ),
    "get_spec": ToolEntry(
        "agents_and_spec",
        "The agent's spec: what it must do, as plain rules with their sources.",
        "spec",
    ),
    "write_spec": ToolEntry(
        "agents_and_spec",
        "Writes the agent's spec as a new version; earlier versions are kept.",
        "spec",
    ),
    "mark_critical_rules": ToolEntry(
        "agents_and_spec",
        "Marks which rules stop a release when they fail.",
        "spec",
    ),
    "raise_clarifications": ToolEntry(
        "agents_and_spec",
        "Asks you about behaviour the spec does not settle.",
        "spec",
    ),
    "list_clarifications": ToolEntry(
        "agents_and_spec",
        "Lists open, answered and parked questions.",
        "spec",
    ),
    "answer_clarifications": ToolEntry(
        "agents_and_spec",
        "Records your answers to open questions.",
        "spec",
        needs_yes=True,
    ),
    # Testing
    "write_scenarios": ToolEntry(
        "testing",
        "Writes scenarios: a caller, their goal and the rules each one tests.",
        "scenarios",
    ),
    "list_scenarios": ToolEntry(
        "testing", "Lists the agent's scenarios, their rules and sets.", "scenarios"
    ),
    "write_scenario_set": ToolEntry(
        "testing", "Groups scenarios into a named set to run together.", "scenarios"
    ),
    "run_scenarios": ToolEntry(
        "testing",
        "Runs scenarios as text calls against your agent, every tool faked.",
        "scenarios",
    ),
    "get_test_runs": ToolEntry(
        "testing",
        "A tested version's results, rule by rule, and each run's simulated calls.",
        "scenarios",
    ),
}


def effect_of(annotations: ToolAnnotations | None) -> Effect:
    """What a tool may do, read from its annotations so it cannot disagree with them:
    read only; reaches out (`openWorldHint`) to run the agent (not idempotent) or to
    read the platform; or writes inside Connexity."""
    if annotations is None:
        return "writes"
    if annotations.readOnlyHint:
        return "reads"
    if annotations.openWorldHint:
        return "reads_platform" if annotations.idempotentHint else "talks_to_agent"
    return "writes"


def guide_uri(name: str) -> str:
    return f"{GUIDE_URI_PREFIX}{name}"
