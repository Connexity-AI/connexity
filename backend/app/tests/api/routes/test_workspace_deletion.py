"""Deleting a workspace's data, through the API.

Everything of the workspace is gone, another workspace of the same agency is untouched,
usage totals stay with the workspace's and the agent's name, and the agency keeps a
record of who deleted what. People and services are invented.
"""

import secrets
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlmodel import Session, SQLModel

from app import crud
from app.core import security
from app.core.config import settings
from app.crud import workspace_deletion as deleting
from app.models import User, UserCreate
from app.models.agency import Agency, AgencyMember, AgencyRole
from app.models.agent import Agent
from app.models.call import Call
from app.models.category import Category
from app.models.check import DecisionRecord, Issue
from app.models.company import Company
from app.models.enums import (
    DecisionKind,
    IntegrationProvider,
    Platform,
    UsageMeter,
)
from app.models.integration import Integration
from app.models.oauth import OAuthClient, OAuthRefreshToken
from app.models.usage import UsageRecord
from app.models.workspace_deletion import WorkspaceDeletion
from app.models.workspace_member import WorkspaceMember
from app.tests.utils.eval import create_test_agent
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "no-reply@example.com")
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


@pytest.fixture
def outbox() -> Generator[Outbox, None, None]:
    box = Outbox()
    with patch("app.api.routes.workspace_deletions.send_email", box):
        yield box


def _person(db: Session, name: str | None = None) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string(), full_name=name
        ),
    )


def _web(db: Session, user: User) -> dict[str, str]:
    db.refresh(user)
    token, _ = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
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


def _new_workspace(client: TestClient, db: Session, admin: User, name: str) -> Company:
    r = client.post(f"{API}/workspaces/", json={"name": name}, cookies=_web(db, admin))
    assert r.status_code == 200, r.text
    workspace = db.get(Company, uuid.UUID(r.json()["id"]))
    assert workspace is not None
    return workspace


