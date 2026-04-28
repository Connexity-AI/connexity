"""Tests for agent config versioning with draft/publish lifecycle (CS-71 + CS-80)."""

import threading
import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models import AgentCreate, AgentMode, AgentUpdate
from app.tests.utils.eval import (
    create_test_agent,
    create_test_eval_config,
    create_test_run,
)

# ── Basic versioning ────────────────────────────────────────────────


def test_create_agent_has_version_one(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    data = {"name": "V1 Agent", "endpoint_url": "http://example.com/agent"}
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1
    assert body["has_draft"] is False


def test_patch_versionable_field_creates_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """PATCH with versionable fields creates a draft instead of auto-publishing."""
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={
            "endpoint_url": "http://new.example/agent",
            "change_description": "new endpoint",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    # Version should stay at 1 (draft, not published)
    assert body["version"] == 1
    assert body["has_draft"] is True
    # Only 1 published version still exists
    items, count = crud.list_agent_versions(session=db, agent_id=agent.id)
    assert count == 1


def test_patch_identity_only_no_version_bump(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"name": "Renamed Only"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 1
    assert r.json()["has_draft"] is False
    _items, count = crud.list_agent_versions(session=db, agent_id=agent.id)
    assert count == 1


def test_list_versions_and_get_one(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Create agent, draft, publish → 2 published versions."""
    agent = create_test_agent(db)
    # Create draft
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://v2.example/agent"},
        cookies=auth_cookies,
    )
    # Publish draft
    client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={},
        cookies=auth_cookies,
    )
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert data["data"][0]["version"] == 2

    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions/1",
        cookies=auth_cookies,
    )
    assert r2.status_code == 200
    assert r2.json()["version"] == 1


def test_versions_diff(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    # Create draft + publish to get version 2
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://diff.example/agent"},
        cookies=auth_cookies,
    )
    client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={},
        cookies=auth_cookies,
    )
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["from_version"] == 1
    assert body["to_version"] == 2
    assert body["endpoint_url_changed"] is not None


def test_rollback_creates_new_version(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    # Draft + publish to get version 2
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://rolled.example/agent"},
        cookies=auth_cookies,
    )
    client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={},
        cookies=auth_cookies,
    )
    # Rollback to version 1
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/rollback",
        json={"version": 1, "change_description": "back to v1"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    rolled = r.json()
    assert rolled["version"] == 3
    assert rolled["endpoint_url"] == agent.endpoint_url
    db.expire_all()
    agent_db = crud.get_agent(session=db, agent_id=agent.id)
    assert agent_db is not None
    assert agent_db.version == 3
    _items, count = crud.list_agent_versions(session=db, agent_id=agent.id)
    assert count == 3


def test_list_runs_filter_agent_version(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    eval_config = create_test_eval_config(db, agent_id=agent.id)
    create_test_run(db, agent_id=agent.id, eval_config_id=eval_config.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        params={"agent_id": str(agent.id), "agent_version": 1},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    for item in r.json()["data"]:
        if item["agent_id"] == str(agent.id):
            assert item["agent_version"] == 1


def test_concurrent_updates_distinct_drafts(db: Session) -> None:
    """Concurrent draft updates should be serialized via row-level locking."""
    agent_in = AgentCreate(
        name=f"concurrent-{uuid.uuid4().hex[:8]}",
        endpoint_url="http://localhost:9999/agent",
    )
    agent = crud.create_agent(session=db, agent_in=agent_in)
    aid = agent.id
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def work(url: str) -> None:
        try:
            with Session(engine) as session:
                barrier.wait()
                locked = crud.get_agent(session=session, agent_id=aid)
                assert locked is not None
                crud.update_agent(
                    session=session,
                    db_agent=locked,
                    agent_in=AgentUpdate(endpoint_url=url),
                    created_by=None,
                )
        except BaseException as e:
            errors.append(e)

    t1 = threading.Thread(target=work, args=("http://c1.example/agent",))
    t2 = threading.Thread(target=work, args=("http://c2.example/agent",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert not errors
    with Session(engine) as session:
        final = crud.get_agent(session=session, agent_id=aid)
        assert final is not None
        # Version should still be 1 (changes are in draft)
        assert final.version == 1
        assert final.has_draft is True


def test_platform_agent_version_on_prompt_change(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json={
            "name": "Platform v",
            "mode": AgentMode.PLATFORM.value,
            "system_prompt": "A",
            "agent_model": "gpt-4o-mini",
            "agent_provider": "openai",
        },
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    aid = r.json()["id"]
    # PATCH versionable field creates draft
    r2 = client.patch(
        f"{settings.API_V1_STR}/agents/{aid}",
        json={"system_prompt": "B"},
        cookies=auth_cookies,
    )
    assert r2.status_code == 200
    assert r2.json()["version"] == 1
    assert r2.json()["has_draft"] is True
    # Publish to get version 2
    r3 = client.post(
        f"{settings.API_V1_STR}/agents/{aid}/publish",
        json={"change_description": "Updated prompt to B"},
        cookies=auth_cookies,
    )
    assert r3.status_code == 200
    assert r3.json()["version"] == 2
    assert r3.json()["system_prompt"] == "B"


# ── Draft/Publish lifecycle tests ──────────────────────────────────


def test_put_draft_creates_new_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://draft.example/agent"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    draft = r.json()
    assert draft["status"] == "draft"
    assert draft["version"] is None
    assert draft["endpoint_url"] == "http://draft.example/agent"
    # Other fields should come from published agent config
    assert draft["mode"] == "endpoint"


def test_put_draft_merges_into_existing(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    # First draft
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://draft.example/agent"},
        cookies=auth_cookies,
    )
    # Merge into existing draft
    r = client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"agent_provider": "openai"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    draft = r.json()
    # Both fields should be present
    assert draft["endpoint_url"] == "http://draft.example/agent"
    assert draft["agent_provider"] == "openai"


def test_get_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    # No draft yet → 404
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        cookies=auth_cookies,
    )
    assert r.status_code == 404

    # Create draft
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://draft.example/agent"},
        cookies=auth_cookies,
    )
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "draft"


def test_publish_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    # Create draft
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://published.example/agent"},
        cookies=auth_cookies,
    )
    # Publish
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={"change_description": "Updated endpoint"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    published = r.json()
    assert published["status"] == "published"
    assert published["version"] == 2
    assert published["endpoint_url"] == "http://published.example/agent"
    assert published["change_description"] == "Updated endpoint"

    # Agent should reflect published config
    db.expire_all()
    agent_db = crud.get_agent(session=db, agent_id=agent.id)
    assert agent_db is not None
    assert agent_db.version == 2
    assert agent_db.has_draft is False
    assert agent_db.endpoint_url == "http://published.example/agent"


def test_publish_no_draft_returns_409(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={},
        cookies=auth_cookies,
    )
    assert r.status_code == 409


def test_publish_draft_validates_mode(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Publishing a draft with invalid mode config should fail."""
    agent = create_test_agent(db)
    # Create draft that switches to platform mode without system_prompt/model
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"mode": "platform"},
        cookies=auth_cookies,
    )
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/publish",
        json={},
        cookies=auth_cookies,
    )
    assert r.status_code == 422


def test_discard_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    # Create draft
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://discarded.example/agent"},
        cookies=auth_cookies,
    )
    # Discard
    r = client.delete(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        cookies=auth_cookies,
    )
    assert r.status_code == 204

    # Draft should be gone
    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        cookies=auth_cookies,
    )
    assert r2.status_code == 404

    # Agent should not have draft flag
    db.expire_all()
    agent_db = crud.get_agent(session=db, agent_id=agent.id)
    assert agent_db is not None
    assert agent_db.has_draft is False


