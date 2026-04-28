from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.core.config import settings
from app.models import ConfigPublic
from app.services.judge_metrics import (
    MetricDefinition,
    custom_metric_row_to_definition,
    get_metrics_for_api,
)
from app.services.llm_models import LLMModelsPublic, get_available_llm_models

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
def get_available_metrics(
    session: SessionDep,
    current_user: CurrentUser,
) -> AvailableMetricsPublic:
    builtin = get_metrics_for_api()
    custom_rows, _ = crud.list_custom_metrics(
        session=session,
        owner_id=current_user.id,
        skip=0,
        limit=10_000,
    )
    custom_defs = [custom_metric_row_to_definition(r) for r in custom_rows]
    merged = [*builtin, *custom_defs]
    return AvailableMetricsPublic(data=merged, count=len(merged))


@router.get("/llm-models", response_model=LLMModelsPublic)
def get_llm_models() -> LLMModelsPublic:
    return get_available_llm_models()
