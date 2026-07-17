"""Resolve the behavioral context test-case generation reads for an agent version.

Requirements are the source of truth: when a version has an extracted requirement
snapshot, generation reads a rendered list of those requirements instead of the
raw system prompt. This unifies single-prompt and conversation-flow agents behind
one input. When no requirements exist yet (legacy agents, extraction still
running, or extraction failure), we fall back to the version's ``system_prompt``
so generation never regresses.
"""

from sqlmodel import Session

from app.crud import requirement as requirement_crud
from app.models import AgentVersion


def render_requirements_text(*, session: Session, version: AgentVersion) -> str:
    """Return generation context for a version: requirements if any, else prompt."""
    requirements = requirement_crud.list_requirements_for_version(
        session=session, agent_version_id=version.id
    )
    if not requirements:
        return version.system_prompt or ""

    lines = [
        "The agent under test must satisfy the following requirements. "
        "Generate test cases that exercise and probe these requirements "
        "(happy paths, edge cases, and adversarial attempts to violate them):",
        "",
    ]
    for index, req in enumerate(requirements, start=1):
        suffix = f" [{req.category}]" if req.category else ""
        lines.append(f"{index}. {req.text}{suffix}")
    return "\n".join(lines)
