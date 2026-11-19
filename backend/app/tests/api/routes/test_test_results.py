"""A version's verdict from its latest full run, the runs with their totals, and a
simulated call on the call screen, on invented agents with Retell and the model mocked
(plans `plans/2026-11-17-test-results.md`,
`plans/2026-11-19-tests-tab-runs-and-verified.md`)."""

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Agent, User
from app.models.enums import VersionVerdict
from app.models.test_case_result import TestCaseResult
from app.models.test_run import RunTotalsPublic
from app.services.test_run import _verdict as full_run_verdict
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
    _llm,
    _runs,
    _start,
    _verdict,
    caller,  # noqa: F401 - the simulated caller's model, mocked
)

RETELL = "https://api.retellai.com/"

# Retell's version reads are mocked here; the simulated caller's model too.
pytestmark = [pytest.mark.provider_versions, pytest.mark.usefixtures("caller")]


def _ready(db: Session, client: TestClient, user: User) -> tuple[Agent, dict[str, str]]:
    agent = _agent(db, user, "Front desk")
    _catalogue(db, agent, "7")
    # The agent is live on version 15, the version Retell answers below.
    _call(db, agent, _booking(1, FULL), days_ago=1, version=15)
    data = _write(client, user, agent, [RULES[0], RULES[1] | {"critical": True}]).json()
    return agent, _keys(data["data"])


def _run(
    client: TestClient,
    user: User,
    agent: Agent,
    outcome: str,
    key: str,
    *,
    prompt: str = "Greet the caller.",
    findings: Any = None,
    scope: dict[str, Any] | None = None,
    judge: Any = None,
) -> str:
    """Start and make a run (every scenario unless ``scope`` says otherwise) against
    version 15 with ``prompt``."""
    run_id = _start(client, user, agent, repeats=1, **(scope or {"all": True})).json()[
        "data"
    ]["run_id"]
    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
        retell.get(url__startswith=f"{RETELL}get-agent/").mock(
            return_value=httpx.Response(
                200,
                json={
                    "agent_name": "Front desk",
                    "version": 15,
                    "last_modification_timestamp": 1,
                    "response_engine": {
                        "type": "retell-llm",
                        "llm_id": "llm_1",
                        "version": 15,
                    },
                },
            )
        )
        retell.get(url__startswith=f"{RETELL}get-retell-llm/").mock(
            return_value=httpx.Response(
                200, json={"general_prompt": prompt, "model": "gpt-4.1", "version": 15}
            )
        )
        with patch(
            "app.services.rule_judge.call_llm",
            new=judge or AsyncMock(return_value=_verdict(key, outcome)),
        ):
            if findings is None:
                _execute(run_id)
            else:
                with patch(
                    "app.services.test_run.check_simulated", return_value=findings
                ):
                    _execute(run_id)
    return run_id


def _both(outcomes: dict[str, str]) -> AsyncMock:
    """A judge answering the price and booking rules with ``outcomes``."""
    return AsyncMock(
        return_value=_llm(
            json.dumps(
                {
                    "rules": [
                        {"key": k, "outcome": o, "reason": "x", "turns": [4]}
                        for k, o in outcomes.items()
                    ]
                }
            )
        )
    )


