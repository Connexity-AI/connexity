"""Agencies: the account above workspaces, the people in it, and what each reaches.

Every request goes through the API, on the web with a session cookie and as an
assistant with a personal access token. There are no invites yet, so a second person
is put into an agency directly, the way an invite will.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core import security
from app.core.config import settings
from app.models import User, UserCreate
from app.models.agency import Agency, AgencyMember, AgencyRole
from app.models.company import Company
from app.models.workspace_member import WorkspaceMember
from app.tests.utils.utils import random_email, random_lower_string

API = settings.API_V1_STR
MCP_URL = "https://mcp.example.com/mcp"


@pytest.fixture(autouse=True)
def _mcp_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")


def _person(db: Session, email: str | None = None) -> User:
    return crud.create_user(
        session=db,
        user_create=UserCreate(
            email=email or random_email(), password=random_lower_string()
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


def _join(
    db: Session,
    user: User,
    agency: Agency,
    *,
    role: AgencyRole = AgencyRole.member,
    all_workspaces: bool = True,
    workspace_ids: list[uuid.UUID] | None = None,
    can_approve: bool = True,
) -> None:
    """Put a person into an agency, as accepting an invite will."""
    member = AgencyMember(
        agency_id=agency.id,
        user_id=user.id,
        role=role,
        all_workspaces=False,
        can_approve=can_approve,
    )
    db.add(member)
    db.commit()
    crud.update_member(
        session=db,
        agency=agency,
        member=member,
        all_workspaces=all_workspaces,
        workspace_ids=workspace_ids or [],
    )


def _new_workspace(client: TestClient, cookies: dict[str, str], name: str) -> str:
    r = client.post(f"{API}/workspaces/", json={"name": name}, cookies=cookies)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _reached_on_web(client: TestClient, cookies: dict[str, str]) -> set[str]:
    r = client.get(f"{API}/workspaces/", cookies=cookies)
    assert r.status_code == 200, r.text
    return {w["id"] for w in r.json()}


def _reached_by_assistant(client: TestClient, headers: dict[str, str]) -> set[str]:
    r = client.get(f"{API}/mcp/workspaces", headers=headers)
    assert r.status_code == 200, r.text
    return {w["id"] for w in r.json()["data"]}


# ── Sign-up ──


def test_sign_up_on_the_web_makes_an_agency_an_admin_and_a_first_workspace(
    client: TestClient, db: Session
) -> None:
    email = f"alex-{uuid.uuid4().hex[:8]}@signal-voice.com"
    r = client.post(
        f"{API}/users/signup", json={"email": email, "password": "correct-horse-7"}
    )
    assert r.status_code == 200, r.text
    user = db.exec(select(User).where(User.email == email)).one()

    agencies = client.get(f"{API}/agencies/", cookies=_web(db, user)).json()

    assert len(agencies) == 1
    assert agencies[0]["name"] == "Signal Voice"
    assert agencies[0]["role"] == "admin"
    assert agencies[0]["all_workspaces"] is True
    assert agencies[0]["can_approve"] is True
    workspaces = client.get(f"{API}/workspaces/", cookies=_web(db, user)).json()
    assert [(w["name"], w["agency_name"]) for w in workspaces] == [
        ("Signal Voice", "Signal Voice")
    ]
    assert workspaces[0]["agency_id"] == agencies[0]["id"]


def test_sign_in_with_google_makes_an_agency_too(db: Session) -> None:
    user = crud.create_google_user(
        session=db,
        email=f"sam-{uuid.uuid4().hex[:8]}@bright-dental.com",
        full_name="Sam Reyes",
    )

    places = crud.list_agencies(session=db, user=user)

    assert [(a.name, m.role) for a, m in places] == [
        ("Bright Dental", AgencyRole.admin)
    ]
    assert _agency_of(db, user).id == places[0][0].id


# ── Who reaches what ──


def test_all_workspaces_includes_one_created_later_and_chosen_does_not(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    first = str(admin.company_id)
    everywhere, chosen = _person(db), _person(db)
    _join(db, everywhere, agency, all_workspaces=True)
    _join(db, chosen, agency, all_workspaces=False, workspace_ids=[admin.company_id])

    later = _new_workspace(client, _web(db, admin), "Kestrel Plumbing")

    own = {str(everywhere.company_id)}
    assert _reached_on_web(client, _web(db, everywhere)) == own | {first, later}
    assert _reached_by_assistant(client, _assistant(db, everywhere)) == own | {
        first,
        later,
    }
    own = {str(chosen.company_id)}
    assert _reached_on_web(client, _web(db, chosen)) == own | {first}
    assert _reached_by_assistant(client, _assistant(db, chosen)) == own | {first}
    refused = client.post(f"{API}/workspaces/{later}/open", cookies=_web(db, chosen))
    assert refused.status_code == 404


def test_one_agency_never_gives_access_to_another(
    client: TestClient, db: Session
) -> None:
    alex, sam = _person(db), _person(db)
    theirs = _agency_of(db, sam)
    other = str(sam.company_id)

    assert other not in _reached_on_web(client, _web(db, alex))
    assert other not in _reached_by_assistant(client, _assistant(db, alex))
    opened = client.post(f"{API}/workspaces/{other}/open", cookies=_web(db, alex))
    assert opened.status_code == 404
    assert (
        client.get(f"{API}/agencies/{theirs.id}", cookies=_web(db, alex)).status_code
        == 404
    )
    created = client.post(
        f"{API}/workspaces/",
        json={"name": "Not mine", "agency_id": str(theirs.id)},
        cookies=_web(db, alex),
    )
    assert created.status_code == 404

    # An Admin cannot choose another agency's workspace for one of their people.
    mine = _agency_of(db, alex)
    helper = _person(db)
    _join(db, helper, mine, all_workspaces=False)
    chosen = client.patch(
        f"{API}/agencies/{mine.id}/members/{helper.id}",
        json={"all_workspaces": False, "workspace_ids": [other]},
        cookies=_web(db, alex),
    )
    assert chosen.status_code == 422
    assert other not in _reached_on_web(client, _web(db, helper))


def test_a_person_in_two_agencies_sees_each_workspace_with_its_agency(
    client: TestClient, db: Session
) -> None:
    sam, alex = _person(db), _person(db)
    second = _agency_of(db, alex)
    _join(db, sam, second, role=AgencyRole.member, can_approve=False)

    listed = client.get(f"{API}/mcp/workspaces", headers=_assistant(db, sam)).json()

    by_id = {w["id"]: w for w in listed["data"]}
    own, shared = by_id[str(sam.company_id)], by_id[str(alex.company_id)]
    assert (own["role"], own["can_approve"]) == ("admin", True)
    assert own["agency"]["id"] == str(_agency_of(db, sam).id)
    assert (shared["role"], shared["can_approve"]) == ("member", False)
    assert shared["agency"] == {"id": str(second.id), "name": second.name}
    assert any("`agency`" in rule for rule in listed["rules"])


# ── What a Member may not do ──


def test_a_member_reads_the_agency_and_changes_nothing(
    client: TestClient, db: Session
) -> None:
    admin, member = _person(db), _person(db)
    agency = _agency_of(db, admin)
    _join(db, member, agency)
    cookies = _web(db, member)
    url = f"{API}/agencies/{agency.id}"

    seen = client.get(url, cookies=cookies)
    assert seen.status_code == 200
    people = {p["email"]: p for p in seen.json()["members"]}
    assert people[member.email]["is_you"] is True
    assert people[member.email]["role"] == "member"
    assert people[admin.email]["role"] == "admin"
    assert people[admin.email]["workspace_ids"] == [str(admin.company_id)]
    assert [w["id"] for w in seen.json()["workspaces"]] == [str(admin.company_id)]

    assert client.patch(url, json={"name": "Mine"}, cookies=cookies).status_code == 403
    change = client.patch(
        f"{url}/members/{member.id}", json={"role": "admin"}, cookies=cookies
    )
    assert change.status_code == 403
    assert (
        client.delete(f"{url}/members/{admin.id}", cookies=cookies).status_code == 403
    )
    db.expire_all()
    assert _agency_of(db, admin).name == agency.name


def test_only_an_admin_creates_a_workspace(client: TestClient, db: Session) -> None:
    admin = _person(db, f"alex-{uuid.uuid4().hex[:8]}@signal-voice.com")
    agency = _agency_of(db, admin)
    member = _person(db)
    _join(db, member, agency)
    crud.open_workspace(
        session=db, user=member, workspace=db.get(Company, admin.company_id)
    )

    on_web = client.post(
        f"{API}/workspaces/", json={"name": "Kestrel"}, cookies=_web(db, member)
    )
    assert on_web.status_code == 403
    assert on_web.json()["detail"] == (
        f"Only Admins can create a workspace. Ask {admin.email}."
    )

    by_assistant = client.post(
        f"{API}/mcp/workspaces",
        json={"name": "Kestrel", "agency_id": str(agency.id)},
        headers=_assistant(db, member),
    )
    assert by_assistant.status_code == 403
    detail = by_assistant.json()["detail"]
    assert detail["error"] == "Only Admins of Signal Voice can create a workspace."
    assert admin.email in detail["next_steps"][0]

    made = client.post(
        f"{API}/mcp/workspaces", json={"name": "Kestrel"}, headers=_assistant(db, admin)
    )
    assert made.status_code == 200, made.text
    assert made.json()["data"]["agency"] == {"id": str(agency.id), "name": agency.name}
    assert made.json()["data"]["role"] == "admin"


def test_an_admin_of_two_agencies_says_which_one(
    client: TestClient, db: Session
) -> None:
    alex, sam = _person(db), _person(db)
    second = _agency_of(db, sam)
    _join(db, alex, second, role=AgencyRole.admin)
    headers = _assistant(db, alex)

    unclear = client.post(
        f"{API}/mcp/workspaces", json={"name": "Kestrel"}, headers=headers
    )
    assert unclear.status_code == 422
    assert str(second.id) in unclear.json()["detail"]["next_steps"][1]

    made = client.post(
        f"{API}/mcp/workspaces",
        json={"name": "Kestrel", "agency_id": str(second.id)},
        headers=headers,
    )
    assert made.status_code == 200, made.text
    assert made.json()["data"]["agency"]["id"] == str(second.id)
    # Sam reaches all of that agency's workspaces, so the new one too.
    assert made.json()["data"]["id"] in _reached_on_web(client, _web(db, sam))


# ── What an Admin does ──


def test_an_admin_renames_the_agency_and_changes_a_person(
    client: TestClient, db: Session
) -> None:
    admin, sam = _person(db), _person(db)
    agency = _agency_of(db, admin)
    cookies = _web(db, admin)
    second = _new_workspace(client, cookies, "Bright Dental")
    _join(db, sam, agency)
    url = f"{API}/agencies/{agency.id}"

    renamed = client.patch(url, json={"name": "  Signal Voice  "}, cookies=cookies)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Signal Voice"

    narrowed = client.patch(
        f"{url}/members/{sam.id}",
        json={"all_workspaces": False, "workspace_ids": [second], "can_approve": False},
        cookies=cookies,
    )
    assert narrowed.status_code == 200, narrowed.text
    assert narrowed.json()["all_workspaces"] is False
    assert narrowed.json()["workspace_ids"] == [second]
    assert narrowed.json()["can_approve"] is False
    assert _reached_on_web(client, _web(db, sam)) == {str(sam.company_id), second}

    # Naming workspaces alone means "these ones", also for a person who had all.
    client.patch(
        f"{url}/members/{sam.id}", json={"all_workspaces": True}, cookies=cookies
    )
    only = client.patch(
        f"{url}/members/{sam.id}",
        json={"workspace_ids": [str(admin.company_id)]},
        cookies=cookies,
    )
    assert only.status_code == 200
    assert only.json()["all_workspaces"] is False
    assert only.json()["workspace_ids"] == [str(admin.company_id)]
    assert second not in _reached_on_web(client, _web(db, sam))

    widened = client.patch(
        f"{url}/members/{sam.id}",
        json={"all_workspaces": True, "role": "admin"},
        cookies=cookies,
    )
    assert widened.status_code == 200
    assert widened.json()["role"] == "admin"
    assert set(widened.json()["workspace_ids"]) == {str(admin.company_id), second}

    stranger = client.patch(
        f"{url}/members/{uuid.uuid4()}", json={"role": "admin"}, cookies=cookies
    )
    assert stranger.status_code == 404


def test_an_agency_always_keeps_an_admin(client: TestClient, db: Session) -> None:
    admin, sam = _person(db), _person(db)
    agency = _agency_of(db, admin)
    _join(db, sam, agency)
    cookies = _web(db, admin)
    me = f"{API}/agencies/{agency.id}/members/{admin.id}"

    demoted = client.patch(me, json={"role": "member"}, cookies=cookies)
    removed = client.delete(me, cookies=cookies)

    assert demoted.status_code == removed.status_code == 409
    assert demoted.json()["detail"] == "An agency needs at least one Admin."

    promote = client.patch(
        f"{API}/agencies/{agency.id}/members/{sam.id}",
        json={"role": "admin"},
        cookies=cookies,
    )
    assert promote.status_code == 200
    assert client.patch(me, json={"role": "member"}, cookies=cookies).status_code == 200
    last = client.patch(
        f"{API}/agencies/{agency.id}/members/{sam.id}",
        json={"role": "member"},
        cookies=_web(db, sam),
    )
    assert last.status_code == 409


# ── Removing a person ──


def test_a_removed_person_and_their_assistant_lose_the_agency_at_once(
    client: TestClient, db: Session
) -> None:
    admin, sam = _person(db), _person(db)
    agency = _agency_of(db, admin)
    shared, own = str(admin.company_id), str(sam.company_id)
    _join(db, sam, agency)
    crud.open_workspace(session=db, user=sam, workspace=db.get(Company, shared))
    session_before = _web(db, sam)
    assistant = _assistant(db, sam)
    assert client.get(f"{API}/workspaces/", cookies=session_before).status_code == 200
    assert _reached_by_assistant(client, assistant) == {shared, own}

    removed = client.delete(
        f"{API}/agencies/{agency.id}/members/{sam.id}", cookies=_web(db, admin)
    )
    assert removed.status_code == 204

    # The session was issued for the shared workspace: it is refused.
    assert client.get(f"{API}/workspaces/", cookies=session_before).status_code == 401
    assert _reached_by_assistant(client, assistant) == {own}
    in_shared = client.get(
        f"{API}/mcp/workspaces/{shared}/readiness", headers=assistant
    )
    assert in_shared.status_code == 404
    # Their own agency still works: its workspace was opened for them.
    assert _reached_on_web(client, _web(db, sam)) == {own}
    seen = client.get(f"{API}/agencies/{agency.id}", cookies=_web(db, admin)).json()
    assert [p["email"] for p in seen["members"]] == [admin.email]


def test_a_person_with_no_workspace_left_is_told_so_at_sign_in(
    client: TestClient, db: Session
) -> None:
    admin = _person(db)
    agency = _agency_of(db, admin)
    password = random_lower_string()
    sam = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=password),
        company_id=admin.company_id,
    )
    signed_in = client.post(
        f"{API}/login/access-token", data={"username": sam.email, "password": password}
    )
    assert signed_in.status_code == 200
    membership = crud.get_membership(session=db, user_id=sam.id, agency_id=agency.id)
    assert membership is not None
    assert (membership.role, membership.all_workspaces) == (AgencyRole.member, False)

    client.delete(
        f"{API}/agencies/{agency.id}/members/{sam.id}", cookies=_web(db, admin)
    )

    refused = client.post(
        f"{API}/login/access-token", data={"username": sam.email, "password": password}
    )
    assert refused.status_code == 403
    assert refused.json()["detail"].startswith(
        "You no longer have access to any workspace."
    )
    assert (
        db.exec(select(WorkspaceMember).where(WorkspaceMember.user_id == sam.id)).all()
        == []
    )


def test_a_workspace_row_alone_gives_no_access(client: TestClient, db: Session) -> None:
    """Access needs the person to be in the workspace's agency, not only a row."""
    alex, sam = _person(db), _person(db)
    other = str(sam.company_id)
    db.add(WorkspaceMember(user_id=alex.id, company_id=sam.company_id))
    db.commit()
    try:
        assert other not in _reached_on_web(client, _web(db, alex))
        assert other not in _reached_by_assistant(client, _assistant(db, alex))
        opened = client.post(f"{API}/workspaces/{other}/open", cookies=_web(db, alex))
        assert opened.status_code == 404
    finally:
        stray = db.get(WorkspaceMember, (alex.id, sam.company_id))
        db.delete(stray)
        db.commit()


