"""The agent's Tests tab and coverage, on invented agents with Retell and the model
mocked (plan `plans/2026-11-17-tests-tab.md`)."""

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
    _with_key,
    caller,  # noqa: F401 - the simulated caller's model, mocked
)

RETELL = "https://api.retellai.com/"

pytestmark = [pytest.mark.provider_versions, pytest.mark.usefixtures("caller")]


def _agent_with_spec(
    db: Session, client: TestClient, user: User
) -> tuple[Agent, dict[str, str]]:
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
    data = _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}]).json()
    _with_key(db, user)
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
        retell.get(url__startswith=f"{RETELL}get-agent-versions/").mock(
            return_value=httpx.Response(200, json=[{"version": 15}])
        )
        retell.get(url__startswith=f"{RETELL}get-agent/").mock(
            return_value=httpx.Response(
                200,
                json={"response_engine": {"type": "retell-llm", "llm_id": "llm_1"}},
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
    assert (coverage["rules"], coverage["checked"], coverage["pct"]) == (2, 0, 0)
    # Critical first, each without a scenario.
    assert [(u["key"], u["why"]) for u in coverage["unchecked"]] == [
        (keys[PRICE], "no_scenario"),
        (keys[BOOKING], "no_scenario"),
    ]
    assert no_scenarios["scenarios"] == []

    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])
    not_run = _tab(client, cookies, agent).json()
    assert not_run["results"] is None
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
    # Listed but never run is still not checked: its scenario has not reached it.
    assert not_run["coverage"]["unchecked"][0]["why"] == "did_not_come_up"


def test_a_failed_version_with_its_calls_coverage_and_all_rules(
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
    assert tab["results"]["verdict"] == "failed"
    assert tab["results"]["version"] == "15"
    [failing] = tab["failing"]
    assert failing["key"] == keys[PRICE]
    assert failing["critical"] is True
    assert (failing["failed"], failing["judged"], failing["flaky"]) == (1, 1, False)
    assert failing["category"] == "Pricing and quotes"
    assert [c["outcome"] for c in failing["calls"]] == ["failed"]
    assert failing["calls"][0]["scenario_name"] == "Price pushback"
    assert failing["calls"][0]["repeat"] == 1

    coverage = tab["coverage"]
    assert (coverage["rules"], coverage["checked"], coverage["pct"]) == (2, 1, 50)
    assert [(u["key"], u["why"]) for u in coverage["unchecked"]] == [
        (keys[BOOKING], "did_not_come_up")
    ]
    rows = {r["key"]: r for g in tab["all_rules"] for r in g["rules"]}
    assert rows[keys[PRICE]]["failed"] == 1
    assert rows[keys[BOOKING]]["did_not_come_up"] == 1
    assert {g["category"] for g in tab["all_rules"]} == {
        "Booking",
        "Pricing and quotes",
    }
    assert len(tab["scenarios"]) == 2

    # The assistant reads the same coverage, with a step for the unchecked rule.
    body = _runs(client, user, agent).json()
    assert body["data"]["results"]["coverage"] == coverage
    assert any("checked 1 of the spec's 2 rules" in s for s in body["next_steps"])


def test_a_critical_rule_not_checked_is_a_next_step(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent, keys = _agent_with_spec(db, client, user)
    _scenarios(client, user, agent, _price(keys, rules=[keys[BOOKING]]))

    _run(client, user, agent, {keys[BOOKING]: "passed"})

    body = _runs(client, user, agent).json()
    assert body["data"]["results"]["verdict"] == "verified"
    assert any(
        f"1 critical rule was not checked ({keys[PRICE]})" in s
        for s in body["next_steps"]
    )


def test_a_code_check_with_its_calls(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _agent_with_spec(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    finding = SimulatedFinding.model_validate(
        {
            "check_type": "tool_call_failed",
            "check_version": 1,
            "kind": "rule",
            "mode": "flags",
            "key": "book_slot",
            "event_ids": ["t2-0"],
        }
    )

    _run(client, user, agent, {keys[PRICE]: "passed"}, findings=[finding])

    tab = _tab(client, cookies, agent).json()
    assert tab["results"]["verdict"] == "verified"
    assert tab["results"]["warnings"] == 1
    [check] = tab["failing_checks"]
    assert (check["check_type"], check["critical"], check["found"], check["of"]) == (
        "tool_call_failed",
        False,
        1,
        1,
    )
    assert check["calls"][0]["scenario_name"] == "Price pushback"
    assert check["calls"][0]["outcome"] is None
    assert tab["failing"] == []


def test_another_workspaces_agent_is_not_found(client: TestClient, db: Session) -> None:
    user, _ = _signed_in(client, db)
    agent = _agent(db, user, "Front desk")
    _, other = _signed_in(client, db)

    assert _tab(client, other, agent).status_code == 404
