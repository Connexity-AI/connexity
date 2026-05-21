import base64
import hashlib
import html
import logging
import secrets
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jwt.exceptions import InvalidTokenError

from app import crud
from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.models import (
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthClientRegistrationRequest,
    OAuthClientRegistrationResponse,
    OAuthRefreshToken,
    TokenPayload,
    User,
    UserCreate,
)

router = APIRouter(tags=["oauth"])
logger = logging.getLogger(__name__)

SUPPORTED_SCOPE = "mcp:access"
SUPPORTED_GRANT_TYPES = {"authorization_code", "refresh_token"}
SUPPORTED_RESPONSE_TYPES = {"code"}
REFRESH_TOKEN_EXPIRE_DAYS = 30
SUPPORTED_REDIRECT_URIS = {
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
}


def _issuer() -> str:
    return settings.oauth_issuer_url


def _metadata() -> dict[str, object]:
    issuer = _issuer()
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "jwks_uri": f"{issuer}/.well-known/jwks.json",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": [SUPPORTED_SCOPE],
    }


def _allowed_redirect_uris() -> set[str]:
    return set(settings.oauth_allowed_redirect_uris) | SUPPORTED_REDIRECT_URIS


def _resolve_resource(resource: str | None) -> str | None:
    if resource and resource.strip():
        return resource.strip()
    return settings.oauth_default_resource_url


def _get_cookie_user(request: Request, session: SessionDep) -> User | None:
    token = request.cookies.get(settings.AUTH_COOKIE)
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[security.ALGORITHM],
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValueError):
        return None
    if not token_data.sub:
        return None
    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError:
        return None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def _validate_authorize_request(
    *,
    session: SessionDep,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str | None,
    code_challenge_method: str | None,
    resource: str | None,
) -> OAuthClient:
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response_type")
    if not _resolve_resource(resource):
        raise HTTPException(status_code=400, detail="Missing resource")
    if not code_challenge:
        raise HTTPException(status_code=400, detail="Missing code_challenge")
    if code_challenge_method != "S256":
        raise HTTPException(status_code=400, detail="Unsupported code_challenge_method")

    client = session.get(OAuthClient, client_id)
    if client is None:
        raise HTTPException(status_code=400, detail="Unknown client_id")
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    return client


def _create_authorization_code(
    *,
    session: SessionDep,
    user: User,
    client_id: str,
    redirect_uri: str,
    scope: str | None,
    resource: str,
    code_challenge: str,
    code_challenge_method: str,
) -> str:
    code = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.OAUTH_AUTH_CODE_EXPIRE_MINUTES
    )
    auth_code = OAuthAuthorizationCode(
        code=code,
        client_id=client_id,
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scope or SUPPORTED_SCOPE,
        resource=resource,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=expires_at,
    )
    session.add(auth_code)
    session.commit()
    return code


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_refresh_token(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    client_id: str,
    scope: str | None,
    resource: str,
) -> str:
    token = secrets.token_urlsafe(64)
    refresh_token = OAuthRefreshToken(
        token_hash=_hash_token(token),
        client_id=client_id,
        user_id=user_id,
        scope=scope or SUPPORTED_SCOPE,
        resource=resource,
        expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(refresh_token)
    return token


def _redirect_with_code(
    *,
    redirect_uri: str,
    code: str,
    state: str | None,
) -> RedirectResponse:
    params = {"code": code}
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        f"{redirect_uri}{separator}{urlencode(params)}",
        status_code=303,
    )


def _hidden_input(name: str, value: str | None) -> str:
    return (
        f'<input type="hidden" name="{html.escape(name)}" '
        f'value="{html.escape(value or "")}" />'
    )


def _authorization_query(
    *,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str | None,
    state: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
    resource: str | None,
) -> str:
    params = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": _resolve_resource(resource),
    }
    return urlencode({key: value for key, value in params.items() if value})


