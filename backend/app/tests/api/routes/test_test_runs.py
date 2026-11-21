"""Running scenarios in text through MCP: starting a run, the simulated calls against
Retell's playground with every tool faked, the judge's rule verdicts, code checks on the
conversation, and reading runs back, on invented agents with Retell and the model
mocked (plan `plans/2026-11-17-text-runner.md`)."""

import asyncio
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app.crud.test_run import fail_stale_runs
from app.models import Agent, User
from app.models.call import Call
from app.models.check import Finding
from app.models.enums import Platform, RunStatus, ToolCallStatus
from app.models.run import Run
from app.models.test_case_result import TestCaseResult
from app.models.test_run import RuleVerdict
from app.services import test_run as runner
from app.services.call_screen import simulated_call_screen
from app.services.eval_runtimes.text.retell import DEFAULT_FAKE_RESULT
from app.services.llm import LLMResponse
from app.tests.api.routes.test_mcp_issues import (  # noqa: F401
    _headers,
    _settings,  # the autouse fixture that sets an encryption key
)
from app.tests.api.routes.test_scenarios import (
    BOOKING,
    PRICE,
    _base,
    _price,
    _ready,
    _scenarios,
    _set,
)

PLAYGROUND = "https://api.retellai.com/agent-playground-completion/"


def _start(client: TestClient, user: User, agent: Agent, **body: Any) -> Any:
    """Start a run. Without `version`, on version 15; with `version=None`, the version
    is read from Retell, which the test mocks."""
    if "version" not in body:
        body["version"] = 15
    elif body["version"] is None:
        del body["version"]
    with patch("app.api.routes.mcp.launch") as launch:
        r = client.post(
            f"{_base(user, agent)}/test-runs", headers=_headers(user), json=body
        )
    if r.status_code == 200:
        launch.assert_called_once()
    else:
        launch.assert_not_called()
    return r


def _runs(
    client: TestClient, user: User, agent: Agent, *, read: bool = False, **params: Any
) -> Any:
    """Read runs. The version's content on Retell is not read (as when Retell does not
    answer) unless ``read``, and then the test mocks Retell."""
    url = f"{_base(user, agent)}/test-runs"
    if read:
        return client.get(url, headers=_headers(user), params=params)
    with patch("app.api.routes.mcp.read_content_now", return_value=None):
        return client.get(url, headers=_headers(user), params=params)


def _llm(content: str) -> LLMResponse:
    return LLMResponse(content=content, model="invented-model", response_cost_usd=0.001)


def _verdict(key: str, outcome: str, turns: list[int] | None = None) -> LLMResponse:
    """The judge's answer for one rule. It rests on turn 1 unless told otherwise:
    before the tool the scenario does not fake answers (turn 3 of ``_agent_turn``)."""
    return _llm(
        json.dumps(
            {
                "rules": [
                    {
                        "key": key,
                        "reason": "Said 80.",
                        "turns": turns or [1],
                        "outcome": outcome,
                    }
                ]
            }
        )
    )


def _agent_turn(request: httpx.Request) -> httpx.Response:
    """Retell: the greeting first, then a tool call the scenario does not fake, its
    default result, a price, and the end of the call."""
    if not json.loads(request.content)["messages"]:
        return httpx.Response(
            200,
            json={"messages": [{"role": "agent", "content": "Hello, dental clinic."}]},
        )
    return httpx.Response(
        200,
        json={
            "messages": [
                {
                    "role": "tool_call_invocation",
                    "tool_call_id": "tc1",
                    "name": "book_slot",
                    "arguments": json.dumps({"date": "2026-12-01"}),
                },
                {
                    "role": "tool_call_result",
                    "tool_call_id": "tc1",
                    "content": DEFAULT_FAKE_RESULT,
                },
                {"role": "agent", "content": "A cleaning costs 80 dollars."},
            ],
            "call_ended": True,
        },
    )


RETELL = "https://api.retellai.com"


BOOK_SLOT_SCHEMA = {
    "type": "object",
    "properties": {
        "date": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
    },
    "required": ["date", "name"],
}


def _tested_version(
    retell: respx.MockRouter,
    number: int,
    prompt: str = "Invented prompt.",
    book_slot_schema: dict[str, Any] | None = None,
) -> None:
    """Retell: the agent at its latest version, a single prompt with two tools of its
    own and a hang-up."""
    retell.get(url__startswith=f"{RETELL}/get-agent/").mock(
        return_value=httpx.Response(
            200,
            json={
                "agent_id": "agent_x",
                "version": number,
                "response_engine": {
                    "type": "retell-llm",
                    "llm_id": "llm_x",
                    "version": number,
                },
            },
        )
    )
    retell.get(url__startswith=f"{RETELL}/get-retell-llm/").mock(
        return_value=httpx.Response(
            200,
            json={
                "llm_id": "llm_x",
                "general_prompt": prompt,
                "general_tools": [
                    {"type": "custom", "name": "check_slot"},
                    {"type": "end_call", "name": "end_call"},
                ],
                "states": [
                    {
                        "name": "booking",
                        "tools": [
                            {"type": "custom", "name": "book_slot"}
                            | (
                                {"parameters": book_slot_schema}
                                if book_slot_schema
                                else {}
                            )
                        ],
                    }
                ],
            },
        )
    )


@pytest.fixture
def caller() -> Iterator[AsyncMock]:
    with patch(
        "app.services.user_simulator.call_llm",
        new=AsyncMock(return_value=_llm("How much is a cleaning?")),
    ) as mock:
        yield mock


def _execute(run_id: str) -> None:
    asyncio.run(runner.execute_run(uuid.UUID(run_id)))


def _counts(db: Session, agent: Agent) -> tuple[int, int]:
    calls = db.exec(
        select(func.count()).select_from(Call).where(Call.agent_id == agent.id)
    ).one()
    findings = db.exec(
        select(func.count()).select_from(Finding).where(Finding.agent_id == agent.id)
    ).one()
    return calls, findings


