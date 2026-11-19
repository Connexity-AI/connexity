"""Running scenarios in text (`plans/2026-11-17-text-runner.md`,
`docs-internal/testing.md`).

A run is a named set, a pick or every scenario of an agent, each repeated. A simulated
caller talks to the agent's own engine (Retell's playground) with every tool faked.
After each conversation one judge call gives each rule the scenario lists a verdict,
and the code checks run on the conversation in memory. Nothing here touches the `call`
or `finding` tables: a simulated call never counts as production.
"""

import asyncio
import json
import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from pydantic import JsonValue
from sqlmodel import Session, col, select

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.core.encryption import decrypt
from app.crud.scenario import (
    live_scenarios,
    members,
    rules_of,
    scenarios_by_rule,
    set_by_name,
)
from app.crud.spec import latest_spec, rules_of_specs
from app.crud.test_run import (
    calls_of_runs,
    create_run,
    runs_of_agent,
    runs_page,
    verdicts_of_runs,
)
from app.models.agent import Agent
from app.models.enums import (
    AgentMode,
    CallEventType,
    CheckMode,
    Platform,
    RuleOutcome,
    RunMode,
    RunScope,
    RunStatus,
    Speaker,
    TextRuntimeKind,
    ToolCallStatus,
    TraceCapability,
    TraceSource,
    TurnRole,
    VersionVerdict,
)
from app.models.integration import Integration
from app.models.run import Run
from app.models.schemas import (
    ConversationTurn,
    RetellRuntimeConfig,
    RunConfig,
    UserSimulatorConfig,
)
from app.models.spec import Spec, SpecRule
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.models.test_run import (
    CheckTotalPublic,
    CoveragePublic,
    RuleTotalPublic,
    RuleVerdict,
    SimulatedCallPublic,
    SimulatedFinding,
    StoppedCallsPublic,
    TestRunCountsPublic,
    TestRunDetailPublic,
    TestRunPublic,
    UncheckedRulePublic,
    VerdictPublic,
    VersionResultsPublic,
)
from app.models.trace import ToolCallEvent, Trace, TraceEvent, UtteranceEvent
from app.services.agent_tool_definitions import snapshot_marks_tool_terminating
from app.services.checks.engine import current_mode, run_checks
from app.services.checks.registry import CHECKS, FACT_SOURCES, get_check
from app.services.component_versions import RetellVersionRead, read_retell_version
from app.services.eval_runtimes import (
    AgentSnapshot,
    RunSnapshot,
    RuntimeRunArgs,
    get_runtime,
)
from app.services.rule_judge import JudgeFailed, RuleToJudge, judge_rules
from app.services.trace_capabilities import derive_capabilities

logger = logging.getLogger(__name__)

MAX_REPEATS = 5
DEFAULT_REPEATS = 3
MAX_CALLS = 200
# Simulated calls in flight at once (Dmytro, 2026-11-19).
CONCURRENCY = 10
# A conversation ends when the agent hangs up or has answered this many times; it is
# then judged on what was said (Dmytro, 2026-11-19).
MAX_AGENT_REPLIES = 40
# A safety net against a stuck platform, not a length: hitting it is an error.
CONVERSATION_CAP_MS = 10 * 60 * 1000

# Runs started in this process, kept so they are not collected while they run.
_RUNNING: set[asyncio.Task[None]] = set()


class RunRefused(Exception):
    """Nothing was started; each problem is one line the assistant can act on."""

    def __init__(self, error: str, problems: list[str] | None = None) -> None:
        super().__init__(error)
        self.error = error
        self.problems = problems or []


@dataclass(frozen=True)
class RunRequest:
    set_name: str | None
    scenario_ids: list[uuid.UUID] | None
    all: bool
    repeats: int
    version: int | None


# ── Starting a run ────────────────────────────────────────────────


def simulation_key_set() -> bool:
    """Whether Connexity's key for the simulation model's provider is set. The
    simulated caller and the judge run on it; workspaces never bring one."""
    provider = settings.SIMULATION_PROVIDER.lower()
    if provider == "anthropic":
        return bool(settings.ANTHROPIC_API_KEY)
    if provider == "openai":
        return bool(settings.OPENAI_API_KEY)
    return True


