import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import RunStatus, RunUpdate
from app.models.enums import AgentMode
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_set,
    create_test_run,
    eval_set_members,
)


def _setup(db: Session) -> tuple:
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    return agent, eval_set


# ── Basic CRUD endpoints ──────────────────────────────────────────


def test_create_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    data = {
        "agent_id": str(agent.id),
        "agent_endpoint_url": "http://localhost:8080/agent",
        "eval_set_id": str(eval_set.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/runs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["agent_id"] == str(agent.id)
    assert result["status"] == "pending"


def test_create_run_agent_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    data = {
        "agent_id": str(uuid.uuid4()),
        "agent_endpoint_url": "http://localhost:8080/agent",
        "eval_set_id": str(eval_set.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/runs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_create_run_platform_agent_without_endpoint_url(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    agent_r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json={
            "name": "Platform run agent",
            "mode": AgentMode.PLATFORM.value,
            "system_prompt": "You are helpful.",
            "agent_model": "gpt-4o-mini",
            "agent_provider": "openai",
        },
        cookies=superuser_auth_cookies,
    )
    assert agent_r.status_code == 200
    agent_id = agent_r.json()["id"]

    data = {
        "agent_id": agent_id,
        "eval_set_id": str(eval_set.id),
        "config": {
            "agent_simulator": {"model": "gpt-4o", "temperature": 0.2},
        },
    }
    r = client.post(
        f"{settings.API_V1_STR}/runs/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["agent_mode"] == AgentMode.PLATFORM.value
    assert body["agent_model"] == "gpt-4o"
    assert body["agent_provider"] == "openai"
    assert body["agent_endpoint_url"] is None
    assert body["agent_system_prompt"] == "You are helpful."


def test_list_runs(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_runs_filter_by_agent(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        params={"agent_id": str(agent.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(item["agent_id"] == str(agent.id) for item in data["data"])


def test_list_runs_filter_by_status(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/runs/",
        params={"status": "pending"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_get_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.get(
        f"{settings.API_V1_STR}/runs/{run.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(run.id)


def test_get_run_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/runs/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.patch(
        f"{settings.API_V1_STR}/runs/{run.id}",
        json={"status": "running"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_delete_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.delete(
        f"{settings.API_V1_STR}/runs/{run.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


# ── POST /runs/{run_id}/execute ────────────────────────────────────


@patch(
    "app.api.routes.runs.execute_run",
    new_callable=AsyncMock,
)
def test_execute_pending_run(
    _mock_exec: AsyncMock,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.post(
        f"{settings.API_V1_STR}/runs/{run.id}/execute",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 202
    assert r.json()["id"] == str(run.id)


@patch(
    "app.api.routes.runs.execute_run",
    new_callable=AsyncMock,
)
def test_execute_failed_run(
    _mock_exec: AsyncMock,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(session=db, db_run=run, run_in=RunUpdate(status=RunStatus.FAILED))
    r = client.post(
        f"{settings.API_V1_STR}/runs/{run.id}/execute",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 202


def test_execute_running_run_fails(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(session=db, db_run=run, run_in=RunUpdate(status=RunStatus.RUNNING))
    r = client.post(
        f"{settings.API_V1_STR}/runs/{run.id}/execute",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 400


def test_execute_completed_run_fails(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(
        session=db, db_run=run, run_in=RunUpdate(status=RunStatus.COMPLETED)
    )
    r = client.post(
        f"{settings.API_V1_STR}/runs/{run.id}/execute",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 400


def test_execute_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/runs/{uuid.uuid4()}/execute",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


# ── POST /runs/{run_id}/cancel ─────────────────────────────────────


def test_cancel_pending_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    r = client.post(
        f"{settings.API_V1_STR}/runs/{run.id}/cancel",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200


def test_cancel_running_run_without_active_task(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """A run in RUNNING status but not tracked by RunManager (e.g. orphaned)."""
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(session=db, db_run=run, run_in=RunUpdate(status=RunStatus.RUNNING))
    r = client.post(
        f"{settings.API_V1_STR}/runs/{run.id}/cancel",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/runs/{uuid.uuid4()}/cancel",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


# ── GET /runs/{run_id}/stream ──────────────────────────────────────


def test_stream_finished_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """A completed run returns a snapshot event then closes."""
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    crud.update_run(
        session=db, db_run=run, run_in=RunUpdate(status=RunStatus.COMPLETED)
    )
    r = client.get(
        f"{settings.API_V1_STR}/runs/{run.id}/stream",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert "event: snapshot" in body
    assert "event: stream_closed" in body


def test_stream_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/runs/{uuid.uuid4()}/stream",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


# ── POST /runs/ with auto_execute ──────────────────────────────────


@patch(
    "app.api.routes.runs.execute_run",
    new_callable=AsyncMock,
)
def test_create_run_with_auto_execute(
    _mock_exec: AsyncMock,
    client: TestClient,
    superuser_auth_cookies: dict[str, str],
    db: Session,
) -> None:
    agent, eval_set = _setup(db)
    data = {
        "agent_id": str(agent.id),
        "agent_endpoint_url": "http://localhost:8080/agent",
        "eval_set_id": str(eval_set.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/runs/",
        json=data,
        params={"auto_execute": True},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["agent_id"] == str(agent.id)


def test_create_run_without_auto_execute(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    data = {
        "agent_id": str(agent.id),
        "agent_endpoint_url": "http://localhost:8080/agent",
        "eval_set_id": str(eval_set.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/runs/",
        json=data,
        params={"auto_execute": False},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
