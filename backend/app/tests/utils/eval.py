import uuid

from sqlmodel import Session, select

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
    User,
)
from app.models.company import Company
from app.models.enums import Platform
from app.models.schemas import (
    CustomEndpointRuntimeConfig,
    RetellRuntimeConfig,
    RunConfig,
)
from app.tests.utils.utils import AUTH_USER_EMAIL


def _resolve_company_id(session: Session, company_id: uuid.UUID | None) -> uuid.UUID:
    """Use the explicit company_id when given, otherwise resolve a stable default.

    Prefer the default auth test user's company so route tests reusing the same
    session see the data. Falls back to picking the first Company in the DB,
    creating one on the fly if there are none.
    """
    if company_id is not None:
        return company_id
    user = session.exec(select(User).where(User.email == AUTH_USER_EMAIL)).first()
    if user is not None:
        return user.company_id
    existing = session.exec(select(Company)).first()
    if existing is not None:
        return existing.id
    new_company = Company()
    session.add(new_company)
    session.commit()
    session.refresh(new_company)
    return new_company.id


def get_test_company_id(session: Session) -> uuid.UUID:
    """Public helper for tests that call ``crud`` directly and need a company_id."""
    return _resolve_company_id(session, None)


def create_test_agent(
    session: Session, *, company_id: uuid.UUID | None = None
) -> Agent:
    cid = _resolve_company_id(session, company_id)
    agent_in = AgentCreate(
        name=f"test-agent-{uuid.uuid4().hex[:8]}",
        endpoint_url="http://localhost:8080/agent",
        description="Test agent for automated tests",
    )
    return crud.create_agent(session=session, agent_in=agent_in, company_id=cid)


def create_test_platform_agent(
    session: Session,
    *,
    system_prompt: str = "You are a test bot.",
    company_id: uuid.UUID | None = None,
) -> Agent:
    cid = _resolve_company_id(session, company_id)
    agent_in = AgentCreate(
        name=f"plat-agent-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt=system_prompt,
        agent_model="gpt-4o-mini",
        agent_provider="openai",
        description="Platform test agent",
    )
    return crud.create_agent(session=session, agent_in=agent_in, company_id=cid)


def create_test_case_fixture(
    session: Session,
    *,
    company_id: uuid.UUID | None = None,
    **overrides: object,
) -> TestCase:
    cid = _resolve_company_id(session, company_id)
    defaults: dict[str, object] = {
        "name": f"test-case-{uuid.uuid4().hex[:8]}",
        "description": "Test case for automated tests",
        "tags": ["test"],
    }
    defaults.update(overrides)
    return crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(**defaults),  # type: ignore[arg-type]
        company_id=cid,
    )


def eval_config_members(*test_case_ids: uuid.UUID) -> list[EvalConfigMemberEntry]:
    """Build member entries with default repetitions=1 (test helper)."""
    return [EvalConfigMemberEntry(test_case_id=sid) for sid in test_case_ids]


def create_test_eval_config(
    session: Session,
    *,
    agent_id: uuid.UUID | None = None,
    members: list[EvalConfigMemberEntry] | None = None,
    config: RunConfig | None = None,
    company_id: uuid.UUID | None = None,
) -> EvalConfig:
    cid = _resolve_company_id(session, company_id)
    if agent_id is None:
        agent = create_test_agent(session, company_id=cid)
        agent_id = agent.id
    else:
        agent = crud.get_agent(session=session, agent_id=agent_id)
        if agent is None:
            raise ValueError(f"Agent {agent_id} not found")

    resolved_config = config
    if resolved_config is None and not (agent.system_prompt or "").strip():
        if agent.platform == Platform.RETELL:
            resolved_config = RunConfig(runtime=RetellRuntimeConfig())
        else:
            ep = (agent.endpoint_url or "").strip() or "http://localhost:8080/agent"
            resolved_config = RunConfig(
                runtime=CustomEndpointRuntimeConfig(url=ep),
            )

    eval_config_in = EvalConfigCreate(
        name=f"test-config-{uuid.uuid4().hex[:8]}",
        description="Test eval config",
        agent_id=agent_id,
        members=members,
        config=resolved_config,
    )
    return crud.create_eval_config(
        session=session, eval_config_in=eval_config_in, company_id=cid
    )


def create_test_run(
    session: Session,
    agent_id: uuid.UUID,
    eval_config_id: uuid.UUID,
    *,
    company_id: uuid.UUID | None = None,
) -> Run:
    cid = _resolve_company_id(session, company_id)
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
    return crud.create_run(session=session, run_in=run_in, company_id=cid)


def create_test_case_result_fixture(
    session: Session,
    run_id: uuid.UUID,
    test_case_id: uuid.UUID,
    *,
    company_id: uuid.UUID | None = None,
) -> TestCaseResult:
    cid = _resolve_company_id(session, company_id)
    result_in = TestCaseResultCreate(
        run_id=run_id,
        test_case_id=test_case_id,
    )
    return crud.create_test_case_result(
        session=session, result_in=result_in, company_id=cid
    )


def create_test_prompt_editor_session(
    session: Session,
    *,
    agent_id: uuid.UUID,
    created_by: uuid.UUID,
    company_id: uuid.UUID | None = None,
    **overrides: object,
) -> PromptEditorSession:
    cid = _resolve_company_id(session, company_id)
    defaults: dict[str, object] = {
        "agent_id": agent_id,
        "title": f"test-session-{uuid.uuid4().hex[:8]}",
    }
    defaults.update(overrides)
    return crud.create_prompt_editor_session(
        session=session,
        session_in=PromptEditorSessionCreate(**defaults),  # type: ignore[arg-type]
        company_id=cid,
        created_by=created_by,
    )


def create_test_prompt_editor_message(
    session: Session,
    session_id: uuid.UUID,
    *,
    company_id: uuid.UUID | None = None,
    **overrides: object,
) -> PromptEditorMessage:
    cid = _resolve_company_id(session, company_id)
    defaults: dict[str, object] = {
        "session_id": session_id,
        "role": TurnRole.USER,
        "content": "hello",
    }
    defaults.update(overrides)
    return crud.create_prompt_editor_message(
        session=session,
        message_in=PromptEditorMessageCreate(**defaults),  # type: ignore[arg-type]
        company_id=cid,
    )
