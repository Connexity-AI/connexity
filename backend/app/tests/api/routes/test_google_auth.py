import time
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate, WorkspaceMember
from app.models.user import AuthProvider
from app.services.google_auth import TOKEN_URL
from app.tests.utils.utils import random_lower_string

API = settings.API_V1_STR
CLIENT_ID = "connexity-test.apps.googleusercontent.com"
SITE = "https://app.example.com"


@pytest.fixture(autouse=True)
def _google_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "SITE_URL", SITE)


def _start(client: TestClient) -> tuple[str, str]:
    """Begin sign-in; returns the state and nonce Google would echo back."""
    r = client.get(f"{API}/auth/google/start", follow_redirects=False)
    assert r.status_code == 302
    query = parse_qs(urlparse(r.headers["location"]).query)
    assert query["client_id"] == [CLIENT_ID]
    assert query["scope"] == ["openid email profile"]
    return query["state"][0], query["nonce"][0]


def _id_token(**overrides: object) -> str:
    claims: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "exp": int(time.time()) + 300,
        "email_verified": True,
        "name": "Ann Example",
    } | overrides
    return jwt.encode(claims, "unused-signature-key", algorithm="HS256")


def _callback(client: TestClient, state: str) -> httpx.Response:
    return client.get(
        f"{API}/auth/google/callback",
        params={"code": "google-code", "state": state},
        follow_redirects=False,
    )


def _email() -> str:
    return f"ann-{random_lower_string()[:8]}@bright-dental.com"


def _signed_in_user(response: httpx.Response, db: Session) -> User:
    location = urlparse(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}" == SITE
    assert location.path == "/api/auth/set-cookie"
    token = parse_qs(location.query)["access_token"][0]
    claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    user = db.get(User, claims["sub"])
    assert user is not None
    db.refresh(user)
    return user


def _assert_back_to_sign_in(response: httpx.Response) -> None:
    assert response.status_code == 302
    assert response.headers["location"] == f"{SITE}/login?error=google"


def test_status_says_whether_google_is_offered(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get(f"{API}/auth/google").json() == {"enabled": True}

    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", None)

    assert client.get(f"{API}/auth/google").json() == {"enabled": False}
    assert (
        client.get(f"{API}/auth/google/start", follow_redirects=False).status_code
        == 404
    )


@respx.mock
def test_a_new_email_creates_the_account_and_its_workspace(
    client: TestClient, db: Session
) -> None:
    email = _email()
    state, nonce = _start(client)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"id_token": _id_token(email=email, nonce=nonce)}
        )
    )

    response = _callback(client, state)

    assert response.status_code == 302
    user = _signed_in_user(response, db)
    assert user.email == email
    assert user.provider == AuthProvider.google
    assert user.hashed_password is None
    assert user.full_name == "Ann Example"
    member = db.get(WorkspaceMember, (user.id, user.company_id))
    assert member is not None


@respx.mock
def test_a_known_email_signs_in_to_the_existing_account(
    client: TestClient, db: Session
) -> None:
    email = _email()
    existing = crud.create_user(
        session=db, user_create=UserCreate(email=email, password=random_lower_string())
    )
    state, nonce = _start(client)
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"id_token": _id_token(email=email.upper(), nonce=nonce)}
        )
    )

    user = _signed_in_user(_callback(client, state), db)

    assert user.id == existing.id
    assert len(db.exec(select(User).where(User.email == email)).all()) == 1


@respx.mock
@pytest.mark.parametrize(
    "claims",
    [
        {"email_verified": False},
        {"aud": "someone-else"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 10},
        {"nonce": "a-different-nonce"},
        {"email": None},
    ],
    ids=["unverified", "audience", "issuer", "expired", "nonce", "no-email"],
)
def test_an_id_token_that_fails_a_check_is_refused(
    client: TestClient, db: Session, claims: dict[str, object]
) -> None:
    email = _email()
    state, nonce = _start(client)
    token_claims: dict[str, object] = {"email": email, "nonce": nonce} | claims
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"id_token": _id_token(**token_claims)})
    )

    _assert_back_to_sign_in(_callback(client, state))
    assert db.exec(select(User).where(User.email == email)).first() is None


@respx.mock
@pytest.mark.parametrize(
    "google",
    [
        httpx.TimeoutException("timed out"),
        httpx.Response(500, json={"error": "server_error"}),
        httpx.Response(200, json={}),
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"id_token": "not-a-jwt"}),
    ],
    ids=["timeout", "error", "empty", "malformed", "not-a-jwt"],
)
def test_google_failing_sends_the_person_back_to_sign_in(
    client: TestClient, google: httpx.Response | Exception
) -> None:
    state, _ = _start(client)
    route = respx.post(TOKEN_URL)
    if isinstance(google, Exception):
        route.mock(side_effect=google)
    else:
        route.mock(return_value=google)

    _assert_back_to_sign_in(_callback(client, state))


def test_a_refusal_or_a_forged_state_never_reaches_google(client: TestClient) -> None:
    state, _ = _start(client)
    with respx.mock(assert_all_called=False) as google:
        token_route = google.post(TOKEN_URL)

        _assert_back_to_sign_in(
            client.get(
                f"{API}/auth/google/callback",
                params={"error": "access_denied", "state": state},
                follow_redirects=False,
            )
        )
        _assert_back_to_sign_in(_callback(client, "forged-state"))
        client.cookies.clear()
        _assert_back_to_sign_in(_callback(client, state))

        assert not token_route.called
