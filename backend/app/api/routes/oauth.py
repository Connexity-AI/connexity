import base64
import hashlib
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
from pydantic import ValidationError

from app import crud
from app.api.deps import SessionDep
from app.api.routes.oauth_pages import (
    AuthorizeParams,
    ErrorField,
    consent_page,
    sign_in_page,
)
from app.core import oauth_redirects, security
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
        # Every authorization response carries `iss` (RFC 9207); ChatGPT then uses its
        # stable callback address.
        "authorization_response_iss_parameter_supported": True,
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
    if not oauth_redirects.matches_registered(redirect_uri, client.redirect_uris):
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
        company_id=user.company_id,
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
    company_id: uuid.UUID,
    client_id: str,
    scope: str | None,
    resource: str,
) -> str:
    token = secrets.token_urlsafe(64)
    refresh_token = OAuthRefreshToken(
        token_hash=_hash_token(token),
        client_id=client_id,
        company_id=company_id,
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
    params = {"code": code, "iss": _issuer()}
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        f"{redirect_uri}{separator}{urlencode(params)}",
        status_code=303,
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


def _params(
    *,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str | None,
    state: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
    resource: str | None,
) -> AuthorizeParams:
    return AuthorizeParams(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=_resolve_resource(resource),
    )


def _query(params: AuthorizeParams) -> str:
    return _authorization_query(
        response_type=params.response_type,
        client_id=params.client_id,
        redirect_uri=params.redirect_uri,
        scope=params.scope,
        state=params.state,
        code_challenge=params.code_challenge,
        code_challenge_method=params.code_challenge_method,
        resource=params.resource,
    )


def _assistant_name(client: OAuthClient) -> str:
    name = (client.client_name or "").strip()
    return name[:60] if name else "Your assistant"


def _sign_in(
    client: OAuthClient,
    params: AuthorizeParams,
    *,
    signup: bool = False,
    error: str | None = None,
    error_field: ErrorField = "form",
    email: str = "",
    full_name: str = "",
) -> HTMLResponse:
    return sign_in_page(
        params=params,
        assistant=_assistant_name(client),
        switch_query=_query(params),
        signup=signup,
        error=error,
        error_field=error_field,
        email=email,
        full_name=full_name,
    )


def _consent(client: OAuthClient, params: AuthorizeParams, user: User) -> HTMLResponse:
    person = f"{user.full_name} · {user.email}" if user.full_name else user.email
    return consent_page(
        params=params,
        assistant=_assistant_name(client),
        person=person,
        switch_query=_query(params),
    )


def _with_session(response: HTMLResponse, user: User) -> HTMLResponse:
    """Sign the person in on this origin, so the approval step knows them."""
    auth_token, _ = security.create_session_token(
        user_id=user.id, company_id=user.company_id
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
        uri
        for uri in body.redirect_uris
        if not oauth_redirects.may_register(uri, allowed_redirect_uris)
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
) -> HTMLResponse:
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    client = _validated(session, params)
    user = _get_cookie_user(request, session)
    if user is None:
        return _sign_in(client, params)
    return _consent(client, params, user)


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
) -> HTMLResponse:
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    client = _validated(session, params)
    user = _get_cookie_user(request, session)
    if user is not None:
        return _consent(client, params, user)
    return _sign_in(client, params, signup=True)


@router.get("/oauth/authorize/switch", response_model=None)
def authorize_switch_account(
    session: SessionDep,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    scope: str | None = None,
    state: str | None = None,
    resource: str | None = None,
) -> HTMLResponse:
    """ "Not you?": sign out on this origin and show the sign-in form again."""
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    response = _sign_in(_validated(session, params), params)
    response.delete_cookie(settings.AUTH_COOKIE)
    return response


@router.post("/oauth/authorize/confirm", response_model=None)
def authorize_confirm(
    session: SessionDep,
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    scope: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
    resource: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Sign in, then ask the person to approve the assistant."""
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    client = _validated(session, params)
    user = crud.authenticate(session=session, email=email.strip(), password=password)
    if user is None or not user.is_active:
        return _sign_in(
            client,
            params,
            error="That email and password don’t match.",
            email=email,
        )
    return _with_session(_consent(client, params, user), user)


@router.post("/oauth/authorize/signup/confirm", response_model=None)
def authorize_signup_confirm(
    session: SessionDep,
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    full_name: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
    resource: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Create an account, then ask the person to approve the assistant."""
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    client = _validated(session, params)
    email = email.strip()
    keep = {"email": email, "full_name": full_name or ""}
    try:
        user_create = UserCreate(
            email=email, password=password, full_name=(full_name or "").strip() or None
        )
    except ValidationError as exc:
        error, error_field = _signup_error(exc)
        return _sign_in(
            client, params, signup=True, error=error, error_field=error_field, **keep
        )
    if crud.find_user_by_email_ignoring_case(session=session, email=email) is not None:
        return _sign_in(
            client,
            params,
            signup=True,
            error="An account already uses this email. Sign in instead.",
            error_field="email",
            **keep,
        )
    user = crud.create_user(session=session, user_create=user_create)
    return _with_session(_consent(client, params, user), user)


@router.post("/oauth/authorize/allow", response_model=None)
def authorize_allow(
    request: Request,
    session: SessionDep,
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    scope: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
    resource: Annotated[str | None, Form()] = None,
) -> HTMLResponse | RedirectResponse:
    """The person approved: hand the assistant its authorization code."""
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    client = _validated(session, params)
    user = _get_cookie_user(request, session)
    if user is None:
        return _sign_in(client, params)
    code = _create_authorization_code(
        session=session,
        user=user,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        resource=params.resource or "",
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    return _redirect_with_code(redirect_uri=redirect_uri, code=code, state=state)


@router.post("/oauth/authorize/cancel", response_model=None)
def authorize_cancel(
    session: SessionDep,
    response_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    code_challenge: Annotated[str, Form()],
    code_challenge_method: Annotated[str, Form()],
    scope: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
    resource: Annotated[str | None, Form()] = None,
) -> RedirectResponse:
    """The person declined: tell the assistant, as OAuth does (`access_denied`)."""
    params = _params(
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        resource=resource,
    )
    _validated(session, params)
    query = {"error": "access_denied", "iss": _issuer()} | (
        {"state": state} if state else {}
    )
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        f"{redirect_uri}{separator}{urlencode(query)}", status_code=303
    )


def _validated(session: SessionDep, params: AuthorizeParams) -> OAuthClient:
    return _validate_authorize_request(
        session=session,
        response_type=params.response_type,
        client_id=params.client_id,
        redirect_uri=params.redirect_uri,
        code_challenge=params.code_challenge,
        code_challenge_method=params.code_challenge_method,
        resource=params.resource,
    )


def _signup_error(exc: ValidationError) -> tuple[str, ErrorField]:
    """What to tell a person whose sign-up details were refused, and where."""
    fields = {str(error["loc"][0]) for error in exc.errors() if error.get("loc")}
    if "email" in fields:
        return "Enter a valid email address.", "email"
    if "password" in fields:
        return "Use at least 8 characters.", "password"
    return "Check your details and try again.", "form"


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
            company_id=stored_refresh_token.company_id,
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
            company_id=auth_code.company_id,
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
