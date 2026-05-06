from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.api.deps import SessionDep, get_current_user
from app.core.config import settings
from app.models import ConfigPublic, PredefinedToolsPublic
from app.services.agent_tool_definitions import list_predefined_tools_for_api
from app.services.judge_metrics import MetricDefinition, get_metrics_for_api
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
        default_llm_model=settings.default_llm_id,
    )


@router.get("/predefined-tools", response_model=PredefinedToolsPublic)
def get_predefined_tools() -> PredefinedToolsPublic:
    """Catalog tool rows (same JSON shape as ``Agent.tools``) for editors and forms."""
    data = list_predefined_tools_for_api()
    return PredefinedToolsPublic(data=data, count=len(data))


@router.get("/available-metrics", response_model=AvailableMetricsPublic)
def get_available_metrics(
    session: SessionDep,
) -> AvailableMetricsPublic:
    """All metrics available for use in eval configs (active, non-draft).

    Both built-in (predefined) and user-created metrics live in the same
    ``custom_metric`` table; ``is_draft`` rows are excluded so the create-eval
    judge picker only shows metrics the user has marked active.
    """
    metrics = get_metrics_for_api(session)
    return AvailableMetricsPublic(data=metrics, count=len(metrics))


@router.get("/llm-models", response_model=LLMModelsPublic)
def get_llm_models() -> LLMModelsPublic:
    return get_available_llm_models()
