import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Agent, Run, RunCreate, RunStatus, RunUpdate
from app.models.enums import AgentMode
from app.models.schemas import RunConfig


def enrich_run_create_from_agent(*, run_in: RunCreate, agent: Agent) -> RunCreate:
    """Fill run snapshot fields from the agent and validate endpoint mode."""
    data = run_in.model_dump()
    cfg = run_in.config or RunConfig()
    asim = cfg.agent_simulator

    if not data.get("agent_endpoint_url") and agent.endpoint_url:
        data["agent_endpoint_url"] = agent.endpoint_url

    if data.get("agent_mode") is None:
        data["agent_mode"] = agent.mode.value

    if agent.mode == AgentMode.PLATFORM:
        if data.get("agent_system_prompt") is None:
            data["agent_system_prompt"] = agent.system_prompt
        if data.get("agent_tools") is None:
            data["agent_tools"] = agent.tools
        eff_model = (asim.model if asim and asim.model else None) or agent.agent_model
        eff_prov = (
            asim.provider if asim and asim.provider else None
        ) or agent.agent_provider
        if data.get("agent_model") is None:
            data["agent_model"] = eff_model
        if data.get("agent_provider") is None:
            data["agent_provider"] = eff_prov
        if not data.get("agent_system_prompt"):
            msg = "agent system_prompt is required for platform-mode agents"
            raise ValueError(msg)
        if not data.get("agent_model"):
            msg = "agent_model is required for platform-mode agents (set on agent or in run config agent_simulator.model)"
            raise ValueError(msg)
    elif agent.mode == AgentMode.ENDPOINT:
        ep = data.get("agent_endpoint_url")
        if not ep or not str(ep).strip():
            msg = "agent_endpoint_url is required when the agent is in endpoint mode"
            raise ValueError(msg)

    return RunCreate.model_validate(data)


def create_run(
    *,
    session: Session,
    run_in: RunCreate,
    created_by: uuid.UUID | None = None,
) -> Run:
    run_data = run_in.model_dump()
    # RunConfig (Pydantic) → dict for JSONB column
    if run_in.config is not None:
        run_data["config"] = run_in.config.model_dump()
    if created_by is not None:
        run_data["created_by"] = created_by
    db_obj = Run.model_validate(run_data)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_run(*, session: Session, run_id: uuid.UUID) -> Run | None:
    return session.get(Run, run_id)


def list_runs(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    agent_id: uuid.UUID | None = None,
    status: RunStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[Run], int]:
    statement = select(Run)
    count_statement = select(func.count()).select_from(Run)

    if agent_id is not None:
        statement = statement.where(Run.agent_id == agent_id)
        count_statement = count_statement.where(Run.agent_id == agent_id)
    if status is not None:
        statement = statement.where(Run.status == status)
        count_statement = count_statement.where(Run.status == status)
    if created_after is not None:
        statement = statement.where(Run.created_at >= created_after)
        count_statement = count_statement.where(Run.created_at >= created_after)
    if created_before is not None:
        statement = statement.where(Run.created_at <= created_before)
        count_statement = count_statement.where(Run.created_at <= created_before)

    count = session.exec(count_statement).one()
    items = list(
        session.exec(
            statement.order_by(col(Run.created_at).desc()).offset(skip).limit(limit)
        ).all()
    )
    return items, count


def update_run(*, session: Session, db_run: Run, run_in: RunUpdate) -> Run:
    update_data = run_in.model_dump(exclude_unset=True)
    # AggregateMetrics (Pydantic) → dict for JSONB column
    if "aggregate_metrics" in update_data and run_in.aggregate_metrics is not None:
        update_data["aggregate_metrics"] = run_in.aggregate_metrics.model_dump()
    db_run.sqlmodel_update(update_data)
    session.add(db_run)
    session.commit()
    session.refresh(db_run)
    return db_run


def delete_run(*, session: Session, db_run: Run) -> None:
    session.delete(db_run)
    session.commit()
