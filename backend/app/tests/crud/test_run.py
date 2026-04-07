from datetime import UTC, datetime

from sqlmodel import Session

from app import crud
from app.models import AgentCreate, RunCreate, RunStatus, RunUpdate
from app.models.enums import AgentMode
from app.models.schemas import AgentSimulatorConfig, JudgeConfig, RunConfig
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_set,
    create_test_run,
    eval_set_members,
)


def _setup_run(db: Session) -> tuple:
    """Create agent + eval set needed for a run."""
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    return agent, eval_set


def test_enrich_run_create_fills_endpoint_snapshot(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    run_in = RunCreate(
        agent_id=agent.id,
        eval_set_id=eval_set.id,
    )
    enriched = crud.enrich_run_create_from_agent(
        session=db, run_in=run_in, agent=agent
    )
    assert enriched.agent_endpoint_url == "http://localhost:8080/agent"
    assert enriched.agent_mode == AgentMode.ENDPOINT.value
    assert enriched.agent_version == agent.version
    assert enriched.agent_version_id is not None


def test_enrich_run_create_platform_agent(db: Session) -> None:
    agent_in = AgentCreate(
        name="platform-agent",
        mode=AgentMode.PLATFORM,
        system_prompt="Be concise.",
        agent_model="gpt-4o-mini",
        agent_provider="openai",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    eval_set = create_test_eval_set(db)
    run_in = RunCreate(agent_id=agent.id, eval_set_id=eval_set.id)
    enriched = crud.enrich_run_create_from_agent(
        session=db, run_in=run_in, agent=agent
    )
    assert enriched.agent_mode == AgentMode.PLATFORM.value
    assert enriched.agent_model == "gpt-4o-mini"
    assert enriched.agent_provider == "openai"
    assert enriched.agent_system_prompt == "Be concise."


def test_enrich_run_create_platform_agent_simulator_model_override(db: Session) -> None:
    agent_in = AgentCreate(
        name="platform-agent-override",
        mode=AgentMode.PLATFORM,
        system_prompt="Be concise.",
        agent_model="gpt-4o-mini",
        agent_provider="openai",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    eval_set = create_test_eval_set(db)
    run_in = RunCreate(
        agent_id=agent.id,
        eval_set_id=eval_set.id,
        config=RunConfig(agent_simulator=AgentSimulatorConfig(model="gpt-4o")),
    )
    enriched = crud.enrich_run_create_from_agent(
        session=db, run_in=run_in, agent=agent
    )
    assert enriched.agent_model == "gpt-4o"
    assert enriched.agent_provider == "openai"


def test_enrich_run_create_platform_agent_simulator_provider_override(
    db: Session,
) -> None:
    agent_in = AgentCreate(
        name="platform-agent-prov-override",
        mode=AgentMode.PLATFORM,
        system_prompt="Hi",
        agent_model="claude-3-5-haiku-20241022",
        agent_provider="openai",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    eval_set = create_test_eval_set(db)
    run_in = RunCreate(
        agent_id=agent.id,
        eval_set_id=eval_set.id,
        config=RunConfig(
            agent_simulator=AgentSimulatorConfig(provider="anthropic"),
        ),
    )
    enriched = crud.enrich_run_create_from_agent(
        session=db, run_in=run_in, agent=agent
    )
    assert enriched.agent_model == "claude-3-5-haiku-20241022"
    assert enriched.agent_provider == "anthropic"


def test_create_run(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    assert run.id is not None
    assert run.agent_id == agent.id
    assert run.eval_set_id == eval_set.id
    assert run.status == RunStatus.PENDING


def test_create_run_with_config(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    config = RunConfig(judge=JudgeConfig(model="claude-3-5-sonnet"), concurrency=3)
    run_in = RunCreate(
        agent_id=agent.id,
        agent_endpoint_url="http://localhost:8080/agent",
        eval_set_id=eval_set.id,
        config=config,
    )
    run_in = crud.enrich_run_create_from_agent(
        session=db, run_in=run_in, agent=agent
    )
    run = crud.create_run(session=db, run_in=run_in)
    assert run.config is not None
    assert run.config["judge"]["model"] == "claude-3-5-sonnet"
    assert run.config["concurrency"] == 3


def test_get_run(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    fetched = crud.get_run(session=db, run_id=run.id)
    assert fetched is not None
    assert fetched.id == run.id


def test_list_runs(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    items, count = crud.list_runs(session=db)
    assert count >= 1


def test_list_runs_filter_by_agent(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    items, count = crud.list_runs(session=db, agent_id=agent.id)
    assert count >= 1
    assert all(r.agent_id == agent.id for r in items)


def test_list_runs_filter_by_agent_version(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    items, count = crud.list_runs(session=db, agent_version=1, agent_id=agent.id)
    assert count >= 1
    assert all(r.agent_version == 1 for r in items)


def test_list_runs_filter_by_status(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(
        session=db, db_run=run, run_in=RunUpdate(status=RunStatus.COMPLETED)
    )
    items, count = crud.list_runs(session=db, status=RunStatus.COMPLETED)
    assert count >= 1
    assert all(r.status == RunStatus.COMPLETED for r in items)


def test_list_runs_filter_by_date_range(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    now = datetime.now(UTC)
    items, count = crud.list_runs(
        session=db,
        created_after=datetime(2020, 1, 1, tzinfo=UTC),
        created_before=now,
    )
    assert count >= 1


def test_update_run(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    updated = crud.update_run(
        session=db,
        db_run=run,
        run_in=RunUpdate(status=RunStatus.RUNNING),
    )
    assert updated.status == RunStatus.RUNNING


def test_delete_run(db: Session) -> None:
    agent, eval_set = _setup_run(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    run_id = run.id
    crud.delete_run(session=db, db_run=run)
    fetched = crud.get_run(session=db, run_id=run_id)
    assert fetched is None
