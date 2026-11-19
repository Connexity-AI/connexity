"""The agent's Tests tab and the Spec tab's results, on invented agents with Retell and
the model mocked (plans `plans/2026-11-17-tests-tab.md`,
`plans/2026-11-19-tests-tab-runs-and-verified.md`)."""

import json
import re
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Agent, User
from app.models.test_run import SimulatedFinding
from app.services.llm import LLMMessage, LLMResponse
from app.tests.api.routes.test_call_screen import _signed_in
from app.tests.api.routes.test_issue_page import _call
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    FULL,
    _agent,
    _booking,
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_scenarios import (
    BOOKING,
    PRICE,
    _keys,
    _price,
    _scenarios,
    _set,
)
from app.tests.api.routes.test_spec_api import API, RULES, _catalogue, _write
from app.tests.api.routes.test_test_runs import (
    PLAYGROUND,
    _agent_turn,
    _execute,
    _runs,
    _start,
    caller,  # noqa: F401 - the simulated caller's model, mocked
)

RETELL = "https://api.retellai.com/"

pytestmark = [pytest.mark.provider_versions, pytest.mark.usefixtures("caller")]


def _agent_with_spec(
    db: Session, client: TestClient, user: User
) -> tuple[Agent, dict[str, str]]:
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=15)
    data = _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}]).json()
    return agent, _keys(data["data"])


def _tab(client: TestClient, cookies: dict[str, str], agent: Agent) -> Any:
    return client.get(f"{API}/agents/{agent.id}/tests", cookies=cookies)


def _judge(outcomes: dict[str, str]) -> AsyncMock:
    """A judge that answers every rule it is asked about from ``outcomes``."""

    async def answer(messages: list[LLMMessage], **_: Any) -> LLMResponse:
        keys = re.findall(r"^- \[([^\]]+)\]", messages[1].content, flags=re.M)
        return LLMResponse(
            content=json.dumps(
                {
                    "rules": [
                        {"key": k, "outcome": outcomes[k], "reason": "x", "turns": [4]}
                        for k in keys
                    ]
                }
            ),
            model="invented-model",
        )

    return AsyncMock(side_effect=answer)


def _run(
    client: TestClient,
    user: User,
    agent: Agent,
    outcomes: dict[str, str],
    findings: Any = None,
) -> str:
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]
    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
        retell.get(url__startswith=f"{RETELL}get-agent/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "version": 15,
                    "response_engine": {"type": "retell-llm", "llm_id": "llm_1"},
                },
            )
        )
        retell.get(url__startswith=f"{RETELL}get-retell-llm/").mock(
            return_value=httpx.Response(200, json={"general_prompt": "Greet."})
        )
        with patch("app.services.rule_judge.call_llm", new=_judge(outcomes)):
            if findings is None:
                _execute(run_id)
            else:
                with patch(
                    "app.services.test_run.check_simulated", return_value=findings
                ):
                    _execute(run_id)
    return run_id


def test_each_empty_state(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")

    no_spec = _tab(client, cookies, agent).json()
    assert no_spec["has_spec"] is False
    assert no_spec["coverage"] is None
    assert no_spec["results"] is None

    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
    data = _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}]).json()
    keys = _keys(data["data"])
    no_scenarios = _tab(client, cookies, agent).json()
    assert no_scenarios["has_spec"] is True
    coverage = no_scenarios["coverage"]
    assert (coverage["rules"], coverage["covered"], coverage["pct"]) == (2, 0, 0)
    # Critical first, each without a scenario.
    assert [u["key"] for u in coverage["uncovered"]] == [keys[PRICE], keys[BOOKING]]
    assert no_scenarios["scenarios"] == []
    # The live version is not verified before anything runs.
    assert no_scenarios["results"]["version"] == "7"
    assert no_scenarios["results"]["verdict"] == "not_verified"
    assert no_scenarios["results"]["runs"] == []

    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])
    not_run = _tab(client, cookies, agent).json()
    assert not_run["scenarios"] == [
        {
            "id": scenario["id"],
            "name": "Price pushback",
            "caller_goal": "Find out what the cleaning costs",
            "rules": 1,
            "sets": ["smoke"],
        }
    ]
    assert not_run["sets"] == [{"name": "smoke", "scenarios": 1}]
    # Coverage is tests written: the price rule has a scenario, run or not.
    assert (not_run["coverage"]["covered"], not_run["coverage"]["pct"]) == (1, 50)
    assert not_run["running"] is False