# ── The migration's grouping ──


def _migration():
    path = Path(__file__).parents[3] / "alembic" / "versions" / "0048_agency.py"
    spec = importlib.util.spec_from_file_location("migration_0048", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_existing_workspaces_are_grouped_by_the_people_they_share() -> None:
    group = _migration().group_into_agencies
    workspaces = [
        ("w1", "Bright Dental"),
        ("w2", "Kestrel Plumbing"),
        ("w3", "Solo"),
        ("w4", "Shared"),
        ("w5", "Nobody's"),
    ]
    memberships = [
        # Alex has two client workspaces and shares one of them with Sam.
        ("alex", "w1", "alex@signal-voice.com"),
        ("alex", "w2", "alex@signal-voice.com"),
        ("sam", "w2", "sam@example.com"),
        # Robin is on their own.
        ("robin", "w3", "robin@north-star.io"),
        # Two people share one workspace; Jo was there first.
        ("jo", "w4", "jo@harbor.co"),
        ("kim", "w4", "kim@example.org"),
    ]

    agencies = {a["name"]: a for a in group(workspaces, memberships)}

    assert set(agencies) == {"Signal Voice", "North Star", "Harbor", "Nobody's"}
    assert sorted(agencies["Signal Voice"]["workspaces"]) == ["w1", "w2"]
    # Alex reached both, so "all workspaces"; Sam keeps only the one they had.
    assert agencies["Signal Voice"]["members"] == [("alex", True), ("sam", False)]
    assert agencies["North Star"]["members"] == [("robin", True)]
    assert agencies["Harbor"]["members"] == [("jo", True), ("kim", True)]
    assert agencies["Nobody's"] == {
        "name": "Nobody's",
        "workspaces": ["w5"],
        "members": [],
    }
    # Every workspace lands in exactly one agency.
    placed = [w for a in agencies.values() for w in a["workspaces"]]
    assert sorted(placed) == ["w1", "w2", "w3", "w4", "w5"]


def test_the_migration_put_every_workspace_and_member_in_an_agency(
    db: Session,
) -> None:
    """The test database is built by the migrations, so this holds for whatever they
    and the routes have produced: no workspace without an agency, and no workspace
    reached by a person who is not in its agency."""
    orphans = db.exec(
        select(WorkspaceMember)
        .join(Company, Company.id == WorkspaceMember.company_id)  # type: ignore[arg-type]
        .where(
            ~select(AgencyMember)
            .where(
                AgencyMember.agency_id == Company.agency_id,
                AgencyMember.user_id == WorkspaceMember.user_id,
            )
            .exists()
        )
    ).all()
    assert orphans == []