def test_a_set_runs_every_repeat_with_every_tool_faked_and_judges_listed_rules(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    _set(client, user, agent, "smoke", [scenario["id"]])
    before = _counts(db, agent)

    r = _start(client, user, agent, set="smoke", repeats=2, version=4)

    assert r.status_code == 200, r.text
    started = r.json()
    assert started["data"]["calls"] == 2
    assert any("get_test_runs" in step for step in started["next_steps"])
    run_id = started["data"]["run_id"]
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None
    assert (run.status, run.scope, run.set_name, run.repeats) == (
        RunStatus.PENDING,
        "set",
        "smoke",
        2,
    )
    assert run.platform_version == "4"

    judge = AsyncMock(
        side_effect=[_verdict(keys[PRICE], "passed"), _verdict(keys[PRICE], "failed")]
    )
    with respx.mock(assert_all_called=True) as retell:
        route = retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
        with patch("app.services.rule_judge.call_llm", new=judge):
            _execute(run_id)

    # Every request names the version, the agent's variables and the fakes, with the
    # scenario's own fake first and the catch-all for every other tool last.
    for call in route.calls:
        sent = json.loads(call.request.content)
        assert call.request.url.params["version"] == "4"
        assert sent["dynamic_variables"] == {"clinic_hours": "9 to 5"}
        assert sent["tool_mocks"] == [
            {
                "tool_name": "check_slot",
                "input_match_rule": {"type": "partial_match", "args": {"date": None}},
                "output": json.dumps({"available": True}),
            },
            {"input_match_rule": {"type": "any"}, "output": DEFAULT_FAKE_RESULT},
        ]
    # The simulated caller is told the goal and behaviour, never the rules.
    prompt = caller.call_args.args[0][0].content
    assert "Find out what the cleaning costs" in prompt
    assert "Insists on a number" in prompt
    assert PRICE not in prompt
    # The judge reads the listed rule only.
    judged = judge.call_args.args[0][1].content
    assert PRICE in judged and BOOKING not in judged
    assert "book_slot" in judged
    # Both run on Claude, on Connexity's own key: the workspace has none.
    for model_call in (caller, judge):
        config = model_call.call_args.kwargs["config"]
        assert (config.model, config.provider) == ("claude-haiku-5-5", "anthropic")

    db.expire_all()
    assert db.get(Run, uuid.UUID(run_id)).status == RunStatus.COMPLETED  # type: ignore[union-attr]
    calls = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).all()
    assert len(calls) == 2
    for call in calls:
        assert call.transcript and call.error_message is None
        assert call.default_fakes == ["book_slot"]
        # The default fake is no result, not a failed tool: no code-check finding.
        assert call.check_findings == []
    verdicts = db.exec(
        select(RuleVerdict).where(RuleVerdict.run_id == uuid.UUID(run_id))
    ).all()
    assert sorted(v.outcome for v in verdicts) == ["failed", "passed"]
    assert all(v.rule_key == keys[PRICE] and v.critical for v in verdicts)
    # Nothing reached production calls or findings.
    assert _counts(db, agent) == before

    body = _runs(client, user, agent, run_id=run_id).json()
    detail = body["data"]["run"]
    assert detail["status"] == "completed"
    assert detail["rules"] == [
        {
            "key": keys[PRICE],
            "text": PRICE,
            "critical": True,
            "passed": 1,
            "failed": 1,
            "did_not_come_up": 0,
            "default_fake": 0,
            "flaky": True,
        }
    ]
    assert detail["counts"] == {
        "calls": 2,
        "queued": 0,
        "running": 0,
        "started": 2,
        "finished": 2,
        "errors": 0,
        "judge_errors": 0,
        "rules_failed": 1,
        "critical_failed": 1,
        "flaky": 1,
        "findings": 0,
    }
    assert detail["spec_version"] == 1
    assert {c["repeat"] for c in detail["calls"]} == {1, 2}
    assert detail["calls"][0]["scenario_name"] == "Price pushback"
    steps = " ".join(body["next_steps"])
    assert "1 critical rule failed" in steps
    assert "flaky" in steps
    assert "book_slot" in steps


