"""Password reset: ask for a link, open it, set a password, be signed in.

Every request goes through the API. The email is captured where it would be handed to
SMTP, and the link's token is read from it, as the person would.
"""

import hashlib
import re
import smtplib
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlmodel import Session, col, select

from app import crud
from app.core import security
from app.core.config import settings
from app.core.security import hash_api_token
from app.models import User, UserCreate
from app.models.password_reset import PasswordResetRequest
from app.tests.utils.utils import random_email, random_lower_string
from app.utils import generate_reset_password_email, send_email

API = settings.API_V1_STR
SITE = "https://app.example.com"
MCP_URL = "https://mcp.example.com/mcp"


@pytest.fixture(autouse=True)
def _email_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_NAME", "Connexity")
    monkeypatch.setattr(settings, "SITE_URL", SITE)
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", MCP_URL)
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")


class Outbox:
    """Emails handed to SMTP during a test."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def __call__(self, *, email_to: str, subject: str, html_content: str) -> bool:
        self.sent.append({"to": email_to, "subject": subject, "html": html_content})
        return True

    def token(self) -> str:
        found = re.search(rf"{re.escape(SITE)}/reset/([\w-]+)", self.sent[-1]["html"])
        assert found, "the email has no reset link"
        return found.group(1)


@pytest.fixture
def outbox() -> Generator[Outbox, None, None]:
    box = Outbox()
    with patch("app.api.routes.password_reset.send_email", box):
        yield box


def _person(db: Session, password: str | None = None) -> tuple[User, str]:
    password = password or random_lower_string()
    user = crud.create_user(
        session=db, user_create=UserCreate(email=random_email(), password=password)
    )
    return user, password


def _unique_address() -> dict[str, str]:
    """A network address no other test uses, so limits do not cross tests."""
    return {"X-Forwarded-For": str(uuid.uuid4())}


def _ask(client: TestClient, email: str, headers: dict[str, str] | None = None):
    return client.post(
        f"{API}/password-reset",
        json={"email": email},
        headers=headers or _unique_address(),
    )


def _age_requests(db: Session, email: str, by: timedelta) -> None:
    """Move an email's stored requests into the past, as if time had gone by."""
    email_hash = hashlib.sha256(email.strip().lower().encode()).hexdigest()
    rows = db.exec(
        select(PasswordResetRequest).where(
            PasswordResetRequest.email_hash == email_hash
        )
    ).all()
    for row in rows:
        row.created_at = row.created_at - by
        db.add(row)
    db.commit()


def _sign_in(client: TestClient, email: str, password: str):
    return client.post(
        f"{API}/login/access-token", data={"username": email, "password": password}
    )


def _web(user: User) -> dict[str, str]:
    token, _ = security.create_session_token(
        user_id=user.id,
        company_id=user.company_id,
        session_version=user.session_version,
    )
    return {settings.AUTH_COOKIE: token}


# ── Asking for a link ──


