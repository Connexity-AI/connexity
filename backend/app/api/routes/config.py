from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import ConfigPublic
from app.services.judge_metrics import MetricDefinition, get_metrics_for_api

router = APIRouter(
    prefix="/config",
    tags=["config"],
    dependencies=[Depends(get_current_user)],
)


class AvailableMetricsPublic(BaseModel):
    data: list[MetricDefinition] = Field(description="Registered judge metrics")
    count: int = Field(description="Number of metrics")


@router.get("/", response_model=ConfigPublic)
def get_config(request: Request) -> ConfigPublic:
    return ConfigPublic(
        project_name=settings.PROJECT_NAME,
        api_version=settings.API_V1_STR,
        environment=settings.ENVIRONMENT,
        docs_url=request.app.docs_url or "/docs",
    )


@router.get("/available-metrics", response_model=AvailableMetricsPublic)
def get_available_metrics() -> AvailableMetricsPublic:
    metrics = get_metrics_for_api()
    return AvailableMetricsPublic(data=metrics, count=len(metrics))