def _scenarios_for(
    session: Session, agent: Agent, request: RunRequest
) -> tuple[RunScope, list[TestCase], uuid.UUID | None]:
    given = [
        request.set_name is not None,
        request.scenario_ids is not None,
        request.all,
    ]
    if sum(given) != 1:
        msg = "Give exactly one of `set`, `scenario_ids` or `all`."
        raise RunRefused(msg)
    live = {
        scenario.id: scenario
        for scenario in live_scenarios(session=session, agent_id=agent.id)
    }
    if request.all:
        return RunScope.ALL, list(live.values()), None
    if request.set_name is not None:
        config = set_by_name(session=session, agent_id=agent.id, name=request.set_name)
        if config is None:
            msg = f"The agent has no set named '{request.set_name}'."
            raise RunRefused(
                msg, ["Call `list_scenarios` without `set`; it lists the sets."]
            )
        ids = members(session=session, set_ids=[config.id]).get(config.id, [])
        return RunScope.SET, [live[i] for i in ids if i in live], config.id
    picked = list(dict.fromkeys(request.scenario_ids or []))
    unknown = [str(i) for i in picked if i not in live]
    if unknown:
        msg = "Some scenario ids are not active scenarios of this agent."
        raise RunRefused(
            msg,
            [f"Unknown or archived scenario: {i}" for i in unknown]
            + ["Call `list_scenarios` for the agent's scenario ids."],
        )
    return RunScope.PICK, [live[i] for i in picked], None


def start_run(
    *, session: Session, agent: Agent, user_id: uuid.UUID | None, request: RunRequest
) -> Run:
    """Store a run and its simulated calls, ready for ``launch``.

    Raises:
        RunRefused: nothing was stored, and why.
    """
    if agent.platform != Platform.RETELL or not (
        agent.integration_id and agent.platform_agent_id
    ):
        msg = "Only agents on Retell can be run in text for now."
        raise RunRefused(
            msg,
            [
                "Self-hosted agents (Pipecat and similar) wait until their contract "
                "takes fake tool results, so their real tools are never called."
            ],
        )
    if not simulation_key_set():
        msg = (
            "Simulations are not available right now: Connexity's model key is missing."
        )
        raise RunRefused(
            msg,
            [
                "Tell the person simulations cannot run until Connexity's model key is "
                "set; there is nothing for you to fix."
            ],
        )
    spec = latest_spec(session=session, agent_id=agent.id)
    if spec is None:
        msg = "The agent has no spec, so there are no rules to judge."
        raise RunRefused(msg, ["Write the spec with `write_spec` first."])
    if not 1 <= request.repeats <= MAX_REPEATS:
        msg = f"`repeats` is from 1 to {MAX_REPEATS}."
        raise RunRefused(msg)
    scope, scenarios, set_id = _scenarios_for(session, agent, request)
    if not scenarios:
        msg = "There are no active scenarios to run."
        raise RunRefused(msg, ["Write scenarios with `write_scenarios` first."])
    calls = len(scenarios) * request.repeats
    if calls > MAX_CALLS:
        msg = f"The run would make {calls} simulated calls; the most is {MAX_CALLS}."
        raise RunRefused(
            msg, ["Run a set or a pick, or fewer repeats, and run the rest after."]
        )
    # The simulated caller runs on Connexity's own key; the run records the model.
    config = RunConfig(
        concurrency=CONCURRENCY,
        max_turns=MAX_AGENT_REPLIES,
        timeout_per_test_case_ms=CONVERSATION_CAP_MS,
        runtime=RetellRuntimeConfig(version=request.version),
        user_simulator=UserSimulatorConfig(
            model=settings.SIMULATION_MODEL, provider=settings.SIMULATION_PROVIDER
        ),
    )
    run = Run(
        name=None,
        agent_id=agent.id,
        company_id=agent.company_id,
        created_by=user_id,
        agent_mode=AgentMode.PLATFORM.value,
        eval_config_id=set_id,
        scope=scope,
        set_name=request.set_name if scope is RunScope.SET else None,
        repeats=request.repeats,
        spec_id=spec.id,
        platform_version=str(request.version) if request.version is not None else None,
        config=config.model_dump(mode="json"),
        status=RunStatus.PENDING,
    )
    return create_run(
        session=session,
        run=run,
        scenario_ids=[scenario.id for scenario in scenarios],
        repeats=request.repeats,
    )


def launch(run_id: uuid.UUID) -> None:
    """Run ``run_id`` in the background of this process."""
    task = asyncio.get_running_loop().create_task(execute_run(run_id))
    _RUNNING.add(task)
    task.add_done_callback(_RUNNING.discard)


# ── Running it ────────────────────────────────────────────────────


def _parsed(raw: Any) -> JsonValue:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return raw


