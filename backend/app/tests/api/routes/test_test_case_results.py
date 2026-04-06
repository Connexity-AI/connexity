import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.tests.utils.eval import (
    create_test_agent,
    create_test_case_fixture,
    create_test_case_result_fixture,
    create_test_eval_set,
    create_test_run,
    eval_set_members,
)


def _setup(db: Session) -> tuple:
    agent = create_test_agent(db)
    test_case = create_test_case_fixture(db)
    eval_set = create_test_eval_set(db, members=eval_set_members(test_case.id))
    run = create_test_run(db, agent_id=agent.id, eval_set_id=eval_set.id)
    return run, test_case


def test_create_test_case_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, test_case = _setup(db)
    data = {
        "run_id": str(run.id),
        "test_case_id": str(test_case.id),
    }
    r = client.post(
        f"{settings.API_V1_STR}/test-case-results/",
        json=data,
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    result = r.json()
    assert result["run_id"] == str(run.id)
    assert result["test_case_id"] == str(test_case.id)


def test_list_test_case_results(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, test_case = _setup(db)
    create_test_case_result_fixture(db, run_id=run.id, test_case_id=test_case.id)
    r = client.get(
        f"{settings.API_V1_STR}/test-case-results/",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_list_test_case_results_filter_by_run(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, test_case = _setup(db)
    create_test_case_result_fixture(db, run_id=run.id, test_case_id=test_case.id)
    r = client.get(
        f"{settings.API_V1_STR}/test-case-results/",
        params={"run_id": str(run.id)},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(item["run_id"] == str(run.id) for item in data["data"])


def test_get_test_case_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, test_case = _setup(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    r = client.get(
        f"{settings.API_V1_STR}/test-case-results/{result.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    assert r.json()["id"] == str(result.id)


def test_get_test_case_result_not_found(
    client: TestClient, superuser_auth_cookies: dict[str, str]
) -> None:
    r = client.get(
        f"{settings.API_V1_STR}/test-case-results/{uuid.uuid4()}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 404


def test_update_test_case_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, test_case = _setup(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    r = client.patch(
        f"{settings.API_V1_STR}/test-case-results/{result.id}",
        json={"passed": True, "turn_count": 3, "total_latency_ms": 500},
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["passed"] is True
    assert updated["turn_count"] == 3
    assert updated["total_latency_ms"] == 500


def test_delete_test_case_result(
    client: TestClient, superuser_auth_cookies: dict[str, str], db: Session
) -> None:
    run, test_case = _setup(db)
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    r = client.delete(
        f"{settings.API_V1_STR}/test-case-results/{result.id}",
        cookies=superuser_auth_cookies,
    )
    assert r.status_code == 200