def test_the_answer_is_the_same_for_a_known_an_unknown_and_a_google_account(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    known, _ = _person(db)
    google = crud.create_google_user(
        session=db, email=random_email(), full_name="Alex Morgan"
    )

    answers = [
        _ask(client, known.email),
        _ask(client, random_email()),
        _ask(client, google.email),
    ]

    assert {r.status_code for r in answers} == {202}
    assert {r.content for r in answers} == {b""}
    assert [(m["to"], m["subject"]) for m in outbox.sent] == [
        (known.email, "Reset your Connexity password"),
        (google.email, "Signing in to Connexity"),
    ]
    google_email = outbox.sent[1]["html"]
    assert "no password to reset" in google_email
    assert "/reset/" not in google_email
    assert f'href="{SITE}/login"' in google_email


def test_the_reset_email_is_the_designed_one(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)

    _ask(client, user.email)

    html = outbox.sent[0]["html"]
    link = f"{SITE}/reset/{outbox.token()}"
    assert "Someone asked to reset the password for this account." in html
    assert html.count(link) == 3  # the button, the plain link and its text
    assert "This link works once and expires in 1 hour." in html
    assert 'src="cid:connexity-logo.png"' in html


def test_the_email_is_matched_ignoring_case(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)

    _ask(client, user.email.upper())

    assert [m["to"] for m in outbox.sent] == [user.email]


def test_an_inactive_account_gets_no_email(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)
    user.is_active = False
    db.add(user)
    db.commit()

    r = _ask(client, user.email)

    assert r.status_code == 202
    assert outbox.sent == []


def test_an_address_that_is_not_an_email_is_refused(
    client: TestClient, outbox: Outbox
) -> None:
    r = _ask(client, "alex@example")

    assert r.status_code == 422
    assert outbox.sent == []


def test_only_hashes_are_stored(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)

    _ask(client, user.email, headers={"X-Forwarded-For": "198.51.100.7"})
    token = outbox.token()

    row = db.exec(
        select(PasswordResetRequest).where(PasswordResetRequest.user_id == user.id)
    ).one()
    assert row.token_hash == hash_api_token(token)
    stored = " ".join(str(value) for value in row.model_dump().values())
    assert token not in stored
    assert user.email not in stored
    assert "198.51.100.7" not in stored
    assert row.expires_at is not None
    assert (
        timedelta(minutes=59) < row.expires_at - datetime.now(UTC) <= timedelta(hours=1)
    )


# ── Opening the link and setting a password ──


def test_a_link_shows_its_account_then_sets_the_password_and_signs_in(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, old_password = _person(db)
    _ask(client, user.email)
    token = outbox.token()

    shown = client.get(f"{API}/password-reset/{token}")
    assert shown.status_code == 200
    assert shown.json() == {"email": user.email}

    saved = client.post(
        f"{API}/password-reset/{token}", json={"new_password": "correct-horse-7"}
    )
    assert saved.status_code == 200, saved.text
    session_cookie = {settings.AUTH_COOKIE: saved.json()["access_token"]}
    me = client.post(f"{API}/login/test-token", cookies=session_cookie)
    assert me.status_code == 200
    assert me.json()["email"] == user.email

    assert _sign_in(client, user.email, "correct-horse-7").status_code == 200
    assert _sign_in(client, user.email, old_password).status_code == 400


def test_a_link_works_once(client: TestClient, db: Session, outbox: Outbox) -> None:
    user, _ = _person(db)
    _ask(client, user.email)
    token = outbox.token()
    url = f"{API}/password-reset/{token}"

    assert client.post(url, json={"new_password": "correct-horse-7"}).status_code == 200

    again = client.post(url, json={"new_password": "another-horse-8"})
    assert again.status_code == 404
    assert client.get(url).status_code == 404
    assert _sign_in(client, user.email, "correct-horse-7").status_code == 200
    assert _sign_in(client, user.email, "another-horse-8").status_code == 400


def test_a_link_stops_working_after_an_hour(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, old_password = _person(db)
    _ask(client, user.email)
    token = outbox.token()
    db.execute(
        update(PasswordResetRequest)
        .where(col(PasswordResetRequest.user_id) == user.id)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    db.commit()
    url = f"{API}/password-reset/{token}"

    assert client.get(url).status_code == 404
    assert client.post(url, json={"new_password": "correct-horse-7"}).status_code == 404
    assert _sign_in(client, user.email, old_password).status_code == 200


def test_an_unknown_link_is_the_same_404(client: TestClient) -> None:
    url = f"{API}/password-reset/not-a-real-token"

    assert client.get(url).status_code == 404
    r = client.post(url, json={"new_password": "correct-horse-7"})
    assert r.status_code == 404
    assert r.json()["detail"] == "This link no longer works"


def test_a_newer_link_ends_the_older_one(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)
    _ask(client, user.email)
    first = outbox.token()
    _age_requests(db, user.email, timedelta(minutes=1))
    assert _ask(client, user.email).status_code == 202
    second = outbox.token()

    assert first != second
    assert client.get(f"{API}/password-reset/{first}").status_code == 404
    assert client.get(f"{API}/password-reset/{second}").status_code == 200


def test_a_short_password_is_refused_and_the_link_still_works(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)
    _ask(client, user.email)
    url = f"{API}/password-reset/{outbox.token()}"

    assert client.post(url, json={"new_password": "abc12"}).status_code == 422
    assert client.post(url, json={"new_password": "correct-horse-7"}).status_code == 200


# ── Sessions and assistants ──


def test_a_reset_ends_earlier_web_sessions_and_keeps_assistants_working(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    user, _ = _person(db)
    before = _web(user)
    _, personal_token = crud.create_personal_access_token(
        session=db, user_id=user.id, name="Claude Code"
    )
    assistant = {"Authorization": f"Bearer {personal_token}"}
    assert client.post(f"{API}/login/test-token", cookies=before).status_code == 200
    assert client.get(f"{API}/mcp/workspaces", headers=assistant).status_code == 200

    _ask(client, user.email)
    saved = client.post(
        f"{API}/password-reset/{outbox.token()}",
        json={"new_password": "correct-horse-7"},
    )
    after = {settings.AUTH_COOKIE: saved.json()["access_token"]}

    refused = client.post(f"{API}/login/test-token", cookies=before)
    assert refused.status_code == 401
    assert client.post(f"{API}/login/test-token", cookies=after).status_code == 200
    assert client.get(f"{API}/mcp/workspaces", headers=assistant).status_code == 200


def test_a_session_from_before_the_version_existed_still_works(
    client: TestClient, db: Session
) -> None:
    user, _ = _person(db)
    old_style = security.create_access_token(
        user.id, timedelta(hours=1), additional_claims={"cid": str(user.company_id)}
    )

    r = client.post(
        f"{API}/login/test-token", cookies={settings.AUTH_COOKIE: old_style}
    )

    assert r.status_code == 200


# ── Limits ──


def test_asking_again_within_45_seconds_is_refused_for_any_email(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    known, _ = _person(db)
    unknown = random_email()
    assert _ask(client, known.email).status_code == 202
    assert _ask(client, unknown).status_code == 202

    again_known = _ask(client, known.email)
    again_unknown = _ask(client, unknown)

    assert again_known.status_code == again_unknown.status_code == 429
    assert again_known.json() == again_unknown.json()
    assert again_known.json()["detail"] == "Too many attempts. Try again later."
    assert len(outbox.sent) == 1

    _age_requests(db, known.email, timedelta(seconds=46))
    assert _ask(client, known.email).status_code == 202


def test_an_email_gets_three_requests_an_hour(
    client: TestClient, db: Session, outbox: Outbox
) -> None:
    for email in (_person(db)[0].email, random_email()):
        for _ in range(3):
            assert _ask(client, email).status_code == 202
            _age_requests(db, email, timedelta(minutes=5))

        assert _ask(client, email).status_code == 429

        _age_requests(db, email, timedelta(minutes=50))
        assert _ask(client, email).status_code == 202


def test_a_network_address_gets_ten_requests_an_hour(
    client: TestClient, outbox: Outbox
) -> None:
    address = _unique_address()
    for _ in range(10):
        assert _ask(client, random_email(), headers=address).status_code == 202

    assert _ask(client, random_email(), headers=address).status_code == 429
    assert _ask(client, random_email()).status_code == 202


def test_the_address_is_the_first_one_forwarded(
    client: TestClient, outbox: Outbox
) -> None:
    person = str(uuid.uuid4())
    for hop in range(10):
        headers = {"X-Forwarded-For": f"{person}, 10.0.0.{hop}"}
        assert _ask(client, random_email(), headers=headers).status_code == 202

    last = {"X-Forwarded-For": f"{person}, 10.0.0.99"}
    assert _ask(client, random_email(), headers=last).status_code == 429


# ── A deployment that cannot send email ──


def test_sign_in_options_say_whether_reset_is_offered(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get(f"{API}/auth/google").json()["password_reset"] is True

    monkeypatch.setattr(settings, "SMTP_HOST", None)

    assert client.get(f"{API}/auth/google").json()["password_reset"] is False


def test_without_email_settings_asking_is_a_404(
    client: TestClient, db: Session, outbox: Outbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, _ = _person(db)
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    r = _ask(client, user.email)

    assert r.status_code == 404
    assert outbox.sent == []


# ── The email provider ──


def _message(send: MagicMock) -> MagicMock:
    message = MagicMock()
    message.send = send
    return message


def test_a_provider_that_times_out_does_not_change_the_answer(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    user, _ = _person(db)
    send = MagicMock(side_effect=TimeoutError("timed out"))

    with patch("app.utils.emails.Message", return_value=_message(send)):
        r = _ask(client, user.email)

    assert r.status_code == 202
    assert send.call_args.kwargs["smtp"]["timeout"] == 10
    assert "Email not sent (Reset your Connexity password): timed out" in caplog.text


def test_a_provider_that_refuses_is_logged_with_its_answer(
    client: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    user, _ = _person(db)
    refused = MagicMock(status_code=550, error=None, status_text="Domain not verified")
    send = MagicMock(return_value=refused)

    with patch("app.utils.emails.Message", return_value=_message(send)):
        r = _ask(client, user.email)

    assert r.status_code == 202
    assert "status 550, Domain not verified" in caplog.text


def test_the_logo_travels_inside_the_email() -> None:
    with_logo, without = MagicMock(), MagicMock()
    with_logo.send.return_value = without.send.return_value = MagicMock(status_code=250)

    with patch("app.utils.emails.Message", side_effect=[with_logo, without]):
        send_email(
            email_to="alex@example.com",
            subject="s",
            html_content=generate_reset_password_email(token="t").html_content,
        )
        send_email(email_to="alex@example.com", subject="s", html_content="<p>hi</p>")

    attached = with_logo.attach.call_args.kwargs
    assert attached["filename"] == "connexity-logo.png"
    assert attached["content_disposition"] == "inline"
    assert attached["data"].startswith(b"\x89PNG")
    without.attach.assert_not_called()


def test_send_email_says_whether_the_provider_accepted() -> None:
    accepted = MagicMock(return_value=MagicMock(status_code=250))
    empty = MagicMock(return_value=MagicMock(status_code=None, error=None))
    broken = MagicMock(side_effect=smtplib.SMTPServerDisconnected("closed"))

    results = []
    for send in (accepted, empty, broken):
        with patch("app.utils.emails.Message", return_value=_message(send)):
            results.append(
                send_email(email_to="alex@example.com", subject="s", html_content="h")
            )

    assert results == [True, False, False]
