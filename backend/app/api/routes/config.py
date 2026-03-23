from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import ConfigPublic

router = APIRouter(
    prefix="/config",
    tags=["config"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=ConfigPublic)
def get_config(request: Request) -> ConfigPublic:
    return ConfigPublic(
        project_name=settings.PROJECT_NAME,
        api_version=settings.API_V1_STR,
        environment=settings.ENVIRONMENT,
        docs_url=request.app.docs_url or "/docs",
    )
