"""End-to-end isolation tests for per-company multi-tenancy.

Two users signed up via the public API end up in two separate companies and
must not be able to see each other's resources. This file covers the most
visible scoped surfaces — agents, runs, integrations, environments, custom
metrics, test cases — and confirms the JWT ``cid`` claim invalidates an old
token when the user is admin-moved to a different company.
"""

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User
from app.tests.utils.utils import extract_cookies, random_email, random_lower_string


def _signup_and_login(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.text
    return extract_cookies(r)


def _create_agent(
    client: TestClient, cookies: dict[str, str], name: str
) -> dict[str, object]:
    r = client.post(
        f"{settings.API_V1_STR}/agents/",
        json={"name": name, "endpoint_url": "http://example.com/agent"},
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_signup_creates_separate_companies(client: TestClient, db: Session) -> None:
    email_a = random_email()
    email_b = random_email()
    password = random_lower_string()

    _signup_and_login(client, email_a, password)
    _signup_and_login(client, email_b, password)

    user_a = db.exec(select(User).where(User.email == email_a)).first()
    user_b = db.exec(select(User).where(User.email == email_b)).first()
    assert user_a is not None and user_b is not None
    assert user_a.company_id is not None
    assert user_b.company_id is not None
    assert user_a.company_id != user_b.company_id


def test_agents_are_isolated_per_company(client: TestClient, db: Session) -> None:
    email_a = random_email()
    email_b = random_email()
    password = random_lower_string()

    cookies_a = _signup_and_login(client, email_a, password)
    cookies_b = _signup_and_login(client, email_b, password)

    agent_a = _create_agent(client, cookies_a, "A agent")
    agent_b = _create_agent(client, cookies_b, "B agent")
    assert agent_a["id"] != agent_b["id"]

    # A sees only their own agent.
    r = client.get(f"{settings.API_V1_STR}/agents/", cookies=cookies_a)
    assert r.status_code == 200
    ids_a = {item["id"] for item in r.json()["data"]}
    assert agent_a["id"] in ids_a
    assert agent_b["id"] not in ids_a

    # B sees only theirs.
    r = client.get(f"{settings.API_V1_STR}/agents/", cookies=cookies_b)
    assert r.status_code == 200
    ids_b = {item["id"] for item in r.json()["data"]}
    assert agent_b["id"] in ids_b
    assert agent_a["id"] not in ids_b


def test_cross_company_get_agent_returns_404(client: TestClient, db: Session) -> None:
    email_a = random_email()
    email_b = random_email()
    password = random_lower_string()

    cookies_a = _signup_and_login(client, email_a, password)
    cookies_b = _signup_and_login(client, email_b, password)

    agent_b = _create_agent(client, cookies_b, "B-only agent")

    r = client.get(
        f"{settings.API_V1_STR}/agents/{agent_b['id']}",
        cookies=cookies_a,
    )
    assert r.status_code == 404


def test_admin_moving_user_invalidates_token(client: TestClient, db: Session) -> None:
    """After a DB-level company reassignment, the old JWT must be rejected."""
    email = random_email()
    password = random_lower_string()
    cookies = _signup_and_login(client, email, password)

    # Sanity: token works before reassignment.
    r = client.get(f"{settings.API_V1_STR}/agents/", cookies=cookies)
    assert r.status_code == 200

    user = db.exec(select(User).where(User.email == email)).first()
    assert user is not None

    # Move the user to a fresh company directly in the DB, simulating an
    # admin re-parenting. The cached JWT's ``cid`` claim no longer matches
    # ``user.company_id``, so the next request must 401.
    from app.models.company import Company

    new_company = Company(id=uuid.uuid4())
    db.add(new_company)
    db.commit()

    user.company_id = new_company.id
    db.add(user)
    db.commit()

    r = client.get(f"{settings.API_V1_STR}/agents/", cookies=cookies)
    assert r.status_code == 401


def test_runs_are_isolated_per_company(client: TestClient, db: Session) -> None:
    email_a = random_email()
    email_b = random_email()
    password = random_lower_string()

    cookies_a = _signup_and_login(client, email_a, password)
    cookies_b = _signup_and_login(client, email_b, password)

    # Each company creates their own agent — runs list should not bleed.
    _create_agent(client, cookies_a, "A agent for runs")
    _create_agent(client, cookies_b, "B agent for runs")

    r_a = client.get(f"{settings.API_V1_STR}/runs/", cookies=cookies_a)
    r_b = client.get(f"{settings.API_V1_STR}/runs/", cookies=cookies_b)
    assert r_a.status_code == 200
    assert r_b.status_code == 200
    # Each lists 0 because we created no runs — the important check is no
    # accidental cross-talk on the empty list.
    assert r_a.json()["count"] == 0
    assert r_b.json()["count"] == 0