def test_a_full_run_decides_the_verdict_and_a_set_never_does(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    both = [keys[PRICE], keys[BOOKING]]
    scenario = _scenarios(client, user, agent, _price(keys, rules=both)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])

    # A set that fails a critical rule is on demand: no verdict yet.
    on_demand = _run(
        client,
        user,
        agent,
        "",
        "",
        scope={"set": "smoke"},
        judge=_both({keys[PRICE]: "failed", keys[BOOKING]: "passed"}),
    )
    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    assert results["version"] == "15"
    assert results["verdict"] == "not_verified"
    assert results["full_run"] is None
    row = results["runs"][0]
    assert (row["id"], row["full"], row["result"], row["verdict"]) == (
        on_demand,
        False,
        "failed",
        None,
    )
    assert row["totals"]["failed"] == 1 and row["totals"]["critical"] == 1
    assert row["ran_by"]
    assert "no completed full run" in body["next_steps"][0]

    # A full run checking both rules with nothing critical verifies the version.
    verified = _run(
        client,
        user,
        agent,
        "",
        "",
        judge=_both({keys[PRICE]: "passed", keys[BOOKING]: "passed"}),
    )
    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    assert results["verdict"] == "verified"
    assert results["full_run"]["id"] == verified
    assert results["full_run"]["totals"] == {
        "rules": 2,
        "passed": 2,
        "failed": 0,
        "did_not_come_up": 0,
        "no_scenario": 0,
        "not_judged": 0,
        "critical": 0,
        "judged_calls": 1,
        "stopped": 0,
    }
    assert [r["id"] for r in results["runs"]] == [verified, on_demand]
    assert results["coverage"]["pct"] == 100
    assert body["next_steps"][0].startswith("Version 15 is verified")

    # A non-critical failure still verifies it; a critical one fails it.
    _run(
        client,
        user,
        agent,
        "",
        "",
        judge=_both({keys[PRICE]: "passed", keys[BOOKING]: "failed"}),
    )
    assert _runs(client, user, agent).json()["data"]["results"]["verdict"] == "verified"
    failed = _run(
        client,
        user,
        agent,
        "",
        "",
        judge=_both({keys[PRICE]: "failed", keys[BOOKING]: "passed"}),
    )
    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    assert results["verdict"] == "failed"
    assert results["critical_failed"] == [keys[PRICE]]
    assert results["full_run"]["id"] == failed
    assert body["next_steps"][0].startswith("Version 15 failed in its full run")
    assert _runs(client, user, agent, version="15").json()["data"]["results"] == results
    assert _runs(client, user, agent, version="9").status_code == 404

    detail = _runs(client, user, agent, run_id=failed).json()
    call = detail["data"]["run"]["calls"][0]
    assert call["url"].endswith(f"/calls/{call['id']}")
    assert any("version 15" in s for s in detail["next_steps"])

    # The simulated call opens on the call screen, judged and failed.
    screen = client.get(f"{API}/calls/{call['id']}/screen", cookies=cookies)
    assert screen.status_code == 200, screen.text
    data = screen.json()
    assert data["result"] == "failed"
    assert data["has_recording"] is False
    assert data["version"] == "15"
    assert data["caller_last_four"] is None
    line = data["simulated"]
    assert line["scenario_name"] == "Price pushback"
    assert line["verdicts"][0]["key"] == keys[PRICE]
    assert line["verdicts"][0]["outcome"] == "failed"
    assert line["verdicts"][0]["critical"] is True
    assert line["verdicts"][0]["text"] == PRICE
    assert line["stopped"] is None
    entries = data["entries"]
    assert [e["kind"] for e in entries] == ["turn", "turn", "tool", "turn"]
    assert entries[2]["tool"] == "book_slot"
    assert entries[2]["status"] == "no result"
    # The verdict's turn 4 is the agent's price, the fourth entry.
    assert line["verdicts"][0]["entry_indexes"] == [3]


def test_a_rule_not_checked_in_the_full_run_leaves_it_partially_tested(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    # The scenario lists the price rule only: the booking rule has no scenario.
    _scenarios(client, user, agent, _price(keys))

    _run(client, user, agent, "passed", keys[PRICE])

    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    assert results["verdict"] == "partial"
    assert [(u["key"], u["why"]) for u in results["unchecked"]] == [
        (keys[BOOKING], "no_scenario")
    ]
    assert results["full_run"]["totals"]["no_scenario"] == 1
    assert results["coverage"]["covered"] == 1 and results["coverage"]["pct"] == 50
    assert body["next_steps"][0].startswith("Version 15 is partially tested")


def test_an_edited_draft_shows_on_its_simulated_call(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))

    _run(client, user, agent, "failed", keys[PRICE], prompt="Quote any price.")
    fixed = _run(client, user, agent, "passed", keys[PRICE], prompt="Never quote.")

    # The latest full run decides, whatever an earlier draft did.
    results = _runs(client, user, agent).json()["data"]["results"]
    assert results["full_run"]["id"] == fixed
    assert results["critical_failed"] == []
    call = _runs(client, user, agent, run_id=fixed).json()["data"]["run"]["calls"][0]
    data = client.get(f"{API}/calls/{call['id']}/screen", cookies=cookies).json()
    assert data["simulated"]["edited"] is True


