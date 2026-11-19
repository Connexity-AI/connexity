"""A tested version's results across its runs, its verdict, and a simulated call on the
call screen, on invented agents with Retell and the model mocked (plan
`plans/2026-11-17-test-results.md`)."""

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
from app.models.run import Run
from app.models.test_case_result import TestCaseResult
from app.models.test_run import CheckTotalPublic, RuleTotalPublic
from app.services.test_run import WARNING_THRESHOLD_PCT, _verdict_of
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
    PRICE,
    _keys,
    _price,
    _scenarios,
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
    _call(db, agent, _booking(1, FULL), days_ago=1, version=7)
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
) -> str:
    """Start and make a run of every scenario against version 15 with ``prompt``."""
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]
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
            new=AsyncMock(return_value=_verdict(key, outcome)),
        ):
            if findings is None:
                _execute(run_id)
            else:
                with patch(
                    "app.services.test_run.check_simulated", return_value=findings
                ):
                    _execute(run_id)
    return run_id


def test_a_versions_results_add_up_its_runs_and_a_critical_failure_fails_it(
    client: TestClient, db: Session
) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))

    first = _run(client, user, agent, "passed", keys[PRICE])
    second = _run(client, user, agent, "failed", keys[PRICE])

    db.expire_all()
    runs = [db.get(Run, uuid.UUID(i)) for i in (first, second)]
    assert all(r is not None and r.platform_version == "15" for r in runs)
    assert runs[0].version_fingerprint == runs[1].version_fingerprint  # type: ignore[union-attr]
    assert runs[0].version_fingerprint  # type: ignore[union-attr]

    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    assert results["version"] == "15"
    assert results["edited"] is False
    assert results["verdict"] == "failed"
    assert results["critical_failed"] == [keys[PRICE]]
    assert results["rules"] == [
        {
            "key": keys[PRICE],
            "text": PRICE,
            "critical": True,
            "passed": 1,
            "failed": 1,
            "did_not_come_up": 0,
            "flaky": True,
        }
    ]
    assert [r["id"] for r in results["runs"]] == [second, first]
    assert body["next_steps"][0].startswith("Version 15 failed: critical rule")
    assert _runs(client, user, agent, version="15").json()["data"]["results"] == results
    assert _runs(client, user, agent, version="9").status_code == 404

    detail = _runs(client, user, agent, run_id=second).json()
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


def test_an_edited_draft_starts_new_results(client: TestClient, db: Session) -> None:
    user, cookies = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))

    _run(client, user, agent, "failed", keys[PRICE], prompt="Quote any price.")
    fixed = _run(client, user, agent, "passed", keys[PRICE], prompt="Never quote.")

    body = _runs(client, user, agent).json()
    results = body["data"]["results"]
    assert results["version"] == "15"
    assert results["edited"] is True
    assert results["verdict"] == "verified"
    assert [r["id"] for r in results["runs"]] == [fixed]
    assert results["rules"][0]["failed"] == 0
    assert any("edited under the same version number" in s for s in body["next_steps"])
    # Both runs are still listed.
    assert len(body["data"]["runs"]) == 2
    # The fixed run's simulated call says it tested an edited draft.
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

    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    data = client.get(f"{API}/calls/{call.id}/screen", cookies=cookies).json()
    assert data["result"] == "failed"
    assert data["findings"][0]["severity"] == "critical"
    assert data["findings"][0]["category"] == "Tools and integrations"
    assert data["entries"][2]["finding_ids"] == [data["findings"][0]["id"]]


def test_a_version_without_a_completed_run_is_not_tested(
    client: TestClient, db: Session
) -> None:
    user, _ = _signed_in(client, db)
    agent, keys = _ready(db, client, user)
    _scenarios(client, user, agent, _price(keys))
    _start(client, user, agent, all=True, repeats=1)

    body = _runs(client, user, agent).json()
    assert body["data"]["results"]["verdict"] == "not_tested"
    assert "no completed run" in body["next_steps"][0]


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


def _total(
    key: str, *, critical: bool = False, passed: int = 0, failed: int = 0
) -> Any:
    return RuleTotalPublic(
        key=key,
        critical=critical,
        passed=passed,
        failed=failed,
        flaky=bool(passed and failed),
    )


def test_the_verdict_counts_warnings_against_the_threshold() -> None:
    assert WARNING_THRESHOLD_PCT == 20
    five = [_total(f"r{n}", passed=1) for n in range(5)]

    one_failed = _verdict_of([*five[:4], _total("r4", failed=1)], [], tested=True)
    assert one_failed["verdict"] is VersionVerdict.VERIFIED
    assert one_failed["warnings"] == 1
    assert one_failed["over_threshold"] is False

    two_failed = _verdict_of(
        [*five[:3], _total("r3", failed=1), _total("r4", failed=2)], [], tested=True
    )
    assert two_failed["verdict"] is VersionVerdict.FAILED
    assert two_failed["over_threshold"] is True
    assert (two_failed["non_critical_failed"], two_failed["non_critical_judged"]) == (
        2,
        5,
    )

    # Didn't come up is not counted: a rule never judged is not in the share.
    unjudged = _verdict_of([*five, _total("r9")], [], tested=True)
    assert unjudged["non_critical_judged"] == 5

    flaky_critical = _verdict_of(
        [*five, _total("c", critical=True, passed=2, failed=1)], [], tested=True
    )
    assert flaky_critical["verdict"] is VersionVerdict.FAILED
    assert flaky_critical["critical_failed"] == ["c"]

    flagged = CheckTotalPublic(check_type="x", title="X", found=1, critical=False)
    warned = _verdict_of(five, [flagged], tested=True)
    assert warned["verdict"] is VersionVerdict.VERIFIED
    assert warned["warnings"] == 1

    assert _verdict_of([], [], tested=False)["verdict"] is VersionVerdict.NOT_TESTED
    # A completed run that judged no rule (every simulated call failed first) checked
    # nothing: never Verified (Dmytro, 2026-11-19).
    nothing = _verdict_of([_total("r0"), _total("r1")], [], tested=True)
    assert nothing["verdict"] is VersionVerdict.NOT_TESTED
    # With no rule judged there is no verdict, whatever the code checks found (Dmytro,
    # 2026-11-19: "Verdict only happens when all rules checked so not tested").
    critical = CheckTotalPublic(check_type="y", title="Y", found=1, critical=True)
    assert _verdict_of([], [critical], tested=True)["verdict"] is (
        VersionVerdict.NOT_TESTED
    )
    # With a rule judged, a critical code check fails it.
    judged = _verdict_of([_total("r0", passed=1)], [critical], tested=True)
    assert judged["verdict"] is VersionVerdict.FAILED
