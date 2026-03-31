import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from litellm.exceptions import APIError
from sqlalchemy.exc import IntegrityError

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.models import (
    CustomMetric,
    CustomMetricCreate,
    CustomMetricPublic,
    CustomMetricsPublic,
    CustomMetricUpdate,
    Message,
)
from app.services.judge_metrics import METRIC_REGISTRY
from app.services.metric_generator import (
    MetricGenerateRequest,
    MetricGenerateResult,
    generate_metric,
)

router = APIRouter(
    prefix="/custom-metrics",
    tags=["custom-metrics"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=CustomMetricPublic)
def create_custom_metric(
    session: SessionDep,
    current_user: CurrentUser,
    metric_in: CustomMetricCreate,
) -> CustomMetric:
    if metric_in.name in METRIC_REGISTRY:
        raise HTTPException(
            status_code=409,
            detail="This metric id is reserved for a built-in metric",
        )
    try:
        return crud.create_custom_metric(
            session=session, metric_in=metric_in, owner_id=current_user.id
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A custom metric with this name already exists for your account",
        ) from None


@router.post("/generate", response_model=MetricGenerateResult)
async def generate_custom_metric_preview(
    request: MetricGenerateRequest,
) -> MetricGenerateResult:
    """Generate a metric definition preview via LLM (not saved)."""
    try:
        return await generate_metric(request)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e


@router.get("/", response_model=CustomMetricsPublic)
def list_custom_metrics(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
) -> CustomMetricsPublic:
    items, count = crud.list_custom_metrics(
        session=session,
        owner_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return CustomMetricsPublic(
        data=[
            CustomMetricPublic.model_validate(m, from_attributes=True) for m in items
        ],
        count=count,
    )


@router.get("/{metric_id}", response_model=CustomMetricPublic)
def get_custom_metric(
    session: SessionDep,
    current_user: CurrentUser,
    metric_id: uuid.UUID,
) -> CustomMetric:
    metric = crud.get_custom_metric(session=session, metric_id=metric_id)
    if not metric or metric.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Custom metric not found")
    return metric


@router.put("/{metric_id}", response_model=CustomMetricPublic)
def update_custom_metric(
    session: SessionDep,
    current_user: CurrentUser,
    metric_id: uuid.UUID,
    metric_in: CustomMetricUpdate,
) -> CustomMetric:
    metric = crud.get_custom_metric(session=session, metric_id=metric_id)
    if not metric or metric.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Custom metric not found")
    if metric_in.name is not None and metric_in.name in METRIC_REGISTRY:
        raise HTTPException(
            status_code=409,
            detail="This metric id is reserved for a built-in metric",
        )
    try:
        return crud.update_custom_metric(
            session=session, db_metric=metric, metric_in=metric_in
        )
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A custom metric with this name already exists for your account",
        ) from None


@router.delete("/{metric_id}", response_model=Message)
def delete_custom_metric(
    session: SessionDep,
    current_user: CurrentUser,
    metric_id: uuid.UUID,
) -> Message:
    metric = crud.get_custom_metric(session=session, metric_id=metric_id)
    if not metric or metric.created_by != current_user.id:
        raise HTTPException(status_code=404, detail="Custom metric not found")
    crud.delete_custom_metric(session=session, db_metric=metric)
    return Message(message="Custom metric deleted successfully")
