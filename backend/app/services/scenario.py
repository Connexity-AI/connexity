"""Scenarios as `write_scenarios`, `list_scenarios` and `write_scenario_set` answer them
(`plans/2026-11-17-scenarios.md`, `docs-internal/testing.md`).

The assistant writes scenarios; Connexity checks and stores them, and never writes one
itself. A scenario has no pass or fail of its own: a run judges the rules it lists.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, col, select

from app import crud
from app.crud import scenario as crud_scenario
from app.crud.check import lock_agent
from app.models.agent import Agent
from app.models.call import Call
from app.models.enums import FirstTurn, TestCaseStatus
from app.models.eval_config import EvalConfig
from app.models.scenario import (
    FakeToolResultPublic,
    ScenarioCountsPublic,
    ScenarioListPublic,
    ScenarioPublic,
    ScenarioRulePublic,
    ScenarioSetPublic,
)
from app.models.spec import SpecRule
from app.models.test_case import TestCase

MAX_SCENARIOS = 20
MAX_RULES_PER_SCENARIO = 20
MAX_NAME = 255
MAX_UNLISTED = 50


@dataclass
class FakeToolDraft:
    tool: str
    arguments: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


@dataclass
class ScenarioDraft:
    id: uuid.UUID | None = None
    archive: bool = False
    name: str = ""
    description: str | None = None
    caller: str | None = None
    caller_goal: str | None = None
    caller_behaviour: str | None = None
    caller_knows: dict[str, Any] | None = None
    agent_variables: dict[str, Any] | None = None
    first_turn: FirstTurn = FirstTurn.USER
    first_message: str | None = None
    fake_tool_results: list[FakeToolDraft] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    from_call_id: uuid.UUID | None = None


class ScenarioRefused(Exception):
    def __init__(self, error: str, problems: list[str]) -> None:
        super().__init__(error)
        self.error = error
        self.problems = problems


@dataclass
class Written:
    stored: list[TestCase]
    archived: int
    unlisted_critical: list[SpecRule]
    # The latest spec's rules, by key.
    rules: dict[str, SpecRule]


def _latest_rules(session: Session, agent: Agent) -> list[SpecRule] | None:
    latest = crud.latest_spec(session=session, agent_id=agent.id)
    if latest is None:
        return None
    return crud.spec_rules(session=session, spec_id=latest.id)


def _text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _check(
    session: Session,
    agent: Agent,
    drafts: Sequence[ScenarioDraft],
    keys: set[str],
) -> tuple[list[str], dict[uuid.UUID, TestCase]]:
    """Every problem with ``drafts``, and the scenarios they replace or archive."""
    problems: list[str] = []
    ids = [d.id for d in drafts if d.id is not None]
    existing = {
        row.id: row
        for row in session.exec(
            select(TestCase).where(
                col(TestCase.id).in_(ids),
                TestCase.agent_id == agent.id,
                col(TestCase.deleted_at).is_(None),
            )
        ).all()
    }
    call_ids = [d.from_call_id for d in drafts if d.from_call_id is not None]
    calls = set(
        session.exec(
            select(Call.id).where(
                col(Call.id).in_(call_ids),
                Call.agent_id == agent.id,
                col(Call.deleted_at).is_(None),
            )
        ).all()
    )
    seen: set[uuid.UUID] = set()
    for n, draft in enumerate(drafts, start=1):
        at = f"Scenario {n}"
        if draft.id is not None:
            if draft.id in seen:
                problems.append(f"{at}: id {draft.id} is given twice.")
            seen.add(draft.id)
            if draft.id not in existing:
                problems.append(
                    f"{at}: id {draft.id} is not one of this agent's scenarios; leave "
                    "the id out for a new one."
                )
        if draft.archive:
            if draft.id is None:
                problems.append(f"{at}: give the id of the scenario to archive.")
            continue
        if not (draft.name or "").strip():
            problems.append(f"{at}: the name is empty.")
        elif len(draft.name.strip()) > MAX_NAME:
            problems.append(f"{at}: the name is longer than {MAX_NAME} characters.")
        rules = list(dict.fromkeys(k.strip() for k in draft.rules if k.strip()))
        if not rules:
            problems.append(
                f"{at}: list the spec rules it expects to come up (keys from "
                "`get_spec`). Something no rule covers is a gap in the spec: add the "
                "rule first."
            )
        elif len(rules) > MAX_RULES_PER_SCENARIO:
            problems.append(f"{at}: at most {MAX_RULES_PER_SCENARIO} rules.")
        for key in rules:
            if key not in keys:
                problems.append(
                    f"{at}: rule '{key}' is not in the agent's latest spec; use the "
                    "keys `get_spec` answers."
                )
        for m, fake in enumerate(draft.fake_tool_results, start=1):
            if not (fake.tool or "").strip():
                problems.append(f"{at}: fake tool result {m} has no tool name.")
        if draft.from_call_id is not None and draft.from_call_id not in calls:
            problems.append(
                f"{at}: call {draft.from_call_id} is not one of this agent's calls."
            )
    return problems, existing


def _fill(scenario: TestCase, draft: ScenarioDraft) -> None:
    scenario.name = draft.name.strip()
    scenario.description = _text(draft.description)
    scenario.persona_context = _text(draft.caller)
    scenario.caller_goal = _text(draft.caller_goal)
    scenario.caller_behaviour = _text(draft.caller_behaviour)
    scenario.user_context = draft.caller_knows or None
    scenario.agent_variables = draft.agent_variables or None
    scenario.first_turn = draft.first_turn
    scenario.first_message = _text(draft.first_message)
    # Stored as the 1.x tool call rows, whose `mock_response` is the canned result.
    scenario.expected_tool_calls = [
        {
            "tool": fake.tool.strip(),
            "expected_params": fake.arguments,
            "mock_response": fake.result,
        }
        for fake in draft.fake_tool_results
    ] or None
    scenario.expected_outcomes = None
    scenario.source_call_id = draft.from_call_id
    scenario.status = TestCaseStatus.ACTIVE
    scenario.updated_at = datetime.now(UTC)


def write_scenarios(
    *, session: Session, agent: Agent, drafts: Sequence[ScenarioDraft]
) -> Written:
    """Check ``drafts`` and store them, all or nothing.

    Raises:
        ScenarioRefused: The agent has no spec, or a scenario is not right; every
            problem is listed and nothing is stored.
    """
    if not drafts:
        raise ScenarioRefused("Give at least one scenario", [])
    if len(drafts) > MAX_SCENARIOS:
        raise ScenarioRefused(f"At most {MAX_SCENARIOS} scenarios per call", [])
    lock_agent(session=session, agent_id=agent.id)
    rules = _latest_rules(session, agent)
    if rules is None:
        session.rollback()
        raise ScenarioRefused(
            "The agent has no spec yet",
            ["Write its spec with `write_spec`; scenarios list its rules."],
        )
    problems, existing = _check(session, agent, drafts, {r.key for r in rules})
    if problems:
        session.rollback()
        raise ScenarioRefused("No scenario was stored", problems)

    stored: list[TestCase] = []
    archived = 0
    for draft in drafts:
        if draft.archive:
            assert draft.id is not None
            scenario = existing[draft.id]
            scenario.status = TestCaseStatus.ARCHIVED
            scenario.updated_at = datetime.now(UTC)
            session.add(scenario)
            crud_scenario.leave_sets(session=session, test_case_id=scenario.id)
            archived += 1
            continue
        scenario = (
            existing[draft.id]
            if draft.id is not None
            else TestCase(company_id=agent.company_id, agent_id=agent.id, name="")
        )
        _fill(scenario, draft)
        session.add(scenario)
        session.flush()
        crud_scenario.set_rules(
            session=session,
            scenario=scenario,
            agent_id=agent.id,
            keys=list(dict.fromkeys(k.strip() for k in draft.rules if k.strip())),
        )
        stored.append(scenario)
    session.commit()
    for scenario in stored:
        session.refresh(scenario)
    listed = crud_scenario.scenarios_by_rule(session=session, agent_id=agent.id)
    return Written(
        stored=stored,
        archived=archived,
        unlisted_critical=[r for r in rules if r.critical and r.key not in listed],
        rules={r.key: r for r in rules},
    )


def scenario_public(
    scenario: TestCase,
    keys: Sequence[str],
    rules: dict[str, SpecRule],
    sets: Sequence[str] = (),
) -> ScenarioPublic:
    return ScenarioPublic(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        caller=scenario.persona_context,
        caller_goal=scenario.caller_goal,
        caller_behaviour=scenario.caller_behaviour,
        caller_knows=scenario.user_context,
        agent_variables=scenario.agent_variables,
        first_turn=scenario.first_turn,
        first_message=scenario.first_message,
        fake_tool_results=[
            FakeToolResultPublic(
                tool=str(row.get("tool", "")),
                arguments=row.get("expected_params"),
                result=row.get("mock_response"),
            )
            for row in scenario.expected_tool_calls or []
        ],
        rules=[_rule_public(key, rules) for key in keys],
        sets=list(sets),
        from_call_id=scenario.source_call_id,
        updated_at=scenario.updated_at,
    )


def _rule_public(key: str, rules: dict[str, SpecRule]) -> ScenarioRulePublic:
    rule = rules.get(key)
    if rule is None:
        return ScenarioRulePublic(key=key, gone=True)
    return ScenarioRulePublic(key=key, text=rule.text, critical=rule.critical)


def list_scenarios(
    *,
    session: Session,
    agent: Agent,
    rule_key: str | None,
    set_name: str | None,
    offset: int,
    limit: int,
) -> tuple[ScenarioListPublic, bool] | None:
    """A page of the agent's scenarios, its sets and the counts, and whether more
    follow. None when ``set_name`` is not one of its sets."""
    sets = crud_scenario.sets_of_agent(session=session, agent_id=agent.id)
    chosen = next((s for s in sets if s.name == set_name), None)
    if set_name is not None and chosen is None:
        return None
    rules = {r.key: r for r in (_latest_rules(session, agent) or [])}
    page, more = crud_scenario.scenarios_page(
        session=session,
        agent_id=agent.id,
        rule_key=rule_key,
        set_id=chosen.id if chosen else None,
        offset=offset,
        limit=limit,
    )
    keys = crud_scenario.rules_of(session=session, test_case_ids=[s.id for s in page])
    live = crud_scenario.live_scenario_ids(session=session, agent_id=agent.id)
    in_sets = crud_scenario.members(session=session, set_ids=[s.id for s in sets])
    names: dict[uuid.UUID, list[str]] = {}
    for config in sets:
        for scenario_id in in_sets[config.id]:
            names.setdefault(scenario_id, []).append(config.name)
    listed = crud_scenario.scenarios_by_rule(session=session, agent_id=agent.id)
    all_keys = crud_scenario.rules_of(session=session, test_case_ids=list(live))
    unlisted = sorted(
        (r for r in rules.values() if r.key not in listed),
        key=lambda r: (not r.critical, r.position, r.key),
    )
    answer = ScenarioListPublic(
        agent_id=agent.id,
        agent_name=agent.name,
        data=[
            scenario_public(s, keys.get(s.id, []), rules, names.get(s.id, []))
            for s in page
        ],
        next_cursor=None,
        sets=[
            ScenarioSetPublic(
                id=config.id,
                name=config.name,
                description=config.description,
                scenario_ids=[i for i in in_sets[config.id] if i in live],
            )
            for config in sets
        ],
        counts=ScenarioCountsPublic(
            scenarios=len(live),
            rules=len(rules),
            rules_listed=sum(1 for key in rules if key in listed),
            critical_unlisted=sum(
                1 for r in rules.values() if r.critical and r.key not in listed
            ),
            listing_gone_rules=sum(
                1
                for scenario_keys in all_keys.values()
                if any(key not in rules for key in scenario_keys)
            ),
        ),
        unlisted_rules=[_rule_public(r.key, rules) for r in unlisted[:MAX_UNLISTED]],
    )
    return answer, more


def write_scenario_set(
    *,
    session: Session,
    agent: Agent,
    name: str,
    scenario_ids: Sequence[uuid.UUID],
    description: str | None,
) -> EvalConfig | None:
    """Create the set, or replace the set of that name; with no scenarios, archive it.

    Returns:
        The set, or None when it was archived.

    Raises:
        ScenarioRefused: The name is empty, there is no such set to archive, or a
            scenario is not one of the agent's active ones.
    """
    name = name.strip()
    if not name:
        raise ScenarioRefused("Give the set a name", [])
    if len(name) > MAX_NAME:
        raise ScenarioRefused(f"A set's name is at most {MAX_NAME} characters", [])
    lock_agent(session=session, agent_id=agent.id)
    config = crud_scenario.set_by_name(session=session, agent_id=agent.id, name=name)
    ids = list(dict.fromkeys(scenario_ids))
    if not ids:
        if config is None:
            session.rollback()
            raise ScenarioRefused(
                f"The agent has no set named '{name}'",
                ["`list_scenarios` lists its sets."],
            )
        crud_scenario.archive_set(session=session, config=config)
        session.commit()
        return None
    live = crud_scenario.live_scenario_ids(session=session, agent_id=agent.id)
    unknown = [i for i in ids if i not in live]
    if unknown:
        session.rollback()
        raise ScenarioRefused(
            "The set was not stored",
            [
                f"Scenario {i} is not one of this agent's active scenarios."
                for i in unknown
            ],
        )
    if config is None:
        config = EvalConfig(
            company_id=agent.company_id,
            agent_id=agent.id,
            name=name,
            description=_text(description),
        )
    else:
        config.version += 1
        config.description = _text(description)
        config.updated_at = datetime.now(UTC)
    session.add(config)
    session.flush()
    crud_scenario.replace_members(session=session, config=config, scenario_ids=ids)
    session.commit()
    session.refresh(config)
    return config
