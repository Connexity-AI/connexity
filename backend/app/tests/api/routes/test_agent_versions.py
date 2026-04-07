"""Tests for agent config versioning (CS-71)."""

import threading
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.models import AgentCreate, AgentMode, AgentUpdate
from app.models.agent_version import AgentVersion
from app.tests.utils.eval import (
    create_test_agent,
    create_test_eval_set,
    create_test_run,
)


def test_create_agent_has_version_one(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    data = {"name": "V1 Agent", "endpoint_url": "http://example.com/agent"}
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1


def test_patch_versionable_field_bumps_version(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={
            "endpoint_url": "http://new.example/agent",
            "change_description": "new endpoint",
        },
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    items, count = crud.list_agent_versions(session=db, agent_id=agent.id)
    assert count == 2


def test_patch_identity_only_no_version_bump(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    r = client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"name": "Renamed Only"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["version"] == 1
    _items, count = crud.list_agent_versions(session=db, agent_id=agent.id)
    assert count == 1


def test_list_versions_and_get_one(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"endpoint_url": "http://v2.example/agent"},
        cookies=superuser_auth_cookies,
    )
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert data["data"][0]["version"] == 2

    r2 = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions/1",
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    assert r2.json()["version"] == 1


def test_versions_diff(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"endpoint_url": "http://diff.example/agent"},
        cookies=superuser_auth_cookies,
    )
    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent.id}/versions/diff",
        params={"from_version": 1, "to_version": 2},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["from_version"] == 1
    assert body["to_version"] == 2
    assert body["endpoint_url_changed"] is not None


def test_rollback_creates_new_version(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    client.patch(
        f"{settings.API_V1_STR}/agents/{agent.id}",
        json={"endpoint_url": "http://rolled.example/agent"},
        cookies=superuser_auth_cookies,
    )
    r = client.post(
        f"{settings.API_V1_STR}/agents/{agent.id}/rollback",
        json={"version": 1, "change_description": "back to v1"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    rolled = r.json()
    assert rolled["version"] == 3
    assert rolled["endpoint_url"] == agent.endpoint_url
    # HTTP client uses its own DB session; expire so we reload agent row.
    db.expire_all()
    agent_db = crud.get_agent(session=db, agent_id=agent.id)
    assert agent_db is not None
    assert agent_db.version == 3
    _items, count = crud.list_agent_versions(session=db, agent_id=agent.id)
    assert count == 3


def test_list_runs_filter_agent_version(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent = create_test_agent(db)
    eval_set = create_test_eval_set(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        params={"agent_id": str(agent.id), "agent_version": 1},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    for item in r.json()["data"]:
        if item["agent_id"] == str(agent.id):
            assert item["agent_version"] == 1


def test_concurrent_updates_distinct_versions(db: Session) -> None:
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
        assert final.version == 3
        cnt = session.exec(
            select(func.count())
            .select_from(AgentVersion)
            .where(AgentVersion.agent_id == aid)
        ).one()
        assert cnt == 3


def test_platform_agent_version_on_prompt_change(
    client: TestClient, superuser_auth_cookies: dict[str, str]
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
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    aid = r.json()["id"]
    r2 = client.patch(
        f"{settings.API_V1_STR}/agents/{aid}",
        json={"system_prompt": "B"},
        cookies=superuser_auth_cookies,
    )
    assert r2.status_code == 200
    assert r2.json()["version"] == 2