def test_a_critical_code_check_fails_the_version_and_its_call(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    finding = {
        "check_type": "tool_call_failed",
        "check_version": 1,
        "kind": "code_based",
        "mode": "fails",
        "key": "book_slot",
        "event_ids": ["t2-0"],
    }
    from app.models.test_run import SimulatedFinding

    run_id = _run(
        client,
        user,
        agent,
        "passed",
        keys[PRICE],
        findings=[SimulatedFinding.model_validate(finding)],
    )

    results = _runs(client, user, agent).json()["data"]["results"]
    assert results["verdict"] == "failed"
    assert results["critical_checks"] == ["tool_call_failed"]
    assert results["checks"][0]["critical"] is True
    assert results["full_run"]["totals"]["critical"] == 1

    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    data = client.get(f"{API}/calls/{call.id}/screen", cookies=cookies).json()
    assert data["result"] == "failed"
    assert data["findings"][0]["severity"] == "critical"
    assert data["findings"][0]["category"] == "Tools and integrations"
    assert data["entries"][2]["finding_ids"] == [data["findings"][0]["id"]]


def test_a_version_not_live_yet_is_verified_with_the_live_one_beside_it(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    both = [keys[PRICE], keys[BOOKING]]
    _scenarios(client, user, agent, _price(keys, rules=both))
    _run(
        client,
        user,
        agent,
        "",
        "",
        judge=_both({keys[PRICE]: "passed", keys[BOOKING]: "passed"}),
    )
    # The agent's latest call is on 14: 15, the version tested, is not live yet.
    _call(db, agent, _booking(2, FULL), days_ago=0, version=14)

    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    # The gate tests before going live: a full run verifies a version not live yet.
    assert (results["version"], results["verdict"]) == ("15", "verified")
    assert results["live_version"] == "14"
    assert results["live"]["version"] == "14"
    assert results["live"]["verdict"] == "not_verified"
    assert any("The live version is 14" in s for s in body["next_steps"])


def test_a_version_whose_full_run_is_still_going_is_not_verified(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    _start(client, user, agent, all=True, repeats=1)

    body = _runs(client, user, agent).json()
    assert body["data"]["results"]["verdict"] == "not_verified"
    assert body["data"]["results"]["runs"][0]["status"] == "pending"
    assert "no completed full run" in body["next_steps"][0]


def test_another_workspaces_simulated_call_is_not_found(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    run_id = _run(client, user, agent, "passed", keys[PRICE])
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()

    _, other = _signed_in(client, db)
    assert client.get(f"{API}/calls/{call.id}/screen", cookies=other).status_code == 404
    assert (
        client.get(f"{API}/calls/{uuid.uuid4()}/screen", cookies=other).status_code
        == 404
    )


def test_a_stopped_conversation_is_not_judged_on_screen(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

    def broken(request: httpx.Request) -> httpx.Response:
        if not json.loads(request.content)["messages"]:
            return httpx.Response(
                200, json={"messages": [{"role": "agent", "content": "Hi."}]}
            )
        return httpx.Response(200, json={"messages": []})

    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=broken)
        with patch(
            "app.services.rule_judge.call_llm", new=AsyncMock(return_value=_llm(""))
        ):
            _execute(run_id)

    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    data = client.get(f"{API}/calls/{call.id}/screen", cookies=cookies).json()
    assert data["result"] == "unchecked"
    assert data["simulated"]["verdicts"] == []
    assert data["simulated"]["stopped"] == (
        "The conversation stopped: Retell returned no messages"
    )
    assert data["simulated"]["edited"] is False


def test_a_full_runs_verdict() -> None:
    def totals(**counts: int) -> RunTotalsPublic:
        return RunTotalsPublic(rules=3, **counts)

    assert full_run_verdict(totals(passed=3)) is VersionVerdict.VERIFIED
    # Non-critical failures never fail it (Dmytro, 2026-11-19).
    assert full_run_verdict(totals(passed=1, failed=2)) is VersionVerdict.VERIFIED
    assert (
        full_run_verdict(totals(passed=2, failed=1, critical=1))
        is VersionVerdict.FAILED
    )
    assert (
        full_run_verdict(totals(passed=2, did_not_come_up=1)) is VersionVerdict.PARTIAL
    )
    assert full_run_verdict(totals(passed=2, no_scenario=1)) is VersionVerdict.PARTIAL
    # Nothing judged: no verdict, whatever the code checks found.
    assert (
        full_run_verdict(totals(critical=1, stopped=3)) is VersionVerdict.NOT_VERIFIED
    )
