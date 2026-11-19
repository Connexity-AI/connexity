"""Score and critical issues on the Agents list and the agent Overview (10.1992): the same
numbers as `get_agent`, `list_agents` and the Issues page, on invented calls (plan
`plans/2026-11-19-agents-score-critical.md`)."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.services import score as score_service
from app.tests.api.routes.test_issues_list import _signed_in
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    API,
    FULL,
    _agent,
    _booking,
    _call,
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)

MISSING_ZIP = {**FULL, "postalCode": ""}


@pytest.fixture
def onboarded(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes import mcp

    monkeypatch.setattr(score_service, "onboarding_complete", lambda **_: True)
    monkeypatch.setattr(mcp, "onboarding_complete", lambda **_: True)


def _list(client: TestClient, cookies: dict[str, str]) -> list[dict]:
    r = client.get(f"{API}/agents/list", cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _page(client: TestClient, cookies: dict[str, str], agent_id, **params: str) -> dict:  # noqa: ANN001
    r = client.get(f"{API}/agents/{agent_id}/page", cookies=cookies, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_the_list_and_page_answer_score_and_critical_issues_as_mcp_and_issues(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user, cookies = _signed_in(client, db)
    clean = _agent(db, user, "Clean desk")
    failing = _agent(db, user, "Failing desk")
    quiet = _agent(db, user, "Quiet desk")
    _call(db, clean, _booking(1, FULL))
    _call(db, failing, _booking(1, FULL))
    _call(db, failing, _booking(2, MISSING_ZIP))
    # The previous 30 days: the failing agent scored 0.
    _call(db, failing, _booking(3, MISSING_ZIP), days_ago=40)

    rows = _list(client, cookies)

    # Lowest score first, then agents without a score.
    assert [r["name"] for r in rows] == ["Failing desk", "Clean desk", "Quiet desk"]
    by_name = {r["name"]: r for r in rows}
    assert (
        by_name["Failing desk"]["score"],
        by_name["Failing desk"]["score_change"],
    ) == (
        50,
        50,
    )
    assert by_name["Failing desk"]["critical_issues"] == 1
    assert (
        by_name["Clean desk"]["score"],
        by_name["Clean desk"]["critical_issues"],
    ) == (
        100,
        0,
    )
    assert by_name["Quiet desk"]["score"] is None

    page = _page(client, cookies, failing.id)
    assert (page["score"]["score"], page["score"]["change"]) == (50, 50)
    assert page["critical_issues"] == 1
    assert _page(client, cookies, quiet.id)["score"]["score"] is None

    # The assistant's tools answer the same.
    base = f"{API}/mcp/workspaces/{user.company_id}"
    mcp_agent = client.get(f"{base}/agents/{failing.id}", headers=_headers(user)).json()
    assert mcp_agent["data"]["score"]["score"] == 50
    assert mcp_agent["data"]["critical_issues"] == 1
    mcp_rows = client.get(f"{base}/agents", headers=_headers(user)).json()["data"]
    assert {r["name"]: r["critical_issues"] for r in mcp_rows} == {
        "Clean desk": 0,
        "Failing desk": 1,
        "Quiet desk": 0,
    }
    # And the Issues page's Critical tile for that agent.
    issues = client.get(
        f"{API}/issues", cookies=cookies, params={"agent_id": str(failing.id)}
    ).json()
    assert issues["tiles"]["critical"] == 1


def test_no_score_before_onboarding_is_complete(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP))

    (row,) = _list(client, cookies)
    assert row["score"] is None
    assert row["critical_issues"] == 1
    page = _page(client, cookies, agent.id)
    assert page["score"]["score"] is None
    assert "onboarding" in page["score"]["why_none"]


def test_a_picked_version_counts_only_its_calls(
    client: TestClient, db: Session, onboarded: None
) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Invented")
    _call(db, agent, _booking(1, MISSING_ZIP), days_ago=2, version=87)
    _call(db, agent, _booking(2, FULL), days_ago=1, version=88)

    whole = _page(client, cookies, agent.id)
    assert (whole["score"]["score"], whole["critical_issues"]) == (50, 1)
    on_88 = _page(client, cookies, agent.id, version="88")
    assert (on_88["score"]["score"], on_88["critical_issues"]) == (100, 0)
    on_87 = _page(client, cookies, agent.id, version="87")
    assert (on_87["score"]["score"], on_87["critical_issues"]) == (0, 1)