def _faked_by_scenario(scenario: TestCase, name: str, arguments: JsonValue) -> bool:
    """Whether one of the scenario's fakes answers this call, matching it as Retell
    does: the tool's name, and the fake's arguments contained in the call's."""
    given = arguments if isinstance(arguments, dict) else {}
    for row in scenario.expected_tool_calls or []:
        if row.get("tool") != name:
            continue
        expected = row.get("expected_params")
        if not isinstance(expected, dict) or not expected:
            return True
        if all(key in given and given[key] == value for key, value in expected.items()):
            return True
    return False


def default_fake_calls(
    transcript: list[ConversationTurn],
    scenario: TestCase,
    agent_tools: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """The tool calls no scenario fake answers, by call id with the tool's name.

    The catch-all answers every other call, so these got the default fake. A tool that
    ends the call (hang-up, transfer) is left out: the conversation ends there, so its
    answer says nothing. Worked out from the fakes sent, not from what Retell echoes
    back.
    """
    return {
        call.id: call.function.name
        for turn in transcript
        for call in turn.tool_calls or []
        if not snapshot_marks_tool_terminating(call.function.name, agent_tools)
        and not _faked_by_scenario(
            scenario, call.function.name, _parsed(call.function.arguments)
        )
    }


def _why_stopped(marker: str) -> str:
    """A platform marker in plain words: "[agent_error] Retell returned no messages"
    becomes "Retell returned no messages"."""
    text = marker.strip()
    if text.startswith("[agent_error]"):
        text = text.removeprefix("[agent_error]").strip()
    elif text.startswith("[platform:") and text.endswith("]"):
        text = text.removeprefix("[platform:").removesuffix("]").strip()
    return text or "the platform did not answer"


def edited_runs(runs: list[Run]) -> set[uuid.UUID]:
    """The runs that tested content an earlier run of the same number did not have.

    A run that could not read its content says nothing either way.
    """
    out: set[uuid.UUID] = set()
    seen: dict[str, set[str]] = {}
    for run in sorted(runs, key=lambda r: r.created_at):
        if run.platform_version is None or run.version_fingerprint is None:
            continue
        before = seen.setdefault(run.platform_version, set())
        if before and run.version_fingerprint not in before:
            out.add(run.id)
        before.add(run.version_fingerprint)
    return out


def _is_marker(content: str | None) -> bool:
    text = (content or "").strip()
    return text.startswith(("[agent_error]", "[platform:"))


def trace_of(
    transcript: list[ConversationTurn],
    *,
    call_id: uuid.UUID,
    started_at: datetime,
    defaults: set[str] | frozenset[str] = frozenset(),
) -> Trace:
    """The conversation as a trace, so code checks read it as they read a real call.

    It has no timing and no recording, so checks that need those are skipped.
    """
    results = {
        turn.tool_call_id: turn.content
        for turn in transcript
        if turn.role == TurnRole.TOOL and turn.tool_call_id
    }
    events: list[TraceEvent] = []
    for turn in transcript:
        if turn.role in (TurnRole.USER, TurnRole.ASSISTANT) and turn.content:
            if not _is_marker(turn.content):
                events.append(
                    UtteranceEvent(
                        id=f"u{turn.index}",
                        type=CallEventType.UTTERANCE,
                        speaker=Speaker.CALLER
                        if turn.role == TurnRole.USER
                        else Speaker.AGENT,
                        text=turn.content,
                    )
                )
        for n, call in enumerate(turn.tool_calls or []):
            arguments = _parsed(call.function.arguments)
            result = _parsed(results.get(call.id))
            status = (
                ToolCallStatus.NO_RESULT
                if call.id not in results or call.id in defaults
                else ToolCallStatus.OK
            )
            events.append(
                ToolCallEvent(
                    id=f"t{turn.index}-{n}",
                    type=CallEventType.TOOL_CALL,
                    name=call.function.name[:255] or "unknown",
                    arguments=arguments if isinstance(arguments, dict) else None,
                    status=status,
                    result=result,
                )
            )
    return Trace(
        provider="retell",
        external_id=f"simulated-{call_id}",
        started_at=started_at,
        source=TraceSource.SIMULATION,
        reports_tool_calls=True,
        events=events,
    )


def check_simulated(
    trace: Trace, modes: dict[str, CheckMode]
) -> list[SimulatedFinding]:
    """What the code checks that are not off find in ``trace``. A check whose needs
    the trace lacks (timing, a recording) is skipped."""
    capabilities: set[TraceCapability] = set(derive_capabilities(trace))
    checks = [
        check
        for check in CHECKS
        if modes.get(check.type, check.default_mode) is not CheckMode.OFF
        and all(need in capabilities for need in check.needs)
    ]
    run = run_checks(
        trace=trace, executions=[], checks=checks, fact_sources=FACT_SOURCES
    )
    for check_type, error in run.broken.items():
        logger.error("Check '%s' broke on a simulated call", check_type, exc_info=error)
    return [
        SimulatedFinding(
            check_type=check.type,
            check_version=check.version,
            kind=check.kind,
            mode=modes.get(check.type, check.default_mode),
            key=raised.key,
            event_ids=list(raised.event_ids),
            detail=raised.detail,
        )
        for check, raised in run.found
    ]


@dataclass(frozen=True)
class _RunContext:
    run_id: uuid.UUID
    company_id: uuid.UUID
    agent_id: uuid.UUID
    agent_snapshot: AgentSnapshot
    run_snapshot: RunSnapshot
    rules: dict[str, SpecRule]
    modes: dict[str, CheckMode]


async def _simulate(
    ctx: _RunContext,
    row: TestCaseResult,
    scenario: TestCase,
    keys: list[str],
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        started = datetime.now(UTC)
        runtime = get_runtime(RunMode.TEXT, TextRuntimeKind.RETELL)
        verdicts: list[RuleVerdict] = []
        update: dict[str, Any] = {"started_at": started}
        try:
            with Session(engine) as session:
                out = await runtime.run_test_case(
                    ctx.run_snapshot.run_config.runtime,
                    RuntimeRunArgs(
                        test_case=scenario,
                        agent_snapshot=ctx.agent_snapshot,
                        run_snapshot=ctx.run_snapshot,
                    ),
                    session,
                )
            transcript = out.transcript
            defaults = default_fake_calls(
                transcript, scenario, ctx.agent_snapshot.tools
            )
            fakes = list(dict.fromkeys(defaults.values()))
            judge_cost = 0.0
            error: str | None = None
            failure = next(
                (t.content for t in transcript if _is_marker(t.content)), None
            )
            if not transcript:
                error = "The conversation is empty."
            elif failure is not None:
                # The platform failed or the call timed out: what was said is not a
                # conversation to judge.
                error = f"The conversation stopped: {_why_stopped(failure)}"[:1000]
            else:
                to_judge = [
                    RuleToJudge(key=key, text=ctx.rules[key].text)
                    for key in keys
                    if key in ctx.rules
                ]
                try:
                    judged = await judge_rules(
                        transcript=transcript,
                        rules=to_judge,
                        caller_goal=scenario.caller_goal,
                        default_fakes=fakes,
                    )
                    judge_cost = judged.cost_usd or 0.0
                    verdicts = [
                        RuleVerdict(
                            company_id=ctx.company_id,
                            agent_id=ctx.agent_id,
                            run_id=ctx.run_id,
                            test_case_result_id=row.id,
                            test_case_id=scenario.id,
                            rule_key=v.key,
                            outcome=v.outcome,
                            reason=v.reason or None,
                            turns=v.turns,
                            critical=ctx.rules[v.key].critical,
                        )
                        for v in judged.verdicts
                    ]
                except JudgeFailed as failed:
                    error = str(failed)
            findings = check_simulated(
                trace_of(
                    transcript,
                    call_id=row.id,
                    started_at=started,
                    defaults=set(defaults),
                ),
                ctx.modes,
            )
            platform_cost = out.platform_cost_usd + judge_cost
            update |= {
                "transcript": [turn.model_dump(mode="json") for turn in transcript],
                "turn_count": len(transcript),
                "default_fakes": fakes,
                "check_findings": [f.model_dump(mode="json") for f in findings],
                "agent_token_usage": out.agent_token_usage or None,
                "platform_token_usage": out.platform_token_usage or None,
                "agent_cost_usd": out.agent_cost_usd or None,
                "platform_cost_usd": platform_cost or None,
                "estimated_cost_usd": (out.agent_cost_usd + platform_cost) or None,
                "error_message": error,
            }
        except Exception as exc:  # noqa: BLE001 - one call's failure must not stop the run
            logger.exception("Simulated call %s failed", row.id)
            update["error_message"] = str(exc)[:1000] or type(exc).__name__
        update["completed_at"] = datetime.now(UTC)
        with Session(engine) as session:
            stored = session.get(TestCaseResult, row.id)
            if stored is None:
                return
            for field, value in update.items():
                setattr(stored, field, value)
            session.add(stored)
            for verdict in verdicts:
                session.add(verdict)
            session.commit()


async def execute_run(run_id: uuid.UUID) -> None:
    """Make every simulated call of a stored run, then mark it completed."""
    try:
        with Session(engine) as session:
            run = session.get(Run, run_id)
            if run is None or run.status != RunStatus.PENDING or run.spec_id is None:
                return
            agent = session.get(Agent, run.agent_id)
            if agent is None:
                return
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(UTC)
            session.add(run)
            session.commit()
            config = RunConfig.model_validate(run.config)
            integration = (
                session.get(Integration, agent.integration_id)
                if agent.integration_id
                else None
            )
            api_key = decrypt(integration.encrypted_api_key) if integration else None
            rows = calls_of_runs(session=session, run_ids=[run.id])[run.id]
            scenario_ids = list({row.test_case_id for row in rows})
            scenarios = {
                s.id: s
                for s in (session.get(TestCase, i) for i in scenario_ids)
                if s is not None
            }
            keys = rules_of(session=session, test_case_ids=scenario_ids)
            rules = {
                rule.key: rule
                for rule in rules_of_specs(session=session, spec_ids=[run.spec_id]).get(
                    run.spec_id, []
                )
            }
            history = crud.check_setting_history(session=session, agent_id=agent.id)
            modes = {
                check.type: current_mode(check, history.get(check.type, []))
                for check in CHECKS
            }
            for item in (*rows, *scenarios.values()):
                session.expunge(item)
            session.expunge(agent)
            ctx = _RunContext(
                run_id=run.id,
                company_id=run.company_id,
                agent_id=agent.id,
                agent_snapshot=AgentSnapshot(
                    agent=agent,
                    agent_id=agent.id,
                    platform=agent.platform,
                    integration_id=agent.integration_id,
                    platform_agent_id=agent.platform_agent_id,
                    endpoint_url=None,
                    system_prompt=None,
                    tools=None,
                    mode=AgentMode.PLATFORM,
                    model=None,
                    provider=None,
                ),
                run_snapshot=RunSnapshot(
                    run_id=run.id,
                    run_config=config,
                    cancel_event=None,
                    company_id=run.company_id,
                ),
                rules=rules,
                modes=modes,
            )
        runtime = config.runtime
        if (
            isinstance(runtime, RetellRuntimeConfig)
            and api_key
            and agent.platform_agent_id
        ):
            # One read of the tested version: its number, so every call talks to the
            # same version and the run says which one it tested; what it does now (a
            # draft is edited under the same number); and its tools, so a hang-up or a
            # transfer ends the conversation.
            read = await _read_version(
                api_key, agent.platform_agent_id, runtime.version
            )
            if read is not None:
                if runtime.version is None and read.version is not None:
                    runtime.version = read.version
                    _pin_version(run_id, read.version, config)
                _store_fingerprint(run_id, read.fingerprint)
                ctx = replace(
                    ctx,
                    agent_snapshot=replace(
                        ctx.agent_snapshot,
                        tools=[
                            {
                                "type": "function",
                                "function": {"name": tool.name},
                                "platform_config": {"terminating": tool.ends_call},
                            }
                            for tool in read.tools
                        ],
                    ),
                )
        semaphore = asyncio.Semaphore(config.concurrency)
        await asyncio.gather(
            *(
                _simulate(
                    ctx,
                    row,
                    scenarios[row.test_case_id],
                    keys.get(row.test_case_id, []),
                    semaphore,
                )
                for row in rows
                if row.test_case_id in scenarios
            )
        )
        _finish(run_id, RunStatus.COMPLETED, None)
    except Exception as exc:  # noqa: BLE001 - the run is marked failed, with why
        logger.exception("Run %s failed", run_id)
        _finish(run_id, RunStatus.FAILED, str(exc)[:1000] or type(exc).__name__)


async def _read_version(
    api_key: str, retell_agent_id: str, version: int | None
) -> RetellVersionRead | None:
    """The tested Retell version, or none when Retell cannot be read: the run goes on
    against "the latest", grouped by number only, with every tool faked."""
    try:
        return await read_retell_version(
            api_key=api_key, provider_agent_id=retell_agent_id, version=version
        )
    except Exception as exc:  # noqa: BLE001 - the run goes on without it
        logger.warning(
            "Could not read the tested Retell version: %s", exc, exc_info=True
        )
        return None


def _store_fingerprint(run_id: uuid.UUID, content: str) -> None:
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.version_fingerprint = content
        session.add(run)
        session.commit()


def _pin_version(run_id: uuid.UUID, version: int, config: RunConfig) -> None:
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.platform_version = str(version)
        run.config = config.model_dump(mode="json")
        session.add(run)
        session.commit()


def _finish(run_id: uuid.UUID, status: RunStatus, detail: str | None) -> None:
    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.status = status
        run.status_detail = detail
        run.completed_at = datetime.now(UTC)
        session.add(run)
        session.commit()


# ── Reading runs ──────────────────────────────────────────────────


def _cost(calls: list[TestCaseResult]) -> float | None:
    costs = [c.estimated_cost_usd for c in calls if c.estimated_cost_usd is not None]
    return round(sum(costs), 4) if costs else None


def _rule_totals(
    verdicts: list[RuleVerdict], rules: dict[str, SpecRule]
) -> list[RuleTotalPublic]:
    totals: dict[str, RuleTotalPublic] = {}
    for verdict in verdicts:
        total = totals.setdefault(
            verdict.rule_key,
            RuleTotalPublic(
                key=verdict.rule_key,
                text=rules[verdict.rule_key].text
                if verdict.rule_key in rules
                else None,
                critical=verdict.critical,
            ),
        )
        # Critical in any run's spec version counts.
        total.critical = total.critical or verdict.critical
        if verdict.outcome is RuleOutcome.PASSED:
            total.passed += 1
        elif verdict.outcome is RuleOutcome.FAILED:
            total.failed += 1
        else:
            total.did_not_come_up += 1
    for total in totals.values():
        total.flaky = total.passed > 0 and total.failed > 0
    return sorted(
        totals.values(),
        key=lambda t: (t.failed == 0, not t.critical, -t.failed, t.key),
    )


def _counts(
    calls: list[TestCaseResult], totals: list[RuleTotalPublic]
) -> TestRunCountsPublic:
    return TestRunCountsPublic(
        calls=len(calls),
        finished=sum(1 for c in calls if c.completed_at is not None),
        errors=sum(1 for c in calls if c.error_message is not None),
        rules_failed=sum(1 for t in totals if t.failed),
        critical_failed=sum(1 for t in totals if t.failed and t.critical),
        flaky=sum(1 for t in totals if t.flaky),
        findings=sum(len(c.check_findings or []) for c in calls),
    )


def _summary(
    run: Run,
    calls: list[TestCaseResult],
    totals: list[RuleTotalPublic],
    spec_versions: dict[uuid.UUID, int],
) -> TestRunPublic:
    assert run.scope is not None
    return TestRunPublic(
        id=run.id,
        status=run.status,
        status_detail=run.status_detail,
        scope=run.scope,
        set_name=run.set_name,
        repeats=run.repeats or 1,
        spec_version=spec_versions.get(run.spec_id) if run.spec_id else None,
        platform_version=run.platform_version,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        counts=_counts(calls, totals),
        cost_usd=_cost(calls),
    )


def _spec_versions(session: Session, runs: list[Run]) -> dict[uuid.UUID, int]:
    out: dict[uuid.UUID, int] = {}
    for spec_id in {run.spec_id for run in runs if run.spec_id}:
        spec = session.get(Spec, spec_id)
        if spec is not None:
            out[spec_id] = spec.version
    return out


def list_runs(
    *, session: Session, agent: Agent, offset: int, limit: int
) -> tuple[list[TestRunPublic], bool]:
    runs, more = runs_page(
        session=session, agent_id=agent.id, offset=offset, limit=limit
    )
    ids = [run.id for run in runs]
    calls = calls_of_runs(session=session, run_ids=ids)
    verdicts = verdicts_of_runs(session=session, run_ids=ids)
    versions = _spec_versions(session, runs)
    return [
        _summary(run, calls[run.id], _rule_totals(verdicts[run.id], {}), versions)
        for run in runs
    ], more


def simulated_call_url(call_id: uuid.UUID) -> str:
    """The simulated call in the app; it opens on the call screen like any call."""
    return f"{settings.public_site_url or ''}/calls/{call_id}"


def _check_totals(calls: list[TestCaseResult]) -> list[CheckTotalPublic]:
    """Each code check that found something, by how many simulated calls; a check is
    critical when any of its findings came while it fails calls."""
    found: Counter[str] = Counter()
    critical: set[str] = set()
    for call in calls:
        findings = call.check_findings or []
        for check_type in {f["check_type"] for f in findings}:
            found[check_type] += 1
        critical |= {
            f["check_type"] for f in findings if f.get("mode") == CheckMode.FAILS.value
        }
    return sorted(
        (
            CheckTotalPublic(
                check_type=check_type,
                title=check.title if (check := get_check(check_type)) else check_type,
                found=count,
                critical=check_type in critical,
            )
            for check_type, count in found.items()
        ),
        key=lambda c: (not c.critical, -c.found, c.check_type),
    )


def run_detail(
    *, session: Session, run: Run, offset: int, limit: int
) -> tuple[TestRunDetailPublic, bool]:
    """The run with its rule totals, then a page of its simulated calls."""
    calls = calls_of_runs(session=session, run_ids=[run.id])[run.id]
    verdicts = verdicts_of_runs(session=session, run_ids=[run.id])[run.id]
    rules = (
        {
            rule.key: rule
            for rule in rules_of_specs(session=session, spec_ids=[run.spec_id]).get(
                run.spec_id, []
            )
        }
        if run.spec_id
        else {}
    )
    totals = _rule_totals(verdicts, rules)
    summary = _summary(run, calls, totals, _spec_versions(session, [run]))
    scenario_ids = list(dict.fromkeys(c.test_case_id for c in calls))
    listed = rules_of(session=session, test_case_ids=scenario_ids)
    dropped = sorted(
        {key for keys in listed.values() for key in keys if key not in rules}
    )
    by_call: dict[uuid.UUID, list[RuleVerdict]] = {}
    for verdict in verdicts:
        by_call.setdefault(verdict.test_case_result_id, []).append(verdict)
    page = calls[offset : offset + limit]
    names = dict(
        session.exec(
            select(TestCase.id, TestCase.name).where(
                col(TestCase.id).in_({c.test_case_id for c in page})
            )
        ).all()
    )
    detail = TestRunDetailPublic(
        **summary.model_dump(),
        rules=totals,
        dropped_rules=dropped,
        checks=_check_totals(calls),
        calls=[
            SimulatedCallPublic(
                id=call.id,
                scenario_id=call.test_case_id,
                scenario_name=names.get(call.test_case_id, ""),
                repeat=call.repetition_index + 1,
                finished=call.completed_at is not None,
                error=call.error_message,
                turns=call.turn_count,
                verdicts=[
                    VerdictPublic(
                        key=v.rule_key,
                        outcome=v.outcome,
                        reason=v.reason,
                        turns=v.turns or [],
                    )
                    for v in sorted(
                        by_call.get(call.id, []),
                        key=lambda v: (v.outcome is not RuleOutcome.FAILED, v.rule_key),
                    )
                ],
                findings=[
                    SimulatedFinding.model_validate(f)
                    for f in call.check_findings or []
                ],
                default_fakes=call.default_fakes or [],
                cost_usd=call.estimated_cost_usd,
                url=simulated_call_url(call.id),
            )
            for call in page
        ],
    )
    return detail, len(calls) > offset + limit


# ── A version's results ───────────────────────────────────────────

# The version fails when more than this share of the non-critical rules judged failed
# (`plans/2026-11-17-test-results.md`, question 3; `testing.md` open question 1).
WARNING_THRESHOLD_PCT = 20


def _group_key(run: Run) -> tuple[str | None, str | None]:
    return run.platform_version, run.version_fingerprint


def _verdict_of(
    totals: list[RuleTotalPublic], checks: list[CheckTotalPublic], tested: bool
) -> dict[str, Any]:
    critical_failed = [t.key for t in totals if t.critical and t.failed]
    critical_checks = [c.check_type for c in checks if c.critical]
    judged = [t for t in totals if not t.critical and (t.passed or t.failed)]
    failed = [t for t in judged if t.failed]
    over = bool(judged) and len(failed) * 100 > WARNING_THRESHOLD_PCT * len(judged)
    # A verdict needs a rule judged: runs whose simulated calls all failed before a
    # judge saw them checked nothing, whatever the code checks found on them (Dmytro,
    # 2026-11-19: "Verdict only happens when all rules checked so not tested"; the
    # all-rules part comes with the full-run verdict).
    checked = any(t.passed or t.failed for t in totals)
    if not tested or not checked:
        verdict = VersionVerdict.NOT_TESTED
    elif critical_failed or critical_checks or over:
        verdict = VersionVerdict.FAILED
    else:
        verdict = VersionVerdict.VERIFIED
    return {
        "verdict": verdict,
        "critical_failed": critical_failed,
        "critical_checks": critical_checks,
        "warnings": len(failed) + sum(1 for c in checks if not c.critical),
        "non_critical_judged": len(judged),
        "non_critical_failed": len(failed),
        "threshold_pct": WARNING_THRESHOLD_PCT,
        "over_threshold": over,
    }


@dataclass(frozen=True)
class VersionUnderTest:
    results: VersionResultsPublic
    counted: list[Run]
    calls: list[TestCaseResult]
    verdicts: list[RuleVerdict]


def version_tested(
    session: Session, agent: Agent, version: str | None
) -> "VersionUnderTest | None":
    runs = runs_of_agent(session=session, agent_id=agent.id)
    if version is not None:
        runs_of_number = [r for r in runs if r.platform_version == version]
        if not runs_of_number:
            return None
        key = _group_key(runs_of_number[-1])
    elif runs:
        key = _group_key(runs[-1])
    else:
        return None
    group = [r for r in runs if _group_key(r) == key]
    edited = group[0].id in edited_runs(runs)
    counted = [r for r in group if r.status == RunStatus.COMPLETED]
    ids = [r.id for r in counted]
    calls = calls_of_runs(session=session, run_ids=ids)
    verdicts = verdicts_of_runs(session=session, run_ids=ids)
    newest_spec = next((r.spec_id for r in reversed(counted) if r.spec_id), None)
    rules = (
        {
            rule.key: rule
            for rule in rules_of_specs(session=session, spec_ids=[newest_spec]).get(
                newest_spec, []
            )
        }
        if newest_spec
        else {}
    )
    all_verdicts = [v for i in ids for v in verdicts[i]]
    totals = _rule_totals(all_verdicts, rules)
    all_calls = [c for i in ids for c in calls[i]]
    checks = _check_totals(all_calls)
    spec_versions = _spec_versions(session, counted)
    results = VersionResultsPublic(
        version=key[0],
        edited=edited,
        first_run_at=group[0].created_at,
        last_run_at=group[-1].created_at,
        rules=totals,
        checks=checks,
        runs=[
            _summary(
                run,
                calls[run.id],
                _rule_totals(verdicts[run.id], {}),
                spec_versions,
            )
            for run in reversed(counted)
        ],
        coverage=coverage_of(session=session, agent=agent, totals=totals),
        stopped=stopped_calls(all_calls),
        **_verdict_of(totals, checks, tested=bool(counted)),
    )
    return VersionUnderTest(
        results=results, counted=counted, calls=all_calls, verdicts=all_verdicts
    )


def stopped_calls(calls: list[TestCaseResult]) -> StoppedCallsPublic | None:
    """The simulated calls that ended in an error, with the most common one."""
    stopped = [c for c in calls if c.error_message]
    if not stopped:
        return None
    kinds = Counter(_error_kind(c.error_message or "") for c in stopped)
    kind, _ = kinds.most_common(1)[0]
    example = next(c for c in stopped if _error_kind(c.error_message or "") == kind)
    return StoppedCallsPublic(
        calls=len(stopped), reason=example.error_message or "", run_id=example.run_id
    )


# Ids that make the same error read differently on every call.
_ERROR_IDS = re.compile(
    r"req_[A-Za-z0-9]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def _error_kind(message: str) -> str:
    """An error with its request and call ids taken out, so the same error on many
    calls counts as one."""
    return _ERROR_IDS.sub("", message)


def coverage_of(
    *, session: Session, agent: Agent, totals: list[RuleTotalPublic]
) -> CoveragePublic | None:
    """How much of the agent's latest spec ``totals`` checked; ``None`` without a spec.

    A rule is checked when it was judged Passed or Failed at least once. One that was
    not says why: no scenario lists it, or its scenarios never reached it.
    """
    spec = latest_spec(session=session, agent_id=agent.id)
    if spec is None:
        return None
    rules = rules_of_specs(session=session, spec_ids=[spec.id]).get(spec.id, [])
    judged = {t.key for t in totals if t.passed or t.failed}
    listed = scenarios_by_rule(session=session, agent_id=agent.id)
    categories = crud.categories_by_id(session=session)
    unchecked = [
        UncheckedRulePublic(
            key=rule.key,
            text=rule.text,
            category=categories[rule.category_id].name
            if rule.category_id in categories
            else "Other",
            critical=rule.critical,
            why="did_not_come_up" if listed.get(rule.key) else "no_scenario",
        )
        for rule in rules
        if rule.key not in judged
    ]
    unchecked.sort(key=lambda u: not u.critical)
    checked = len(rules) - len(unchecked)
    return CoveragePublic(
        rules=len(rules),
        checked=checked,
        pct=(checked * 100 // len(rules)) if rules else 0,
        unchecked=unchecked,
    )


def version_results(
    *, session: Session, agent: Agent, version: str | None
) -> VersionResultsPublic | None:
    """The results of one tested version: ``version`` by its number, or the version of
    the newest run. ``None`` when the agent has no such run.

    Runs are grouped by the version number and the content they tested. Every completed
    run of the group counts: sets, picks and every scenario alike.
    """
    found = version_tested(session, agent, version)
    return found.results if found else None
