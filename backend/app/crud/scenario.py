"""Reading and writing scenarios and their sets (`plans/2026-11-17-scenarios.md`).

A scenario is a `test_case` of an agent with at least one `scenario_rule`; a set is an
`eval_config`. Both keep their 1.x tables until the runner unfreezes the eval stack.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import ColumnElement
from sqlmodel import Session, col, delete, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models.enums import TestCaseStatus
from app.models.eval_config import EvalConfig, EvalConfigMember
from app.models.scenario import ScenarioRule
from app.models.test_case import TestCase


def _live_where(agent_id: uuid.UUID) -> list[ColumnElement[bool]]:
    """The agent's active scenarios: its test cases with at least one rule."""
    listed = select(ScenarioRule.test_case_id).where(ScenarioRule.agent_id == agent_id)
    return [
        col(TestCase.agent_id) == agent_id,
        col(TestCase.status) == TestCaseStatus.ACTIVE,
        col(TestCase.deleted_at).is_(None),
        col(TestCase.id).in_(listed),
    ]


def _live_ids(agent_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    return select(TestCase.id).where(*_live_where(agent_id))


def scenarios_page(
    *,
    session: Session,
    agent_id: uuid.UUID,
    rule_key: str | None,
    set_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> tuple[list[TestCase], bool]:
    """A page of the agent's active scenarios, oldest first, and whether more follow."""
    query = select(TestCase).where(*_live_where(agent_id))
    if rule_key is not None:
        query = query.where(
            col(TestCase.id).in_(
                select(ScenarioRule.test_case_id).where(
                    ScenarioRule.agent_id == agent_id, ScenarioRule.rule_key == rule_key
                )
            )
        )
    if set_id is not None:
        query = query.where(
            col(TestCase.id).in_(
                select(EvalConfigMember.test_case_id).where(
                    EvalConfigMember.eval_config_id == set_id
                )
            )
        )
    rows = list(
        session.exec(
            query.order_by(col(TestCase.created_at), col(TestCase.id))
            .offset(offset)
            .limit(limit + 1)
        ).all()
    )
    return rows[:limit], len(rows) > limit


def live_scenario_ids(*, session: Session, agent_id: uuid.UUID) -> set[uuid.UUID]:
    return set(session.exec(_live_ids(agent_id)).all())


def rules_of(
    *, session: Session, test_case_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """Each scenario's rule keys, in the order they were given."""
    if not test_case_ids:
        return {}
    out: dict[uuid.UUID, list[str]] = {}
    for row in session.exec(
        select(ScenarioRule)
        .where(col(ScenarioRule.test_case_id).in_(test_case_ids))
        .order_by(col(ScenarioRule.position))
    ).all():
        out.setdefault(row.test_case_id, []).append(row.rule_key)
    return out


def scenarios_by_rule(*, session: Session, agent_id: uuid.UUID) -> dict[str, int]:
    """How many of the agent's active scenarios list each rule key."""
    live = _live_ids(agent_id)
    rows = session.exec(
        select(ScenarioRule.rule_key, func.count())
        .where(
            ScenarioRule.agent_id == agent_id,
            col(ScenarioRule.test_case_id).in_(live),
        )
        .group_by(col(ScenarioRule.rule_key))
    ).all()
    return {key: int(count) for key, count in rows}


def agents_with_scenarios(
    *, session: Session, agent_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, set[str]]:
    """For each agent, the rule keys its active scenarios list."""
    if not agent_ids:
        return {}
    rows = session.exec(
        select(ScenarioRule.agent_id, ScenarioRule.rule_key)
        .join(TestCase, col(TestCase.id) == col(ScenarioRule.test_case_id))
        .where(
            col(ScenarioRule.agent_id).in_(agent_ids),
            TestCase.status == TestCaseStatus.ACTIVE,
            col(TestCase.deleted_at).is_(None),
        )
    ).all()
    out: dict[uuid.UUID, set[str]] = {}
    for agent_id, key in rows:
        out.setdefault(agent_id, set()).add(key)
    return out


def set_rules(
    *,
    session: Session,
    scenario: TestCase,
    agent_id: uuid.UUID,
    keys: Sequence[str],
) -> None:
    """Replace the scenario's rule keys. Does not commit."""
    session.exec(  # type: ignore[call-overload]
        delete(ScenarioRule).where(col(ScenarioRule.test_case_id) == scenario.id)
    )
    for position, key in enumerate(keys):
        session.add(
            ScenarioRule(
                test_case_id=scenario.id,
                rule_key=key,
                company_id=scenario.company_id,
                agent_id=agent_id,
                position=position,
            )
        )


def leave_sets(*, session: Session, test_case_id: uuid.UUID) -> None:
    """Take the scenario out of every set. Does not commit."""
    session.exec(  # type: ignore[call-overload]
        delete(EvalConfigMember).where(
            col(EvalConfigMember.test_case_id) == test_case_id
        )
    )


def sets_of_agent(*, session: Session, agent_id: uuid.UUID) -> list[EvalConfig]:
    return list(
        session.exec(
            select(EvalConfig)
            .where(
                EvalConfig.agent_id == agent_id, col(EvalConfig.deleted_at).is_(None)
            )
            .order_by(col(EvalConfig.name))
        ).all()
    )


def set_by_name(
    *, session: Session, agent_id: uuid.UUID, name: str
) -> EvalConfig | None:
    return session.exec(
        select(EvalConfig).where(
            EvalConfig.agent_id == agent_id,
            EvalConfig.name == name,
            col(EvalConfig.deleted_at).is_(None),
        )
    ).first()


def members(
    *, session: Session, set_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Each set's scenario ids, in order."""
    if not set_ids:
        return {}
    out: dict[uuid.UUID, list[uuid.UUID]] = {set_id: [] for set_id in set_ids}
    for row in session.exec(
        select(EvalConfigMember)
        .where(col(EvalConfigMember.eval_config_id).in_(set_ids))
        .order_by(col(EvalConfigMember.position))
    ).all():
        out[row.eval_config_id].append(row.test_case_id)
    return out


def replace_members(
    *, session: Session, config: EvalConfig, scenario_ids: Sequence[uuid.UUID]
) -> None:
    """The set's scenarios become ``scenario_ids``, in that order. Does not commit."""
    session.exec(  # type: ignore[call-overload]
        delete(EvalConfigMember).where(
            col(EvalConfigMember.eval_config_id) == config.id
        )
    )
    for position, test_case_id in enumerate(scenario_ids):
        session.add(
            EvalConfigMember(
                company_id=config.company_id,
                eval_config_id=config.id,
                test_case_id=test_case_id,
                position=position,
                repetitions=1,
            )
        )


def archive_set(*, session: Session, config: EvalConfig) -> None:
    """Does not commit."""
    config.deleted_at = datetime.now(UTC)
    session.add(config)
    session.exec(  # type: ignore[call-overload]
        delete(EvalConfigMember).where(
            col(EvalConfigMember.eval_config_id) == config.id
        )
    )


def live_scenarios(*, session: Session, agent_id: uuid.UUID) -> list[TestCase]:
    """Every active scenario of the agent, oldest first."""
    return list(
        session.exec(
            select(TestCase)
            .where(*_live_where(agent_id))
            .order_by(col(TestCase.created_at), col(TestCase.id))
        ).all()
    )
