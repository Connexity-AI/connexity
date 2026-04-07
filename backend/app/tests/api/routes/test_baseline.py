"""Tests for baseline run management (CS-30)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models.enums import RunStatus
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_eval_set,
    create_test_run,
    eval_set_members,
)

_PREFIX = f"{settings.API_V1_STR}/runs"


def _setup(db: Session) -> tuple:
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    return agent, eval_set


def _mark_completed(db: Session, run: object) -> None:
    """Set a test run's status to completed so it can be used as a baseline."""
    run.status = RunStatus.COMPLETED  # type: ignore[attr-defined]
    db.add(run)
    db.commit()
    db.refresh(run)


# ── CRUD: set_baseline enforces single baseline per scope ─────────


def test_set_baseline_clears_previous(db: Session) -> None:
    agent, eval_set = _setup(db)
    run1 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    run2 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run1)
    _mark_completed(db, run2)

    crud.set_baseline(session=db, db_run=run1)
    assert run1.is_baseline is True

    crud.set_baseline(session=db, db_run=run2)
    db.refresh(run1)
    assert run2.is_baseline is True
    assert run1.is_baseline is False


def test_set_baseline_different_scope_independent(db: Session) -> None:
    agent, eval_set1 = _setup(db)
    test_case2 = create_test_case_fixture(db)
    eval_set2 = create_test_eval_set(db, members=eval_set_members(test_case2.id))

    run1 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set1.id)
    run2 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set2.id)
    _mark_completed(db, run1)
    _mark_completed(db, run2)

    crud.set_baseline(session=db, db_run=run1)
    crud.set_baseline(session=db, db_run=run2)

    db.refresh(run1)
    db.refresh(run2)
    assert run1.is_baseline is True
    assert run2.is_baseline is True


def test_set_baseline_rejects_non_completed_run(db: Session) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    # run is pending by default
    with pytest.raises(ValueError, match="Only completed runs"):
        crud.set_baseline(session=db, db_run=run)


# ── CRUD: get_baseline_run ────────────────────────────────────────


def test_get_baseline_run_found(db: Session) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run)
    crud.set_baseline(session=db, db_run=run)

    result = crud.get_baseline_run(
        session=db, agent_id=agent.id, eval_set_id=eval_set.id
    )
    assert result is not None
    assert result.id == run.id


def test_get_baseline_run_not_found(db: Session) -> None:
    agent, eval_set = _setup(db)
    result = crud.get_baseline_run(
        session=db, agent_id=agent.id, eval_set_id=eval_set.id
    )
    assert result is None


# ── GET /runs/baseline ────────────────────────────────────────────


def test_get_baseline_endpoint(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run)
    crud.set_baseline(session=db, db_run=run)

    r = client.get(
        f"{_PREFIX}/baseline",
        params={"agent_id": str(agent.id), "eval_set_id": str(eval_set.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(run.id)
    assert r.json()["is_baseline"] is True


def test_get_baseline_filters_by_agent_version(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """GET /runs/baseline?agent_version=N only returns baseline for that version."""
    agent, eval_set = _setup(db)

    # Create a completed run at agent v1 and mark it baseline.
    run_v1 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run_v1)
    crud.set_baseline(session=db, db_run=run_v1)

    base_params = {"agent_id": str(agent.id), "eval_set_id": str(eval_set.id)}

    # Matching version filter → returns the baseline.
    r = client.get(
        f"{_PREFIX}/baseline",
        params={**base_params, "agent_version": 1},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(run_v1.id)
    assert r.json()["agent_version"] == 1

    # Non-matching version filter → 404 (baseline exists but for a different version).
    r = client.get(
        f"{_PREFIX}/baseline",
        params={**base_params, "agent_version": 99},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404

    # Bump agent to v2 via draft→publish and set a new baseline — this clears v1.
    from app.crud.agent_version import create_or_update_draft, publish_draft

    create_or_update_draft(
        session=db,
        agent=agent,
        draft_data={"endpoint_url": "http://v2.example.com/agent"},
        created_by=None,
    )
    publish_draft(session=db, agent=agent, change_description=None, created_by=None)
    db.refresh(agent)
    assert agent.version == 2

    run_v2 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run_v2)
    crud.set_baseline(session=db, db_run=run_v2)

    # agent_version=2 matches → returns v2 baseline.
    r = client.get(
        f"{_PREFIX}/baseline",
        params={**base_params, "agent_version": 2},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(run_v2.id)
    assert r.json()["agent_version"] == 2

    # agent_version=1 → 404 (v1 baseline was cleared when v2 was set).
    r = client.get(
        f"{_PREFIX}/baseline",
        params={**base_params, "agent_version": 1},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_get_baseline_endpoint_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    r = client.get(
        f"{_PREFIX}/baseline",
        params={"agent_id": str(agent.id), "eval_set_id": str(eval_set.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


# ── PATCH /runs/{id} with is_baseline enforcement ────────────────


def test_patch_set_baseline_enforces_single(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run1 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    run2 = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run1)
    _mark_completed(db, run2)

    # Set run1 as baseline
    r = client.patch(
        f"{_PREFIX}/{run1.id}",
        json={"is_baseline": True},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["is_baseline"] is True

    # Set run2 as baseline — run1 should be cleared
    r = client.patch(
        f"{_PREFIX}/{run2.id}",
        json={"is_baseline": True},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["is_baseline"] is True

    # Verify run1 is no longer baseline
    r = client.get(
        f"{_PREFIX}/{run1.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.json()["is_baseline"] is False


def test_patch_set_baseline_rejects_non_completed(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    # run is pending — should be rejected
    r = client.patch(
        f"{_PREFIX}/{run.id}",
        json={"is_baseline": True},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 409
    assert "Only completed runs" in r.json()["detail"]

    # Verify is_baseline was NOT persisted
    db.refresh(run)
    assert run.is_baseline is False


def test_patch_unset_baseline(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    _mark_completed(db, run)
    crud.set_baseline(session=db, db_run=run)

    r = client.patch(
        f"{_PREFIX}/{run.id}",
        json={"is_baseline": False},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["is_baseline"] is False


def test_patch_other_fields_without_baseline(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    """Patching non-baseline fields should not affect baseline state."""
    agent, eval_set = _setup(db)
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)

    r = client.patch(
        f"{_PREFIX}/{run.id}",
        json={"name": "renamed"},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"
    assert r.json()["is_baseline"] is False