def _fill(db: Session, workspace: Company, person: User) -> Agent:
    """A connected agent with a call, an issue, a decision, usage and an assistant
    connection made while this workspace was open."""
    agent = create_test_agent(db, company_id=workspace.id, name="Front desk")
    integration = Integration(
        provider=IntegrationProvider.RETELL,
        name="Production",
        company_id=workspace.id,
        encrypted_api_key="encrypted",
        masked_api_key="key_****",
    )
    db.add(integration)
    db.flush()
    agent.platform = Platform.RETELL
    agent.integration_id = integration.id
    agent.platform_agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    agent.agent_metadata = {"prompt": "You are the front desk."}
    db.add(agent)
    call = Call(
        company_id=workspace.id,
        agent_id=agent.id,
        integration_id=integration.id,
        provider="retell",
        external_id=f"call-{uuid.uuid4().hex[:8]}",
        provider_agent_id=agent.platform_agent_id,
        started_at=datetime.now(UTC).replace(tzinfo=None),
        recording_url="https://recordings.example.com/a.wav",
    )
    db.add(call)
    category = db.execute(select(Category)).scalars().first()
    assert category is not None
    db.add(
        Issue(
            company_id=workspace.id,
            agent_id=agent.id,
            check_type="silence",
            category_id=category.id,
            key=uuid.uuid4().hex,
        )
    )
    db.add(
        DecisionRecord(
            company_id=workspace.id,
            agent_id=agent.id,
            kind=DecisionKind.ISSUE_STATE,
            subject="silence",
            decided_by=person.id,
            decided_by_email=person.email,
        )
    )
    db.flush()
    db.add(
        UsageRecord(
            company_id=workspace.id,
            agent_id=agent.id,
            meter=UsageMeter.OBSERVED_MINUTES,
            quantity=7,
            occurred_at=datetime.now(UTC),
            source_key=f"call:{call.id}",
            call_id=call.id,
        )
    )
    oauth_client = OAuthClient(
        client_id=f"client-{uuid.uuid4().hex}",
        client_name="Claude Code",
        redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
    )
    db.add(oauth_client)
    db.flush()
    db.add(
        OAuthRefreshToken(
            token_hash=secrets.token_hex(32),
            company_id=workspace.id,
            client_id=oauth_client.client_id,
            user_id=person.id,
            resource="https://mcp.example.com/mcp",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    db.commit()
    db.refresh(agent)
    return agent


def _rows(db: Session, company_id: uuid.UUID) -> dict[str, int]:
    """How many rows each table holds for the workspace, for tables with any."""
    held: dict[str, int] = {}
    for table in SQLModel.metadata.sorted_tables:
        if "company_id" not in table.c:
            continue
        n = db.execute(
            select(func.count())
            .select_from(table)
            .where(table.c.company_id == company_id)
        ).scalar_one()
        if n:
            held[table.name] = n
    return held


def _delete(
    client: TestClient, db: Session, who: User, workspace: Company, name: str | None
):
    agency_id = workspace.agency_id
    return client.post(
        f"{API}/agencies/{agency_id}/workspaces/{workspace.id}/deletion",
        json={"name": workspace.name if name is None else name},
        cookies=_web(db, who),
    )


def test_deleting_removes_the_workspaces_data_and_nothing_else(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db, "Alex Morgan")
    agency = _agency_of(db, admin)
    kept = db.get(Company, admin.company_id)
    assert kept is not None
    gone = _new_workspace(client, db, admin, "Bright Dental")
    kept_agent = _fill(db, kept, admin)
    gone_agent = _fill(db, gone, admin)
    kept_before = _rows(db, kept.id)
    assert _rows(db, gone.id).keys() >= {"call", "issue", "decision_record"}

    preview = client.get(
        f"{API}/agencies/{agency.id}/workspaces/{gone.id}/deletion",
        cookies=_web(db, admin),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json() == {
        "workspace_id": str(gone.id),
        "workspace_name": "Bright Dental",
        "calls": 1,
        "agents": 1,
        "issues": 1,
        "connections": ["retell"],
        "is_last": False,
    }

    done = _delete(client, db, admin, gone, None)

    assert done.status_code == 200, done.text
    assert done.json()["state"] == "done"
    assert done.json()["deleted_by"] == "Alex Morgan"
    db.expire_all()
    # Only the rows that are meant to stay are left, and they hold no content.
    assert _rows(db, gone.id) == {
        "usage_record": 1,
        "agent": 1,
        "workspace_deletion": 1,
    }
    agent = db.get(Agent, gone_agent.id)
    assert agent is not None
    assert agent.name == "Front desk"
    assert agent.deleted_at is not None
    assert (agent.description, agent.platform, agent.integration_id) == (
        None,
        None,
        None,
    )
    assert (agent.platform_agent_id, agent.agent_metadata) == (None, None)
    usage = db.execute(
        select(UsageRecord).where(UsageRecord.company_id == gone.id)  # type: ignore[arg-type]
    ).scalar_one()
    assert (usage.quantity, usage.agent_id, usage.call_id) == (7, gone_agent.id, None)
    workspace = db.get(Company, gone.id)
    assert workspace is not None
    assert workspace.name == "Bright Dental"
    assert workspace.deleted_at is not None
    # The other workspace of the same agency is exactly as it was, but for the
    # assistant connection that moved to it with its person.
    kept_after = _rows(db, kept.id)
    assert kept_after.pop("oauth_refresh_token") == 2
    assert kept_before.pop("oauth_refresh_token") == 1
    assert kept_after == kept_before
    assert db.get(Agent, kept_agent.id).platform_agent_id is not None  # type: ignore[union-attr]
    # The Admins are told once.
    assert [m["to"] for m in outbox.sent] == [admin.email]
    assert outbox.sent[0]["subject"] == "Bright Dental was deleted from Connexity"
    assert "Alex Morgan deleted the workspace Bright Dental" in outbox.sent[0]["html"]


def test_a_deleted_workspace_is_gone_for_people_and_assistants(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    gone = _new_workspace(client, db, admin, "Bright Dental")
    _fill(db, gone, admin)
    opened = client.post(f"{API}/workspaces/{gone.id}/open", cookies=_web(db, admin))
    assert opened.status_code == 200, opened.text
    headers = _assistant(db, admin)

    assert _delete(client, db, admin, gone, None).status_code == 200

    db.expire_all()
    db.refresh(admin)
    # The person who had it open is moved to a workspace they still reach.
    assert admin.company_id != gone.id
    listed = client.get(f"{API}/workspaces/", cookies=_web(db, admin)).json()
    assert str(gone.id) not in {w["id"] for w in listed}
    by_assistant = client.get(f"{API}/mcp/workspaces", headers=headers).json()["data"]
    assert str(gone.id) not in {w["id"] for w in by_assistant}
    assert (
        client.get(
            f"{API}/mcp/workspaces/{gone.id}/agents", headers=headers
        ).status_code
        == 404
    )
    assert client.post(
        f"{API}/workspaces/{gone.id}/open", cookies=_web(db, admin)
    ).status_code in (403, 404)
    # Their assistant's connection moved with them instead of being cut.
    tokens = (
        db.execute(
            select(OAuthRefreshToken).where(OAuthRefreshToken.user_id == admin.id)  # type: ignore[arg-type]
        )
        .scalars()
        .all()
    )
    assert [t.company_id for t in tokens] == [admin.company_id]
    # The agency's table no longer has it, and its record says who and when.
    table = client.get(
        f"{API}/agencies/{agency.id}/workspaces", cookies=_web(db, admin)
    ).json()
    assert str(gone.id) not in {w["id"] for w in table["workspaces"]}
    assert table["can_delete"] is True
    assert [
        (d["workspace_name"], d["state"], d["calls"]) for d in table["deleted"]
    ] == [("Bright Dental", "done", 1)]
    # A second try finds nothing to delete.
    assert _delete(client, db, admin, gone, "Bright Dental").status_code == 409


def test_a_session_in_a_deleted_workspace_goes_on_when_the_person_has_another(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, only_here = _person(db), _person(db)
    agency = _agency_of(db, admin)
    gone = _new_workspace(client, db, admin, "Bright Dental")
    # A person who reaches nothing but the workspace that is deleted.
    db.execute(
        delete(WorkspaceMember).where(WorkspaceMember.user_id == only_here.id)  # type: ignore[arg-type]
    )
    # And who is an Admin nowhere: an Admin is let in with no workspace.
    db.execute(
        delete(AgencyMember).where(AgencyMember.user_id == only_here.id)  # type: ignore[arg-type]
    )
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=only_here.id,
            role=AgencyRole.member,
            all_workspaces=False,
            can_approve=False,
        )
    )
    db.add(WorkspaceMember(user_id=only_here.id, company_id=gone.id))
    only_here.company_id = gone.id
    db.add(only_here)
    db.commit()
    assert (
        client.post(
            f"{API}/workspaces/{gone.id}/open", cookies=_web(db, admin)
        ).status_code
        == 200
    )
    # Sessions issued while the workspace was open.
    admins_session = _web(db, admin)
    others_session = _web(db, only_here)
    assert client.get(f"{API}/users/me", cookies=others_session).status_code == 200
    stays = _new_workspace(client, db, admin, "Northfield Group")
    removed = _person(db)
    db.add(WorkspaceMember(user_id=removed.id, company_id=stays.id))
    db.commit()
    removed.company_id = stays.id
    db.add(removed)
    db.commit()
    removeds_session = _web(db, removed)

    assert _delete(client, db, admin, gone, None).status_code == 200

    # The Admin's old session goes on, in a workspace they still reach.
    me = client.get(f"{API}/users/me", cookies=admins_session)
    assert me.status_code == 200, me.text
    assert me.json()["company_id"] != str(gone.id)
    listed = client.get(f"{API}/workspaces/", cookies=admins_session)
    assert listed.status_code == 200
    assert str(gone.id) not in {w["id"] for w in listed.json()}
    # A person with no other workspace is refused, and so is sign-in for them.
    assert client.get(f"{API}/users/me", cookies=others_session).status_code == 401
    # Being removed from a workspace that still exists ends the session, as before.
    db.execute(
        delete(WorkspaceMember).where(
            WorkspaceMember.user_id == removed.id,  # type: ignore[arg-type]
            WorkspaceMember.company_id == stays.id,  # type: ignore[arg-type]
        )
    )
    db.commit()
    assert client.get(f"{API}/users/me", cookies=removeds_session).status_code == 401


def test_only_an_admin_who_can_approve_deletes(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, member, other = _person(db, "Alex Morgan"), _person(db), _person(db)
    agency = _agency_of(db, admin)
    gone = _new_workspace(client, db, admin, "Bright Dental")
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=member.id,
            role=AgencyRole.member,
            all_workspaces=True,
            can_approve=True,
        )
    )
    db.commit()
    viewer = _person(db)
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=viewer.id,
            role=AgencyRole.admin,
            all_workspaces=True,
            can_approve=False,
        )
    )
    db.commit()

    by_member = _delete(client, db, member, gone, None)
    by_viewer = _delete(client, db, viewer, gone, None)
    by_outsider = _delete(client, db, other, gone, None)
    by_assistant = client.post(
        f"{API}/agencies/{agency.id}/workspaces/{gone.id}/deletion",
        json={"name": "Bright Dental"},
        headers=_assistant(db, admin),
    )
    wrong_name = _delete(client, db, admin, gone, "bright dental")

    assert by_member.status_code == by_viewer.status_code == 403
    assert by_member.json()["detail"] == (
        "Deleting a workspace needs an Admin who can approve. Ask Alex Morgan."
    )
    assert by_outsider.status_code == 404
    assert by_assistant.status_code in (401, 403)
    assert wrong_name.status_code == 422
    assert wrong_name.json()["detail"] == "Type Bright Dental to confirm."
    db.expire_all()
    assert db.get(Company, gone.id).deleted_at is None  # type: ignore[union-attr]
    table = client.get(
        f"{API}/agencies/{agency.id}/workspaces", cookies=_web(db, member)
    ).json()
    assert table["can_delete"] is False
    assert {w["name"] for w in table["workspaces"]} >= {"Bright Dental"}
    assert outbox.sent == []


