"""The agent's Tests tab (`plans/2026-11-19-tests-tab-runs-and-verified.md`,
`designs/12-adjustments.md` item 32): the live version's verdict from its latest full
run, every run with its totals, coverage as tests written, and the scenarios and sets.
Read only.
"""

import uuid

from sqlmodel import Session

from app.crud.scenario import live_scenarios, members, rules_of, sets_of_agent
from app.crud.spec import latest_spec
from app.crud.test_run import runs_of_agent
from app.models.agent import Agent
from app.models.enums import RunStatus
from app.models.test_run import (
    ScenarioRowPublic,
    SetChipPublic,
    TestsTabPublic,
)
from app.services.test_run import run_views, version_tested

# Runs listed on the tab, newest first.
RUNS_LISTED = 100


def tests_tab(
    *, session: Session, agent: Agent, version: str | None = None
) -> TestsTabPublic:
    """The Tests tab for the live version, or for agent version ``version``."""
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

    found = version_tested(session, agent, version)
    # One list, newest first (Dmytro, 2026-11-19); with a version picked, its runs.
    runs = (
        found.results.runs
        if version is not None
        else run_views(
            session,
            list(reversed(runs_of_agent(session=session, agent_id=agent.id)))[
                :RUNS_LISTED
            ],
        )
    )
    running = any(r.status in (RunStatus.PENDING, RunStatus.RUNNING) for r in runs)

    return TestsTabPublic(
        has_spec=spec is not None,
        results=found.results if spec is not None else None,
        coverage=found.results.coverage,
        runs=runs,
        live_version=found.results.live_version,
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
