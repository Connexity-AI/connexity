from typing import Any

from fastapi import APIRouter

from app.api.routes import (
    agents,
    config,
    custom_metrics,
    eval_configs,
    health,
    login,
    prompt_editor,
    runs,
    test_case_results,
    test_cases,
    users,
)
from app.models import ErrorResponse

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 422, 500)
}

api_router = APIRouter(responses=ERROR_RESPONSES)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(agents.router)
api_router.include_router(test_cases.router)
api_router.include_router(custom_metrics.router)
api_router.include_router(eval_configs.router)
api_router.include_router(runs.router)
api_router.include_router(test_case_results.router)
api_router.include_router(prompt_editor.router)
api_router.include_router(config.router)

root_router = APIRouter()
root_router.include_router(health.router)
