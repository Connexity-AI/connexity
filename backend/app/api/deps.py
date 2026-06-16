import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    APIKeyCookie,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.models import Agent, TokenPayload, User

cookie_scheme = APIKeyCookie(name=settings.AUTH_COOKIE, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
CookieDep = Annotated[str | None, Depends(cookie_scheme)]
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_user(session: SessionDep, cookie: CookieDep, bearer: BearerDep) -> User:
    token = cookie or (bearer.credentials if bearer else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Token's company claim must match the user's current company. If an admin
    # reassigned the user to a different company via direct DB UPDATE, this
    # forces a fresh login so the new claim is embedded.
    if token_data.cid is None or token_data.cid != str(user.company_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Company reassigned; please log in again",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_company_id(session: SessionDep, current_user: CurrentUser) -> uuid.UUID:
    # Side effect: bind the ambient LLM tenant context so downstream
    # ``call_llm`` calls pick up the right per-company API key automatically.
    _bind_tenant_llm_context_inline(session=session, current_user=current_user)
    return current_user.company_id


CurrentCompany = Annotated[uuid.UUID, Depends(get_current_company_id)]


def _bind_tenant_llm_context_inline(*, session: Session, current_user: User) -> None:
    from app.crud.company import company_has_any_llm_key, get_company
    from app.services.tenant_llm import (
        set_current_tenant,
        tenant_context_from_company,
    )

    company = get_company(session=session, company_id=current_user.company_id)
    if company is None or not company_has_any_llm_key(company=company):
        set_current_tenant(None)
        return
    set_current_tenant(tenant_context_from_company(company))


def bind_tenant_llm_context(session: SessionDep, current_user: CurrentUser) -> None:
    """Load the current user's LLM tenant context and set it as ambient.

    Mounted as a route-level dependency on every authenticated router so any
    downstream ``call_llm`` automatically uses the right per-company API key.
    No-op if the company has no LLM keys configured — the LLM service will
    fall back to env vars and the dedicated gate dependency below raises 409.
    """
    from app.crud.company import company_has_any_llm_key, get_company
    from app.services.tenant_llm import (
        set_current_tenant,
        tenant_context_from_company,
    )

    company = get_company(session=session, company_id=current_user.company_id)
    if company is None or not company_has_any_llm_key(company=company):
        set_current_tenant(None)
        return
    set_current_tenant(tenant_context_from_company(company))


def require_llm_key(session: SessionDep, current_user: CurrentUser) -> None:
    """Reject the request when the company has no LLM key configured.

    Mount on routes that depend on LLM features (evals, generation, prompt
    editor). 409 ``LLM_KEY_REQUIRED`` so the frontend can route the user to
    onboarding / settings.
    """
    from app.crud.company import company_has_any_llm_key, get_company

    company = get_company(session=session, company_id=current_user.company_id)
    if company is None or not company_has_any_llm_key(company=company):
        raise HTTPException(
            status_code=409,
            detail=(
                "This workspace has no LLM API key configured. Add an OpenAI "
                "or Anthropic key in Settings."
            ),
        )


def require_mcp_user(session: SessionDep, bearer: BearerDep) -> User:
    token = bearer.credentials if bearer else None
    audience = settings.oauth_default_resource_url
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if not audience:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MCP OAuth audience is not configured",
        )

    try:
        payload = jwt.decode(
            token,
            security.oauth_public_key(),
            algorithms=[security.OAUTH_ALGORITHM],
            audience=audience,
            issuer=settings.oauth_issuer_url,
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    scopes = payload.get("scope")
    if not isinstance(scopes, str) or "mcp:access" not in scopes.split():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    if not token_data.sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    try:
        user_id = uuid.UUID(token_data.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return user


McpCurrentUser = Annotated[User, Depends(require_mcp_user)]


def get_owned_agent(
    *, agent_id: uuid.UUID, session: Session, current_user: User
) -> Agent:
    from app import crud

    agent = crud.get_agent(
        session=session,
        agent_id=agent_id,
        company_id=current_user.company_id,
    )
    if not agent or agent.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
