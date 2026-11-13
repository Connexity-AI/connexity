"""The fixed categories, and `list_categories` through MCP."""

import uuid
from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app import crud
from app.core import security
from app.core.config import settings
from app.models import Agent, Category, Issue, User, UserCreate
from app.models.enums import IssueState
from app.services.checks.registry import CHECKS
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"
ISSUER = "https://backend.example.com"

# Design prompt 06, in its order.
DESIGN = [
    ("Greeting and identification", "behaviour"),
    ("Information collection", "behaviour"),
    ("Booking", "behaviour"),
    ("Rescheduling and cancelling", "behaviour"),
    ("Pricing and quotes", "behaviour"),
    ("Objection handling", "behaviour"),
    ("Transfers and escalation", "behaviour"),
    ("Compliance and privacy", "behaviour"),
    ("Conversation flow quality", "behaviour"),
    ("Ending the call", "behaviour"),
    ("Responsiveness", "technical"),
    ("Tools and integrations", "technical"),
    ("Speech recognition", "technical"),
    ("Other", "behaviour"),
]


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", ISSUER)
    yield


def _person(db: Session) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )


def _headers(user: User) -> dict[str, str]:
    token, _ = security.create_oauth_access_token(
        subject=user.id,
        audience=MCP_URL,
        issuer=ISSUER,
        client_id="claude-code",
        scope="mcp:access",
        expires_delta=timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


def test_the_fourteen_categories_are_seeded_in_order(db: Session) -> None:
    categories = crud.list_categories(session=db)

    assert [(c.name, c.kind) for c in categories] == DESIGN
    assert [c.position for c in categories] == list(range(1, 15))
    assert len({c.key for c in categories}) == 14


def test_every_check_names_a_category_that_exists(db: Session) -> None:
    keys = {c.key for c in crud.list_categories(session=db)}

    for check in CHECKS:
        assert check.category in keys, check.type


def test_a_category_in_use_cannot_be_deleted(db: Session) -> None:
    user = _person(db)
    agent = Agent(company_id=user.company_id, name="Invented")
    db.add(agent)
    db.commit()
    booking = db.exec(select(Category).where(Category.key == "booking")).one()
    db.add(
        Issue(
            company_id=user.company_id,
            agent_id=agent.id,
            check_type="invented",
            category_id=booking.id,
            key=uuid.uuid4().hex,
            state=IssueState.OPEN,
        )
    )
    db.commit()

    db.delete(booking)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_list_categories_answers_the_set_in_order(
    client: TestClient, db: Session
) -> None:
    user = _person(db)

    r = client.get(
        f"{API}/mcp/workspaces/{user.company_id}/categories", headers=_headers(user)
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert [(c["name"], c["kind"]) for c in body["data"]] == DESIGN
    assert body["data"][11] == {
        "key": "tools_and_integrations",
        "name": "Tools and integrations",
        "position": 12,
        "kind": "technical",
    }
    assert body["guide"] == "connexity://guides/categories"
    assert any("same for every workspace" in rule for rule in body["rules"])


def test_a_renamed_category_shows_its_new_name(client: TestClient, db: Session) -> None:
    user = _person(db)
    db.execute(
        update(Category)
        .where(Category.key == "other")  # type: ignore[arg-type]
        .values(name="Everything else")
    )
    db.commit()
    try:
        r = client.get(
            f"{API}/mcp/workspaces/{user.company_id}/categories",
            headers=_headers(user),
        )
        assert r.json()["data"][-1]["name"] == "Everything else"
    finally:
        db.execute(
            update(Category)
            .where(Category.key == "other")  # type: ignore[arg-type]
            .values(name="Other")
        )
        db.commit()


def test_another_workspace_is_not_found(client: TestClient, db: Session) -> None:
    user = _person(db)
    other = _person(db)

    r = client.get(
        f"{API}/mcp/workspaces/{other.company_id}/categories", headers=_headers(user)
    )

    assert r.status_code == 404
