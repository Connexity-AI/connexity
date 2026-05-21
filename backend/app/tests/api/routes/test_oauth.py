import base64
import hashlib
from urllib.parse import parse_qs, urlparse

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
    assert "Create your Connexity account" in signup.text

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
    assert "Connect Claude" in authorize.text

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