@pytest.mark.provider_versions
def test_a_failed_tool_fake_is_found_by_code_checks_but_never_in_production(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    before = _counts(db, agent)
    # The version is read from Retell before the run is stored.
    with respx.mock(assert_all_called=False) as reading:
        _tested_version(reading, 5)
        run_id = _start(client, user, agent, all=True, repeats=1, version=None).json()[
            "data"
        ]["run_id"]

    def failing(request: httpx.Request) -> httpx.Response:
        if not json.loads(request.content)["messages"]:
            return httpx.Response(
                200, json={"messages": [{"role": "agent", "content": "Hi."}]}
            )
        return httpx.Response(
            200,
            json={
                "messages": [
                    {
                        "role": "tool_call_invocation",
                        "tool_call_id": "tc1",
                        "name": "check_slot",
                        "arguments": json.dumps({"date": None, "time": "9:00"}),
                    },
                    {
                        "role": "tool_call_result",
                        "tool_call_id": "tc1",
                        "content": "{}",
                    },
                    {"role": "agent", "content": "Sorry."},
                ],
                "call_ended": True,
            },
        )

    real = runner.check_simulated

    def found_failed(trace: Any, modes: Any) -> Any:
        # The real checks, on the trace with the fake's result marked as an error.
        return real(
            trace.model_copy(
                update={
                    "events": [
                        e.model_copy(update={"status": ToolCallStatus.ERROR})
                        if e.type == "tool_call"
                        else e
                        for e in trace.events
                    ]
                }
            ),
            modes,
        )

    with respx.mock() as retell:
        playground = retell.post(url__startswith=PLAYGROUND).mock(side_effect=failing)
        _tested_version(retell, 5)
        with (
            patch(
                "app.services.rule_judge.call_llm",
                new=AsyncMock(return_value=_verdict(keys[PRICE], "did_not_come_up")),
            ),
            patch("app.services.test_run.check_simulated", side_effect=found_failed),
        ):
            _execute(run_id)

    db.expire_all()
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    assert [f["check_type"] for f in call.check_findings or []] == ["tool_call_failed"]
    # The call matched the scenario's own fake, so no default fake was used.
    assert call.default_fakes == []
    # "The latest" was pinned to a number read from the agent, and every request used
    # it.
    assert {c.request.url.params["version"] for c in playground.calls} == {"5"}
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None and run.platform_version == "5"
    assert _counts(db, agent) == before
    body = _runs(client, user, agent, run_id=run_id).json()
    detail = body["data"]["run"]
    assert detail["checks"] == [
        {
            "check_type": "tool_call_failed",
            "title": "Tool call failed",
            "found": 1,
            "critical": True,
        }
    ]
    assert detail["rules"][0]["did_not_come_up"] == 1
    assert detail["counts"]["rules_failed"] == 0
    assert detail["platform_version"] == "5"
    assert any("do not count as production" in s for s in body["next_steps"])


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(500, json={"error": "invented outage"}),
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, json={"messages": []}),
        httpx.TimeoutException("timed out"),
    ],
    ids=["error", "malformed", "empty", "timeout"],
)
def test_a_platform_failure_is_an_error_with_no_verdicts(
    client: TestClient, db: Session, caller: AsyncMock, answer: Any
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

    def reply(request: httpx.Request) -> httpx.Response:
        if not json.loads(request.content)["messages"]:
            return httpx.Response(
                200, json={"messages": [{"role": "agent", "content": "Hi."}]}
            )
        if isinstance(answer, Exception):
            raise answer
        return answer

    judge = AsyncMock()
    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=reply)
        with (
            patch("app.services.rule_judge.call_llm", new=judge),
            patch("app.services.retell.asyncio.sleep", new=AsyncMock()),
        ):
            _execute(run_id)

    judge.assert_not_called()
    db.expire_all()
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    assert call.error_message and call.error_message.startswith(
        "The conversation stopped"
    )
    assert call.completed_at is not None
    assert not db.exec(
        select(RuleVerdict).where(RuleVerdict.run_id == uuid.UUID(run_id))
    ).all()
    # The version's results say the calls stopped, why, and which run to open.
    results = _runs(client, user, agent).json()
    assert results["data"]["results"]["verdict"] == "not_verified"
    stopped = results["data"]["results"]["stopped"]
    assert stopped["calls"] == 1 and stopped["run_id"] == run_id
    assert stopped["reason"].startswith("The conversation stopped")
    assert any("stopped with an error" in s for s in results["next_steps"])
    body = _runs(client, user, agent, run_id=run_id).json()
    assert body["data"]["run"]["counts"]["errors"] == 1
    assert any("No result" in s for s in body["next_steps"])
    # The run completed but judged no rule: the version is not verified.
    results = _runs(client, user, agent).json()
    assert results["data"]["results"]["verdict"] == "not_verified"
    assert "judged no rule" in results["next_steps"][0]


@pytest.mark.parametrize(
    ("answer", "error"),
    [
        (_llm("not json"), "The judge did not answer JSON"),
        (_llm(""), "The judge did not answer JSON"),
        (_llm(json.dumps({"rules": []})), "The judge did not answer "),
        (httpx.TimeoutException("timed out"), "The judge's model call failed"),
        (
            ValueError("`temperature` is deprecated for this model."),
            "The judge's model call failed: `temperature` is deprecated",
        ),
    ],
    ids=["malformed", "empty", "missing-rule", "timeout", "refused"],
)
def test_a_judge_answer_it_cannot_read_gives_no_verdicts(
    client: TestClient, db: Session, caller: AsyncMock, answer: Any, error: str
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=_agent_turn)
        with patch(
            "app.services.rule_judge.call_llm",
            new=AsyncMock(side_effect=[answer]),
        ):
            _execute(run_id)

    db.expire_all()
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    assert call.error_message and call.error_message.startswith(error)
    assert call.transcript
    assert not db.exec(
        select(RuleVerdict).where(RuleVerdict.run_id == uuid.UUID(run_id))
    ).all()


def test_refusals_store_nothing(client: TestClient, db: Session) -> None:
    user, agent, keys = _ready(db, client)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]

    def runs() -> int:
        return db.exec(
            select(func.count()).select_from(Run).where(Run.agent_id == agent.id)
        ).one()

    both = _start(client, user, agent, all=True, scenario_ids=[scenario["id"]])
    assert both.status_code == 422
    assert "exactly one" in both.json()["detail"]["error"]
    unknown = _start(client, user, agent, scenario_ids=[str(uuid.uuid4())])
    assert unknown.status_code == 422
    assert "Unknown or archived" in " ".join(unknown.json()["detail"]["next_steps"])
    no_set = _start(client, user, agent, set="nightly")
    assert no_set.status_code == 422
    too_many = _start(client, user, agent, all=True, repeats=6)
    assert too_many.status_code == 422
    with patch.object(runner, "MAX_CALLS", 1):
        over = _start(client, user, agent, all=True, repeats=2)
    assert over.status_code == 422
    assert "2 simulated calls" in over.json()["detail"]["error"]

    agent.platform = Platform.VAPI
    db.add(agent)
    db.commit()
    other = _start(client, user, agent, all=True)
    assert other.status_code == 422
    assert "Retell" in other.json()["detail"]["error"]
    assert runs() == 0


def test_an_agent_without_scenarios_or_spec_is_refused(
    client: TestClient, db: Session
) -> None:
    user, agent, _ = _ready(db, client)

    r = _start(client, user, agent, all=True)

    assert r.status_code == 422
    assert "no active scenarios" in r.json()["detail"]["error"]


