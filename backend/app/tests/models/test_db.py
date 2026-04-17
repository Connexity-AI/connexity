import uuid

from app.models.agent import Agent, AgentCreate
from app.models.enums import (
    Difficulty,
    RunStatus,
    TestCaseStatus,
)
from app.models.eval_set import (
    EvalSet,
    EvalSetCreate,
    EvalSetMember,
    EvalSetMemberEntry,
)
from app.models.run import Run, RunCreate
from app.models.test_case import TestCase, TestCaseCreate
from app.models.test_case_result import TestCaseResult, TestCaseResultCreate

# ── Agent ──────────────────────────────────────────────────────────


def test_agent_create():
    agent = AgentCreate(
        name="Test Agent",
        endpoint_url="https://example.com/agent",
    )
    assert agent.name == "Test Agent"
    assert agent.agent_metadata is None


def test_agent_create_with_metadata():
    agent = AgentCreate(
        name="Test Agent",
        endpoint_url="https://example.com/agent",
        agent_metadata={"version": "1.0", "provider": "openai"},
    )
    assert agent.agent_metadata["version"] == "1.0"


def test_agent_table_defaults():
    agent = Agent(
        name="Test Agent",
        endpoint_url="https://example.com/agent",
    )
    assert agent.id is not None
    assert isinstance(agent.id, uuid.UUID)


# ── TestCase ───────────────────────────────────────────────────────


def test_test_case_create_minimal():
    tc = TestCaseCreate(name="Test TestCase")
    assert tc.difficulty == Difficulty.NORMAL
    assert tc.status == TestCaseStatus.ACTIVE
    assert tc.first_message is None


def test_test_case_create_with_tags():
    tc = TestCaseCreate(
        name="Red Team TestCase",
        tags=["red-team", "edge-case"],
        difficulty=Difficulty.HARD,
    )
    assert "red-team" in tc.tags
    assert tc.difficulty == Difficulty.HARD


def test_test_case_table_defaults():
    tc = TestCase(name="Test TestCase")
    assert tc.id is not None
    assert isinstance(tc.id, uuid.UUID)


# ── EvalSet ────────────────────────────────────────────────────


def test_eval_set_create():
    a, b = uuid.uuid4(), uuid.uuid4()
    ss = EvalSetCreate(
        name="Baseline Set",
        members=[
            EvalSetMemberEntry(test_case_id=a),
            EvalSetMemberEntry(test_case_id=b),
        ],
    )
    assert ss.members is not None
    assert len(ss.members) == 2


def test_eval_set_table_defaults():
    ss = EvalSet(name="Test Set")
    assert ss.id is not None
    assert ss.version == 1


def test_eval_set_member():
    member = EvalSetMember(
        eval_set_id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),
        position=3,
    )
    assert member.position == 3
    assert member.repetitions == 1


# ── Run ────────────────────────────────────────────────────────────


def test_run_create_minimal():
    run = RunCreate(
        agent_id=uuid.uuid4(),
        agent_endpoint_url="https://example.com/agent",
        eval_set_id=uuid.uuid4(),
    )
    assert run.is_baseline is False
    assert run.config is None


def test_run_create_with_config():
    from app.models.schemas import JudgeConfig, RunConfig

    run = RunCreate(
        agent_id=uuid.uuid4(),
        agent_endpoint_url="https://example.com/agent",
        eval_set_id=uuid.uuid4(),
        config=RunConfig(concurrency=10, judge=JudgeConfig(model="gpt-4o")),
    )
    assert run.config.concurrency == 10


def test_run_table_defaults():
    run = Run(
        agent_id=uuid.uuid4(),
        agent_endpoint_url="https://example.com/agent",
        eval_set_id=uuid.uuid4(),
    )
    assert run.id is not None
    assert run.status == RunStatus.PENDING
    assert run.is_baseline is False


def test_run_enum_values():
    for status in RunStatus:
        run = Run(
            agent_id=uuid.uuid4(),
            agent_endpoint_url="https://example.com/agent",
            eval_set_id=uuid.uuid4(),
            status=status,
        )
        assert run.status == status


# ── TestCaseResult ─────────────────────────────────────────────────


def test_test_case_result_create():
    sr = TestCaseResultCreate(
        run_id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),
    )
    assert sr.run_id is not None


def test_test_case_result_table_defaults():
    sr = TestCaseResult(
        run_id=uuid.uuid4(),
        test_case_id=uuid.uuid4(),
    )
    assert sr.id is not None
    assert sr.passed is None
