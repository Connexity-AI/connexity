"""Load DB-backed context for the test-case AI agent."""

import uuid
from dataclasses import dataclass

from sqlmodel import Session

from app import crud
from app.models import Agent, ConversationTurn, TestCase
from app.services.test_case_generator.agent.schemas import (
    AgentMode,
    TestCaseAgentRequest,
)
from app.services.test_case_generator.schemas import (
    ToolDefinition,
    tool_definitions_from_agent_tools,
)

_CATEGORY_TAGS: tuple[str, ...] = ("normal", "edge-case", "red-team")


class TestCaseAgentContextError(Exception):
    """Raised when context cannot be built; maps to HTTP errors in the route."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class AgentContext:
    """Resolved inputs for prompt building and LLM call."""

    agent: Agent
    agent_prompt: str
    tools: list[ToolDefinition]
    available_tags: list[str]
    existing_cases_summary: list[dict[str, object]] | None
    target_test_case: TestCase | None
    transcript: list[ConversationTurn] | None


def merge_available_tags(*, category: list[str], from_db: list[str]) -> list[str]:
    """Stable-unique merge: category tags first, then DB tags alphabetically."""
    seen: set[str] = set()
    out: list[str] = []
    for t in category:
        if t not in seen:
            seen.add(t)
            out.append(t)
    for t in sorted(from_db):
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_agent_context(
    *, session: Session, request: TestCaseAgentRequest
) -> AgentContext:
    """Load agent, version prompt/tools, tags, and mode-specific extras."""
    agent = session.get(Agent, request.agent_id)
    if agent is None:
        raise TestCaseAgentContextError(
            status_code=404, detail=f"Agent not found: {request.agent_id}"
        )

    version_num = (
        request.agent_version if request.agent_version is not None else agent.version
    )
    version = crud.get_agent_version(
        session=session, agent_id=agent.id, version=version_num
    )
    if version is None:
        raise TestCaseAgentContextError(
            status_code=404,
            detail=f"Agent version {version_num} not found for agent {agent.id}",
        )

    agent_prompt = version.system_prompt or ""
    tools = tool_definitions_from_agent_tools(version.tools)

    db_tags = crud.list_distinct_tags_for_agent(session=session, agent_id=agent.id)
    available_tags = merge_available_tags(
        category=list(_CATEGORY_TAGS), from_db=db_tags
    )

    existing_summary: list[dict[str, object]] | None = None
    target_test_case: TestCase | None = None
    transcript: list[ConversationTurn] | None = None

    if request.mode == AgentMode.CREATE:
        recent = crud.list_recent_test_cases_for_agent(
            session=session, agent_id=agent.id, limit=20
        )
        existing_summary = [
            {
                "name": tc.name,
                "tags": list(tc.tags),
                "difficulty": str(tc.difficulty),
            }
            for tc in recent
        ]
    elif request.mode == AgentMode.EDIT:
        tc_id: uuid.UUID = request.test_case_id  # type: ignore[assignment]
        tc = crud.get_test_case(session=session, test_case_id=tc_id)
        if tc is None:
            raise TestCaseAgentContextError(
                status_code=404, detail="Test case not found"
            )
        if tc.agent_id != request.agent_id:
            raise TestCaseAgentContextError(
                status_code=422,
                detail="test_case_id does not belong to the given agent_id",
            )
        target_test_case = tc
    elif request.mode == AgentMode.FROM_TRANSCRIPT:
        transcript = list(request.transcript or [])

    return AgentContext(
        agent=agent,
        agent_prompt=agent_prompt,
        tools=tools,
        available_tags=available_tags,
        existing_cases_summary=existing_summary,
        target_test_case=target_test_case,
        transcript=transcript,
    )
