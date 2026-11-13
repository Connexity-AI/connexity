"""Routes for Connexity's own infrastructure, not for people or assistants.

`POST /internal/calls/pull` runs the scheduled call pull. Cloud Scheduler calls it
every minute with a Google-signed identity token; nothing else can. Hidden from the
OpenAPI schema and the generated client.
"""

import logging
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.deps import SessionDep
from app.core.config import settings
from app.services.call_pull import PullRun, run_pull

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)

GOOGLE_CERTS = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

_NOT_FOUND = HTTPException(status_code=404, detail="Not Found")
_REFUSED = HTTPException(status_code=401, detail="Not allowed")


@lru_cache(maxsize=1)
def _google_keys() -> jwt.PyJWKClient:
    # Fetches Google's public keys on first use and caches them.
    return jwt.PyJWKClient(GOOGLE_CERTS, cache_keys=True)


def google_signing_key(token: str) -> object:
    return _google_keys().get_signing_key_from_jwt(token).key


def require_scheduler(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Allow only Cloud Scheduler's service account, with a token for this address."""
    audience = settings.CALL_PULL_AUDIENCE
    invoker = settings.CALL_PULL_INVOKER
    if not audience or not invoker:
        raise _NOT_FOUND
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _REFUSED
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(
            token,
            key=google_signing_key(token),  # type: ignore[arg-type]
            algorithms=["RS256"],
            audience=audience,
            options={"require": ["exp", "iat", "iss", "aud", "email"]},
        )
    except (jwt.PyJWTError, ValueError) as exc:
        logger.warning("Call pull refused a token: %s", type(exc).__name__)
        raise _REFUSED from exc
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise _REFUSED
    if claims.get("email") != invoker or claims.get("email_verified") is not True:
        raise _REFUSED


@router.post(
    "/calls/pull", response_model=PullRun, dependencies=[Depends(require_scheduler)]
)
async def pull_calls(session: SessionDep) -> PullRun:
    return await run_pull(session=session)
