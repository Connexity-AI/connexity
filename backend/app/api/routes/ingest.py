"""Ingest: the only way for something outside Connexity to send it a call.

Authenticated by an ingest token, which can send traces for its company's agents and
do nothing else. Managing tokens is done by a logged-in user and lives in the second
router below.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import crud
from app.api.deps import CurrentCompany, CurrentUser, SessionDep, get_current_user
from app.core.config import settings
from app.models import (
    IngestToken,
    IngestTokenCreate,
    IngestTokenCreated,
    IngestTokenPublic,
    IngestTokensPublic,
    IngestTraceRequest,
    IngestTraceResult,
    Message,
)
from app.models.enums import TraceCapability
from app.services.trace_capabilities import derive_capabilities

_ingest_bearer = HTTPBearer(auto_error=False)

# One message for every way a token can be wrong, so a caller cannot probe which
# tokens exist or were revoked.
_UNAUTHORIZED = HTTPException(
    status_code=401,
    detail="Missing or invalid ingest token",
    headers={"WWW-Authenticate": "Bearer"},
)


def require_ingest_token(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(_ingest_bearer),
) -> IngestToken:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED
    token = crud.use_ingest_token(session=session, token=credentials.credentials)
    if token is None:
        raise _UNAUTHORIZED
    return token


async def enforce_body_limit(
    request: Request, _token: IngestToken = Depends(require_ingest_token)
) -> None:
    """Refuse a body over the configured size.

    This bounds what Connexity accepts and stores, not what the server reads: the
    framework has already read the body by the time this runs. Protection against a
    sender streaming an enormous body belongs in the proxy in front of the API.

    Depends on the token so that a caller with a bad token always gets 401, never a
    hint about limits.
    """
    limit = settings.INGEST_MAX_BODY_BYTES
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status_code=413, detail=_too_large(limit))
    # A sender can omit or understate Content-Length, so measure what arrived too.
    if len(await request.body()) > limit:
        raise HTTPException(status_code=413, detail=_too_large(limit))


def _too_large(limit: int) -> str:
    return f"Request body is larger than the limit of {limit} bytes"


router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/traces",
    response_model=IngestTraceResult,
    dependencies=[Depends(enforce_body_limit)],
)
def ingest_trace(
    session: SessionDep,
    body: IngestTraceRequest,
    token: IngestToken = Depends(require_ingest_token),
) -> IngestTraceResult:
    """Store a call trace for one of the token's company's agents.

    Sending a call again (same ``external_id`` for the same agent) replaces its trace.
    """
    if len(body.trace.events) > settings.INGEST_MAX_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"trace.events has {len(body.trace.events)} events; the limit is "
                f"{settings.INGEST_MAX_EVENTS}"
            ),
        )

    # The company comes from the token. An agent of another company is reported
    # exactly like one that does not exist.
    agent = crud.get_agent(
        session=session, agent_id=body.agent_id, company_id=token.company_id
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    stored = crud.store_trace(
        session=session,
        trace=body.trace,
        agent_id=agent.id,
        company_id=token.company_id,
        integration_id=agent.integration_id,
        raw=body.raw,
    )
    capabilities = derive_capabilities(body.trace)
    return IngestTraceResult(
        call_id=stored.call.id,
        created=stored.created,
        capabilities=capabilities,
        missing_capabilities=[c for c in TraceCapability if c not in capabilities],
    )


tokens_router = APIRouter(
    prefix="/ingest-tokens",
    tags=["ingest"],
    dependencies=[Depends(get_current_user)],
)


@tokens_router.post("/", response_model=IngestTokenCreated)
def create_ingest_token(
    session: SessionDep,
    current_user: CurrentUser,
    company_id: CurrentCompany,
    body: IngestTokenCreate,
) -> IngestTokenCreated:
    """Create an ingest token. The token itself is returned only here."""
    row, token = crud.create_ingest_token(
        session=session,
        company_id=company_id,
        name=body.name,
        created_by=current_user.id,
    )
    return IngestTokenCreated(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
        token=token,
    )


@tokens_router.get("/", response_model=IngestTokensPublic)
def list_ingest_tokens(
    session: SessionDep, company_id: CurrentCompany
) -> IngestTokensPublic:
    rows = crud.list_ingest_tokens(session=session, company_id=company_id)
    return IngestTokensPublic(
        data=[
            IngestTokenPublic.model_validate(row, from_attributes=True) for row in rows
        ],
        count=len(rows),
    )


@tokens_router.delete("/{token_id}", response_model=Message)
def revoke_ingest_token(
    session: SessionDep, company_id: CurrentCompany, token_id: uuid.UUID
) -> Message:
    """Revoke a token. It stops working immediately and stays listed as revoked."""
    row = crud.get_ingest_token(
        session=session, token_id=token_id, company_id=company_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Ingest token not found")
    crud.revoke_ingest_token(session=session, token=row)
    return Message(message="Ingest token revoked")