def test_an_assistant_prepares_a_deletion_and_deletes_nothing(
    client: TestClient, db: Session, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SITE_URL", "https://app.example.com")
    admin, member = _person(db, "Alex Morgan"), _person(db)
    agency = _agency_of(db, admin)
    gone = _new_workspace(client, db, admin, "Bright Dental")
    _fill(db, gone, admin)
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=member.id,
            role=AgencyRole.member,
            all_workspaces=False,
            can_approve=False,
        )
    )
    db.add(WorkspaceMember(user_id=member.id, company_id=gone.id))
    db.commit()
    before = _rows(db, gone.id)
    path = f"{API}/mcp/workspaces/{gone.id}/deletion"

    for_admin = client.get(path, headers=_assistant(db, admin))
    for_member = client.get(path, headers=_assistant(db, member))
    only = client.get(
        f"{API}/mcp/workspaces/{member.company_id}/deletion",
        headers=_assistant(db, member),
    )

    assert for_admin.status_code == 200, for_admin.text
    answer = for_admin.json()
    assert answer["data"] == {
        "workspace": {"id": str(gone.id), "name": "Bright Dental"},
        "agency": {"id": str(agency.id), "name": agency.name},
        "calls": 1,
        "agents": 1,
        "issues": 1,
        "connections": ["retell"],
        "is_last_workspace": False,
        "your_person_can_delete": True,
        "who_can_delete": "Alex Morgan",
        "where": "https://app.example.com/agency?section=workspaces",
    }
    assert "You cannot do this step." in answer["next_steps"][1]
    told = for_member.json()
    assert told["data"]["your_person_can_delete"] is False
    assert "Alex Morgan" in told["next_steps"][0]
    last = only.json()
    assert last["data"]["is_last_workspace"] is True
    # The last workspace is no longer refused; the assistant says what follows.
    assert "last workspace" in last["next_steps"][0]
    assert "subscription keeps running" in last["next_steps"][0]
    # Reading it removed nothing.
    assert _rows(db, gone.id) == before
    assert db.get(Company, gone.id).deleted_at is None  # type: ignore[union-attr]


