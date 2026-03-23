from fastapi import APIRouter

from app.api.routes import (
    agents,
    health,
    login,
    runs,
    scenario_results,
    scenario_sets,
    scenarios,
    users,
)

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(agents.router)
api_router.include_router(scenarios.router)
api_router.include_router(scenario_sets.router)
api_router.include_router(runs.router)
api_router.include_router(scenario_results.router)

root_router = APIRouter()
root_router.include_router(health.router)
