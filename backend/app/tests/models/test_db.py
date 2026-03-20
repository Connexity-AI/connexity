"""ORM model instantiation tests — no database required."""

import uuid

from app.models.agent import Agent, AgentCreate
from app.models.enums import (
    Difficulty,
    ErrorCategory,
    RunStatus,
    ScenarioStatus,
    SimulationMode,
)
from app.models.run import Run, RunCreate
from app.models.scenario import Scenario, ScenarioCreate
from app.models.scenario_result import ScenarioResult, ScenarioResultCreate
from app.models.scenario_set import ScenarioSet, ScenarioSetCreate, ScenarioSetMember

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


# ── Scenario ───────────────────────────────────────────────────────


def test_scenario_create_minimal():
    scenario = ScenarioCreate(name="Test Scenario")
    assert scenario.difficulty == Difficulty.NORMAL
    assert scenario.status == ScenarioStatus.ACTIVE
    assert scenario.simulation_mode == SimulationMode.LLM_DRIVEN
    assert scenario.max_turns == 20


def test_scenario_create_with_tags():
    scenario = ScenarioCreate(
        name="Red Team Scenario",
        tags=["red-team", "edge-case"],
        difficulty=Difficulty.HARD,
    )
    assert "red-team" in scenario.tags
    assert scenario.difficulty == Difficulty.HARD


def test_scenario_table_defaults():
    scenario = Scenario(name="Test Scenario")
    assert scenario.id is not None
    assert isinstance(scenario.id, uuid.UUID)


# ── ScenarioSet ────────────────────────────────────────────────────


def test_scenario_set_create():
    ss = ScenarioSetCreate(
        name="Baseline Set",
        scenario_ids=[uuid.uuid4(), uuid.uuid4()],
    )
    assert len(ss.scenario_ids) == 2
    assert ss.version == 1


def test_scenario_set_table_defaults():
    ss = ScenarioSet(name="Test Set")
    assert ss.id is not None
    assert ss.version == 1


def test_scenario_set_member():
    member = ScenarioSetMember(
        scenario_set_id=uuid.uuid4(),
        scenario_id=uuid.uuid4(),
        position=3,
    )
    assert member.position == 3


# ── Run ────────────────────────────────────────────────────────────


def test_run_create_minimal():
    run = RunCreate(
        agent_id=uuid.uuid4(),
        agent_endpoint_url="https://example.com/agent",
        scenario_set_id=uuid.uuid4(),
    )
    assert run.is_baseline is False
    assert run.config is None


def test_run_create_with_config():
    from app.models.schemas import RunConfig

    run = RunCreate(
        agent_id=uuid.uuid4(),
        agent_endpoint_url="https://example.com/agent",
        scenario_set_id=uuid.uuid4(),
        config=RunConfig(concurrency=10, judge_model="gpt-4o"),
    )
    assert run.config.concurrency == 10


def test_run_table_defaults():
    run = Run(
        agent_id=uuid.uuid4(),
        agent_endpoint_url="https://example.com/agent",
        scenario_set_id=uuid.uuid4(),
    )
    assert run.id is not None
    assert run.status == RunStatus.PENDING
    assert run.is_baseline is False


def test_run_enum_values():
    for status in RunStatus:
        run = Run(
            agent_id=uuid.uuid4(),
            agent_endpoint_url="https://example.com/agent",
            scenario_set_id=uuid.uuid4(),
            status=status,
        )
        assert run.status == status


# ── ScenarioResult ─────────────────────────────────────────────────


def test_scenario_result_create():
    sr = ScenarioResultCreate(
        run_id=uuid.uuid4(),
        scenario_id=uuid.uuid4(),
    )
    assert sr.run_id is not None


def test_scenario_result_table_defaults():
    sr = ScenarioResult(
        run_id=uuid.uuid4(),
        scenario_id=uuid.uuid4(),
    )
    assert sr.id is not None
    assert sr.error_category == ErrorCategory.NONE
    assert sr.passed is None