def _authorize_form(
    *,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str | None,
    state: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
    resource: str | None,
    mode: str = "signin",
    error: str | None = None,
) -> HTMLResponse:
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    hidden = "\n".join(
        [
            _hidden_input("response_type", response_type),
            _hidden_input("client_id", client_id),
            _hidden_input("redirect_uri", redirect_uri),
            _hidden_input("scope", scope),
            _hidden_input("state", state),
            _hidden_input("code_challenge", code_challenge),
            _hidden_input("code_challenge_method", code_challenge_method),
            _hidden_input("resource", _resolve_resource(resource)),
        ]
    )
    signup_mode = mode == "signup"
    title = "Create your Connexity account" if signup_mode else "Connect Claude"
    description = (
        "Create an account, then Claude can use your MCP tools for that workspace."
        if signup_mode
        else "Sign in to Connexity to allow Claude to use your MCP tools."
    )
    form_action = (
        "/oauth/authorize/signup/confirm" if signup_mode else "/oauth/authorize/confirm"
    )
    password_autocomplete = "new-password" if signup_mode else "current-password"
    full_name_field = (
        """
        <label for="full_name">Name</label>
        <input id="full_name" name="full_name" type="text" autocomplete="name" />
        """.strip()
        if signup_mode
        else ""
    )
    switch_query = _authorization_query(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    switch_html = (
        f'<p class="switch">Already have an account? '
        f'<a href="/oauth/authorize?{html.escape(switch_query)}">Sign in</a></p>'
        if signup_mode
        else f'<p class="switch">Don&apos;t have an account? '
        f'<a href="/oauth/authorize/signup?{html.escape(switch_query)}">Create one</a></p>'
    )
    return HTMLResponse(
        f"""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Connect Claude</title>
    <style>
      body {{
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #f7f7f5;
        color: #181817;
      }}
      main {{
        width: min(420px, calc(100vw - 32px));
        background: white;
        border: 1px solid #deded8;
        border-radius: 8px;
        padding: 28px;
        box-shadow: 0 18px 50px rgb(0 0 0 / 0.08);
      }}
      h1 {{ font-size: 22px; margin: 0 0 8px; }}
      p {{ color: #5c5c56; line-height: 1.5; margin: 0 0 20px; }}
      label {{ display: block; font-size: 13px; font-weight: 600; margin: 14px 0 6px; }}
      input[type="email"], input[type="password"], input[type="text"] {{
        width: 100%;
        box-sizing: border-box;
        border: 1px solid #cfcfca;
        border-radius: 6px;
        padding: 11px 12px;
        font-size: 15px;
      }}
      button {{
        width: 100%;
        margin-top: 20px;
        border: 0;
        border-radius: 6px;
        background: #181817;
        color: white;
        font-weight: 700;
        padding: 12px 14px;
        cursor: pointer;
      }}
      .error {{ color: #b42318; font-weight: 600; }}
      .switch {{
        margin: 18px 0 0;
        text-align: center;
        font-size: 14px;
      }}
      .switch a {{ color: #181817; font-weight: 700; }}
    </style>
  </head>
  <body>
    <main>
      <h1>{html.escape(title)}</h1>
      <p>{html.escape(description)}</p>
      {error_html}
      <form method="post" action="{form_action}">
        {hidden}
        {full_name_field}
        <label for="email">Email</label>
        <input id="email" name="email" type="email" autocomplete="email" required />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" autocomplete="{password_autocomplete}" minlength="6" maxlength="40" required />
        <button type="submit">Connect</button>
      </form>
      {switch_html}
    </main>
  </body>
</html>
""".strip()
    )


@router.get("/.well-known/oauth-authorization-server")
def oauth_authorization_server_metadata() -> Mapping[str, object]:
    return _metadata()


@router.get("/.well-known/openid-configuration")
def openid_configuration() -> Mapping[str, object]:
    return _metadata()


@router.get("/.well-known/jwks.json")
def jwks() -> Mapping[str, object]:
    return security.oauth_jwks()


@router.post("/oauth/register", response_model=OAuthClientRegistrationResponse)
async def register_oauth_client(
    request: Request,
    session: SessionDep,
    body: OAuthClientRegistrationRequest,
) -> OAuthClientRegistrationResponse:
    logger.info("OAuth DCR request body: %s", (await request.body()).decode("utf-8"))
    logger.info(
        "OAuth DCR parsed metadata: redirect_uris=%s grant_types=%s "
        "response_types=%s token_endpoint_auth_method=%s scope=%s",
        body.redirect_uris,
        body.grant_types,
        body.response_types,
        body.token_endpoint_auth_method,
        body.scope,
    )
    if not body.redirect_uris:
        logger.warning("OAuth DCR rejected: redirect_uris is required")
        raise HTTPException(status_code=400, detail="redirect_uris is required")

    allowed_redirect_uris = _allowed_redirect_uris()
    invalid_redirects = [
        uri for uri in body.redirect_uris if uri not in allowed_redirect_uris
    ]
    if invalid_redirects:
        logger.warning(
            "OAuth DCR rejected: unsupported redirect_uri values=%s allowed=%s",
            invalid_redirects,
            sorted(allowed_redirect_uris),
        )
        raise HTTPException(status_code=400, detail="Unsupported redirect_uri")

    token_auth_method = body.token_endpoint_auth_method or "none"
    if token_auth_method != "none":
        logger.warning(
            "OAuth DCR rejected: unsupported token_endpoint_auth_method=%s",
            token_auth_method,
        )
        raise HTTPException(
            status_code=400,
            detail="Only public PKCE clients are supported",
        )

    grant_types = body.grant_types or ["authorization_code"]
    response_types = body.response_types or ["code"]
    unsupported_grants = set(grant_types) - SUPPORTED_GRANT_TYPES
    unsupported_responses = set(response_types) - SUPPORTED_RESPONSE_TYPES
    if (
        "authorization_code" not in grant_types
        or unsupported_grants
        or unsupported_responses
    ):
        logger.warning(
            "OAuth DCR rejected: unsupported grant_types=%s response_types=%s",
            grant_types,
            response_types,
        )
        raise HTTPException(status_code=400, detail="Unsupported client metadata")

    client = OAuthClient(
        client_id=secrets.token_urlsafe(32),
        client_name=body.client_name or "Claude",
        redirect_uris=body.redirect_uris,
        grant_types=grant_types,
        response_types=response_types,
        scope=body.scope or SUPPORTED_SCOPE,
        token_endpoint_auth_method=token_auth_method,
        raw_metadata=body.model_dump(mode="json"),
    )
    session.add(client)
    session.commit()
    return OAuthClientRegistrationResponse(
        client_id=client.client_id,
        client_id_issued_at=int(client.created_at.timestamp()),
        client_name=client.client_name,
        redirect_uris=client.redirect_uris,
        grant_types=client.grant_types,
        response_types=client.response_types,
        scope=client.scope,
        token_endpoint_auth_method=client.token_endpoint_auth_method,
    )


@router.get("/oauth/authorize", response_model=None)
def authorize(
    request: Request,
    session: SessionDep,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    scope: str | None = None,
    state: str | None = None,
    resource: str | None = None,
):
    resolved_resource = _resolve_resource(resource)
    _validate_authorize_request(
        session=session,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resolved_resource,
    )
    user = _get_cookie_user(request, session)
    if user is None:
        return _authorize_form(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resolved_resource,
        )

    code = _create_authorization_code(
        session=session,
        user=user,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        resource=resolved_resource or "",
        code_challenge=code_challenge or "",
        code_challenge_method=code_challenge_method or "S256",
    )
    return _redirect_with_code(redirect_uri=redirect_uri, code=code, state=state)


@router.get("/oauth/authorize/signup", response_model=None)
def authorize_signup(
    request: Request,
    session: SessionDep,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    scope: str | None = None,
    state: str | None = None,
    resource: str | None = None,
):
    resolved_resource = _resolve_resource(resource)
    _validate_authorize_request(
        session=session,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resolved_resource,
    )
    user = _get_cookie_user(request, session)
    if user is not None:
        code = _create_authorization_code(
            session=session,
            user=user,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            resource=resolved_resource or "",
            code_challenge=code_challenge or "",
            code_challenge_method=code_challenge_method or "S256",
        )
        return _redirect_with_code(redirect_uri=redirect_uri, code=code, state=state)

    return _authorize_form(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resolved_resource,
        mode="signup",
    )


@router.post("/oauth/authorize/confirm", response_model=None)
def authorize_confirm(
    session: SessionDep,
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    scope: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
    resource: Annotated[str | None, Form()] = None,
):
    resolved_resource = _resolve_resource(resource)
    _validate_authorize_request(
        session=session,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resolved_resource,
    )
    user = crud.authenticate(session=session, email=email, password=password)
    if user is None or not user.is_active:
        return _authorize_form(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resolved_resource,
            error="Incorrect email or password.",
        )

    code = _create_authorization_code(
        session=session,
        user=user,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        resource=resolved_resource or "",
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    response = _redirect_with_code(redirect_uri=redirect_uri, code=code, state=state)
    auth_token = security.create_access_token(
        user.id,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    response.set_cookie(
        settings.AUTH_COOKIE,
        auth_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "local",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60,
    )
    return response


@router.post("/oauth/authorize/signup/confirm", response_model=None)
def authorize_signup_confirm(
    session: SessionDep,
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    full_name: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
    resource: Annotated[str | None, Form()] = None,
):
    resolved_resource = _resolve_resource(resource)
    _validate_authorize_request(
        session=session,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resolved_resource,
    )
    existing_user = crud.get_user_by_email(session=session, email=email)
    if existing_user is not None:
        return _authorize_form(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            resource=resolved_resource,
            mode="signup",
            error="An account already exists for this email. Sign in instead.",
        )

    user = crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password=password,
            full_name=full_name or None,
        ),
    )
    code = _create_authorization_code(
        session=session,
        user=user,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        resource=resolved_resource or "",
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    response = _redirect_with_code(redirect_uri=redirect_uri, code=code, state=state)
    auth_token = security.create_access_token(
        user.id,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    response.set_cookie(
        settings.AUTH_COOKIE,
        auth_token,
        httponly=True,
        secure=settings.ENVIRONMENT != "local",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_HOURS * 60 * 60,
    )
    return response


def _verify_pkce(*, code_verifier: str, code_challenge: str) -> bool:
    try:
        verifier_bytes = code_verifier.encode("ascii")
    except UnicodeEncodeError:
        return False
    digest = hashlib.sha256(verifier_bytes).digest()
    expected = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return secrets.compare_digest(expected, code_challenge)


def _is_expired(expires_at: datetime, now: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at < now


def _oauth_token_response(
    *,
    subject: uuid.UUID,
    audience: str,
    issuer: str,
    client_id: str,
    scope: str,
    expires_delta: timedelta,
    refresh_token: str | None = None,
) -> JSONResponse:
    access_token, expires_at = security.create_oauth_access_token(
        subject=subject,
        audience=audience,
        issuer=issuer,
        client_id=client_id,
        scope=scope,
        expires_delta=expires_delta,
    )
    body: dict[str, object] = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": int(expires_delta.total_seconds()),
        "expires_at": int(expires_at),
        "scope": scope,
    }
    if refresh_token:
        body["refresh_token"] = refresh_token
    return JSONResponse(body)


@router.post("/oauth/token")
def token(
    session: SessionDep,
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    code_verifier: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
) -> JSONResponse:
    if grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh_token")

        stored_refresh_token = session.get(
            OAuthRefreshToken, _hash_token(refresh_token)
        )
        now = datetime.now(UTC)
        if (
            stored_refresh_token is None
            or stored_refresh_token.client_id != client_id
            or stored_refresh_token.revoked_at is not None
            or _is_expired(stored_refresh_token.expires_at, now)
        ):
            raise HTTPException(status_code=400, detail="Invalid refresh_token")

        stored_refresh_token.revoked_at = now
        rotated_refresh_token = _create_refresh_token(
            session=session,
            user_id=stored_refresh_token.user_id,
            client_id=stored_refresh_token.client_id,
            scope=stored_refresh_token.scope,
            resource=stored_refresh_token.resource,
        )
        session.add(stored_refresh_token)
        session.commit()

        expires_delta = timedelta(minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
        return _oauth_token_response(
            subject=stored_refresh_token.user_id,
            audience=stored_refresh_token.resource,
            issuer=_issuer(),
            client_id=stored_refresh_token.client_id,
            scope=stored_refresh_token.scope or SUPPORTED_SCOPE,
            expires_delta=expires_delta,
            refresh_token=rotated_refresh_token,
        )

    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Unsupported grant_type")
    if not code or not redirect_uri or not code_verifier:
        raise HTTPException(status_code=400, detail="Missing authorization code fields")

    auth_code = session.get(OAuthAuthorizationCode, code)
    now = datetime.now(UTC)
    if (
        auth_code is None
        or auth_code.client_id != client_id
        or auth_code.redirect_uri != redirect_uri
        or auth_code.consumed_at is not None
        or _is_expired(auth_code.expires_at, now)
    ):
        raise HTTPException(status_code=400, detail="Invalid authorization code")

    if not _verify_pkce(
        code_verifier=code_verifier,
        code_challenge=auth_code.code_challenge,
    ):
        raise HTTPException(status_code=400, detail="Invalid code_verifier")

    auth_code.consumed_at = now
    client = session.get(OAuthClient, client_id)
    refresh_token_value = None
    if client and "refresh_token" in client.grant_types:
        refresh_token_value = _create_refresh_token(
            session=session,
            user_id=auth_code.user_id,
            client_id=auth_code.client_id,
            scope=auth_code.scope,
            resource=auth_code.resource,
        )
    session.add(auth_code)
    session.commit()

    expires_delta = timedelta(minutes=settings.OAUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
    return _oauth_token_response(
        subject=auth_code.user_id,
        audience=auth_code.resource,
        issuer=_issuer(),
        client_id=auth_code.client_id,
        scope=auth_code.scope or SUPPORTED_SCOPE,
        expires_delta=expires_delta,
        refresh_token=refresh_token_value,
    )
