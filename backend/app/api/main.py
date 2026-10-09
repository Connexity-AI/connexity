from typing import Any

from fastapi import APIRouter

from app.api.routes import (
    agents,
    calls,
    company,
    component_versions,
    config,
    custom_metrics,
    environments,
    eval_configs,
    health,
    ingest,
    integrations,
    login,
    mcp,
    oauth,
    runs,
    test_case_results,
    test_cases,
    tool_backends,
    users,
    webhooks,
)
from app.models import ErrorResponse

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 422, 500)
}

api_router = APIRouter(responses=ERROR_RESPONSES)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(mcp.router)
api_router.include_router(agents.router)
api_router.include_router(test_cases.router)
api_router.include_router(custom_metrics.router)
api_router.include_router(eval_configs.router)
api_router.include_router(runs.router)
api_router.include_router(test_case_results.router)
api_router.include_router(config.router)
api_router.include_router(integrations.router)
api_router.include_router(environments.router)
api_router.include_router(calls.router)
api_router.include_router(ingest.router)
api_router.include_router(ingest.tokens_router)
api_router.include_router(webhooks.router)
api_router.include_router(tool_backends.router)
api_router.include_router(component_versions.router)
api_router.include_router(company.router)

root_router = APIRouter()
root_router.include_router(health.router)
root_router.include_router(oauth.router)
