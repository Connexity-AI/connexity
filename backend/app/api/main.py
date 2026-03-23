from typing import Any

from fastapi import APIRouter

from app.api.routes import (
    agents,
    config,
    health,
    login,
    runs,
    scenario_results,
    scenario_sets,
    scenarios,
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
api_router.include_router(scenarios.router)
api_router.include_router(scenario_sets.router)
api_router.include_router(runs.router)
api_router.include_router(scenario_results.router)
api_router.include_router(config.router)

root_router = APIRouter()
root_router.include_router(health.router)
