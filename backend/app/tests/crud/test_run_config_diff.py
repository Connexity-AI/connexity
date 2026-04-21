"""Tests for compute_run_config_diff (agent config from AgentVersion)."""

import uuid

from sqlmodel import Session

from app import crud
from app.crud.agent_version import publish_draft
from app.models import AgentCreate, AgentUpdate
from app.models.enums import AgentMode
from app.services.diff import compute_run_config_diff
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_config,
    create_test_run,
    eval_config_members,
)


def _tool(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "x",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_compute_run_config_diff_no_changes(db: Session) -> None:
    agent = create_test_agent(db)
    tc = create_test_case_fixture(db)
    es = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(tc.id)
    )
    r1 = create_test_run(db, agent.id, es.id)
    r2 = create_test_run(db, agent.id, es.id)
    sids = {tc.id}
    diff = compute_run_config_diff(r1, r2, sids, sids, session=db)
    assert diff.prompt_diff is not None
    assert diff.prompt_diff.changed is False
    assert diff.model_changed is None
    assert diff.provider_changed is None
    assert diff.baseline_agent_version == r1.agent_version
    assert diff.candidate_agent_version == r2.agent_version


def test_compute_run_config_diff_model_swap(db: Session) -> None:
    agent_in = AgentCreate(
        name=f"plat-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt="Hello",
        agent_model="gpt-4o",
        agent_provider="openai",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    tc = create_test_case_fixture(db)
    es = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(tc.id)
    )
    r1 = create_test_run(db, agent.id, es.id)
    crud.update_agent(
        session=db,
        db_agent=agent,
        agent_in=AgentUpdate(agent_model="gpt-4o-mini"),
    )
    publish_draft(session=db, agent=agent, change_description=None, created_by=None)
    r2 = create_test_run(db, agent.id, es.id)
    sids = {tc.id}
    diff = compute_run_config_diff(r1, r2, sids, sids, session=db)
    assert diff.model_changed is not None
    assert diff.model_changed.old_value == "gpt-4o"
    assert diff.model_changed.new_value == "gpt-4o-mini"


def test_compute_run_config_diff_prompt_and_tools(db: Session) -> None:
    tools_v1 = [_tool("search")]
    agent_in = AgentCreate(
        name=f"plat-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt="V1 prompt",
        tools=tools_v1,
        agent_model="gpt-4o",
        agent_provider="openai",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    tc = create_test_case_fixture(db)
    es = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(tc.id)
    )
    r1 = create_test_run(db, agent.id, es.id)
    crud.update_agent(
        session=db,
        db_agent=agent,
        agent_in=AgentUpdate(
            system_prompt="V2 prompt completely rewritten",
            tools=[_tool("search"), _tool("weather")],
        ),
    )
    publish_draft(session=db, agent=agent, change_description=None, created_by=None)
    r2 = create_test_run(db, agent.id, es.id)
    sids = {tc.id}
    diff = compute_run_config_diff(r1, r2, sids, sids, session=db)
    assert diff.prompt_diff is not None
    assert diff.prompt_diff.changed is True
    assert diff.tool_diff is not None
    assert diff.tool_diff.added == ["weather"]


def test_compute_run_config_diff_judge_model_change(db: Session) -> None:
    agent = create_test_agent(db)
    tc = create_test_case_fixture(db)
    es = create_test_eval_config(
        db, agent_id=agent.id, members=eval_config_members(tc.id)
    )
    r1 = create_test_run(db, agent.id, es.id)
    r2 = create_test_run(db, agent.id, es.id)
    r1.config = {"judge": {"model": "gpt-4o", "provider": "openai"}}
    r2.config = {"judge": {"model": "claude-3-5-sonnet", "provider": "anthropic"}}
    db.add(r1)
    db.add(r2)
    db.commit()
    db.refresh(r1)
    db.refresh(r2)
    sids = {tc.id}
    diff = compute_run_config_diff(r1, r2, sids, sids, session=db)
    assert diff.judge_model_changed is not None
    assert diff.judge_model_changed.old_value == "gpt-4o"
    assert diff.judge_model_changed.new_value == "claude-3-5-sonnet"
    assert diff.judge_provider_changed is not None
