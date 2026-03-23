import uuid

from sqlmodel import Session

from app import crud
from app.models import (
    Agent,
    AgentCreate,
    Run,
    RunCreate,
    Scenario,
    ScenarioCreate,
    ScenarioResult,
    ScenarioResultCreate,
    ScenarioSet,
    ScenarioSetCreate,
)


def create_test_agent(session: Session) -> Agent:
    agent_in = AgentCreate(
        name=f"test-agent-{uuid.uuid4().hex[:8]}",
        endpoint_url="http://localhost:8080/agent",
        description="Test agent for automated tests",
    )
    return crud.create_agent(session=session, agent_in=agent_in)


def create_test_scenario(session: Session, **overrides: object) -> Scenario:
    defaults: dict[str, object] = {
        "name": f"test-scenario-{uuid.uuid4().hex[:8]}",
        "description": "Test scenario for automated tests",
        "tags": ["test"],
    }
    defaults.update(overrides)
    return crud.create_scenario(
        session=session,
        scenario_in=ScenarioCreate(**defaults),  # type: ignore[arg-type]
    )


def create_test_scenario_set(
    session: Session,
    scenario_ids: list[uuid.UUID] | None = None,
) -> ScenarioSet:
    scenario_set_in = ScenarioSetCreate(
        name=f"test-set-{uuid.uuid4().hex[:8]}",
        description="Test scenario set",
        scenario_ids=scenario_ids,
    )
    return crud.create_scenario_set(session=session, scenario_set_in=scenario_set_in)


def create_test_run(
    session: Session,
    agent_id: uuid.UUID,
    scenario_set_id: uuid.UUID,
) -> Run:
    run_in = RunCreate(
        name=f"test-run-{uuid.uuid4().hex[:8]}",
        agent_id=agent_id,
        agent_endpoint_url="http://localhost:8080/agent",
        scenario_set_id=scenario_set_id,
    )
    return crud.create_run(session=session, run_in=run_in)


def create_test_scenario_result(
    session: Session,
    run_id: uuid.UUID,
    scenario_id: uuid.UUID,
) -> ScenarioResult:
    result_in = ScenarioResultCreate(
        run_id=run_id,
        scenario_id=scenario_id,
    )
    return crud.create_scenario_result(session=session, result_in=result_in)