def test_runs_are_listed_newest_first_by_page_and_scoped_to_the_agent(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    first = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]
    second = _start(
        client, user, agent, scenario_ids=[scenario["id"]], repeats=3
    ).json()["data"]["run_id"]

    page = _runs(client, user, agent, limit=1).json()
    assert [r["id"] for r in page["data"]["runs"]] == [second]
    assert page["data"]["runs"][0]["scope"] == "pick"
    assert page["data"]["runs"][0]["counts"]["calls"] == 3
    assert page["next_cursor"]
    rest = _runs(client, user, agent, limit=1, cursor=page["next_cursor"]).json()
    assert [r["id"] for r in rest["data"]["runs"]] == [first]

    pending = _runs(client, user, agent, run_id=second).json()
    assert pending["data"]["run"]["status"] == "pending"
    assert "Still running: 0 of 3" in pending["next_steps"][0]
    paged = _runs(client, user, agent, run_id=second, limit=2).json()
    assert len(paged["data"]["run"]["calls"]) == 2 and paged["next_cursor"]

    missing = _runs(client, user, agent, run_id=str(uuid.uuid4()))
    assert missing.status_code == 404

    other_user, other_agent, _ = _ready(db, client)
    foreign = client.get(
        f"{_base(other_user, other_agent)}/test-runs",
        headers=_headers(other_user),
        params={"run_id": first},
    )
    assert foreign.status_code == 404


def _age(db: Session, run_id: str, minutes: int, status: RunStatus) -> Run:
    """Make the run look as if its server last gave a sign of life ``minutes`` ago."""
    db.expire_all()
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None
    run.status = status
    run.started_at = run.heartbeat_at = datetime.now(UTC) - timedelta(minutes=minutes)
    db.add(run)
    db.commit()
    return run


def test_a_run_whose_server_stopped_is_failed_and_a_live_one_is_left_alone(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    live = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]
    dead = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]
    _age(db, live, 1, RunStatus.RUNNING)
    _age(db, dead, 16, RunStatus.RUNNING)

    # A server starting beside a live run does not fail it.
    assert fail_stale_runs(session=db, agent_id=agent.id) == 1

    db.expire_all()
    assert db.get(Run, uuid.UUID(live)).status == RunStatus.RUNNING  # type: ignore[union-attr]
    run = db.get(Run, uuid.UUID(dead))
    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.status_detail and "server running it stopped" in run.status_detail
    assert run.completed_at is not None
    # A failed run is not started again.
    _execute(dead)
    db.expire_all()
    assert db.get(Run, uuid.UUID(dead)).status == RunStatus.FAILED  # type: ignore[union-attr]


def test_polling_a_run_is_cheap_and_says_how_far_it_is(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=2).json()["data"]["run_id"]

    # No Retell mock: a poll never asks the platform.
    r = _runs(client, user, agent, read=True, run_id=run_id, status_only="true")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["run"] is None and body["data"]["results"] is None
    status = body["data"]["status"]
    assert status["status"] == "pending"
    assert status["progress"] == {
        "calls": 2,
        "queued": 2,
        "running": 0,
        "started": 0,
        "finished": 0,
        "errors": 0,
        "judge_errors": 0,
    }
    assert status["stalled"] is False
    assert len(r.content) < 2048 + len(json.dumps(body["rules"]))
    assert (
        "0 of 2 simulated calls finished, 0 running, 2 queued" in body["next_steps"][0]
    )
    assert "`status_only`" in body["next_steps"][0]
    # The full read of a run in progress points at the cheap one too.
    full = _runs(client, user, agent, run_id=run_id).json()
    assert "`status_only`" in full["next_steps"][0]

    # Without a run there is nothing to poll.
    refused = _runs(client, user, agent, status_only="true")
    assert refused.status_code == 422
    assert "run_id" in refused.json()["detail"]["error"]