def test_an_agencys_last_workspace_can_be_deleted_and_its_admin_stays_in(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db, "Alex Morgan")
    agency = _agency_of(db, admin)
    only = db.get(Company, admin.company_id)
    assert only is not None
    _fill(db, only, admin)
    password = "correct-horse-7"
    admin.hashed_password = security.get_password_hash(password)
    db.add(admin)
    db.commit()
    session = _web(db, admin)
    assistant = _assistant(db, admin)

    preview = client.get(
        f"{API}/agencies/{agency.id}/workspaces/{only.id}/deletion", cookies=session
    )
    deleted = _delete(client, db, admin, only, None)

    assert preview.json()["is_last"] is True
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["state"] == "done"
    # The same session goes on, with no workspace open.
    assert client.get(f"{API}/users/me", cookies=session).status_code == 200
    assert client.get(f"{API}/workspaces/", cookies=session).json() == []
    # Routes that need a workspace say so; the agency's own routes work.
    needs_one = client.get(f"{API}/readiness", cookies=session)
    assert needs_one.status_code == 409
    assert (
        needs_one.json()["detail"] == "No workspace is open. Create a workspace first."
    )
    assert client.get(f"{API}/agencies/{agency.id}", cookies=session).status_code == 200
    table = client.get(f"{API}/agencies/{agency.id}/workspaces", cookies=session).json()
    assert table["workspaces"] == []
    assert [d["workspace_name"] for d in table["deleted"]] == [only.name]
    # Signing in again lets the Admin in.
    login = client.post(
        f"{API}/login/access-token",
        data={"username": admin.email, "password": password},
    )
    assert login.status_code == 200, login.text
    fresh = {settings.AUTH_COOKIE: login.json()["access_token"]}
    assert client.get(f"{API}/users/me", cookies=fresh).status_code == 200

    # Their assistant is still connected, lists nothing, and is told what to do.
    listed = client.get(f"{API}/mcp/workspaces", headers=assistant).json()
    assert listed["data"] == []
    assert "create_workspace" in listed["next_steps"][0]

    # Creating a workspace needs no agency named, and opening it brings the app back.
    made = client.post(
        f"{API}/workspaces/", json={"name": "Bright Dental"}, cookies=fresh
    )
    assert made.status_code == 200, made.text
    assert made.json()["agency_id"] == str(agency.id)
    opened = client.post(f"{API}/workspaces/{made.json()['id']}/open", cookies=fresh)
    assert opened.status_code == 200, opened.text
    back = {settings.AUTH_COOKIE: opened.json()["access_token"]}
    assert client.get(f"{API}/readiness", cookies=back).status_code == 200