def test_discard_nonexistent_draft_is_idempotent(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Discarding when no draft exists should succeed (204)."""
    agent = create_test_agent(db)
    r = client.delete(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        cookies=auth_cookies,
    )
    assert r.status_code == 204


def test_agent_live_fields_reflect_published_not_draft(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """Agent's versionable fields always reflect latest PUBLISHED version, not draft."""
    agent = create_test_agent(db)
    original_url = agent.endpoint_url
    # Create draft with different config
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://draft-only.example/agent"},
        cookies=auth_cookies,
    )
    # Get agent — should still have original config
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["endpoint_url"] == original_url
    assert r.json()["has_draft"] is True


def test_list_versions_excludes_drafts(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    """List versions should only return published versions."""
    agent = create_test_agent(db)
    # Create a draft
    client.put(
        f"{settings.API_V1_STR}/agents/{agent.id}/draft",
        json={"endpoint_url": "http://draft.example/agent"},
        cookies=auth_cookies,
    )
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    # Only the initial published version should appear
    assert data["count"] == 1
    assert all(v["status"] == "published" for v in data["data"])


def test_full_draft_publish_cycle(
    client: TestClient, auth_cookies: dict[str, str]
) -> None:
    """Full lifecycle: create → draft → iterate → publish → verify."""
    # Create agent
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json={"name": "Lifecycle Agent", "endpoint_url": "http://v1.example/agent"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    aid = r.json()["id"]

    # Step 1: Create draft
    r = client.put(
        f"{settings.API_V1_STR}/agents/{aid}/draft",
        json={"endpoint_url": "http://wip.example/agent"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200

    # Step 2: Iterate on draft
    r = client.put(
        f"{settings.API_V1_STR}/agents/{aid}/draft",
        json={"endpoint_url": "http://v2.example/agent"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["endpoint_url"] == "http://v2.example/agent"

    # Step 3: Publish
    r = client.post(
        f"{settings.API_V1_STR}/agents/{aid}/publish",
        json={"change_description": "Finalized v2 endpoint"},
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["status"] == "published"

    # Verify agent reflects published config
    r = client.get(
        f"{settings.API_V1_STR}/agents/{aid}",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["has_draft"] is False
    assert r.json()["endpoint_url"] == "http://v2.example/agent"

    # Verify version history
    r = client.get(
        f"{settings.API_V1_STR}/agents/{aid}/versions",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] == 2


def test_version_public_includes_status(
    client: TestClient, auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions/1",
        cookies=auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "published"
