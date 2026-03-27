import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.main import api_router, root_router
from app.core.config import settings
from app.utils import log_settings

logger = logging.getLogger(__name__)


def _sync_llm_api_keys() -> None:
    """Expose Pydantic-loaded API keys to ``os.environ`` so LiteLLM can read them."""
    if settings.OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    if settings.ANTHROPIC_API_KEY:
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.ANTHROPIC_API_KEY)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _sync_llm_api_keys()

    # Mark any runs left in RUNNING status as FAILED (server crash recovery)
    from datetime import UTC, datetime

    from sqlmodel import Session, select

    from app.core.db import engine
    from app.models import Run, RunStatus

    with Session(engine) as session:
        stale_runs = session.exec(
            select(Run).where(Run.status == RunStatus.RUNNING)
        ).all()
        for run in stale_runs:
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            session.add(run)
        if stale_runs:
            session.commit()
            logger.warning("Marked %d stale RUNNING runs as FAILED", len(stale_runs))

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# For Github login Request object
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

app.include_router(root_router)
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Exception handlers ────────────────────────────────────────────


HTTP_CODE_TO_ERROR_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
}


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    code = HTTP_CODE_TO_ERROR_CODE.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": code, "status": exc.status_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    )
    code = HTTP_CODE_TO_ERROR_CODE[422]
    return JSONResponse(
        status_code=422,
        content={"detail": details, "code": code, "status": 422},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    code = HTTP_CODE_TO_ERROR_CODE[500]
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": code, "status": 500},
    )


log_settings(settings)
