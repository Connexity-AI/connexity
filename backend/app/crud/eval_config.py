import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, select

from app.models import TestCase
from app.models.agent import Agent
from app.models.enums import Platform, TestCaseStatus, TextRuntimeKind
from app.models.eval_config import (
    EvalConfig,
    EvalConfigCreate,
    EvalConfigMember,
    EvalConfigMemberEntry,
    EvalConfigMemberPublic,
    EvalConfigUpdate,
)
from app.models.schemas import (
    CustomEndpointRuntimeConfig,
    RetellRuntimeConfig,
    RunConfig,
    TestCaseExecution,
)


def _default_run_config_for_agent(agent: Agent) -> RunConfig:
    """Choose a practical default runtime for a newly created eval config.

    Connexity stays the global default, but endpoint-style agents without a
    platform prompt need a concrete HTTP URL to be runnable. Retell agents
    should default to the Retell runtime even if their imported prompt/model is
    incomplete.
    """
    if agent.platform == Platform.RETELL:
        return RunConfig(runtime=RetellRuntimeConfig())

    if not (agent.system_prompt or "").strip():
        endpoint_url = (agent.endpoint_url or "").strip()
        if endpoint_url:
            return RunConfig(runtime=CustomEndpointRuntimeConfig(url=endpoint_url))

    return RunConfig()


