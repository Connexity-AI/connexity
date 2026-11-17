"""The agent's Tests tab (`plans/2026-11-17-tests-tab.md`, `designs/12-adjustments.md`
item 31): the newest tested version's verdict, what failed with its simulated calls,
coverage, every rule's totals, and the scenarios and sets. Read only.
"""

import uuid

from sqlmodel import Session, col, select

from app import crud
from app.crud.scenario import live_scenarios, members, rules_of, sets_of_agent
from app.crud.spec import latest_spec, rules_of_specs
from app.models.agent import Agent
from app.models.enums import RuleOutcome
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.models.test_run import (
    FailingCheckPublic,
    FailingRulePublic,
    JudgedCallPublic,
    RuleGroupPublic,
    RuleRowPublic,
    RuleVerdict,
    ScenarioRowPublic,
    SetChipPublic,
    TestsTabPublic,
)
from app.services.test_run import coverage_of, version_tested

# Simulated calls listed under one failing rule or check.
CALLS_SHOWN = 20


def _names(session: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    return dict(
        session.exec(
            select(TestCase.id, TestCase.name).where(col(TestCase.id).in_(ids))
        ).all()
    )


def tests_tab(*, session: Session, agent: Agent) -> TestsTabPublic:
    spec = latest_spec(session=session, agent_id=agent.id)
    categories = crud.categories_by_id(session=session)
    spec_rules = (
        rules_of_specs(session=session, spec_ids=[spec.id]).get(spec.id, [])
        if spec
        else []
    )
    category_of = {
        rule.key: categories[rule.category_id].name
        if rule.category_id in categories
        else "Other"
        for rule in spec_rules
    }

    # The scenarios and sets.
    scenarios = live_scenarios(session=session, agent_id=agent.id)
    live = {s.id for s in scenarios}
    sets = sets_of_agent(session=session, agent_id=agent.id)
    set_members = members(session=session, set_ids=[s.id for s in sets])
    sets_of: dict[uuid.UUID, list[str]] = {}
    for config in sets:
        for scenario_id in set_members.get(config.id, []):
            sets_of.setdefault(scenario_id, []).append(config.name)
    listed = rules_of(session=session, test_case_ids=[s.id for s in scenarios])

    found = version_tested(session, agent, None)
    results = found.results if found else None
    totals = results.rules if results else []
    by_key = {t.key: t for t in totals}

    # What failed, with its simulated calls.
    calls = {c.id: c for c in found.calls} if found else {}
    names = _names(session, {c.test_case_id for c in calls.values()})

    def judged_call(
        result: TestCaseResult, outcome: RuleOutcome | None
    ) -> JudgedCallPublic:
        return JudgedCallPublic(
            id=result.id,
            scenario_name=names.get(result.test_case_id, ""),
            repeat=result.repetition_index + 1,
            outcome=outcome,
        )

    verdicts_of: dict[str, list[RuleVerdict]] = {}
    for verdict in found.verdicts if found else []:
        if verdict.outcome is not RuleOutcome.DID_NOT_COME_UP:
            verdicts_of.setdefault(verdict.rule_key, []).append(verdict)
    failing = [
        FailingRulePublic(
            key=t.key,
            text=t.text,
            category=category_of.get(t.key, "Other"),
            critical=t.critical,
            failed=t.failed,
            judged=t.passed + t.failed,
            flaky=t.flaky,
            calls=[
                judged_call(calls[v.test_case_result_id], v.outcome)
                for v in sorted(
                    verdicts_of.get(t.key, []),
                    key=lambda v: v.outcome is not RuleOutcome.FAILED,
                )[:CALLS_SHOWN]
                if v.test_case_result_id in calls
            ],
        )
        for t in totals
        if t.failed
    ]
    failing.sort(key=lambda f: (not f.critical, -f.failed, f.key))
    failing_checks = [
        FailingCheckPublic(
            check_type=c.check_type,
            title=c.title,
            critical=c.critical,
            found=c.found,
            of=len(calls),
            calls=[
                judged_call(result, None)
                for result in calls.values()
                if any(
                    f.get("check_type") == c.check_type
                    for f in result.check_findings or []
                )
            ][:CALLS_SHOWN],
        )
        for c in (results.checks if results else [])
    ]

    # Every rule of the latest spec, by category.
    groups: dict[str, list[RuleRowPublic]] = {}
    for rule in spec_rules:
        total = by_key.get(rule.key)
        groups.setdefault(category_of[rule.key], []).append(
            RuleRowPublic(
                key=rule.key,
                text=rule.text,
                critical=rule.critical,
                passed=total.passed if total else 0,
                failed=total.failed if total else 0,
                did_not_come_up=total.did_not_come_up if total else 0,
            )
        )

    return TestsTabPublic(
        has_spec=spec is not None,
        results=results,
        coverage=results.coverage
        if results
        else coverage_of(session=session, agent=agent, totals=[]),
        failing=failing,
        failing_checks=failing_checks,
        all_rules=[
            RuleGroupPublic(category=name, rules=rows) for name, rows in groups.items()
        ],
        sets=[
            SetChipPublic(
                name=config.name,
                scenarios=sum(1 for i in set_members.get(config.id, []) if i in live),
            )
            for config in sets
        ],
        scenarios=[
            ScenarioRowPublic(
                id=s.id,
                name=s.name,
                caller_goal=s.caller_goal,
                rules=len(listed.get(s.id, [])),
                sets=sets_of.get(s.id, []),
            )
            for s in scenarios
        ],
    )
