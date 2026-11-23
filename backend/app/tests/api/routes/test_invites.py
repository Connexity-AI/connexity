"""Invites to an agency, joining from one, and what "can approve" refuses.

Every request goes through the API. The email is captured where it would be handed to
SMTP, and the link's token is read from it, as the invited person would.
"""

import re
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import security
from app.core.config import settings
from app.core.security import hash_api_token
from app.models import User, UserCreate
from app.models.agency import Agency, AgencyInvite, AgencyRole
from app.models.category import Category
from app.models.check import Issue
from app.models.company import Company
from app.models.enums import IssueState
from app.tests.utils.eval import create_test_agent
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
SITE = "https://app.example.com"


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(settings, "SITE_URL", SITE)
    monkeypatch.setattr(
        settings, "OAUTH_DEFAULT_RESOURCE_URL", "https://mcp.example.com/mcp"
    )
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")


class Outbox:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def __call__(self, *, email_to: str, subject: str, html_content: str) -> bool:
        self.sent.append({"to": email_to, "subject": subject, "html": html_content})
        return True

    def token(self, to: str | None = None) -> str:
        mail = next(m for m in reversed(self.sent) if to is None or m["to"] == to)
        found = re.search(rf"{re.escape(SITE)}/invite/([\w-]+)", mail["html"])
        assert found, "the email has no invite link"
        return found.group(1)


@pytest.fixture
def outbox() -> Generator[Outbox, None, None]:
    box = Outbox()
    with patch("app.api.routes.agencies.send_email", box):
        yield box


def _person(db: Session, email: str | None = None, name: str | None = None) -> User:
    user = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email or random_email(),
            password=random_lower_string(),
            full_name=name,
        ),
    )
    return user


def _web(db: Session, user: User) -> dict[str, str]:
    db.refresh(user)
    token, _ = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return {settings.AUTH_COOKIE: token}


def _cookie(token: str) -> dict[str, str]:
    return {settings.AUTH_COOKIE: token}


def _assistant(db: Session, user: User) -> dict[str, str]:
    _, token = crud.create_personal_access_token(
        session=db, user_id=user.id, name="Claude Code"
    )
    return {"Authorization": f"Bearer {token}"}


def _agency_of(db: Session, user: User) -> Agency:
    workspace = db.get(Company, user.company_id)
    assert workspace is not None
    agency = db.get(Agency, workspace.agency_id)
    assert agency is not None
    return agency


def _invite(
    client: TestClient, db: Session, admin: User, emails: list[str], **what: object
):
    agency = _agency_of(db, admin)
    return client.post(
        f"{API}/agencies/{agency.id}/invites",
        json={"emails": emails, **what},
        cookies=_web(db, admin),
    )


def _fresh() -> str:
    return f"sam-{uuid.uuid4().hex[:10]}@example.com"


def _reached(client: TestClient, cookies: dict[str, str]) -> set[str]:
    r = client.get(f"{API}/workspaces/", cookies=cookies)
    assert r.status_code == 200, r.text
    return {w["id"] for w in r.json()}


# ── Inviting ──