def validate_test_case_ids(
    *, session: Session, test_case_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    """Return any test case IDs that do not exist (or are soft-deleted)."""
    if not test_case_ids:
        return []
    existing_ids = set(
        session.exec(
            select(TestCase.id).where(
                col(TestCase.id).in_(test_case_ids),
                col(TestCase.deleted_at).is_(None),
            )
        ).all()
    )
    return [tid for tid in test_case_ids if tid not in existing_ids]


def _validate_runtime(
    *,
    session: Session,
    agent: Agent,
    run_config: RunConfig,
    config_id: uuid.UUID | None,
    extra_test_case_ids: list[uuid.UUID] | None = None,
) -> None:
    """Raise ``ValueError`` if ``run_config.runtime`` is invalid for ``agent``.

    Checks runtime availability for the agent's platform, delegates to the
    runtime's validator (requirements are expressed in terms of runtime + agent
    fields, not ``Agent.mode``), and forbids tool calls on custom endpoint runtimes.
    """
    from app.services.eval_runtimes import get_runtime  # local import to avoid cycle

    runtime_config = run_config.runtime
    try:
        runtime = get_runtime(run_config.mode, runtime_config.kind)
    except KeyError as exc:
        msg = f"Unknown runtime: {runtime_config.kind}"
        raise ValueError(msg) from exc

    if not runtime.supported_for_platform(agent.platform):
        platform_label = agent.platform.value if agent.platform else "this agent"
        msg = (
            f"Runtime '{runtime_config.kind.value}' is not available "
            f"for {platform_label}."
        )
        raise ValueError(msg)

    runtime.validate_config(runtime_config, agent, session)

    if runtime_config.kind == TextRuntimeKind.CUSTOM_ENDPOINT:
        # Tool calls can only be exercised by the in-process Connexity simulator.
        # Reject configs that link test cases declaring expected_tool_calls.
        test_case_filter = (
            [EvalConfigMember.eval_config_id == config_id]
            if config_id is not None
            else []
        )

        candidate_ids: set[uuid.UUID] = set(extra_test_case_ids or [])
        if config_id is not None:
            existing = session.exec(
                select(EvalConfigMember.test_case_id).where(*test_case_filter)
            ).all()
            candidate_ids.update(existing)

        if candidate_ids:
            rows = session.exec(
                select(TestCase.id, TestCase.expected_tool_calls).where(
                    col(TestCase.id).in_(candidate_ids)
                )
            ).all()
            offenders = [
                test_case_id for test_case_id, expected_calls in rows if expected_calls
            ]
            if offenders:
                msg = (
                    "Tool calls are only supported with the Connexity runtime. "
                    "Remove expected_tool_calls from the linked test cases, "
                    "or switch the runtime to 'connexity'."
                )
                raise ValueError(msg)


def create_eval_config(
    *, session: Session, eval_config_in: EvalConfigCreate, company_id: uuid.UUID
) -> EvalConfig:
    agent = session.get(Agent, eval_config_in.agent_id)
    if agent is None:
        msg = f"Agent {eval_config_in.agent_id} not found"
        raise ValueError(msg)

    run_config = eval_config_in.config or _default_run_config_for_agent(agent)
    member_ids = (
        [m.test_case_id for m in eval_config_in.members]
        if eval_config_in.members
        else []
    )
    _validate_runtime(
        session=session,
        agent=agent,
        run_config=run_config,
        config_id=None,
        extra_test_case_ids=member_ids,
    )

    create_data = eval_config_in.model_dump(exclude={"members", "config"})
    create_data["company_id"] = company_id
    db_obj = EvalConfig.model_validate(create_data)
    if eval_config_in.config is not None:
        db_obj.config = eval_config_in.config.model_dump()
    else:
        db_obj.config = run_config.model_dump()
    session.add(db_obj)
    session.flush()

    if eval_config_in.members:
        missing = validate_test_case_ids(session=session, test_case_ids=member_ids)
        if missing:
            raise ValueError(f"Test cases not found: {missing}")
        for position, entry in enumerate(eval_config_in.members):
            member = EvalConfigMember(
                eval_config_id=db_obj.id,
                company_id=company_id,
                test_case_id=entry.test_case_id,
                position=position,
                repetitions=entry.repetitions,
            )
            session.add(member)

    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_eval_config(
    *,
    session: Session,
    eval_config_id: uuid.UUID,
    company_id: uuid.UUID | None = None,
    include_deleted: bool = False,
) -> EvalConfig | None:
    """Fetch an eval config by id.

    Soft-deleted rows are hidden by default; pass ``include_deleted=True``
    to look up an already-deleted config (e.g. when rendering an
    environment's gate strip after the gated config was deleted).
    """
    cfg = session.get(EvalConfig, eval_config_id)
    if cfg is None:
        return None
    if cfg.deleted_at is not None and not include_deleted:
        return None
    if company_id is not None and cfg.company_id != company_id:
        return None
    return cfg


def list_eval_configs(
    *,
    session: Session,
    company_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    agent_id: uuid.UUID | None = None,
) -> tuple[list[EvalConfig], int]:
    statement = (
        select(EvalConfig)
        .where(col(EvalConfig.deleted_at).is_(None))
        .where(EvalConfig.company_id == company_id)
    )
    count_statement = (
        select(func.count())
        .select_from(EvalConfig)
        .where(col(EvalConfig.deleted_at).is_(None))
        .where(EvalConfig.company_id == company_id)
    )

    if agent_id is not None:
        statement = statement.where(EvalConfig.agent_id == agent_id)
        count_statement = count_statement.where(EvalConfig.agent_id == agent_id)

    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count


def update_eval_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    eval_config_in: EvalConfigUpdate,
) -> EvalConfig:
    if eval_config_in.config is not None:
        agent = session.get(Agent, db_eval_config.agent_id)
        if agent is None:
            msg = f"Agent {db_eval_config.agent_id} not found"
            raise ValueError(msg)
        _validate_runtime(
            session=session,
            agent=agent,
            run_config=eval_config_in.config,
            config_id=db_eval_config.id,
        )

    update_data = eval_config_in.model_dump(exclude_unset=True, exclude={"config"})
    db_eval_config.sqlmodel_update(update_data)
    if eval_config_in.config is not None:
        db_eval_config.config = eval_config_in.config.model_dump()
        _bump_version(session=session, eval_config=db_eval_config)
    session.add(db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def delete_eval_config(*, session: Session, db_eval_config: EvalConfig) -> None:
    """Soft-delete: stamp ``deleted_at`` so historical runs and environments
    that reference this config keep working while it's hidden from lists.
    """
    db_eval_config.deleted_at = datetime.now(UTC)
    session.add(db_eval_config)
    session.commit()


def _bump_version(*, session: Session, eval_config: EvalConfig) -> None:
    """Atomically increment the version at the SQL level to avoid race conditions."""
    session.execute(
        sa_update(EvalConfig)
        .where(EvalConfig.id == eval_config.id)
        .values(version=EvalConfig.version + 1)
    )


def _next_position(*, session: Session, eval_config_id: uuid.UUID) -> int:
    """Return max(position) + 1 for existing members, or 0 if empty."""
    result = session.exec(
        select(func.max(EvalConfigMember.position)).where(
            EvalConfigMember.eval_config_id == eval_config_id
        )
    ).one()
    return (result + 1) if result is not None else 0


def add_test_cases_to_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    members: list[EvalConfigMemberEntry],
) -> EvalConfig:
    test_case_ids = [m.test_case_id for m in members]
    if len(test_case_ids) != len(set(test_case_ids)):
        msg = "Duplicate test_case_id in request body"
        raise ValueError(msg)
    missing = validate_test_case_ids(session=session, test_case_ids=test_case_ids)
    if missing:
        raise ValueError(f"Test cases not found: {missing}")
    if db_eval_config.config is not None:
        agent = session.get(Agent, db_eval_config.agent_id)
        if agent is None:
            msg = f"Agent {db_eval_config.agent_id} not found"
            raise ValueError(msg)
        _validate_runtime(
            session=session,
            agent=agent,
            run_config=RunConfig.model_validate(db_eval_config.config),
            config_id=db_eval_config.id,
            extra_test_case_ids=test_case_ids,
        )
    existing = set(
        session.exec(
            select(EvalConfigMember.test_case_id).where(
                EvalConfigMember.eval_config_id == db_eval_config.id,
                col(EvalConfigMember.test_case_id).in_(test_case_ids),
            )
        ).all()
    )
    if existing:
        raise ValueError(f"Test cases already in config: {sorted(existing)}")
    next_pos = _next_position(session=session, eval_config_id=db_eval_config.id)
    for i, entry in enumerate(members):
        member = EvalConfigMember(
            eval_config_id=db_eval_config.id,
            company_id=db_eval_config.company_id,
            test_case_id=entry.test_case_id,
            position=next_pos + i,
            repetitions=entry.repetitions,
        )
        session.add(member)
    _bump_version(session=session, eval_config=db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def remove_test_case_from_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    test_case_id: uuid.UUID,
) -> EvalConfig:
    member = session.exec(
        select(EvalConfigMember).where(
            EvalConfigMember.eval_config_id == db_eval_config.id,
            EvalConfigMember.test_case_id == test_case_id,
        )
    ).first()
    if member:
        session.delete(member)
        _bump_version(session=session, eval_config=db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def replace_test_cases_in_config(
    *,
    session: Session,
    db_eval_config: EvalConfig,
    members: list[EvalConfigMemberEntry],
) -> EvalConfig:
    test_case_ids = [m.test_case_id for m in members]
    missing = validate_test_case_ids(session=session, test_case_ids=test_case_ids)
    if missing:
        raise ValueError(f"Test cases not found: {missing}")
    if db_eval_config.config is not None:
        agent = session.get(Agent, db_eval_config.agent_id)
        if agent is None:
            msg = f"Agent {db_eval_config.agent_id} not found"
            raise ValueError(msg)
        # Replace path: only the new ids count; pass them explicitly and pretend
        # there's no existing config to avoid double-counting old members.
        _validate_runtime(
            session=session,
            agent=agent,
            run_config=RunConfig.model_validate(db_eval_config.config),
            config_id=None,
            extra_test_case_ids=test_case_ids,
        )
    existing = session.exec(
        select(EvalConfigMember).where(
            EvalConfigMember.eval_config_id == db_eval_config.id
        )
    ).all()
    for member in existing:
        session.delete(member)
    session.flush()

    for position, entry in enumerate(members):
        member = EvalConfigMember(
            eval_config_id=db_eval_config.id,
            company_id=db_eval_config.company_id,
            test_case_id=entry.test_case_id,
            position=position,
            repetitions=entry.repetitions,
        )
        session.add(member)

    _bump_version(session=session, eval_config=db_eval_config)
    session.commit()
    session.refresh(db_eval_config)
    return db_eval_config


def count_test_cases_in_config(*, session: Session, eval_config_id: uuid.UUID) -> int:
    return session.exec(
        select(func.count()).where(EvalConfigMember.eval_config_id == eval_config_id)
    ).one()


def sum_member_repetitions_in_config(
    *, session: Session, eval_config_id: uuid.UUID
) -> int:
    """Sum of per-test-case repetitions across all members — total expanded executions."""
    total = session.exec(
        select(func.coalesce(func.sum(EvalConfigMember.repetitions), 0)).where(
            EvalConfigMember.eval_config_id == eval_config_id
        )
    ).one()
    return int(total)


def count_test_cases_in_configs(
    *, session: Session, eval_config_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch test case counts for multiple configs in a single query."""
    if not eval_config_ids:
        return {}
    rows = session.exec(
        select(EvalConfigMember.eval_config_id, func.count())
        .where(col(EvalConfigMember.eval_config_id).in_(eval_config_ids))
        .group_by(EvalConfigMember.eval_config_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def sum_member_repetitions_in_configs(
    *, session: Session, eval_config_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Batch-fetch sum of per-test-case repetitions per config — total expanded executions."""
    if not eval_config_ids:
        return {}
    rows = session.exec(
        select(
            EvalConfigMember.eval_config_id,
            func.coalesce(func.sum(EvalConfigMember.repetitions), 0),
        )
        .where(col(EvalConfigMember.eval_config_id).in_(eval_config_ids))
        .group_by(EvalConfigMember.eval_config_id)
    ).all()
    result = {eid: 0 for eid in eval_config_ids}
    for eid, total in rows:
        result[eid] = int(total)
    return result


def list_test_cases_in_config(
    *,
    session: Session,
    eval_config_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[EvalConfigMemberPublic], int]:
    count = session.exec(
        select(func.count())
        .select_from(EvalConfigMember)
        .where(EvalConfigMember.eval_config_id == eval_config_id)
    ).one()
    rows = list(
        session.exec(
            select(EvalConfigMember)
            .where(EvalConfigMember.eval_config_id == eval_config_id)
            .order_by(EvalConfigMember.position)
            .offset(skip)
            .limit(limit)
        ).all()
    )
    public = [
        EvalConfigMemberPublic(
            test_case_id=m.test_case_id,
            position=m.position,
            repetitions=m.repetitions,
        )
        for m in rows
    ]
    return public, count


def get_test_cases_for_config(
    *, session: Session, eval_config_id: uuid.UUID
) -> list[TestCaseExecution]:
    """Get all active test cases for a config, ordered by position, with member repetitions."""

    statement = (
        select(TestCase, EvalConfigMember.repetitions, EvalConfigMember.position)
        .join(EvalConfigMember, TestCase.id == EvalConfigMember.test_case_id)
        .where(
            EvalConfigMember.eval_config_id == eval_config_id,
            TestCase.status == TestCaseStatus.ACTIVE,
            col(TestCase.deleted_at).is_(None),
        )
        .order_by(EvalConfigMember.position)
    )
    rows = session.exec(statement).all()
    return [
        TestCaseExecution(test_case=row[0], repetitions=row[1], position=row[2])
        for row in rows
    ]
