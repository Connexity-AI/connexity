"""DB-backed tests for ``crud.sync_conversation_flow_agent``.

Requires the real `app_test` Postgres DB (Agent/AgentVersion use
`postgresql.JSONB` and partial indexes, so this cannot run against SQLite).
Uses the session-scoped `db` fixture from `app/tests/conftest.py`.
"""

from sqlmodel import Session

from app import crud
from app.models.imported_platform_config import ImportedPlatformConfig
from app.tests.utils.eval import (
    create_test_case_fixture,
    create_test_platform_agent,
    get_test_company_id,
)


def _flow_metadata(*, flow_version: int, node_count: int) -> dict[str, object]:
    return {
        "retell_response_engine": "conversation-flow",
        "conversation_flow_id": "flow_1",
        "conversation_flow_version": flow_version,
        "conversation_flow_global_prompt": "Be helpful.",
        "conversation_flow_nodes": [{"id": f"n{i}"} for i in range(node_count)],
        "conversation_flow_edges": [],
    }


def test_sync_publishes_new_version_with_fresh_metadata(db: Session) -> None:
    company_id = get_test_company_id(db)
    agent = create_test_platform_agent(
        db,
        system_prompt="This agent is backed by a Retell Conversation Flow.",
        company_id=company_id,
    )
    agent.agent_model = "conversation-flow"
    agent.agent_metadata = _flow_metadata(flow_version=7, node_count=1)
    db.add(agent)
    db.commit()
    db.refresh(agent)

    imported = ImportedPlatformConfig(
        system_prompt="This agent is backed by a Retell Conversation Flow.\n\nBe extra helpful now.",
        agent_model="conversation-flow",
        tools=None,
        agent_metadata=_flow_metadata(flow_version=9, node_count=2),
    )

    updated_agent, new_version = crud.sync_conversation_flow_agent(
        session=db,
        db_agent=agent,
        imported=imported,
        version_description="Synced from Retell (v7 → v9)",
        created_by=None,
    )

    # A new published version was created (v1 was the initial create version).
    assert new_version.version == 2
    assert new_version.is_active is True
    assert new_version.system_prompt == imported.system_prompt
    assert new_version.version_description == "Synced from Retell (v7 → v9)"

    # The agent row's live fields reflect the fresh flow snapshot.
    assert updated_agent.system_prompt == imported.system_prompt
    assert updated_agent.agent_metadata is not None
    assert updated_agent.agent_metadata["conversation_flow_version"] == 9
    assert len(updated_agent.agent_metadata["conversation_flow_nodes"]) == 2

    # The old v1 is no longer the active version.
    old_version = crud.get_agent_version(session=db, agent_id=agent.id, version=1)
    assert old_version is not None
    assert old_version.is_active is False


def test_sync_leaves_test_cases_untouched(db: Session) -> None:
    company_id = get_test_company_id(db)
    agent = create_test_platform_agent(
        db,
        system_prompt="This agent is backed by a Retell Conversation Flow.",
        company_id=company_id,
    )
    agent.agent_model = "conversation-flow"
    agent.agent_metadata = _flow_metadata(flow_version=7, node_count=1)
    db.add(agent)
    db.commit()
    db.refresh(agent)

    test_case = create_test_case_fixture(
        db,
        company_id=company_id,
        agent_id=agent.id,
        persona_context=(
            "[Persona type] x [Description] y [Behavioral instructions] z"
        ),
        expected_outcomes=["Agent MUST greet"],
    )

    imported = ImportedPlatformConfig(
        system_prompt="Updated prompt.",
        agent_model="conversation-flow",
        tools=None,
        agent_metadata=_flow_metadata(flow_version=9, node_count=1),
    )
    crud.sync_conversation_flow_agent(
        session=db,
        db_agent=agent,
        imported=imported,
        version_description=None,
        created_by=None,
    )

    still_there = crud.get_test_case(session=db, test_case_id=test_case.id)
    assert still_there is not None
    assert still_there.agent_id == agent.id
