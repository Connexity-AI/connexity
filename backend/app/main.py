import logging
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import and_, or_
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router, root_router
from app.core.config import settings
from app.core.encryption import decrypt
from app.models import Agent, Integration, Run, RunStatus, TestCaseResult
from app.models.enums import IntegrationProvider
from app.services.retell import delete_retell_chat_agent, end_retell_chat

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


async def _cleanup_stale_retell_resources_for_runs(run_ids: list[uuid.UUID]) -> None:
    if not run_ids:
        return

    from datetime import UTC, datetime

    from sqlmodel import Session, select

    from app import crud
    from app.core.db import engine

    with Session(engine) as session:
        runs = {
            run.id: run
            for run in session.exec(select(Run).where(Run.id.in_(run_ids))).all()
        }
        results = session.exec(
            select(TestCaseResult).where(
                TestCaseResult.run_id.in_(run_ids),
                or_(
                    and_(
                        TestCaseResult.retell_chat_id.is_not(None),
                        TestCaseResult.retell_chat_ended_at.is_(None),
                    ),
                    and_(
                        TestCaseResult.retell_temp_chat_agent_id.is_not(None),
                        TestCaseResult.retell_temp_chat_agent_deleted_at.is_(None),
                    ),
                ),
            )
        ).all()

        payloads: list[dict[str, object]] = []
        for result in results:
            run = runs.get(result.run_id)
            if run is None:
                continue
            agent = session.get(Agent, run.agent_id)
            if agent is None or agent.integration_id is None:
                continue
            integration = session.get(Integration, agent.integration_id)
            if integration is None or integration.provider != IntegrationProvider.RETELL:
                continue
            try:
                api_key = decrypt(integration.encrypted_api_key)
            except Exception:
                logger.exception(
                    "Could not decrypt Retell API key during stale-run cleanup: run_id=%s result_id=%s integration_id=%s",
                    run.id,
                    result.id,
                    integration.id,
                )
                continue
            payloads.append(
                {
                    "result_id": result.id,
                    "run_id": run.id,
                    "api_key": api_key,
                    "retell_chat_id": result.retell_chat_id,
                    "retell_temp_chat_agent_id": result.retell_temp_chat_agent_id,
                }
            )

    cleaned_chats = 0
    cleaned_temp_agents = 0
    for payload in payloads:
        result_id = payload["result_id"]
        run_id = payload["run_id"]
        api_key = str(payload["api_key"])
        retell_chat_id = payload["retell_chat_id"]
        retell_temp_chat_agent_id = payload["retell_temp_chat_agent_id"]

        if isinstance(retell_chat_id, str) and retell_chat_id:
            closed = await end_retell_chat(api_key=api_key, chat_id=retell_chat_id)
            if closed:
                cleaned_chats += 1
                from app.core.db import engine
                from sqlmodel import Session

                with Session(engine) as session:
                    crud.set_retell_runtime_state(
                        session=session,
                        result_id=result_id,
                        retell_chat_ended_at=datetime.now(UTC),
                    )
            else:
                logger.warning(
                    "Failed to close stale Retell chat during startup recovery: run_id=%s result_id=%s chat_id=%s",
                    run_id,
                    result_id,
                    retell_chat_id,
                )

        if (
            isinstance(retell_temp_chat_agent_id, str)
            and retell_temp_chat_agent_id
        ):
            deleted = await delete_retell_chat_agent(
                api_key=api_key,
                agent_id=retell_temp_chat_agent_id,
            )
            if deleted:
                cleaned_temp_agents += 1
                from app.core.db import engine
                from sqlmodel import Session

                with Session(engine) as session:
                    crud.set_retell_runtime_state(
                        session=session,
                        result_id=result_id,
                        retell_temp_chat_agent_deleted_at=datetime.now(UTC),
                    )
            else:
                logger.warning(
                    "Failed to delete stale Retell temp chat agent during startup recovery: run_id=%s result_id=%s temp_chat_agent_id=%s",
                    run_id,
                    result_id,
                    retell_temp_chat_agent_id,
                )

    if payloads:
        logger.warning(
            "Retell stale-run cleanup finished: runs=%s result_rows=%s chats_closed=%s temp_agents_deleted=%s",
            len(run_ids),
            len(payloads),
            cleaned_chats,
            cleaned_temp_agents,
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _sync_llm_api_keys()

    # Mark any runs left in RUNNING status as FAILED (server crash recovery)
    from datetime import UTC, datetime

    from sqlmodel import Session, select

    from app.core.db import engine

    stale_run_ids: list[uuid.UUID] = []
    with Session(engine) as session:
        stale_runs = session.exec(
            select(Run).where(Run.status == RunStatus.RUNNING)
        ).all()
        stale_run_ids = [run.id for run in stale_runs]
        for run in stale_runs:
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            session.add(run)
        if stale_runs:
            session.commit()
            logger.warning("Marked %d stale RUNNING runs as FAILED", len(stale_runs))
    if stale_run_ids:
        await _cleanup_stale_retell_resources_for_runs(stale_run_ids)

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
