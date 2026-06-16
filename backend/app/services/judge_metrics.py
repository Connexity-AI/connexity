"""Judge metric resolution: read definitions from the ``custom_metric`` table.

Both built-in (predefined) and user-created metrics live in the same table.
Predefined rows are seeded once by the Alembic migration from
:mod:`app.services.predefined_metrics`; this module only reads from the DB.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from app.core.db import engine
from app.crud.custom_metrics import get_custom_metric_by_name
from app.models.custom_metric import CustomMetric
from app.models.enums import MetricTier, ScoreType
from app.models.schemas import JudgeConfig, MetricSelection


class MetricDefinition(BaseModel):
    name: str = Field(description="Stable metric id (snake_case)")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="What this metric measures")
    tier: MetricTier
    default_weight: float = Field(
        ge=0.0,
        description="Default weight before renormalization (0 for opt-in-only metrics)",
    )
    score_type: ScoreType
    rubric: str = Field(description="Rubric and examples for the judge prompt")
    include_in_defaults: bool = Field(
        default=True,
        description="If False, metric is omitted unless explicitly selected",
    )


def _list_active_db_metrics(
    session: Session, *, company_id: uuid.UUID | None = None
) -> list[CustomMetric]:
    """All non-deleted, non-draft metrics ordered with predefined first.

    When ``company_id`` is given (the normal request path) results are scoped
    to that tenant's per-company copies. When omitted (legacy tests and some
    background scripts) every row is returned.
    """
    filters: list[Any] = [
        CustomMetric.deleted_at.is_(None),  # type: ignore[union-attr]
        CustomMetric.is_draft.is_(False),  # type: ignore[union-attr]
    ]
    if company_id is not None:
        filters.append(col(CustomMetric.company_id) == company_id)
    statement = (
        select(CustomMetric)
        .where(*filters)
        .order_by(
            col(CustomMetric.is_predefined).desc(),
            col(CustomMetric.created_at).asc(),
        )
    )
    return list(session.exec(statement).all())


def get_default_metrics(
    session: Session | None = None, *, company_id: uuid.UUID | None = None
) -> list[MetricDefinition]:
    """Predefined scored metrics flagged ``include_in_defaults`` for the tenant."""
    with _session_scope(session) as db_session:
        rows = _list_active_db_metrics(db_session, company_id=company_id)
        return [
            custom_metric_row_to_definition(r)
            for r in rows
            if r.is_predefined
            and r.include_in_defaults
            and r.score_type == ScoreType.SCORED
        ]


def get_metrics_for_api(
    session: Session | None = None, *, company_id: uuid.UUID | None = None
) -> list[MetricDefinition]:
    """All active (non-draft, non-deleted) metrics visible to the tenant."""
    with _session_scope(session) as db_session:
        rows = _list_active_db_metrics(db_session, company_id=company_id)
        return [custom_metric_row_to_definition(r) for r in rows]


def custom_metric_row_to_definition(row: CustomMetric) -> MetricDefinition:
    """Map a persisted custom metric row to the shared :class:`MetricDefinition` shape."""
    return MetricDefinition(
        name=row.name,
        display_name=row.display_name,
        description=row.description,
        tier=row.tier,
        default_weight=row.default_weight,
        score_type=row.score_type,
        rubric=row.rubric,
        include_in_defaults=row.include_in_defaults,
    )


@contextmanager
def _session_scope(session: Session | None) -> Iterator[Session]:
    if session is not None:
        yield session
    else:
        with Session(engine) as owned:
            yield owned


def _normalize_weights(
    pairs: list[tuple[MetricDefinition, float]],
) -> list[tuple[MetricDefinition, float]]:
    total = sum(w for _, w in pairs)
    if total <= 0:
        msg = "Metric weights must sum to a positive value"
        raise ValueError(msg)
    return [(m, w / total) for m, w in pairs]


def resolve_metrics(
    judge_config: JudgeConfig | None,
    *,
    session: Session | None = None,
    company_id: uuid.UUID | None = None,
) -> list[tuple[MetricDefinition, float]]:
    """Resolve selected metrics and weights; weights renormalized to sum to 1.0.

    Looks up metric definitions in the tenant's per-company copies. Raises
    ``ValueError`` for any name not present.
    """
    if judge_config is None or judge_config.metrics is None:
        defaults = get_default_metrics(session, company_id=company_id)
        pairs = [(m, m.default_weight) for m in defaults]
        return _normalize_weights(pairs)

    selections: list[MetricSelection] = judge_config.metrics
    if not selections:
        defaults = get_default_metrics(session, company_id=company_id)
        pairs = [(m, m.default_weight) for m in defaults]
        return _normalize_weights(pairs)

    pairs: list[tuple[MetricDefinition, float]] = []
    for sel in selections:
        with _session_scope(session) as db_session:
            row = get_custom_metric_by_name(
                session=db_session,
                name=sel.metric,
                company_id=company_id,
                include_deleted=True,
            )
        if row is None:
            msg = f"Unknown metric: {sel.metric}"
            raise ValueError(msg)
        definition = custom_metric_row_to_definition(row)
        if sel.metric == "task_completion" and sel.weight is None:
            msg = "task_completion requires an explicit weight when selected"
            raise ValueError(msg)
        weight = sel.weight if sel.weight is not None else definition.default_weight
        if weight < 0:
            msg = f"Negative weight for metric {sel.metric}"
            raise ValueError(msg)
        pairs.append((definition, weight))

    return _normalize_weights(pairs)