def test_a_run_with_no_sign_of_life_is_stalled_then_failed(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

    _age(db, run_id, 1, RunStatus.RUNNING)
    alive = _runs(client, user, agent, run_id=run_id, status_only="true").json()
    assert alive["data"]["status"]["stalled"] is False

    _age(db, run_id, 3, RunStatus.RUNNING)
    body = _runs(client, user, agent, run_id=run_id, status_only="true").json()
    status = body["data"]["status"]
    assert (status["status"], status["stalled"]) == ("running", True)
    assert status["stalled_since"] is not None
    assert body["next_steps"][0].startswith("Stalled:")
    assert _runs(client, user, agent, run_id=run_id).json()["data"]["run"]["stalled"]

    _age(db, run_id, 16, RunStatus.RUNNING)
    body = _runs(client, user, agent, run_id=run_id, status_only="true").json()
    status = body["data"]["status"]
    assert (status["status"], status["stalled"]) == ("failed", False)
    assert "server running it stopped" in status["status_detail"]
    # Nothing is running in a run that stopped.
    assert (status["progress"]["queued"], status["progress"]["running"]) == (0, 0)
    assert "Start it again" in body["next_steps"][0]


def test_a_run_without_connexitys_model_key_is_refused(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    monkeypatch.setattr(runner.settings, "ANTHROPIC_API_KEY", None)

    r = _start(client, user, agent, all=True)

    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "model key is missing" in detail["error"]
    assert any("nothing for you to fix" in s for s in detail["next_steps"])
    assert not db.exec(select(Run).where(Run.agent_id == agent.id)).all()


@pytest.mark.provider_versions
def test_a_hang_up_ends_the_conversation_and_it_is_judged(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    # The version is read from Retell before the run is stored.
    with respx.mock(assert_all_called=False) as reading:
        _tested_version(reading, 88)
        run_id = _start(client, user, agent, all=True, repeats=1, version=None).json()[
            "data"
        ]["run_id"]

    def hangs_up(request: httpx.Request) -> httpx.Response:
        if not json.loads(request.content)["messages"]:
            return httpx.Response(
                200, json={"messages": [{"role": "agent", "content": "Hello."}]}
            )
        # The agent says goodbye and calls its hang-up tool. Retell does not report
        # the chat ended (the catch-all may answer the hang-up): the tool call, which
        # the tested version marks as ending the call, ends it.
        return httpx.Response(
            200,
            json={
                "messages": [
                    {"role": "agent", "content": "A cleaning is 80 dollars. Bye."},
                    {
                        "role": "tool_call_invocation",
                        "tool_call_id": "tc9",
                        "name": "end_call",
                        "arguments": "{}",
                    },
                ]
            },
        )

    judge = AsyncMock(return_value=_verdict(keys[PRICE], "passed"))
    with respx.mock() as retell:
        playground = retell.post(url__startswith=PLAYGROUND).mock(side_effect=hangs_up)
        _tested_version(retell, 88)
        with patch("app.services.rule_judge.call_llm", new=judge):
            _execute(run_id)

    # The greeting, then one exchange: the hang-up ended it.
    assert playground.call_count == 2
    judge.assert_awaited_once()
    db.expire_all()
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    assert call.error_message is None
    assert "end_call" not in (call.default_fakes or [])
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None and run.platform_version == "88"


def test_a_conversation_ends_at_the_turn_limit_and_is_judged(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    with patch.object(runner, "MAX_AGENT_REPLIES", 3):
        run_id = _start(client, user, agent, all=True, repeats=1).json()["data"][
            "run_id"
        ]

    def never_ends(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"messages": [{"role": "agent", "content": "Anything else?"}]}
        )

    judge = AsyncMock(return_value=_verdict(keys[PRICE], "did_not_come_up"))
    with respx.mock() as retell:
        playground = retell.post(url__startswith=PLAYGROUND).mock(
            side_effect=never_ends
        )
        with patch("app.services.rule_judge.call_llm", new=judge):
            _execute(run_id)

    # The greeting and two more replies make three; a fourth never happens.
    assert playground.call_count == 3
    judge.assert_awaited_once()
    db.expire_all()
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(run_id))
    ).one()
    assert call.error_message is None
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None and run.platform_version == "15"
    assert run.config["max_turns"] == 3
    sent = json.loads(playground.calls[0].request.content)["tool_mocks"]
    assert sent[-1] == {
        "input_match_rule": {"type": "any"},
        "output": DEFAULT_FAKE_RESULT,
    }


def test_the_same_error_on_many_calls_counts_as_one() -> None:
    def failed(message: str) -> TestCaseResult:
        return TestCaseResult(
            run_id=uuid.uuid4(),
            test_case_id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            error_message=message,
        )

    judge = 'The judge\'s model call failed: 400 {{"request_id":"req_{}"}}'
    calls = [
        failed(judge.format("011AAA")),
        failed(judge.format("011BBB")),
        failed("The conversation stopped: Retell returned no messages"),
    ]

    stopped = runner.stopped_calls(calls)

    assert stopped is not None
    assert stopped.calls == 3
    assert stopped.reason.startswith("The judge's model call failed")


def test_a_run_says_who_ran_it_and_whether_it_decides_the_verdict(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]

    full = _start(client, user, agent, all=True, repeats=1, session="Testing")
    on_demand = _start(client, user, agent, scenario_ids=[scenario["id"]], repeats=1)

    assert full.status_code == 200, full.text
    assert any("full run" in s for s in full.json()["next_steps"])
    assert any("on-demand run" in s for s in on_demand.json()["next_steps"])
    run = db.get(Run, uuid.UUID(full.json()["data"]["run_id"]))
    assert run is not None
    assert (run.session_name, run.created_by) == ("Testing", user.id)
    rows = {r["id"]: r for r in _runs(client, user, agent).json()["data"]["runs"]}
    row = rows[str(run.id)]
    assert (row["full"], row["session_name"]) == (True, "Testing")
    assert row["ran_by"] == (user.full_name or user.email)


def test_a_run_whose_version_cannot_be_read_is_refused(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))

    # Retell cannot be read (tests never reach it): nothing is stored.
    r = _start(client, user, agent, all=True, version=None)

    assert r.status_code == 422
    assert "Could not read the agent's version" in r.json()["detail"]["error"]
    assert not db.exec(select(Run).where(Run.agent_id == agent.id)).all()