def test_the_runs_with_their_totals_and_the_spec_tabs_results(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _agent_with_spec(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    _scenarios(
        client,
        user,
        agent,
        _price(keys, name="Booking on Sunday", rules=[keys[BOOKING]]),
    )

    _run(client, user, agent, {keys[PRICE]: "failed", keys[BOOKING]: "did_not_come_up"})

    tab = _tab(client, cookies, agent).json()
    results = tab["results"]
    assert (results["version"], results["verdict"]) == ("15", "failed")
    [run] = results["runs"]
    assert run["full"] is True and run["verdict"] == "failed"
    assert run["totals"] == {
        "rules": 2,
        "passed": 0,
        "failed": 1,
        "did_not_come_up": 1,
        "no_scenario": 0,
        "not_judged": 0,
        "critical": 1,
        "judged_calls": 2,
        "stopped": 0,
    }
    assert run["ran_by"]
    assert [r["id"] for r in tab["runs"]] == [run["id"]]
    assert tab["live_version"] == "15"
    assert (tab["coverage"]["covered"], tab["coverage"]["pct"]) == (2, 100)
    assert len(tab["scenarios"]) == 2

    # The Spec tab marks each rule with its result in that full run.
    spec = client.get(f"{API}/agents/{agent.id}/spec", cookies=cookies).json()
    marks = {r["key"]: r["result"] for g in spec["groups"] for r in g["rules"]}
    assert marks == {keys[PRICE]: "failed", keys[BOOKING]: "did_not_come_up"}
    assert spec["results_version"] == "15"
    assert spec["results_at"] is not None

    # The assistant reads the same verdict.
    body = _runs(client, user, agent).json()
    assert body["data"]["results"]["verdict"] == "failed"


def test_a_version_not_live_yet_is_followed_with_every_run_in_one_list(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _agent_with_spec(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    _run(client, user, agent, {keys[PRICE]: "passed"})
    # The agent's latest call is on 14: version 15, the one tested, is not live yet.
    _call(db, agent, _booking(2, FULL), days_ago=0, version=14)

    tab = _tab(client, cookies, agent).json()
    assert tab["results"]["version"] == "15"
    assert tab["live_version"] == "14"
    assert tab["results"]["live"] == {
        "version": "14",
        "verdict": "not_verified",
        "at": None,
    }
    assert [r["platform_version"] for r in tab["runs"]] == ["15"]
    # The Spec tab marks rules from 15's full run too.
    spec = client.get(f"{API}/agents/{agent.id}/spec", cookies=cookies).json()
    assert spec["results_version"] == "15"
    assert spec["results_at"] is not None


def test_a_run_in_progress_shows_as_running(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _agent_with_spec(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    _start(client, user, agent, all=True, repeats=1)

    tab = _tab(client, cookies, agent).json()
    assert tab["running"] is True
    assert tab["results"]["runs"][0]["status"] == "pending"
    assert tab["results"]["runs"][0]["totals"] is None


def test_a_code_check_counts_once_as_critical(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _agent_with_spec(db, client, user)
    _scenarios(client, user, agent, _price(keys, rules=[keys[PRICE], keys[BOOKING]]))
    finding = SimulatedFinding.model_validate(
        {
            "check_type": "tool_call_failed",
            "check_version": 1,
            "kind": "code_based",
            "mode": "fails",
            "key": "book_slot",
            "event_ids": ["t2-0"],
        }
    )

    _run(
        client,
        user,
        agent,
        {keys[PRICE]: "passed", keys[BOOKING]: "passed"},
        findings=[finding],
    )

    results = _tab(client, cookies, agent).json()["results"]
    assert results["verdict"] == "failed"
    assert results["critical_checks"] == ["tool_call_failed"]
    assert results["full_run"]["totals"]["critical"] == 1


def test_another_workspaces_agent_is_not_found(client: TestClient, db: Session) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _, other = _signed_in(client, db)

    assert _tab(client, other, agent).status_code == 404
