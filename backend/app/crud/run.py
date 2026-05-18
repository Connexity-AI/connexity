import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.crud import agent_version as agent_version_crud
from app.models import (
    Agent,
    AgentVersion,
    EvalConfig,
    Run,
    RunCreate,
    RunStatus,
    RunUpdate,
)
from app.models.enums import AgentMode, RunMode, TextRuntimeKind
from app.models.schemas import CustomEndpointRuntimeConfig, RunConfig
from app.services.agent_tool_definitions import normalize_and_validate_agent_tools
from app.services.tool_dispatch import validate_live_tool_snapshot


def enrich_run_create_from_agent(
    *,
    session: Session,
    run_in: RunCreate,
    agent: Agent,
    eval_config: EvalConfig,
) -> RunCreate:
    """Fill run snapshot fields from the agent and eval config.

    Snapshot requirements follow ``RunConfig.mode`` and ``RunConfig.runtime``, not
    ``Agent.mode`` (the latter is still copied onto the run row for audit).

    If `run_in.agent_version` is provided and differs from the active published
    version, snapshot fields (system_prompt, tools, model, etc.) are taken from
    that AgentVersion row so the eval actually tests the requested version's
    behavior. Otherwise fields are taken from the live agent.
    """
    data = run_in.model_dump()
    requested_version = data.pop("agent_version", None)
    data.pop("agent_version_id", None)

    active_row = agent_version_crud.get_active_published_version(
        session=session, agent_id=agent.id
    )
    current_version_num = active_row.version if active_row is not None else None

    source: Agent | AgentVersion
    target_version: int | None
    ver_row: AgentVersion | None

    if requested_version is not None and (
        current_version_num is None or requested_version != current_version_num
    ):
        ver_row = agent_version_crud.get_current_version_row(
            session=session, agent_id=agent.id, version=requested_version
        )
        if ver_row is None:
            msg = f"Agent version {requested_version} not found for agent {agent.id}"
            raise ValueError(msg)
        source = ver_row
        target_version = requested_version
    else:
        if current_version_num is None:
            msg = f"Agent {agent.id} has no published version"
            raise ValueError(msg)
        source = agent
        target_version = current_version_num
        ver_row = active_row

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

    if not data.get("agent_endpoint_url") and source.endpoint_url:
        data["agent_endpoint_url"] = source.endpoint_url

    source_mode = (
        source.mode if isinstance(source.mode, AgentMode) else AgentMode(source.mode)
    )
    if data.get("agent_mode") is None:
        data["agent_mode"] = source_mode.value

    text_kind: TextRuntimeKind | None = (
        cfg.runtime.kind if cfg.mode == RunMode.TEXT else None
    )

    if cfg.mode == RunMode.TEXT and text_kind is not None:
        if text_kind == TextRuntimeKind.CONNEXITY:
            if data.get("agent_system_prompt") is None:
                data["agent_system_prompt"] = source.system_prompt
            if data.get("agent_tools") is None:
                data["agent_tools"] = source.tools
            eff_model = (
                asim.model if asim and asim.model else None
            ) or source.agent_model
            eff_prov = (
                asim.provider if asim and asim.provider else None
            ) or source.agent_provider
            if data.get("agent_model") is None:
                data["agent_model"] = eff_model
            if data.get("agent_provider") is None:
                data["agent_provider"] = eff_prov
            if not data.get("agent_system_prompt"):
                msg = (
                    "Connexity runtime requires agent_system_prompt on the run snapshot "
                    "(set system_prompt on the agent or agent version)."
                )
                raise ValueError(msg)
        elif text_kind == TextRuntimeKind.CUSTOM_ENDPOINT:
            rt = cfg.runtime
            assert isinstance(rt, CustomEndpointRuntimeConfig)
            url = rt.url.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                msg = "custom endpoint runtime url must start with http:// or https://"
                raise ValueError(msg)
            if data.get("agent_tools") is None and source.tools:
                data["agent_tools"] = source.tools
            if data.get("agent_system_prompt") is None and source.system_prompt:
                data["agent_system_prompt"] = source.system_prompt
            if data.get("agent_model") is None and source.agent_model:
                data["agent_model"] = source.agent_model
            if data.get("agent_provider") is None and source.agent_provider:
                data["agent_provider"] = source.agent_provider
        elif text_kind == TextRuntimeKind.RETELL:
            if data.get("agent_tools") is None and source.tools:
                data["agent_tools"] = source.tools
    elif source_mode == AgentMode.PLATFORM:
        if data.get("agent_system_prompt") is None:
            data["agent_system_prompt"] = source.system_prompt
        if data.get("agent_tools") is None:
            data["agent_tools"] = source.tools
        eff_model = (asim.model if asim and asim.model else None) or source.agent_model
        eff_prov = (
            asim.provider if asim and asim.provider else None
        ) or source.agent_provider
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
    elif source_mode == AgentMode.ENDPOINT:
        ep = data.get("agent_endpoint_url")
        if not ep or not str(ep).strip():
            msg = "agent_endpoint_url is required when the agent is in endpoint mode"
            raise ValueError(msg)
        if data.get("agent_tools") is None and source.tools:
            data["agent_tools"] = source.tools

    data["agent_version"] = target_version
    data["agent_version_id"] = ver_row.id if ver_row else None

    if data.get("agent_tools") is not None:
        data["agent_tools"] = normalize_and_validate_agent_tools(data["agent_tools"])

    if (
        cfg.mode == RunMode.TEXT
        and cfg.runtime.kind == TextRuntimeKind.CONNEXITY
        and cfg.tool_mode == "live"
    ):
        validate_live_tool_snapshot(data.get("agent_tools"))

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

    If *agent_version* is None, returns the baseline for the active published
    version.
    """
    statement = select(Run).where(
        Run.agent_id == agent_id,
        Run.eval_config_id == eval_config_id,
        Run.is_baseline == True,  # noqa: E712
    )
    if agent_version is not None:
        statement = statement.where(Run.agent_version == agent_version)
    else:
        active = agent_version_crud.get_active_published_version(
            session=session, agent_id=agent_id
        )
        if active is None or active.version is None:
            return None
        statement = statement.where(Run.agent_version == active.version)
    statement = statement.order_by(col(Run.created_at).desc()).limit(1)
    return session.exec(statement).first()


def delete_run(*, session: Session, db_run: Run) -> None:
    session.delete(db_run)
    session.commit()


def get_latest_completed_run_for_version(
    *,
    session: Session,
    agent_id: uuid.UUID,
    eval_config_id: uuid.UUID,
    agent_version: int,
) -> Run | None:
    """Latest completed run for the (agent, eval_config, agent_version) triple."""
    statement = (
        select(Run)
        .where(
            Run.agent_id == agent_id,
            Run.eval_config_id == eval_config_id,
            Run.agent_version == agent_version,
            Run.status == RunStatus.COMPLETED,
        )
        .order_by(col(Run.created_at).desc())
        .limit(1)
    )
    return session.exec(statement).first()


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
