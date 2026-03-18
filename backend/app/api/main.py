from fastapi import APIRouter

from app.api.routes import health, login, users, utils

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)

root_router = APIRouter()
root_router.include_router(health.router)
