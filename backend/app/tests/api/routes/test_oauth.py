import base64
import hashlib
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import UserCreate
from app.tests.utils.utils import random_email, random_lower_string

REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"
RESOURCE = "https://mcp.example.com/mcp"


def _pkce_pair() -> tuple[str, str]:
    verifier = "test-code-verifier-with-enough-entropy"
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _allow(client: TestClient, consent: httpx.Response) -> httpx.Response:
    """Press Allow on the consent page reached by a sign-in or sign-up form post."""
    sent = parse_qs(consent.request.content.decode())
    fields = {
        key: values[0]
        for key, values in sent.items()
        if key not in {"email", "password", "full_name"}
    }
    return client.post("/oauth/authorize/allow", data=fields, follow_redirects=False)


def _register_client(client: TestClient) -> str:
    response = client.post(
        "/oauth/register",
        json={
            "client_name": "Claude",
            "redirect_uris": [REDIRECT_URI],
            "grant_types": ["authorization_code", "refresh_token"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grant_types"] == ["authorization_code", "refresh_token"]
    assert body["token_endpoint_auth_method"] == "none"
    return body["client_id"]


def test_oauth_metadata_and_jwks(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")

    metadata = client.get("/.well-known/oauth-authorization-server")
    assert metadata.status_code == 200
    body = metadata.json()
    assert body["issuer"] == "https://backend.example.com"
    assert body["registration_endpoint"] == "https://backend.example.com/oauth/register"
    assert body["grant_types_supported"] == ["authorization_code", "refresh_token"]
    assert body["token_endpoint_auth_methods_supported"] == ["none"]

    jwks = client.get("/.well-known/jwks.json")
    assert jwks.status_code == 200
    assert jwks.json()["keys"][0]["kty"] == "OKP"


def test_dcr_rejects_non_claude_redirect(client: TestClient) -> None:
    response = client.post(
        "/oauth/register",
        json={
            "client_name": "Bad client",
            "redirect_uris": ["https://attacker.example.com/callback"],
        },
    )

    assert response.status_code == 400


def test_dcr_accepts_claude_refresh_token_metadata(client: TestClient) -> None:
    response = client.post(
        "/oauth/register",
        json={
            "redirect_uris": [REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "mcp:access",
            "client_name": "Claude",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["client_name"] == "Claude"
    assert body["grant_types"] == ["authorization_code", "refresh_token"]


def test_oauth_signup_flow_creates_user_and_continues_to_claude(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    client_id = _register_client(client)
    verifier, challenge = _pkce_pair()
    email = random_email()
    password = random_lower_string()

    signup = client.get(
        "/oauth/authorize/signup",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "state": "signup-state",
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert signup.status_code == 200
    assert "Create an account" in signup.text
    assert "Claude wants to connect to Connexity" in signup.text

    confirmed = client.post(
        "/oauth/authorize/signup/confirm",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "state": "signup-state",
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "full_name": "New User",
            "email": email,
            "password": password,
        },
        follow_redirects=False,
    )
    assert confirmed.status_code == 200
    assert "Allow" in confirmed.text
    confirmed = _allow(client, confirmed)
    assert confirmed.status_code == 303
    location = confirmed.headers["location"]
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == REDIRECT_URI
    query = parse_qs(parsed.query)
    assert query["state"] == ["signup-state"]

    token = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": query["code"][0],
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200
    assert token.json()["access_token"]


def test_authorize_uses_default_resource_when_client_omits_resource(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    monkeypatch.setattr(settings, "OAUTH_DEFAULT_RESOURCE_URL", RESOURCE)
    client.cookies.clear()
    client_id = _register_client(client)
    _, challenge = _pkce_pair()

    authorize = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "state": "state-without-resource",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )

    assert authorize.status_code == 200
    assert f'name="resource" value="{RESOURCE}"' in authorize.text


def test_authorization_code_pkce_flow_issues_mcp_access_token(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    client.cookies.clear()
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    email = random_email()
    password = random_lower_string()
    user = crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    client_id = _register_client(client)
    verifier, challenge = _pkce_pair()

    authorize = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "state": "state-123",
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert authorize.status_code == 200
    assert "Claude wants to connect to Connexity" in authorize.text

    confirmed = client.post(
        "/oauth/authorize/confirm",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "state": "state-123",
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "email": email,
            "password": password,
        },
        follow_redirects=False,
    )
    assert confirmed.status_code == 200
    assert "Allow" in confirmed.text
    confirmed = _allow(client, confirmed)
    assert confirmed.status_code == 303
    location = confirmed.headers["location"]
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == REDIRECT_URI
    query = parse_qs(parsed.query)
    assert query["state"] == ["state-123"]
    code = query["code"][0]

    token = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200
    token_body = token.json()
    assert token_body["token_type"] == "Bearer"
    assert token_body["scope"] == "mcp:access"
    assert token_body["refresh_token"]

    jwk_set = jwt.PyJWKSet.from_dict(client.get("/.well-known/jwks.json").json())
    signing_key = jwk_set.keys[0].key
    payload = jwt.decode(
        token_body["access_token"],
        signing_key,
        algorithms=["EdDSA"],
        audience=RESOURCE,
        issuer="https://backend.example.com",
    )
    assert payload["sub"] == str(user.id)
    assert payload["azp"] == client_id
    assert payload["scope"] == "mcp:access"

    refreshed = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": token_body["refresh_token"],
        },
    )
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()
    assert refreshed_body["access_token"]
    assert refreshed_body["refresh_token"]
    assert refreshed_body["refresh_token"] != token_body["refresh_token"]


def test_token_rejects_non_ascii_code_verifier(
    client: TestClient,
    db: Session,
    monkeypatch,
) -> None:
    client.cookies.clear()
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    email = random_email()
    password = random_lower_string()
    crud.create_user(
        session=db,
        user_create=UserCreate(email=email, password=password),
    )
    client_id = _register_client(client)
    _, challenge = _pkce_pair()

    confirmed = client.post(
        "/oauth/authorize/confirm",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "state": "state-non-ascii",
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "email": email,
            "password": password,
        },
        follow_redirects=False,
    )
    assert confirmed.status_code == 200
    assert "Allow" in confirmed.text
    confirmed = _allow(client, confirmed)
    assert confirmed.status_code == 303
    code = parse_qs(urlparse(confirmed.headers["location"]).query)["code"][0]

    token = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": "verifier-with-accent-é",
        },
    )

    assert token.status_code == 400
    assert token.json()["detail"] == "Invalid code_verifier"


def test_oauth_signup_with_an_invalid_email_shows_the_form_again(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    client_id = _register_client(client)
    _, challenge = _pkce_pair()

    response = client.post(
        "/oauth/authorize/signup/confirm",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "mcp:access",
            "resource": RESOURCE,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "email": "ann@bright-dental.test",
            "password": random_lower_string(),
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Enter a valid email address." in response.text


def _authorize_fields(client_id: str, challenge: str) -> dict[str, str]:
    return {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "mcp:access",
        "state": "the-state",
        "resource": RESOURCE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }


def _signed_up(client: TestClient, monkeypatch) -> tuple[dict[str, str], str]:
    """Create an account through the connection page; returns the fields and email."""
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    client.cookies.clear()
    fields = _authorize_fields(_register_client(client), _pkce_pair()[1])
    email = random_email()
    consent = client.post(
        "/oauth/authorize/signup/confirm",
        data=fields | {"email": email, "password": random_lower_string()},
    )
    assert consent.status_code == 200
    assert "Connect Claude to Connexity" in consent.text
    assert email in consent.text
    return fields, email


def test_a_signed_in_person_is_asked_before_the_assistant_connects(
    client: TestClient, monkeypatch
) -> None:
    fields, _ = _signed_up(client, monkeypatch)

    again = client.get("/oauth/authorize", params=fields, follow_redirects=False)

    assert again.status_code == 200
    assert "Connect Claude to Connexity" in again.text
    assert "Allow" in again.text


def test_cancel_tells_the_assistant_access_was_denied(
    client: TestClient, monkeypatch
) -> None:
    fields, _ = _signed_up(client, monkeypatch)

    cancelled = client.post(
        "/oauth/authorize/cancel", data=fields, follow_redirects=False
    )

    assert cancelled.status_code == 303
    query = parse_qs(urlparse(cancelled.headers["location"]).query)
    assert query == {
        "error": ["access_denied"],
        "iss": ["https://backend.example.com"],
        "state": ["the-state"],
    }


def test_allow_without_a_session_shows_sign_in(client: TestClient, monkeypatch) -> None:
    fields, _ = _signed_up(client, monkeypatch)
    client.cookies.clear()

    response = client.post(
        "/oauth/authorize/allow", data=fields, follow_redirects=False
    )

    assert response.status_code == 200
    assert "Sign in" in response.text
    assert "code=" not in response.headers.get("location", "")


def test_not_you_signs_out_and_shows_sign_in(client: TestClient, monkeypatch) -> None:
    fields, _ = _signed_up(client, monkeypatch)

    switched = client.get("/oauth/authorize/switch", params=fields)

    assert switched.status_code == 200
    assert "Claude wants to connect to Connexity" in switched.text
    assert settings.AUTH_COOKIE not in client.cookies
    assert "Allow" not in client.get("/oauth/authorize", params=fields).text


def test_sign_up_errors_sit_under_their_field(client: TestClient, monkeypatch) -> None:
    fields, email = _signed_up(client, monkeypatch)
    client.cookies.clear()

    taken = client.post(
        "/oauth/authorize/signup/confirm",
        data=fields | {"email": email.upper(), "password": random_lower_string()},
    )
    short = client.post(
        "/oauth/authorize/signup/confirm",
        data=fields | {"email": random_email(), "password": "abc1234"},
    )

    assert "An account already uses this email." in taken.text
    assert "Use at least 8 characters." in short.text


def test_a_wrong_password_on_the_connection_page(
    client: TestClient, monkeypatch
) -> None:
    fields, email = _signed_up(client, monkeypatch)
    client.cookies.clear()

    response = client.post(
        "/oauth/authorize/confirm",
        data=fields | {"email": email, "password": "not-the-password"},
    )

    assert response.status_code == 200
    assert "That email and password don’t match." in response.text
    assert f'value="{email}"' in response.text


def test_connection_pages_cannot_be_framed(client: TestClient, monkeypatch) -> None:
    fields, _ = _signed_up(client, monkeypatch)

    consent = client.get("/oauth/authorize", params=fields)

    assert consent.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in consent.headers["content-security-policy"]


def _connect_like(
    client: TestClient, monkeypatch, *, registered: str, used: str
) -> httpx.Response:
    """Register a client, sign up through the connection page and press Allow."""
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    client.cookies.clear()
    reg = client.post(
        "/oauth/register",
        json={
            "client_name": "Claude Code",
            "redirect_uris": [registered],
            "grant_types": ["authorization_code", "refresh_token"],
        },
    )
    assert reg.status_code == 200, reg.text
    _, challenge = _pkce_pair()
    fields = _authorize_fields(reg.json()["client_id"], challenge) | {
        "redirect_uri": used
    }
    consent = client.post(
        "/oauth/authorize/signup/confirm",
        data=fields | {"email": random_email(), "password": random_lower_string()},
    )
    assert consent.status_code == 200, consent.text
    return client.post("/oauth/authorize/allow", data=fields, follow_redirects=False)


def test_claude_code_connects_with_a_loopback_callback_on_a_new_port(
    client: TestClient, monkeypatch
) -> None:
    allowed = _connect_like(
        client,
        monkeypatch,
        registered="http://localhost/callback",
        used="http://localhost:53122/callback",
    )

    assert allowed.status_code == 303
    location = urlparse(allowed.headers["location"])
    assert (location.hostname, location.port, location.path) == (
        "localhost",
        53122,
        "/callback",
    )
    query = parse_qs(location.query)
    assert query["iss"] == ["https://backend.example.com"]
    assert query["code"]


def test_chatgpt_connects_with_its_stable_callback(
    client: TestClient, monkeypatch
) -> None:
    stable = "https://chatgpt.com/connector_platform_oauth_redirect"

    allowed = _connect_like(client, monkeypatch, registered=stable, used=stable)

    assert allowed.status_code == 303
    assert allowed.headers["location"].startswith(f"{stable}?")
    assert "iss=https%3A%2F%2Fbackend.example.com" in allowed.headers["location"]


def test_a_loopback_registration_cannot_send_codes_elsewhere(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "OAUTH_ISSUER_URL", "https://backend.example.com")
    reg = client.post(
        "/oauth/register",
        json={"client_name": "Local", "redirect_uris": ["http://localhost/callback"]},
    )
    _, challenge = _pkce_pair()
    fields = _authorize_fields(reg.json()["client_id"], challenge) | {
        "redirect_uri": "http://evil.example.com/callback"
    }

    response = client.get("/oauth/authorize", params=fields)

    assert response.status_code == 400


def test_metadata_advertises_issuer_identification(client: TestClient) -> None:
    body = client.get("/.well-known/oauth-authorization-server").json()

    assert body["authorization_response_iss_parameter_supported"] is True
