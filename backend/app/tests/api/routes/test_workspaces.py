import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User, WorkspaceMember
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR


def _sign_up(client: TestClient, email: str) -> dict[str, str]:
    password = random_lower_string()
    r = client.post(f"{API}/users/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    r = client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return {settings.AUTH_COOKIE: r.json()["access_token"]}


def _agent_names(client: TestClient, cookies: dict[str, str]) -> list[str]:
    r = client.get(f"{API}/agents/", cookies=cookies)
    assert r.status_code == 200, r.text
    return [agent["name"] for agent in r.json()["data"]]


def test_sign_up_creates_one_open_workspace_named_from_the_domain(
    client: TestClient,
) -> None:
    suffix = random_lower_string()[:6]
    cookies = _sign_up(client, f"ann@bright-dental-{suffix}.com")

    r = client.get(f"{API}/workspaces/", cookies=cookies)

    assert r.status_code == 200
    assert [(w["name"], w["is_open"]) for w in r.json()] == [
        (f"Bright Dental {suffix.capitalize()}", True)
    ]


def test_create_switch_and_scope(client: TestClient) -> None:
    cookies = _sign_up(client, random_email())
    r = client.post(
        f"{API}/agents/",
        json={"name": "First workspace agent", "endpoint_url": "http://example.com/a"},
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    first_id = next(
        w["id"] for w in client.get(f"{API}/workspaces/", cookies=cookies).json()
    )

    created = client.post(
        f"{API}/workspaces/", json={"name": "  Kestrel Plumbing "}, cookies=cookies
    )
    assert created.status_code == 200, created.text
    second = created.json()
    assert second["name"] == "Kestrel Plumbing"
    assert second["is_open"] is False
    assert _agent_names(client, cookies) == ["First workspace agent"]

    opened = client.post(f"{API}/workspaces/{second['id']}/open", cookies=cookies)
    assert opened.status_code == 200, opened.text
    second_cookies = {settings.AUTH_COOKIE: opened.json()["access_token"]}
    assert _agent_names(client, second_cookies) == []
    listed = client.get(f"{API}/workspaces/", cookies=second_cookies).json()
    assert {w["name"]: w["is_open"] for w in listed}["Kestrel Plumbing"] is True

    # The old cookie still works and follows the workspace open now (accepted:
    # switching in one tab switches the others).
    assert _agent_names(client, cookies) == []

    back = client.post(f"{API}/workspaces/{first_id}/open", cookies=second_cookies)
    assert back.status_code == 200
    assert _agent_names(
        client, {settings.AUTH_COOKIE: back.json()["access_token"]}
    ) == ["First workspace agent"]


def test_opening_a_workspace_you_do_not_belong_to_is_not_found(
    client: TestClient,
) -> None:
    ann = _sign_up(client, random_email())
    bob = _sign_up(client, random_email())
    bobs_workspace = client.get(f"{API}/workspaces/", cookies=bob).json()[0]["id"]

    for workspace_id in (bobs_workspace, str(uuid.uuid4())):
        r = client.post(f"{API}/workspaces/{workspace_id}/open", cookies=ann)
        assert r.status_code == 404


def test_a_blank_workspace_name_is_refused(client: TestClient) -> None:
    cookies = _sign_up(client, random_email())

    for name in ("", "   ", "x" * 256):
        r = client.post(f"{API}/workspaces/", json={"name": name}, cookies=cookies)
        assert r.status_code == 422


def test_losing_membership_of_the_open_workspace_ends_the_session(
    client: TestClient, db: Session
) -> None:
    email = random_email()
    cookies = _sign_up(client, email)
    user = db.exec(select(User).where(User.email == email)).one()
    member = db.get(WorkspaceMember, (user.id, user.company_id))
    assert member is not None

    db.delete(member)
    db.commit()

    r = client.get(f"{API}/agents/", cookies=cookies)
    assert r.status_code == 401


def test_workspaces_are_listed_by_name_ignoring_case(client: TestClient) -> None:
    cookies = _sign_up(client, f"ann@zeta-{random_lower_string()[:6]}.com")
    for name in ("beta clinic", "Alpha Dental"):
        assert (
            client.post(
                f"{API}/workspaces/", json={"name": name}, cookies=cookies
            ).status_code
            == 200
        )

    names = [
        w["name"] for w in client.get(f"{API}/workspaces/", cookies=cookies).json()
    ]

    assert names[:2] == ["Alpha Dental", "beta clinic"]
    assert names[2].startswith("Zeta ")


def test_sign_up_refuses_an_email_that_differs_only_in_case(client: TestClient) -> None:
    email = random_email()
    _sign_up(client, email)

    r = client.post(
        f"{API}/users/signup",
        json={"email": email.upper(), "password": random_lower_string()},
    )

    assert r.status_code == 400
