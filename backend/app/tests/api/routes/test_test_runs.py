"""Running scenarios in text through MCP: starting a run, the simulated calls against
Retell's playground with every tool faked, the judge's rule verdicts, code checks on the
conversation, and reading runs back, on invented agents with Retell and the model
mocked (plan `plans/2026-11-17-text-runner.md`)."""

import asyncio
import json
import uuid
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.crud.test_run import fail_stale_runs
from app.models import Agent, User
from app.models.call import Call
from app.models.check import Finding
from app.models.enums import Platform, RunStatus, ToolCallStatus
from app.models.run import Run
from app.models.test_case_result import TestCaseResult
from app.models.test_run import RuleVerdict
from app.services import test_run as runner
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
    with patch("app.api.routes.mcp.launch") as launch:
        r = client.post(
            f"{_base(user, agent)}/test-runs", headers=_headers(user), json=body
        )
    if r.status_code == 200:
        launch.assert_called_once()
    else:
        launch.assert_not_called()
    return r


def _runs(client: TestClient, user: User, agent: Agent, **params: Any) -> Any:
    return client.get(
        f"{_base(user, agent)}/test-runs", headers=_headers(user), params=params
    )


def _llm(content: str) -> LLMResponse:
    return LLMResponse(content=content, model="invented-model", response_cost_usd=0.001)


def _verdict(key: str, outcome: str) -> LLMResponse:
    return _llm(
        json.dumps(
            {
                "rules": [
                    {"key": key, "outcome": outcome, "reason": "Said 80.", "turns": [4]}
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


def _tested_version(retell: respx.MockRouter, number: int) -> None:
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
                "general_prompt": "Invented prompt.",
                "general_tools": [
                    {"type": "custom", "name": "check_slot"},
                    {"type": "end_call", "name": "end_call"},
                ],
                "states": [
                    {
                        "name": "booking",
                        "tools": [{"type": "custom", "name": "book_slot"}],
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
        assert call.passed is None
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
            "flaky": True,
        }
    ]
    assert detail["counts"] == {
        "calls": 2,
        "finished": 2,
        "errors": 0,
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
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

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
    assert results["data"]["results"]["verdict"] == "not_tested"
    stopped = results["data"]["results"]["stopped"]
    assert stopped["calls"] == 1 and stopped["run_id"] == run_id
    assert stopped["reason"].startswith("The conversation stopped")
    assert any("stopped with an error" in s for s in results["next_steps"])
    body = _runs(client, user, agent, run_id=run_id).json()
    assert body["data"]["run"]["counts"]["errors"] == 1
    assert any("ended in an error" in s for s in body["next_steps"])
    # The run completed but judged no rule: the version is not tested, never verified.
    results = _runs(client, user, agent).json()
    assert results["data"]["results"]["verdict"] == "not_tested"
    assert "checked no rule" in results["next_steps"][0]


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


def test_a_restart_fails_runs_it_stopped(client: TestClient, db: Session) -> None:
    user, agent, keys = _ready(db, client)
    _scenarios(client, user, agent, _price(keys))
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

    assert fail_stale_runs(session=db) >= 1

    db.expire_all()
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None
    assert run.status == RunStatus.FAILED
    assert run.status_detail and "restart" in run.status_detail
    assert run.completed_at is not None
    # A failed run is not started again.
    _execute(run_id)
    db.expire_all()
    assert db.get(Run, uuid.UUID(run_id)).status == RunStatus.FAILED  # type: ignore[union-attr]


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
    run_id = _start(client, user, agent, all=True, repeats=1).json()["data"]["run_id"]

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
    # Retell could not be read (tests never reach it), so the run went on against
    # the latest, and says it could not name the version.
    run = db.get(Run, uuid.UUID(run_id))
    assert run is not None and run.platform_version is None
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
