"""The agent's Tests tab (`plans/2026-11-19-tests-tab-runs-and-verified.md`,
`designs/12-adjustments.md` item 32): the live version's verdict from its latest full
run, every run with its totals, coverage as tests written, and the scenarios and sets.
Read only.
"""

import uuid

from sqlmodel import Session

from app.crud.scenario import live_scenarios, members, rules_of, sets_of_agent
from app.crud.spec import latest_spec
from app.models.agent import Agent
from app.models.enums import RunStatus
from app.models.test_run import (
    ScenarioRowPublic,
    SetChipPublic,
    TestsTabPublic,
    VersionRunsPublic,
)
from app.services.test_run import run_views, version_number, version_tested

# Runs of earlier versions listed under "N runs on earlier versions".
EARLIER_RUNS = 50


def tests_tab(*, session: Session, agent: Agent) -> TestsTabPublic:
    spec = latest_spec(session=session, agent_id=agent.id)
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
    # Earlier versions' runs, newest first, at most this many.
    shown = list(reversed(found.others))[:EARLIER_RUNS]
    by_version: dict[str | None, list[uuid.UUID]] = {}
    for run in shown:
        by_version.setdefault(run.platform_version, []).append(run.id)
    otherrun_views = {v.id: v for v in run_views(session, list(reversed(found.others)))}
    earlier = [
        VersionRunsPublic(version=version, runs=[otherrun_views[i] for i in ids])
        for version, ids in sorted(
            by_version.items(), key=lambda item: version_number(item[0]), reverse=True
        )
    ]
    running = any(
        r.status in (RunStatus.PENDING, RunStatus.RUNNING) for r in found.others
    ) or any(
        v.status in (RunStatus.PENDING, RunStatus.RUNNING) for v in found.results.runs
    )

    return TestsTabPublic(
        has_spec=spec is not None,
        results=found.results if spec is not None else None,
        coverage=found.results.coverage,
        earlier=earlier,
        running=running,
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