def test_a_member_with_no_workspace_is_still_refused(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, member = _person(db), _person(db)
    agency = _agency_of(db, admin)
    only = db.get(Company, admin.company_id)
    assert only is not None
    password = "correct-horse-7"
    member.hashed_password = security.get_password_hash(password)
    db.add(member)
    db.execute(delete(WorkspaceMember).where(WorkspaceMember.user_id == member.id))  # type: ignore[arg-type]
    db.execute(delete(AgencyMember).where(AgencyMember.user_id == member.id))  # type: ignore[arg-type]
    db.add(
        AgencyMember(
            agency_id=agency.id,
            user_id=member.id,
            role=AgencyRole.member,
            all_workspaces=True,
            can_approve=True,
        )
    )
    db.add(WorkspaceMember(user_id=member.id, company_id=only.id))
    member.company_id = only.id
    db.commit()
    session = _web(db, member)
    assert client.get(f"{API}/users/me", cookies=session).status_code == 200

    assert _delete(client, db, admin, only, None).status_code == 200

    assert client.get(f"{API}/users/me", cookies=session).status_code == 401
    login = client.post(
        f"{API}/login/access-token",
        data={"username": member.email, "password": password},
    )
    assert login.status_code == 403
    # A Member cannot create the agency's next workspace through an assistant either.
    made = client.post(
        f"{API}/mcp/workspaces", json={"name": "Next"}, headers=_assistant(db, member)
    )
    assert made.status_code == 403


def test_an_admin_of_two_agencies_with_no_workspace_says_which(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin, other = _person(db), _person(db)
    agency, second = _agency_of(db, admin), _agency_of(db, other)
    only = db.get(Company, admin.company_id)
    assert only is not None
    db.add(
        AgencyMember(
            agency_id=second.id,
            user_id=admin.id,
            role=AgencyRole.admin,
            all_workspaces=False,
            can_approve=True,
        )
    )
    db.commit()
    session = _web(db, admin)
    assert _delete(client, db, admin, only, None).status_code == 200

    unsaid = client.post(f"{API}/workspaces/", json={"name": "Next"}, cookies=session)
    said = client.post(
        f"{API}/workspaces/",
        json={"name": "Next", "agency_id": str(agency.id)},
        cookies=session,
    )

    assert unsaid.status_code == 422
    assert unsaid.json()["detail"] == "Say which agency the workspace is for."
    assert said.status_code == 200, said.text
    assert said.json()["agency_id"] == str(agency.id)


def test_a_failed_deletion_can_be_tried_again(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    gone = _new_workspace(client, db, admin, "Bright Dental")
    _fill(db, gone, admin)
    real = Session.execute
    broken = {"on": True}

    def breaks_on_calls(self: Session, statement: object, *a: object, **k: object):
        if broken["on"] and str(statement).startswith("DELETE FROM call "):
            raise RuntimeError("database went away")
        return real(self, statement, *a, **k)  # type: ignore[arg-type]

    with patch.object(Session, "execute", breaks_on_calls):
        failed = _delete(client, db, admin, gone, None)
        assert failed.status_code == 200, failed.text
        assert failed.json()["state"] == "failed"
        db.expire_all()
        record = db.execute(
            select(WorkspaceDeletion).where(WorkspaceDeletion.company_id == gone.id)  # type: ignore[arg-type]
        ).scalar_one()
        # The record names the step and the kind of error, never data.
        assert record.error == "call: RuntimeError"
        # Its agents are already unlinked, so no new call can arrive meanwhile.
        linked = db.execute(
            select(Agent).where(
                Agent.company_id == gone.id,  # type: ignore[arg-type]
                Agent.platform_agent_id.is_not(None),  # type: ignore[union-attr]
            )
        ).all()
        assert linked == []
        assert "call" in _rows(db, gone.id)
        # Nobody reaches it while it waits, and the table shows the failed row.
        listed = client.get(f"{API}/workspaces/", cookies=_web(db, admin)).json()
        assert str(gone.id) not in {w["id"] for w in listed}
        table = client.get(
            f"{API}/agencies/{agency.id}/workspaces", cookies=_web(db, admin)
        ).json()
        assert ("Bright Dental", "failed") in {
            (w["name"], w["state"]) for w in table["workspaces"]
        }
        assert outbox.sent == []

        broken["on"] = False
        again = client.post(
            f"{API}/agencies/{agency.id}/workspaces/{gone.id}/deletion/retry",
            cookies=_web(db, admin),
        )

    assert again.status_code == 200, again.text
    assert again.json()["state"] == "done"
    db.expire_all()
    assert _rows(db, gone.id) == {
        "usage_record": 1,
        "agent": 1,
        "workspace_deletion": 1,
    }
    assert len(outbox.sent) == 1
    once_more = client.post(
        f"{API}/agencies/{agency.id}/workspaces/{gone.id}/deletion/retry",
        cookies=_web(db, admin),
    )
    assert once_more.status_code == 409


def test_a_deletion_whose_request_died_can_be_continued(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    gone = _new_workspace(client, db, admin, "Bright Dental")
    _fill(db, gone, admin)
    # What a request that died midway leaves: access gone, the record still running.
    db.add(
        WorkspaceDeletion(
            agency_id=agency.id,
            company_id=gone.id,
            workspace_name=gone.name,
            deleted_by_user_id=admin.id,
            deleted_by_name="Alex Morgan",
            calls=1,
            agents=1,
            issues=1,
        )
    )
    gone.deleted_at = datetime.now(UTC)
    db.add(gone)
    db.execute(delete(WorkspaceMember).where(WorkspaceMember.company_id == gone.id))  # type: ignore[arg-type]
    db.commit()
    retry = f"{API}/agencies/{agency.id}/workspaces/{gone.id}/deletion/retry"
    table = f"{API}/agencies/{agency.id}/workspaces"

    # While it may still be running it is left alone.
    assert client.post(retry, cookies=_web(db, admin)).status_code == 409
    running = client.get(table, cookies=_web(db, admin)).json()
    assert ("Bright Dental", "deleting") in {
        (w["name"], w["state"]) for w in running["workspaces"]
    }

    record = db.execute(
        select(WorkspaceDeletion).where(WorkspaceDeletion.company_id == gone.id)  # type: ignore[arg-type]
    ).scalar_one()
    record.created_at = (
        datetime.now(UTC) - deleting.STALLED_AFTER - timedelta(minutes=1)
    )
    db.add(record)
    db.commit()

    stalled = client.get(table, cookies=_web(db, admin)).json()
    assert ("Bright Dental", "failed") in {
        (w["name"], w["state"]) for w in stalled["workspaces"]
    }
    again = client.post(retry, cookies=_web(db, admin))
    assert again.status_code == 200, again.text
    assert again.json()["state"] == "done"
    db.expire_all()
    assert _rows(db, gone.id) == {
        "usage_record": 1,
        "agent": 1,
        "workspace_deletion": 1,
    }


def test_every_table_with_workspace_data_is_part_of_a_deletion() -> None:
    """A table added later cannot be missed: whatever points at a row a deletion
    removes is itself removed with the workspace, or says what happens to it."""
    tables = {t.name: t for t in SQLModel.metadata.sorted_tables}
    emptied = {
        name
        for name, t in tables.items()
        if "company_id" in t.c and name not in deleting.KEPT_TABLES
    }
    assert deleting.KEPT_TABLES <= tables.keys()
    # Columns of kept rows that a deletion empties itself.
    handled = {
        ("agent", "integration_id"),
        ("usage_record", "call_id"),
        ("usage_record", "test_case_result_id"),
        ("usage_record", "run_id"),
    }
    unsafe = [
        f"{name}.{column.name} -> {fk.column.table.name}"
        for name, t in tables.items()
        if name not in emptied
        for column in t.columns
        for fk in column.foreign_keys
        if fk.column.table.name in emptied
        and fk.ondelete not in ("CASCADE", "SET NULL")
        and (name, column.name) not in handled
    ]
    assert unsafe == []
    # A kept table holds no column that could carry call content.
    assert emptied >= {"call", "call_event", "finding", "issue", "spec", "integration"}
