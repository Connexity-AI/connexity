"""Tests for prompt editor preset definitions and filtering (CS-63).

Lives under ``app/tests/`` (not ``app/tests/services/``) so the root ``db``
fixture is used; ``services/conftest.py`` replaces ``db`` with ``None`` for
pure unit tests in that package.
"""

import uuid

from sqlmodel import Session

from app import crud
from app.models import Agent, AgentCreate, RunStatus, RunUpdate
from app.models.enums import AgentMode
from app.services.prompt_editor.presets import (
    ALL_PRESETS,
    PresetContext,
    get_available_presets,
)
from app.tests.utils.eval import (
    create_test_agent,
    create_test_eval_config,
    create_test_platform_agent,
    create_test_run,
)


def _preset_ids(session: Session, agent: Agent) -> list[str]:
    return [p.id for p in get_available_presets(agent=agent, session=session)]


def test_all_presets_six_definitions() -> None:
    assert len(ALL_PRESETS) == 6
    ids = {p.id for p in ALL_PRESETS}
    assert ids == {
        "help_create_agent",
        "improve_prompt",
        "make_concise",
        "add_examples",
        "suggest_from_evals",
        "review_tools",
    }


def test_suggest_from_evals_uses_eval_context() -> None:
    preset = next(p for p in ALL_PRESETS if p.id == "suggest_from_evals")
    assert preset.context == PresetContext.EVAL
    others = [p for p in ALL_PRESETS if p.id != "suggest_from_evals"]
    assert all(p.context == PresetContext.NONE for p in others)


def test_endpoint_agent_without_prompt_only_help_create(db: Session) -> None:
    agent = create_test_agent(db)
    assert agent.system_prompt is None
    ids = _preset_ids(db, agent)
    assert ids == ["help_create_agent"]


def test_platform_agent_default_three_prompt_presets(db: Session) -> None:
    agent = create_test_platform_agent(db)
    ids = _preset_ids(db, agent)
    assert ids == ["improve_prompt", "make_concise", "add_examples"]


def test_platform_agent_with_tools_includes_review_tools(db: Session) -> None:
    agent_in = AgentCreate(
        name=f"plat-tools-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt="You are a test bot.",
        agent_model="gpt-4o-mini",
        agent_provider="openai",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Look something up",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    ids = _preset_ids(db, agent)
    assert ids == [
        "improve_prompt",
        "make_concise",
        "add_examples",
        "review_tools",
    ]


def test_platform_agent_with_completed_run_includes_suggest_from_evals(
    db: Session,
) -> None:
    agent = create_test_platform_agent(db)
    eval_config = create_test_eval_config(db, agent_id=agent.id)
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    crud.update_run(
        session=db,
        db_run=run,
        run_in=RunUpdate(status=RunStatus.COMPLETED),
    )
    db.refresh(agent)
    ids = _preset_ids(db, agent)
    assert ids == [
        "improve_prompt",
        "make_concise",
        "add_examples",
        "suggest_from_evals",
    ]


def test_completed_run_for_other_agent_does_not_unlock_eval_preset(
    db: Session,
) -> None:
    agent_a = create_test_platform_agent(db)
    agent_b = create_test_platform_agent(db)
    eval_config = create_test_eval_config(db, agent_id=agent_b.id)
    run = create_test_run(db, agent_id=agent_b.id, eval_config_id=eval_config.id)
    crud.update_run(
        session=db,
        db_run=run,
        run_in=RunUpdate(status=RunStatus.COMPLETED),
    )
    ids = _preset_ids(db, agent_a)
    assert "suggest_from_evals" not in ids


def test_non_completed_run_does_not_unlock_eval_preset(db: Session) -> None:
    agent = create_test_platform_agent(db)
    eval_config = create_test_eval_config(db, agent_id=agent.id)
    create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    ids = _preset_ids(db, agent)
    assert "suggest_from_evals" not in ids


def test_platform_agent_tools_and_completed_run_five_presets(db: Session) -> None:
    agent_in = AgentCreate(
        name=f"plat-full-{uuid.uuid4().hex[:8]}",
        mode=AgentMode.PLATFORM,
        system_prompt="You are a test bot.",
        agent_model="gpt-4o-mini",
        agent_provider="openai",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "x",
                    "description": "d",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    eval_config = create_test_eval_config(db, agent_id=agent.id)
    run = create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    crud.update_run(
        session=db,
        db_run=run,
        run_in=RunUpdate(status=RunStatus.COMPLETED),
    )
    db.refresh(agent)
    ids = _preset_ids(db, agent)
    assert ids == [
        "improve_prompt",
        "make_concise",
        "add_examples",
        "suggest_from_evals",
        "review_tools",
    ]


def test_whitespace_only_prompt_treated_as_absent(db: Session) -> None:
    """Filtering uses stripped prompt text; empty-after-strip => no prompt presets."""
    agent = create_test_platform_agent(db, system_prompt="real")
    agent.system_prompt = "   \n\t  "
    db.add(agent)
    db.commit()
    db.refresh(agent)
    try:
        ids = _preset_ids(db, agent)
        assert ids == ["help_create_agent"]
    finally:
        # Drop the row — its whitespace-only system_prompt violates AgentBase's
        # mode validator and would break any later test that validates Agent
        # rows through AgentPublic (e.g. the agents list endpoint).
        db.delete(agent)
        db.commit()
