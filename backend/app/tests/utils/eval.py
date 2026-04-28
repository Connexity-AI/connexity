import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    Agent,
    AgentCreate,
    AgentMode,
    EvalConfig,
    EvalConfigCreate,
    EvalConfigMemberEntry,
    PromptEditorMessage,
    PromptEditorMessageCreate,
    PromptEditorSession,
    PromptEditorSessionCreate,
    Run,
    RunCreate,
    TestCase,
    TestCaseCreate,
    TestCaseResult,
    TestCaseResultCreate,
    TurnRole,
)


def create_test_agent(session: Session) -> Agent:
    agent_in = AgentCreate(
        name=f"test-agent-{uuid.uuid4().hex[:8]}",
        endpoint_url="http://localhost:8080/agent",
        description="Test agent for automated tests",
    )
    return crud.create_agent(session=session, agent_in=agent_in)


def create_test_platform_agent(
    session: Session, *, system_prompt: str = "You are a test bot."
) -> Agent:
    agent_in = AgentCreate(
        name=f"plat-agent-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt=system_prompt,
        agent_model="gpt-4o-mini",
        agent_provider="openai",
        description="Platform test agent",
    )
    return crud.create_agent(session=session, agent_in=agent_in)


def create_test_case_fixture(session: Session, **overrides: object) -> TestCase:
    defaults: dict[str, object] = {
        "name": f"test-case-{uuid.uuid4().hex[:8]}",
        "description": "Test case for automated tests",
        "tags": ["test"],
    }
    defaults.update(overrides)
    return crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(**defaults),  # type: ignore[arg-type]
    )


def eval_config_members(*test_case_ids: uuid.UUID) -> list[EvalConfigMemberEntry]:
    """Build member entries with default repetitions=1 (test helper)."""
    return [EvalConfigMemberEntry(test_case_id=sid) for sid in test_case_ids]


def create_test_eval_config(
    session: Session,
    *,
    agent_id: uuid.UUID | None = None,
    members: list[EvalConfigMemberEntry] | None = None,
) -> EvalConfig:
    if agent_id is None:
        agent = create_test_agent(session)
        agent_id = agent.id
    eval_config_in = EvalConfigCreate(
        name=f"test-config-{uuid.uuid4().hex[:8]}",
        description="Test eval config",
        agent_id=agent_id,
        members=members,
    )
    return crud.create_eval_config(session=session, eval_config_in=eval_config_in)


def create_test_run(
    session: Session,
    agent_id: uuid.UUID,
    eval_config_id: uuid.UUID,
) -> Run:
    agent = crud.get_agent(session=session, agent_id=agent_id)
    assert agent is not None
    eval_config = crud.get_eval_config(session=session, eval_config_id=eval_config_id)
    assert eval_config is not None
    run_in = RunCreate(
        name=f"test-run-{uuid.uuid4().hex[:8]}",
        agent_id=agent_id,
        agent_endpoint_url="http://localhost:8080/agent",
        eval_config_id=eval_config_id,
    )
    run_in = crud.enrich_run_create_from_agent(
        session=session, run_in=run_in, agent=agent, eval_config=eval_config
    )
    return crud.create_run(session=session, run_in=run_in)


def create_test_case_result_fixture(
    session: Session,
    run_id: uuid.UUID,
    test_case_id: uuid.UUID,
) -> TestCaseResult:
    result_in = TestCaseResultCreate(
        run_id=run_id,
        test_case_id=test_case_id,
    )
    return crud.create_test_case_result(session=session, result_in=result_in)


def create_test_prompt_editor_session(
    session: Session,
    *,
    agent_id: uuid.UUID,
    created_by: uuid.UUID,
    **overrides: object,
) -> PromptEditorSession:
    defaults: dict[str, object] = {
        "agent_id": agent_id,
        "title": f"test-session-{uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    return crud.create_prompt_editor_session(
        session=session,
        session_in=PromptEditorSessionCreate(**defaults),  # type: ignore[arg-type]
        created_by=created_by,
    )


def create_test_prompt_editor_message(
    session: Session,
    session_id: uuid.UUID,
    **overrides: object,
) -> PromptEditorMessage:
    defaults: dict[str, object] = {
        "session_id": session_id,
        "role": TurnRole.USER,
        "content": "hello",
    }
    defaults.update(overrides)
    return crud.create_prompt_editor_message(
        session=session,
        message_in=PromptEditorMessageCreate(**defaults),  # type: ignore[arg-type]
    )
