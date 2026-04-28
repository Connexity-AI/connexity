import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.crud import agent_version as agent_version_crud
from app.models import Agent, EvalConfig, Run, RunCreate, RunStatus, RunUpdate
from app.models.enums import AgentMode
from app.models.schemas import RunConfig


def enrich_run_create_from_agent(
    *,
    session: Session,
    run_in: RunCreate,
    agent: Agent,
    eval_config: EvalConfig,
) -> RunCreate:
    """Fill run snapshot fields from the agent and eval config; validate endpoint mode."""
    data = run_in.model_dump()
    data.pop("agent_version", None)
    data.pop("agent_version_id", None)

    # Snapshot the eval config's run config when the caller didn't override it,
    # so max_turns / concurrency / judge / tool_mode set on the eval config are
    # actually honored at run time. Always persist the resolved config so the
    # run row never has a NULL config and frontend defaults are not relied on.
    if run_in.config is not None:
        cfg = run_in.config
    elif eval_config.config is not None:
        cfg = RunConfig.model_validate(eval_config.config)
    else:
        cfg = RunConfig()
    data["config"] = cfg.model_dump()

    data["eval_config_version"] = eval_config.version

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

    data["agent_version"] = agent.version
    ver_row = agent_version_crud.get_current_version_row(
        session=session, agent_id=agent.id, version=agent.version
    )
    data["agent_version_id"] = ver_row.id if ver_row else None

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
    agent_version: int | None = None,
    eval_config_id: uuid.UUID | None = None,
    status: RunStatus | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[Run], int]:
    statement = select(Run)
    count_statement = select(func.count()).select_from(Run)

    if agent_id is not None:
        statement = statement.where(Run.agent_id == agent_id)
        count_statement = count_statement.where(Run.agent_id == agent_id)
    if agent_version is not None:
        statement = statement.where(Run.agent_version == agent_version)
        count_statement = count_statement.where(Run.agent_version == agent_version)
    if eval_config_id is not None:
        statement = statement.where(Run.eval_config_id == eval_config_id)
        count_statement = count_statement.where(Run.eval_config_id == eval_config_id)
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


def set_baseline(*, session: Session, db_run: Run) -> Run:
    """Mark *db_run* as the baseline for its (agent_id, eval_config_id) pair.

    Any other run that was previously the baseline for the same pair is cleared.

    Raises:
        ValueError: If the run's status is not ``completed``.
    """
    if db_run.status != RunStatus.COMPLETED:
        raise ValueError(
            f"Only completed runs can be marked as baseline (status={db_run.status})"
        )

    # Clear existing baselines for the same (agent, agent_version, eval_config) scope
    statement = select(Run).where(
        Run.agent_id == db_run.agent_id,
        Run.agent_version == db_run.agent_version,
        Run.eval_config_id == db_run.eval_config_id,
        Run.is_baseline == True,  # noqa: E712
        Run.id != db_run.id,
    )
    for old in session.exec(statement).all():
        old.is_baseline = False
        session.add(old)

    db_run.is_baseline = True
    session.add(db_run)
    session.commit()
    session.refresh(db_run)
    return db_run


def get_baseline_run(
    *,
    session: Session,
    agent_id: uuid.UUID,
    eval_config_id: uuid.UUID,
    agent_version: int | None = None,
) -> Run | None:
    """Return baseline for (agent, eval_config), optionally scoped to a version.

    If *agent_version* is None, returns the baseline for the agent's current
    version (``Agent.version``).
    """
    statement = select(Run).where(
        Run.agent_id == agent_id,
        Run.eval_config_id == eval_config_id,
        Run.is_baseline == True,  # noqa: E712
    )
    if agent_version is not None:
        statement = statement.where(Run.agent_version == agent_version)
    else:
        agent = session.exec(select(Agent).where(Agent.id == agent_id)).first()
        if agent is None:
            return None
        statement = statement.where(Run.agent_version == agent.version)
    statement = statement.order_by(col(Run.created_at).desc()).limit(1)
    return session.exec(statement).first()


def delete_run(*, session: Session, db_run: Run) -> None:
    session.delete(db_run)
    session.commit()


def count_runs_for_eval_config(*, session: Session, eval_config_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count()).where(Run.eval_config_id == eval_config_id)
    ).one()


def count_runs_by_eval_config_ids(
    *, session: Session, eval_config_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch run counts for multiple eval configs in a single query."""
    if not eval_config_ids:
        return {}
    rows = session.exec(
        select(Run.eval_config_id, func.count())
        .where(col(Run.eval_config_id).in_(eval_config_ids))
        .group_by(Run.eval_config_id)
    ).all()
    result: dict[uuid.UUID, int] = {eid: 0 for eid in eval_config_ids}
    for eid, n in rows:
        result[eid] = int(n)
    return result