def test_a_run_of_scenarios_cannot_be_stored_without_a_version(
    client: TestClient, db: Session
) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.models.enums import RunScope

    _user, agent, _keys = _ready(db, client)
    db.add(
        Run(
            agent_id=agent.id,
            company_id=agent.company_id,
            scope=RunScope.ALL,
            repeats=1,
            status=RunStatus.PENDING,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_a_run_whose_calls_all_stopped_has_no_result(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=2).json()["data"]["run_id"]

    def broken(request: httpx.Request) -> httpx.Response:
        if not json.loads(request.content)["messages"]:
            return httpx.Response(
                200, json={"messages": [{"role": "agent", "content": "Hi."}]}
            )
        return httpx.Response(200, json={"messages": []})

    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(side_effect=broken)
        _execute(run_id)

    body = _runs(client, user, agent).json()
    [row] = [r for r in body["data"]["runs"] if r["id"] == run_id]
    totals = row["totals"]
    # The price rule only stopped calls listed: it counts in no column.
    assert (totals["passed"], totals["failed"], totals["did_not_come_up"]) == (0, 0, 0)
    assert totals["not_judged"] == 1 and totals["judged_calls"] == 0
    assert totals["stopped"] == 2
    assert row["verdict"] == "not_verified" and row["result"] is None
    detail = _runs(client, user, agent, run_id=run_id).json()
    assert detail["next_steps"][0].startswith("No result")


def _made(
    client: TestClient,
    user: User,
    agent: Agent,
    judge: AsyncMock,
    *,
    version: int = 15,
    repeats: int = 1,
    agent_turn: Any = None,
    book_slot_schema: dict[str, Any] | None = None,
    readable: bool = True,
    **scope: Any,
) -> str:
    """Start a run of ``version`` and make it, with Retell's version read mocked."""
    run_id = _start(
        client,
        user,
        agent,
        repeats=repeats,
        version=version,
        **(scope or {"all": True}),
    ).json()["data"]["run_id"]
    with respx.mock() as retell:
        retell.post(url__startswith=PLAYGROUND).mock(
            side_effect=agent_turn or _agent_turn
        )
        if readable:
            _tested_version(retell, version, book_slot_schema=book_slot_schema)
        else:
            retell.get(url__startswith=f"{RETELL}/get-agent/").mock(
                return_value=httpx.Response(500)
            )
        with patch("app.services.rule_judge.call_llm", new=judge):
            _execute(run_id)
    return run_id


@pytest.mark.provider_versions
def test_a_verdict_that_rests_on_a_default_fake_is_marked_and_not_counted(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    # The judge fails the critical price rule on turn 4, after `book_slot`, which the
    # scenario does not fake, answered with the default fake on turn 3.
    judge = AsyncMock(return_value=_verdict(keys[PRICE], "failed", turns=[4]))

    run_id = _made(client, user, agent, judge)

    db.expire_all()
    stored = db.exec(
        select(RuleVerdict).where(RuleVerdict.run_id == uuid.UUID(run_id))
    ).one()
    assert (stored.outcome, stored.mark, stored.mark_detail) == (
        "failed",
        "default_fake",
        ["book_slot"],
    )
    body = _runs(client, user, agent, run_id=run_id).json()
    detail = body["data"]["run"]
    verdict = detail["calls"][0]["verdicts"][0]
    assert (verdict["mark"], verdict["mark_detail"]) == ("default_fake", ["book_slot"])
    # It counts as neither a failure nor a pass: the rule is not checked.
    rule = detail["rules"][0]
    assert (rule["failed"], rule["passed"], rule["default_fake"]) == (0, 0, 1)
    assert detail["counts"]["critical_failed"] == 0
    assert (detail["totals"]["failed"], detail["totals"]["default_fake"]) == (0, 1)
    assert detail["verdict"] == "not_verified"
    steps = " ".join(body["next_steps"])
    assert "marked and not counted" in steps and "book_slot" in steps
    assert "1 rule was not checked because of it" in steps
    assert "critical rule failed" not in steps
    # An on-demand run of the same kind has no result, not "passed".
    pick = _made(
        client,
        user,
        agent,
        AsyncMock(return_value=_verdict(keys[PRICE], "passed", turns=[4])),
        scenario_ids=[detail["calls"][0]["scenario_id"]],
    )
    picked = _runs(client, user, agent, run_id=pick).json()["data"]["run"]
    assert picked["result"] is None
    # The simulated call's own result does not fail on it either.
    stored_call = db.get(TestCaseResult, uuid.UUID(detail["calls"][0]["id"]))
    stored_run = db.get(Run, uuid.UUID(run_id))
    assert stored_call is not None and stored_run is not None
    screen = simulated_call_screen(session=db, result=stored_call, run=stored_run)
    assert screen.result == "clean"
    # The version's results say why the rule is not checked.
    results = _runs(client, user, agent).json()["data"]["results"]
    assert results["verdict"] == "not_verified"
    assert results["full_run"]["totals"]["default_fake"] == 1


def test_which_verdicts_rest_on_a_default_fake() -> None:
    fake_turns = {"book_slot": 3, "send_sms": 7}
    passed, failed, skipped = "passed", "failed", "did_not_come_up"
    rests = runner.rests_on_default_fakes
    # Before the fake answered: the verdict stands.
    assert rests(runner.RuleOutcome(passed), [1, 2], fake_turns) == []
    # At or after it: marked, with every fake that had answered by then.
    assert rests(runner.RuleOutcome(failed), [3], fake_turns) == ["book_slot"]
    assert rests(runner.RuleOutcome(passed), [2, 9], fake_turns) == [
        "book_slot",
        "send_sms",
    ]
    # Nothing to rest on: a rule that did not come up, or a verdict citing no turn.
    assert rests(runner.RuleOutcome(skipped), [9], fake_turns) == []
    assert rests(runner.RuleOutcome(failed), [], fake_turns) == []
    assert rests(runner.RuleOutcome(failed), [9], {}) == []


@pytest.mark.provider_versions
@pytest.mark.parametrize(
    ("now", "content"),
    [
        ("Invented prompt.", "same"),
        ("Invented prompt, edited.", "edited"),
        # Retell fails, times out or answers something unreadable: never "same".
        (httpx.Response(500), "unknown"),
        (httpx.ConnectTimeout("timed out"), "unknown"),
        (httpx.Response(200, text="not json"), "unknown"),
        (httpx.Response(200, json=[]), "unknown"),
    ],
)
def test_a_run_says_whether_its_version_was_edited_since(
    client: TestClient,
    db: Session,
    caller: AsyncMock,
    now: Any,
    content: str,
) -> None:
    user, agent, keys = _ready(db, client)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    # A smoke run, not a full one: it says so too.
    run_id = _made(
        client,
        user,
        agent,
        AsyncMock(return_value=_verdict(keys[PRICE], "passed")),
        scenario_ids=[scenario["id"]],
    )

    with respx.mock() as retell:
        if isinstance(now, str):
            _tested_version(retell, 15, prompt=now)
        elif isinstance(now, Exception):
            retell.get(url__startswith=f"{RETELL}/get-agent/").mock(side_effect=now)
        else:
            retell.get(url__startswith=f"{RETELL}/get-agent/").mock(return_value=now)
        body = _runs(client, user, agent, read=True, run_id=run_id).json()
        results = _runs(client, user, agent, read=True).json()["data"]["results"]

    detail = body["data"]["run"]
    assert detail["content"] == content
    assert (detail["content_checked_at"] is not None) == isinstance(now, str)
    assert results["runs"][0]["content"] == content
    first = body["next_steps"][0]
    if content == "edited":
        assert "Version 15 was edited after this run" in first
    elif content == "unknown":
        assert "Could not confirm that version 15 still has the content" in first
    else:
        assert "edited" not in first and "Could not confirm" not in first


@pytest.mark.provider_versions
def test_an_edit_after_the_last_run_unverifies_the_version_when_read(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys, rules=list(keys.values())))
    judge = AsyncMock(
        return_value=_llm(
            json.dumps(
                {
                    "rules": [
                        {"key": k, "reason": "x", "turns": [1], "outcome": "passed"}
                        for k in keys.values()
                    ]
                }
            )
        )
    )
    _made(client, user, agent, judge)

    with respx.mock() as retell:
        _tested_version(retell, 15)
        same = _runs(client, user, agent, read=True).json()["data"]["results"]
    with respx.mock() as retell:
        _tested_version(retell, 15, prompt="Invented prompt, edited.")
        body = _runs(client, user, agent, read=True).json()

    assert (same["verdict"], same["edited_since"]) == ("verified", None)
    edited = body["data"]["results"]
    # No run saw the new content, yet the full run no longer counts.
    assert edited["verdict"] == "not_verified"
    assert edited["edited_since"] is not None
    assert edited["runs"][0]["content"] == "edited"
    assert "edited after its full run" in body["next_steps"][0]


@pytest.mark.provider_versions
def test_a_run_names_its_spec_and_warns_when_the_agent_version_is_newer(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    judge = AsyncMock(return_value=_verdict(keys[PRICE], "passed"))
    # The spec was written for agent version 7.
    newer = _made(client, user, agent, judge, version=15)
    written_for = _made(client, user, agent, judge, version=7)

    ahead = _runs(client, user, agent, run_id=newer).json()
    level = _runs(client, user, agent, run_id=written_for).json()

    run = ahead["data"]["run"]
    assert (run["spec_version"], run["spec_written_for"], run["spec_behind"]) == (
        1,
        "7",
        True,
    )
    assert any(
        "written for agent version 7; this run tested 15" in step
        for step in ahead["next_steps"]
    )
    assert level["data"]["run"]["spec_behind"] is False
    assert not any("written for agent version" in s for s in level["next_steps"])


@pytest.mark.provider_versions
def test_a_call_is_marked_started_when_it_starts(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    seen: list[int] = []

    async def judge(*_args: Any, **_kwargs: Any) -> LLMResponse:
        # While the judge is asked, the call is in flight: started, not finished.
        idle.append(runner.engine.pool.checkedout())  # type: ignore[attr-defined]
        with Session(db.get_bind()) as other:
            in_flight = other.exec(
                select(TestCaseResult)
                .join(Run, col(Run.id) == col(TestCaseResult.run_id))
                .where(
                    Run.agent_id == agent.id,
                    col(TestCaseResult.started_at).is_not(None),
                    col(TestCaseResult.completed_at).is_(None),
                )
            ).all()
            seen.append(len(in_flight))
        return _verdict(keys[PRICE], "passed")

    held: list[int] = []
    idle: list[int] = []

    def agent_turn(request: httpx.Request) -> httpx.Response:
        held.append(runner.engine.pool.checkedout())  # type: ignore[attr-defined]
        return _agent_turn(request)

    run_id = _made(
        client, user, agent, AsyncMock(side_effect=judge), agent_turn=agent_turn
    )

    assert seen == [1]
    # A call does not keep a database connection while it talks to the agent: 25 run
    # at once and the pool is smaller.
    assert held and idle and max(held) <= min(idle)
    detail = _runs(client, user, agent, run_id=run_id).json()["data"]["run"]
    counts = detail["counts"]
    assert (counts["queued"], counts["running"], counts["started"]) == (0, 0, 1)
    assert detail["last_progress_at"] is not None
    # The run said it was alive when it started.
    db.expire_all()
    assert db.get(Run, uuid.UUID(run_id)).heartbeat_at is not None  # type: ignore[union-attr]


@pytest.mark.provider_versions
def test_a_run_that_lost_calls_says_so_and_is_incomplete_not_passed(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    scenario = _scenarios(client, user, agent, _price(keys)).json()["data"][
        "scenarios"
    ][0]
    # Two repeats: the judge answers one and cannot be read for the other. It is not
    # asked again.
    judge = AsyncMock(side_effect=[_verdict(keys[PRICE], "passed"), _llm("not json")])

    run_id = _made(client, user, agent, judge, repeats=2, scenario_ids=[scenario["id"]])

    assert judge.await_count == 2
    body = _runs(client, user, agent, run_id=run_id).json()
    run = body["data"]["run"]
    counts = run["counts"]
    assert (counts["finished"], counts["errors"], counts["judge_errors"]) == (2, 1, 1)
    assert run["result"] == "incomplete"
    first = body["next_steps"][0]
    assert first.startswith("1 of 2 calls judged, 1 judge error")
    assert "incomplete, not passed" in first
    assert not any("stopped" in step.split(":")[0] for step in body["next_steps"][:1])


@pytest.mark.provider_versions
def test_a_run_counts_the_platforms_too_many_requests_answers(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    refused = iter([True])

    def throttled_once(request: httpx.Request) -> httpx.Response:
        if json.loads(request.content)["messages"] and next(refused, False):
            return httpx.Response(429, headers={"Retry-After": "1"})
        return _agent_turn(request)

    with patch("app.services.retell.asyncio.sleep", new=AsyncMock()):
        run_id = _made(
            client,
            user,
            agent,
            AsyncMock(return_value=_verdict(keys[PRICE], "passed")),
            agent_turn=throttled_once,
        )

    body = _runs(client, user, agent, run_id=run_id).json()
    run = body["data"]["run"]
    assert (run["throttled"], run["calls"][0]["throttled"]) == (1, 1)
    assert run["counts"]["errors"] == 0
    assert any("'too many requests' 1 time" in step for step in body["next_steps"])


def test_where_a_calls_time_went() -> None:
    started = datetime(2026, 11, 20, 12, 0, 0)

    def call(total_s: int, agent_ms: int, caller_ms: int, judge_ms: int | None) -> Any:
        return TestCaseResult(
            run_id=uuid.uuid4(),
            test_case_id=uuid.uuid4(),
            started_at=started,
            completed_at=started + timedelta(seconds=total_s),
            judge_ms=judge_ms,
            transcript=[
                {"index": 0, "role": "assistant", "latency_ms": agent_ms},
                {"index": 1, "role": "user", "latency_ms": caller_ms},
                {"index": 2, "role": "tool", "latency_ms": None},
            ],
        )

    timing = runner.call_timing(call(100, 40_000, 20_000, 5_000))
    assert timing is not None
    assert (timing.agent_s, timing.caller_s, timing.judge_s, timing.server_s) == (
        40.0,
        20.0,
        5.0,
        35.0,
    )
    # A call made before the judge was timed, and one still in flight.
    assert runner.call_timing(call(100, 40_000, 20_000, None)).judge_s is None  # type: ignore[union-attr]
    assert (
        runner.call_timing(
            TestCaseResult(run_id=uuid.uuid4(), test_case_id=uuid.uuid4())
        )
        is None
    )

    slow = runner.run_timing([call(100, 20_000, 10_000, 5_000)] * 3)
    fast = runner.run_timing([call(40, 25_000, 10_000, 4_000)] * 3)
    assert slow is not None and fast is not None
    assert (slow.calls, slow.total_s, slow.server_s, slow.server_share_pct) == (
        3,
        100.0,
        65.0,
        65,
    )
    assert fast.server_share_pct == 2
    assert runner.run_timing([]) is None


def test_a_run_makes_25_calls_at_once_unless_set_otherwise(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))

    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None and run.config is not None
    assert run.config["concurrency"] == 25


def test_a_run_in_progress_keeps_saying_it_is_alive(
    client: TestClient, db: Session
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]
    old = _age(db, run_id, 5, RunStatus.RUNNING).heartbeat_at

    async def beat_twice() -> None:
        done = asyncio.Event()
        with patch.object(runner, "HEARTBEAT_SECONDS", 0.01):
            beating = asyncio.create_task(runner._heartbeat(uuid.UUID(run_id), done))
            await asyncio.sleep(0.1)
            done.set()
            await beating

    asyncio.run(beat_twice())

    db.expire_all()
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None and run.heartbeat_at is not None and old is not None
    assert run.heartbeat_at > old


@pytest.mark.provider_versions
def test_a_runs_requests_to_retell_go_through_the_pacer(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    waited: list[str] = []

    async def wait(key: str) -> None:
        waited.append(key)

    with patch("app.services.retell.PLAYGROUND_PACER.wait", new=wait):
        _made(
            client,
            user,
            agent,
            AsyncMock(return_value=_verdict(keys[PRICE], "passed")),
        )

    # The greeting and the reply: each took a slot, under the same Retell key.
    assert len(waited) == 2 and len(set(waited)) == 1


@pytest.mark.provider_versions
def test_tool_arguments_that_break_the_tools_schema_are_reported_and_fail_nothing(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    judge = AsyncMock(return_value=_verdict(keys[PRICE], "passed"))
    # The agent books with a date and no name; the tool's schema requires both.
    broken = _made(client, user, agent, judge, book_slot_schema=BOOK_SLOT_SCHEMA)
    # The same run against a version whose tools declare no schema.
    plain = _made(client, user, agent, judge)

    body = _runs(client, user, agent, run_id=broken).json()
    run = body["data"]["run"]
    assert run["tool_schemas_checked"] is True
    assert run["calls"][0]["schema_violations"] == [
        {
            "tool": "book_slot",
            "field": "name",
            "problem": "is missing; the schema requires it",
            "turn": 2,
        }
    ]
    assert run["schema_check"] == {
        "tools_checked": 1,
        "tools_unreadable": [],
        "calls_with_violations": 1,
        "violations": [
            {
                "tool": "book_slot",
                "field": "name",
                "problem": "is missing; the schema requires it",
                "calls": 1,
            }
        ],
    }
    assert body["next_steps"][0].startswith(
        "The agent sent tool arguments that break the tool's schema in 1 call: "
        "`book_slot`: `name` is missing"
    )
    assert any("`schema_check`" in rule for rule in body["rules"])
    # Nothing was sent back to the agent: the fake answered as always.
    db.expire_all()
    call = db.exec(
        select(TestCaseResult).where(TestCaseResult.run_id == uuid.UUID(broken))
    ).one()
    assert call.transcript is not None
    assert [t["content"] for t in call.transcript if t["role"] == "tool"] == [
        DEFAULT_FAKE_RESULT
    ]
    assert call.check_findings == []

    # It changes no verdict, total or count: the run reads as one without it.
    clean = _runs(client, user, agent, run_id=plain).json()["data"]["run"]
    for key in ("verdict", "result", "totals", "counts"):
        assert run[key] == clean[key]
    assert clean["tool_schemas_checked"] is True
    assert clean["schema_check"]["tools_checked"] == 0
    assert clean["schema_check"]["violations"] == []
    assert clean["calls"][0]["schema_violations"] == []


@pytest.mark.provider_versions
def test_a_run_whose_version_could_not_be_read_says_its_schemas_were_not_checked(
    client: TestClient, db: Session, caller: AsyncMock
) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))

    run_id = _made(
        client,
        user,
        agent,
        AsyncMock(return_value=_verdict(keys[PRICE], "passed")),
        readable=False,
    )

    body = _runs(client, user, agent, run_id=run_id).json()
    run = body["data"]["run"]
    assert (run["tool_schemas_checked"], run["schema_check"]) == (False, None)
    assert any(
        "were not checked against the tools' schemas" in s for s in body["next_steps"]
    )