def test_inviting_sends_the_designed_email_once_per_address(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(
        db, f"alex-{uuid.uuid4().hex[:8]}@signal-voice.com", name="Alex Morgan"
    )
    one, two = _fresh(), _fresh()

    r = _invite(client, db, admin, [f" {one.upper()} ", two, one])

    assert r.status_code == 200, r.text
    assert [i["email"] for i in r.json()["sent"]] == [one, two]
    assert r.json()["refused"] == []
    assert sorted(m["to"] for m in outbox.sent) == sorted([one, two])
    mail = outbox.sent[0]
    assert mail["subject"] == "Alex invited you to Signal Voice on Connexity"
    assert (
        "Alex Morgan invited you to work on 1 client workspace at Signal Voice."
        in mail["html"]
    )
    assert "Accept invite" in mail["html"]
    assert "This invite expires in 7 days." in mail["html"]
    assert 'src="cid:connexity-logo.png"' in mail["html"]

    seen = client.get(
        f"{API}/agencies/{_agency_of(db, admin).id}", cookies=_web(db, admin)
    ).json()
    waiting = {i["email"]: i for i in seen["invites"]}
    assert set(waiting) == {one, two}
    assert waiting[one]["invited_by"] == "Alex Morgan"
    assert waiting[one]["role"] == "member"
    assert waiting[one]["can_approve"] is False
    left = datetime.fromisoformat(waiting[one]["expires_at"]) - datetime.now(UTC)
    assert timedelta(days=6, hours=23) < left <= timedelta(days=7)


def test_addresses_that_cannot_be_invited_come_back_with_why(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db, f"alex-{uuid.uuid4().hex[:8]}@signal-voice.com")
    invited = _fresh()
    assert _invite(client, db, admin, [invited]).status_code == 200

    r = _invite(client, db, admin, ["sam@example", admin.email, invited])

    assert r.json()["sent"] == []
    assert [(x["email"], x["reason"], x["message"]) for x in r.json()["refused"]] == [
        (
            "sam@example",
            "invalid",
            "Enter a full email address, like alex@example.com.",
        ),
        (admin.email, "member", f"{admin.email} is already in Signal Voice."),
        (invited, "invited", f"{invited} already has an invite."),
    ]
    assert len(outbox.sent) == 1


def test_an_invite_gives_at_least_one_of_the_agencys_workspaces(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, other = _person(db), _person(db)

    none = _invite(client, db, admin, [_fresh()], all_workspaces=False)
    foreign = _invite(
        client,
        db,
        admin,
        [_fresh()],
        all_workspaces=False,
        workspace_ids=[str(other.company_id)],
    )

    assert none.status_code == foreign.status_code == 422
    assert none.json()["detail"] == "Choose at least one of this agency's workspaces."
    assert outbox.sent == []


def test_only_a_hash_of_the_link_is_stored(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, email = _person(db), _fresh()
    _invite(client, db, admin, [email])
    token = outbox.token()

    row = db.exec(select(AgencyInvite).where(AgencyInvite.email == email)).one()

    assert row.token_hash == hash_api_token(token)
    assert token not in " ".join(str(v) for v in row.model_dump().values())


def test_a_member_cannot_invite_resend_or_cancel(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, email = _person(db), _fresh()
    agency = _agency_of(db, admin)
    invite_id = _invite(client, db, admin, [email]).json()["sent"][0]["id"]
    member = _join_as(client, db, admin, outbox, role="member")
    cookies = _web(db, member)
    base = f"{API}/agencies/{agency.id}/invites"

    assert (
        client.post(base, json={"emails": [_fresh()]}, cookies=cookies).status_code
        == 403
    )
    assert client.post(f"{base}/{invite_id}/resend", cookies=cookies).status_code == 403
    assert client.delete(f"{base}/{invite_id}", cookies=cookies).status_code == 403
    seen = client.get(f"{API}/agencies/{agency.id}", cookies=cookies).json()
    assert seen["invites"] == []


# ── Resend, cancel, expiry ──


def test_resend_replaces_the_link_and_cancel_ends_it(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, email = _person(db), _fresh()
    agency = _agency_of(db, admin)
    invite_id = _invite(client, db, admin, [email]).json()["sent"][0]["id"]
    first = outbox.token()
    base = f"{API}/agencies/{agency.id}/invites/{invite_id}"

    resent = client.post(f"{base}/resend", cookies=_web(db, admin))
    second = outbox.token()

    assert resent.status_code == 200
    assert first != second
    assert len(outbox.sent) == 2
    assert client.get(f"{API}/invites/{first}").status_code == 404
    assert client.get(f"{API}/invites/{second}").status_code == 200

    assert client.delete(base, cookies=_web(db, admin)).status_code == 204
    assert client.get(f"{API}/invites/{second}").status_code == 404
    assert client.delete(base, cookies=_web(db, admin)).status_code == 404
    # The address can be invited again once its invite is gone.
    assert _invite(client, db, admin, [email]).json()["sent"][0]["email"] == email


def test_an_invite_stops_working_after_seven_days(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, email = _person(db), _fresh()
    _invite(client, db, admin, [email])
    token = outbox.token()
    row = db.exec(select(AgencyInvite).where(AgencyInvite.email == email)).one()
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.add(row)
    db.commit()

    look = client.get(f"{API}/invites/{token}")
    join = client.post(
        f"{API}/invites/{token}/signup",
        json={"full_name": "Sam Reyes", "password": "correct-horse-7"},
    )

    assert look.status_code == join.status_code == 404
    assert look.json()["detail"] == "This invite no longer works"
    assert client.get(f"{API}/invites/not-a-real-token").status_code == 404


# ── Joining ──


def _join_as(
    client: TestClient,
    db: Session,
    admin: User,
    outbox: Outbox,
    **what: object,
) -> User:
    """Invite a new address and join with a new account; returns that person."""
    email = _fresh()
    assert _invite(client, db, admin, [email], **what).status_code == 200
    joined = client.post(
        f"{API}/invites/{outbox.token(email)}/signup",
        json={"full_name": "Sam Reyes", "password": "correct-horse-7"},
    )
    assert joined.status_code == 200, joined.text
    return db.exec(select(User).where(User.email == email)).one()


def test_a_new_person_joins_with_what_the_invite_said_and_no_agency_of_their_own(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(
        db, f"alex-{uuid.uuid4().hex[:8]}@signal-voice.com", name="Alex Morgan"
    )
    agency = _agency_of(db, admin)
    second = client.post(
        f"{API}/workspaces/", json={"name": "Bright Dental"}, cookies=_web(db, admin)
    ).json()["id"]
    email = _fresh()
    _invite(
        client,
        db,
        admin,
        [email],
        role="member",
        all_workspaces=False,
        workspace_ids=[second],
        can_approve=True,
    )
    token = outbox.token()

    look = client.get(f"{API}/invites/{token}")
    assert look.json() == {
        "agency_name": "Signal Voice",
        "invited_by": "Alex Morgan",
        "email": email,
        "workspaces": 1,
        "has_account": False,
    }

    joined = client.post(
        f"{API}/invites/{token}/signup",
        json={"full_name": "Sam Reyes", "password": "correct-horse-7"},
    )
    assert joined.status_code == 200, joined.text
    session = _cookie(joined.json()["access_token"])

    assert _reached(client, session) == {second}
    mine = client.get(f"{API}/agencies/", cookies=session).json()
    assert [
        (a["id"], a["role"], a["all_workspaces"], a["can_approve"]) for a in mine
    ] == [(str(agency.id), "member", False, True)]
    sam = db.exec(select(User).where(User.email == email)).one()
    assert _reached_by_assistant(client, _assistant(db, sam)) == {second}
    signed_in = client.post(
        f"{API}/login/access-token",
        data={"username": email, "password": "correct-horse-7"},
    )
    assert signed_in.status_code == 200

    # The link worked once; the Admin's page shows the person, not the invite.
    assert client.get(f"{API}/invites/{token}").status_code == 404
    seen = client.get(f"{API}/agencies/{agency.id}", cookies=_web(db, admin)).json()
    assert seen["invites"] == []
    assert email in {p["email"] for p in seen["members"]}


def _reached_by_assistant(client: TestClient, headers: dict[str, str]) -> set[str]:
    r = client.get(f"{API}/mcp/workspaces", headers=headers)
    assert r.status_code == 200, r.text
    return {w["id"] for w in r.json()["data"]}


def test_a_person_with_an_account_joins_signed_in_and_keeps_their_own_agency(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, sam = _person(db), _person(db)
    _invite(client, db, admin, [sam.email.upper()], role="admin")
    token = outbox.token()
    assert client.get(f"{API}/invites/{token}").json()["has_account"] is True

    signup = client.post(
        f"{API}/invites/{token}/signup",
        json={"full_name": "Sam Reyes", "password": "correct-horse-7"},
    )
    assert signup.status_code == 409

    joined = client.post(f"{API}/invites/{token}/accept", cookies=_web(db, sam))

    assert joined.status_code == 200, joined.text
    assert _reached(client, _web(db, sam)) == {
        str(sam.company_id),
        str(admin.company_id),
    }
    places = {a.id: m.role for a, m in crud.list_agencies(session=db, user=sam)}
    assert places[_agency_of(db, admin).id] is AgencyRole.admin
    assert len(places) == 2
    assert (
        client.post(f"{API}/invites/{token}/accept", cookies=_web(db, sam)).status_code
        == 404
    )


def test_a_person_removed_and_invited_again_signs_in_from_the_invite(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    email = _fresh()
    _invite(client, db, admin, [email])
    first = client.post(
        f"{API}/invites/{outbox.token()}/signup",
        json={"full_name": "Sam Reyes", "password": "correct-horse-7"},
    )
    assert first.status_code == 200, first.text
    sam = crud.find_user_by_email_ignoring_case(session=db, email=email)
    assert sam is not None
    removed = client.delete(
        f"{API}/agencies/{agency.id}/members/{sam.id}", cookies=_web(db, admin)
    )
    assert removed.status_code == 204
    # With no workspace left, the ordinary sign-in refuses them.
    login = client.post(
        f"{API}/login/access-token",
        data={"username": email, "password": "correct-horse-7"},
    )
    assert login.status_code == 403

    _invite(client, db, admin, [email])
    token = outbox.token()
    wrong = client.post(f"{API}/invites/{token}/signin", json={"password": "nope-nope"})
    joined = client.post(
        f"{API}/invites/{token}/signin", json={"password": "correct-horse-7"}
    )

    assert wrong.status_code == 400
    assert joined.status_code == 200, joined.text
    assert _reached(client, _cookie(joined.json()["access_token"])) == {
        str(admin.company_id)
    }
    assert client.get(f"{API}/invites/{token}").status_code == 404


def test_an_invite_cannot_be_used_by_another_email(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, sam, other = _person(db), _person(db), _person(db)
    _invite(client, db, admin, [sam.email])
    token = outbox.token()

    wrong = client.post(f"{API}/invites/{token}/accept", cookies=_web(db, other))
    declined_by_other = client.post(
        f"{API}/invites/{token}/decline", cookies=_web(db, other)
    )
    nobody = client.post(f"{API}/invites/{token}/accept")

    assert wrong.status_code == declined_by_other.status_code == 403
    assert wrong.json()["detail"] == f"This invite is for {sam.email}."
    assert nobody.status_code == 401
    assert str(admin.company_id) not in _reached(client, _web(db, other))
    # The invite is still good for the person it was sent to, who may decline it.
    assert (
        client.post(f"{API}/invites/{token}/decline", cookies=_web(db, sam)).status_code
        == 204
    )
    assert client.get(f"{API}/invites/{token}").status_code == 404
    assert str(admin.company_id) not in _reached(client, _web(db, sam))


# ── "Can approve" ──


def _issue(db: Session, company_id: uuid.UUID) -> Issue:
    agent = create_test_agent(db, company_id=company_id)
    category = db.exec(select(Category)).first()
    assert category is not None
    issue = Issue(
        company_id=company_id,
        agent_id=agent.id,
        check_type="silence",
        category_id=category.id,
        key=uuid.uuid4().hex,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def test_a_person_who_cannot_approve_is_refused_and_told_who_can(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db, name="Alex Morgan")
    viewer = _join_as(client, db, admin, outbox, can_approve=False)
    approver = _join_as(client, db, admin, outbox, can_approve=True)
    issue = _issue(db, admin.company_id)
    state = f"{API}/issues/{issue.id}/state"
    archive = {"state": "archived", "reason": "Not worth fixing"}

    refused = client.put(state, json=archive, cookies=_web(db, viewer))
    assert refused.status_code == 403
    assert refused.json()["detail"].startswith(
        "This needs someone who can approve. Ask "
    )
    assert "Alex Morgan" in refused.json()["detail"]
    by_assistant = client.post(
        f"{API}/mcp/workspaces/{admin.company_id}/issues/{issue.id}/archive",
        json={"reason": "Not worth fixing"},
        headers=_assistant(db, viewer),
    )
    assert by_assistant.status_code == 403
    assert "cannot approve" in by_assistant.json()["detail"]["error"]
    db.refresh(issue)
    assert issue.state is IssueState.OPEN

    # Resolving an issue is not a critical decision; anyone may.
    resolved = client.put(state, json={"state": "resolved"}, cookies=_web(db, viewer))
    assert resolved.status_code == 200, resolved.text

    allowed = client.put(state, json=archive, cookies=_web(db, approver))
    assert allowed.status_code == 200, allowed.text
    unarchive = client.put(state, json={"state": "open"}, cookies=_web(db, viewer))
    assert unarchive.status_code == 403
    by_assistant = client.post(
        f"{API}/mcp/workspaces/{admin.company_id}/issues/{issue.id}/unarchive",
        json={},
        headers=_assistant(db, approver),
    )
    assert by_assistant.status_code == 200, by_assistant.text


# ── The assistant's tools ──


def test_an_admins_assistant_reads_invites_changes_and_removes(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(
        db, f"alex-{uuid.uuid4().hex[:8]}@signal-voice.com", name="Alex Morgan"
    )
    sam = _join_as(client, db, admin, outbox)
    people = f"{API}/mcp/workspaces/{admin.company_id}/people"
    headers = _assistant(db, admin)
    email = _fresh()

    invited = client.post(
        f"{people}/invites", json={"emails": [email, admin.email]}, headers=headers
    )
    assert invited.status_code == 200, invited.text
    assert [i["email"] for i in invited.json()["data"]["sent"]] == [email]
    assert invited.json()["data"]["refused"][0]["reason"] == "member"
    assert outbox.sent[-1]["to"] == email

    listed = client.get(people, headers=headers).json()
    data = listed["data"]
    assert data["agency"]["name"] == "Signal Voice"
    assert data["your_role"] == "admin"
    by_email = {p["email"]: p for p in data["people"]}
    assert by_email[admin.email]["is_you"] is True
    # The Admin's assistant made this call with a token, so it counts as connected.
    assert by_email[admin.email]["assistants"] == 1
    assert by_email[sam.email]["role"] == "member"
    assert [i["email"] for i in data["invites"]] == [email]
    assert listed["guide"] == "connexity://guides/people"

    changed = client.patch(
        f"{people}/{sam.id}", json={"can_approve": True}, headers=headers
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"]["can_approve"] is True

    last_admin = client.delete(f"{people}/{admin.id}", headers=headers)
    assert last_admin.status_code == 409
    assert last_admin.json()["detail"]["error"] == "An agency needs at least one Admin."

    cancelled = client.delete(f"{people}/{data['invites'][0]['id']}", headers=headers)
    assert cancelled.json()["data"] == {"removed": "invite", "who": email}
    removed = client.delete(f"{people}/{sam.id}", headers=headers)
    assert removed.json()["data"] == {"removed": "person", "who": "Sam Reyes"}
    after = client.get(people, headers=headers).json()["data"]
    assert [p["email"] for p in after["people"]] == [admin.email]
    assert after["invites"] == []
    assert client.delete(f"{people}/{uuid.uuid4()}", headers=headers).status_code == 404


def test_a_members_assistant_reads_people_and_changes_nothing(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db, name="Alex Morgan")
    _invite(client, db, admin, [_fresh()])
    member = _join_as(client, db, admin, outbox)
    people = f"{API}/mcp/workspaces/{admin.company_id}/people"
    headers = _assistant(db, member)

    listed = client.get(people, headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"]["your_role"] == "member"
    assert listed.json()["data"]["invites"] == []
    assert len(listed.json()["data"]["people"]) == 2

    invite = client.post(
        f"{people}/invites", json={"emails": [_fresh()]}, headers=headers
    )
    change = client.patch(
        f"{people}/{member.id}", json={"role": "admin"}, headers=headers
    )
    remove = client.delete(f"{people}/{admin.id}", headers=headers)

    assert invite.status_code == change.status_code == remove.status_code == 403
    assert "Alex Morgan" in invite.json()["detail"]["next_steps"][0]
