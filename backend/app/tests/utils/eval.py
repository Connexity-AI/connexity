import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    Agent,
    AgentCreate,
    EvalSet,
    EvalSetCreate,
    EvalSetMemberEntry,
    Run,
    RunCreate,
    TestCase,
    TestCaseCreate,
    TestCaseResult,
    TestCaseResultCreate,
)


def create_test_agent(session: Session) -> Agent:
    agent_in = AgentCreate(
        name=f"test-agent-{uuid.uuid4().hex[:8]}",
        endpoint_url="http://localhost:8080/agent",
        description="Test agent for automated tests",
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


def eval_set_members(*test_case_ids: uuid.UUID) -> list[EvalSetMemberEntry]:
    """Build member entries with default repetitions=1 (test helper)."""
    return [EvalSetMemberEntry(test_case_id=sid) for sid in test_case_ids]


def create_test_eval_set(
    session: Session,
    *,
    members: list[EvalSetMemberEntry] | None = None,
) -> EvalSet:
    eval_set_in = EvalSetCreate(
        name=f"test-set-{uuid.uuid4().hex[:8]}",
        description="Test eval set",
        members=members,
    )
    return crud.create_eval_set(session=session, eval_set_in=eval_set_in)


def create_test_run(
    session: Session,
    agent_id: uuid.UUID,
    eval_set_id: uuid.UUID,
) -> Run:
    run_in = RunCreate(
        name=f"test-run-{uuid.uuid4().hex[:8]}",
        agent_id=agent_id,
        agent_endpoint_url="http://localhost:8080/agent",
        eval_set_id=eval_set_id,
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
