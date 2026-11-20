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
from typing import Any, Literal

import anyio.from_thread
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
    VerdictMark,
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
    LiveVersionPublic,
    RuleTotalPublic,
    RuleVerdict,
    RunTotalsPublic,
    SameContentPublic,
    SimulatedCallPublic,
    SimulatedFinding,
    StoppedCallsPublic,
    TestRunCountsPublic,
    TestRunDetailPublic,
    TestRunPublic,
    UncheckedRulePublic,
    VerdictPublic,
    VerifiedVersionPublic,
    VersionResultsPublic,
)
from app.models.trace import ToolCallEvent, Trace, TraceEvent, UtteranceEvent
from app.models.user import User
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
    fingerprint: str | None = None
    assistant_name: str | None = None
    session_name: str | None = None


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


@dataclass(frozen=True)
class VersionToTest:
    number: int | None
    # The content it has now; none for a version the assistant named (the run's own
    # read at its start fills it in).
    fingerprint: str | None


async def version_to_test(
    *, session: Session, agent: Agent, asked: int | None
) -> VersionToTest:
    """The version a run will test and its content, read before anything is stored:
    the one asked for, else the agent's newest version on Retell, so a run always has
    one (Dmytro, 2026-11-19). No number for an agent a run refuses anyway (not on
    Retell).

    Raises:
        RunRefused: no version was asked for and Retell could not be read.
    """
    # A version the assistant named is read when the run starts, content included.
    if asked is not None or (
        agent.platform != Platform.RETELL
        or not (agent.integration_id and agent.platform_agent_id)
    ):
        return VersionToTest(number=asked, fingerprint=None)
    integration = session.get(Integration, agent.integration_id)
    api_key = decrypt(integration.encrypted_api_key) if integration else None
    read = (
        await _read_version(api_key, agent.platform_agent_id, None) if api_key else None
    )
    if read is None or read.version is None:
        msg = "Could not read the agent's version on Retell; try again."
        raise RunRefused(
            msg,
            [
                "Retell did not answer with the agent's version, so no run was stored. "
                "Try again in a minute, or pass `version`."
            ],
        )
    return VersionToTest(number=read.version, fingerprint=read.fingerprint)


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
        assistant_name=request.assistant_name,
        session_name=request.session_name,
        platform_version=str(request.version) if request.version is not None else None,
        version_fingerprint=request.fingerprint,
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


def default_fake_turns(
    transcript: list[ConversationTurn], defaults: dict[str, str]
) -> dict[str, int]:
    """Each default-faked tool with the first turn its made-up answer was in the
    conversation: the tool turn that answers the call, else the turn that called it."""
    answered = {
        turn.tool_call_id: turn.index
        for turn in transcript
        if turn.role == TurnRole.TOOL and turn.tool_call_id in defaults
    }
    first: dict[str, int] = {}
    for turn in transcript:
        for call in turn.tool_calls or []:
            if call.id not in defaults:
                continue
            at = answered.get(call.id, turn.index)
            name = defaults[call.id]
            first[name] = min(first.get(name, at), at)
    return first


def rests_on_default_fakes(
    outcome: RuleOutcome, turns: list[int], fake_turns: dict[str, int]
) -> list[str]:
    """The default-faked tools a Passed or Failed verdict rests on: those that had
    answered by the last turn the verdict cites. Such a verdict judges what the agent
    did with a made-up error, so it is marked and not counted (Dmytro, 2026-11-20)."""
    if outcome is RuleOutcome.DID_NOT_COME_UP or not turns:
        return []
    last = max(turns)
    return sorted(name for name, at in fake_turns.items() if at <= last)


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
            fake_turns = default_fake_turns(transcript, defaults)
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
                    rested = {
                        v.key: rests_on_default_fakes(v.outcome, v.turns, fake_turns)
                        for v in judged.verdicts
                    }
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
                            mark=VerdictMark.DEFAULT_FAKE if rested[v.key] else None,
                            mark_detail=rested[v.key] or None,
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
            # One read of the tested version (its number is stored with the run): what
            # it does now (a draft is edited under the same number), and its tools, so
            # a hang-up or a transfer ends the conversation.
            read = await _read_version(
                api_key, agent.platform_agent_id, runtime.version
            )
            if read is not None:
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
        if verdict.mark is VerdictMark.DEFAULT_FAKE:
            # Not evidence: it counts as neither a pass nor a failure.
            total.default_fake += 1
        elif verdict.outcome is RuleOutcome.PASSED:
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


@dataclass(frozen=True)
class _RunFacts:
    """What a run's views are read from, loaded for many runs at once."""

    run: Run
    calls: list[TestCaseResult]
    verdicts: list[RuleVerdict]
    spec_rules: list[SpecRule]
    listed: frozenset[str]


def _facts(session: Session, runs: list[Run]) -> dict[uuid.UUID, _RunFacts]:
    ids = [run.id for run in runs]
    calls = calls_of_runs(session=session, run_ids=ids)
    verdicts = verdicts_of_runs(session=session, run_ids=ids)
    spec_rules = rules_of_specs(
        session=session, spec_ids=list({r.spec_id for r in runs if r.spec_id})
    )
    listing = rules_of(
        session=session,
        test_case_ids=list({c.test_case_id for i in ids for c in calls[i]}),
    )
    return {
        run.id: _RunFacts(
            run=run,
            calls=calls[run.id],
            verdicts=verdicts[run.id],
            spec_rules=spec_rules.get(run.spec_id, []) if run.spec_id else [],
            # What the run's scenarios listed: every rule the judge answered (it
            # answers each listed rule, Didn't come up included), so a scenario edited
            # later does not rewrite the run; the current lists only add rules of
            # calls that stopped before a judge.
            listed=frozenset(v.rule_key for v in verdicts[run.id])
            | frozenset(
                key for c in calls[run.id] for key in listing.get(c.test_case_id, [])
            ),
        )
        for run in runs
    }


type RuleMark = Literal[
    "passed",
    "failed",
    "flaky",
    "did_not_come_up",
    "no_scenario",
    "not_judged",
    "default_fake",
]


def rule_marks(facts: _RunFacts) -> dict[str, RuleMark]:
    """Each rule of the run's spec, once: Failed when any repeat failed it (Flaky when
    another passed it), Passed, Didn't come up when no judged repeat reached it, not
    judged when only calls that stopped listed it, or no scenario of the run lists it
    (Dmytro, 2026-11-19: count rules, and stopped calls in no column). A verdict that
    rests on a default fake is not counted; a rule with only such verdicts is not
    checked (Dmytro, 2026-11-20)."""
    outcomes: dict[str, set[RuleOutcome]] = {}
    marked: set[str] = set()
    for verdict in facts.verdicts:
        if verdict.mark is not None:
            marked.add(verdict.rule_key)
            continue
        outcomes.setdefault(verdict.rule_key, set()).add(verdict.outcome)
    marks: dict[str, RuleMark] = {}
    for rule in facts.spec_rules:
        seen = outcomes.get(rule.key, set())
        if rule.key not in facts.listed:
            marks[rule.key] = "no_scenario"
        elif not seen:
            # Only marked verdicts, or only calls that stopped before a judge, listed
            # it: it counts in no column (Dmytro, 2026-11-19 and 2026-11-20).
            marks[rule.key] = "default_fake" if rule.key in marked else "not_judged"
        elif RuleOutcome.FAILED in seen:
            marks[rule.key] = "flaky" if RuleOutcome.PASSED in seen else "failed"
        elif RuleOutcome.PASSED in seen:
            marks[rule.key] = "passed"
        else:
            marks[rule.key] = "did_not_come_up"
    return marks


def _run_judgement(
    facts: _RunFacts,
) -> tuple[RunTotalsPublic, list[str], list[str]]:
    """The run's totals, its failed critical rules and its critical code checks."""
    marks = rule_marks(facts)
    critical = {rule.key for rule in facts.spec_rules if rule.critical}
    failed = [k for k, m in marks.items() if m in ("failed", "flaky")]
    critical_failed = [k for k in failed if k in critical]
    # Calls that stopped count in no column, their code checks included.
    judged = {v.test_case_result_id for v in facts.verdicts}
    critical_checks = [
        c.check_type
        for c in _check_totals([call for call in facts.calls if call.id in judged])
        if c.critical
    ]
    totals = RunTotalsPublic(
        rules=len(facts.spec_rules),
        passed=sum(1 for m in marks.values() if m == "passed"),
        failed=len(failed),
        did_not_come_up=sum(1 for m in marks.values() if m == "did_not_come_up"),
        no_scenario=sum(1 for m in marks.values() if m == "no_scenario"),
        not_judged=sum(1 for m in marks.values() if m == "not_judged"),
        default_fake=sum(1 for m in marks.values() if m == "default_fake"),
        judged_calls=len(judged),
        critical=len(critical_failed) + len(critical_checks),
        stopped=sum(1 for c in facts.calls if c.error_message),
    )
    return totals, critical_failed, critical_checks


def _verdict(totals: RunTotalsPublic) -> VersionVerdict:
    """A full run's verdict (Dmytro, 2026-11-19): Verified only when every spec rule
    was checked and nothing critical was found; non-critical failures never fail it."""
    checked = totals.passed + totals.failed
    if not checked:
        return VersionVerdict.NOT_VERIFIED
    if totals.critical:
        return VersionVerdict.FAILED
    if checked < totals.rules:
        return VersionVerdict.PARTIAL
    return VersionVerdict.VERIFIED


def _people(session: Session, runs: list[Run]) -> dict[uuid.UUID, str]:
    ids = {run.created_by for run in runs if run.created_by}
    if not ids:
        return {}
    return {
        user.id: user.full_name or user.email
        for user in session.exec(select(User).where(col(User.id).in_(ids))).all()
    }


def _content(
    run: Run, now: dict[str, str], newest: dict[str, str]
) -> Literal["same", "edited", "unknown"]:
    """Whether ``run``'s version still has the content the run tested. ``now`` is what
    the platform holds, by version number, where it was just read; without a read, a
    later run of the same number that saw other content still proves an edit, and
    nothing proves the content is the same."""
    tested, number = run.version_fingerprint, run.platform_version
    if tested is None or number is None:
        return "unknown"
    if number in now:
        return "same" if now[number] == tested else "edited"
    return "edited" if newest.get(number, tested) != tested else "unknown"


def _spec_behind(run: Run, spec: Spec | None) -> bool:
    """The run tested an agent version newer than the one its spec's rules were
    written for, so it judged new behaviour against older rules."""
    if spec is None or run.platform_version is None:
        return False
    written = version_number(spec.written_for or spec.agent_version)[0]
    tested = version_number(run.platform_version)[0]
    return written >= 0 and tested > written


def run_views(
    session: Session,
    runs: list[Run],
    now: dict[str, str] | None = None,
    history: list[Run] | None = None,
) -> list[TestRunPublic]:
    """Each run as one row: what it is, its totals, and who ran it. ``now`` is the
    content the platform holds now, by version number, for the versions just read;
    ``history`` is every run of the agent, oldest first, when the caller has it."""
    facts = _facts(session, runs)
    specs = _specs(session, runs)
    people = _people(session, runs)
    now = now or {}
    checked_at = datetime.now(UTC) if now else None
    # What the newest run of each version number saw.
    newest: dict[str, str] = {}
    if history is None:
        history = [
            other
            for agent_id in {run.agent_id for run in runs}
            for other in runs_of_agent(session=session, agent_id=agent_id)
        ]
    for other in history:
        if other.platform_version and other.version_fingerprint:
            newest[other.platform_version] = other.version_fingerprint
    out: list[TestRunPublic] = []
    for run in runs:
        assert run.scope is not None
        fact = facts[run.id]
        spec = specs.get(run.spec_id) if run.spec_id else None
        full = run.scope is RunScope.ALL
        done = run.status == RunStatus.COMPLETED
        totals = _run_judgement(fact)[0] if done else None
        result: Literal["passed", "failed"] | None = None
        # A run no judge read has no result (Dmytro, 2026-11-19: "No result").
        # Nor has one whose every verdict rests on a default fake: nothing was checked.
        if (
            totals is not None
            and not full
            and totals.judged_calls
            and (
                totals.passed
                or totals.failed
                or totals.critical
                or not totals.default_fake
            )
        ):
            result = "failed" if totals.failed or totals.critical else "passed"
        out.append(
            TestRunPublic(
                id=run.id,
                status=run.status,
                status_detail=run.status_detail,
                scope=run.scope,
                set_name=run.set_name,
                repeats=run.repeats or 1,
                spec_version=spec.version if spec else None,
                spec_written_for=(spec.written_for or spec.agent_version)
                if spec
                else None,
                spec_behind=_spec_behind(run, spec),
                platform_version=run.platform_version,
                content=_content(run, now, newest),
                content_checked_at=checked_at
                if run.platform_version in now and run.version_fingerprint
                else None,
                created_at=run.created_at,
                started_at=run.started_at,
                completed_at=run.completed_at,
                counts=_counts(fact.calls, _rule_totals(fact.verdicts, {})),
                cost_usd=_cost(fact.calls),
                full=full,
                verdict=_verdict(totals) if totals is not None and full else None,
                result=result,
                totals=totals,
                ran_by=people.get(run.created_by) if run.created_by else None,
                assistant_name=run.assistant_name,
                session_name=run.session_name,
            )
        )
    return out


def _specs(session: Session, runs: list[Run]) -> dict[uuid.UUID, Spec]:
    out: dict[uuid.UUID, Spec] = {}
    for spec_id in {run.spec_id for run in runs if run.spec_id}:
        spec = session.get(Spec, spec_id)
        if spec is not None:
            out[spec_id] = spec
    return out


def list_runs(
    *, session: Session, agent: Agent, offset: int, limit: int
) -> tuple[list[TestRunPublic], bool]:
    runs, more = runs_page(
        session=session, agent_id=agent.id, offset=offset, limit=limit
    )
    return run_views(session, runs), more


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
    *,
    session: Session,
    run: Run,
    offset: int,
    limit: int,
    content_now: str | None = None,
) -> tuple[TestRunDetailPublic, bool]:
    """The run with its rule totals, then a page of its simulated calls.
    ``content_now`` is its version's content on the platform, when just read."""
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
    summary = run_views(session, [run], _now(run.platform_version, content_now))[0]
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
                        mark=v.mark,
                        mark_detail=v.mark_detail or [],
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


@dataclass(frozen=True)
class VersionUnderTest:
    results: VersionResultsPublic
    full_run: Run | None
    marks: dict[str, RuleMark]


def version_number(text: str | None) -> tuple[int, str]:
    return (int(text), "") if text and text.isdigit() else (-1, text or "")


def _now(version: str | None, content: str | None) -> dict[str, str]:
    return {version: content} if version is not None and content is not None else {}


def _target(runs: list[Run], live: str | None, version: str | None) -> str | None:
    """The version results are about: the one asked for, else the newest tested
    version, live or not (Dmytro, 2026-11-19: the runner tests Retell's newest
    version, which can be a draft ahead of the live one), else the live one."""
    if version is not None:
        return version
    tested = [r.platform_version for r in runs if r.platform_version is not None]
    return max(tested, key=version_number) if tested else live


def results_version(
    *, session: Session, agent: Agent, version: str | None
) -> str | None:
    """The version ``version_results`` answers about, so its content can be read on
    the platform first."""
    return _target(
        runs_of_agent(session=session, agent_id=agent.id),
        crud.current_agent_version(session=session, agent_id=agent.id),
        version,
    )


def read_content_now(
    *, session: Session, agent: Agent, version: str | None
) -> str | None:
    """The content version ``version`` of the agent holds on Retell right now, as a
    fingerprint; none when it cannot be read (not on Retell, not a number, or Retell
    did not answer), and then nothing is claimed about it.

    Called from a route's worker thread: the read itself runs on the event loop,
    and the database work around it stays off it, where runs are executing.
    """
    if (
        version is None
        or not version.isdigit()
        or agent.platform != Platform.RETELL
        or not (agent.integration_id and agent.platform_agent_id)
    ):
        return None
    integration = session.get(Integration, agent.integration_id)
    if integration is None:
        return None
    read = anyio.from_thread.run(
        _read_version,
        decrypt(integration.encrypted_api_key),
        agent.platform_agent_id,
        int(version),
    )
    return read.fingerprint if read is not None else None


def version_tested(
    session: Session,
    agent: Agent,
    version: str | None,
    content_now: str | None = None,
) -> VersionUnderTest:
    """One version's verdict from its latest completed full run, and its runs.

    The version is ``version``, else the newest tested one, else the agent's live
    version (its most recent call's). Runs of a set or a pick are listed but never
    decide. ``content_now`` is the version's content on the platform when it was just
    read: an edit made after the newest run then shows, and that run no longer counts.
    """
    runs = runs_of_agent(session=session, agent_id=agent.id)
    live = crud.current_agent_version(session=session, agent_id=agent.id)
    target = _target(runs, live, version)

    def is_mine(run: Run) -> bool:
        return run.platform_version == target

    mine = [r for r in runs if is_mine(r)]
    fulls = [
        r for r in runs if r.scope is RunScope.ALL and r.status == RunStatus.COMPLETED
    ]
    # Verified belongs to the content that passed (Dmytro, 2026-11-19): the version's
    # content now is what its newest run tested, and the verdict comes from the latest
    # full run of that content, this version's first, else another number's.
    own_full = next((r for r in reversed(fulls) if is_mine(r)), None)
    # What the version holds now: just read on the platform, else what the newest run
    # saw; none when that read failed, and then nothing is known to have changed.
    content = content_now or (mine[-1].version_fingerprint if mine else None)
    edited_since: datetime | None = None
    if content is None:
        full = own_full
    else:
        full = next(
            (
                r
                for r in reversed(fulls)
                if is_mine(r) and r.version_fingerprint == content
            ),
            None,
        ) or next(
            (r for r in reversed(fulls) if r.version_fingerprint == content), None
        )
        if full is None and own_full is not None:
            if own_full.version_fingerprint is None:
                # Its full run could not read its content: it still counts.
                full = own_full
            else:
                edited_since = own_full.completed_at or own_full.created_at
    facts = _facts(session, [full]) if full is not None else {}

    def latest_full_verdict(of: str) -> tuple[VersionVerdict, Run | None]:
        run = next((r for r in reversed(fulls) if r.platform_version == of), None)
        if run is None:
            return VersionVerdict.NOT_VERIFIED, None
        return _verdict(_run_judgement(_facts(session, [run])[run.id])[0]), run

    # The newest other version a full run verified: each version's latest full run,
    # newest first, read one at a time until one verified.
    last_verified: VerifiedVersionPublic | None = None
    seen: set[str] = set()
    for r in reversed(fulls):
        if r.platform_version is None or is_mine(r) or r.platform_version in seen:
            continue
        seen.add(r.platform_version)
        verdict, _run = latest_full_verdict(r.platform_version)
        if verdict is VersionVerdict.VERIFIED:
            last_verified = VerifiedVersionPublic(
                version=r.platform_version, at=r.completed_at or r.created_at
            )
            break
    # The live version's state, beside a tested version that is not live.
    live_state: LiveVersionPublic | None = None
    if live is not None and live != target:
        verdict, run = latest_full_verdict(live)
        live_state = LiveVersionPublic(
            version=live,
            verdict=verdict,
            at=(run.completed_at or run.created_at) if run else None,
        )
    views = run_views(
        session, list(reversed(mine)), _now(target, content_now), history=runs
    )
    results = VersionResultsPublic(
        version=target,
        edited_since=edited_since,
        live_version=live,
        live=live_state,
        verdict=VersionVerdict.NOT_VERIFIED,
        last_verified=last_verified,
        runs=views,
        coverage=coverage_of(session=session, agent=agent),
    )
    marks: dict[str, RuleMark] = {}
    if full is not None:
        fact = facts[full.id]
        totals, critical_failed, critical_checks = _run_judgement(fact)
        marks = rule_marks(fact)
        categories = crud.categories_by_id(session=session)
        rules = {rule.key: rule for rule in fact.spec_rules}
        results.verdict = _verdict(totals)
        if is_mine(full):
            results.full_run = next(v for v in views if v.id == full.id)
        else:
            results.full_run = run_views(session, [full], history=runs)[0]
            results.same_content = SameContentPublic(
                version=full.platform_version or "",
                run_id=full.id,
                at=full.completed_at or full.created_at,
            )
        results.critical_failed = critical_failed
        results.critical_checks = critical_checks
        results.rules = _rule_totals(fact.verdicts, rules)
        # Like the counts, the code checks of calls a judge read only.
        judged = {v.test_case_result_id for v in fact.verdicts}
        results.checks = _check_totals([c for c in fact.calls if c.id in judged])
        results.unchecked = sorted(
            (
                UncheckedRulePublic(
                    key=rule.key,
                    text=rule.text,
                    category=categories[rule.category_id].name
                    if rule.category_id in categories
                    else "Other",
                    critical=rule.critical,
                    why=marks[rule.key],  # type: ignore[arg-type]
                )
                for rule in fact.spec_rules
                if marks[rule.key]
                in ("no_scenario", "did_not_come_up", "not_judged", "default_fake")
            ),
            key=lambda u: not u.critical,
        )
        results.stopped = stopped_calls(fact.calls)
    return VersionUnderTest(results=results, full_run=full, marks=marks)


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


def coverage_of(*, session: Session, agent: Agent) -> CoveragePublic | None:
    """Tests written (Dmytro, 2026-11-19): the share of the agent's latest spec's rules
    that at least one active scenario lists; ``None`` without a spec."""
    spec = latest_spec(session=session, agent_id=agent.id)
    if spec is None:
        return None
    rules = rules_of_specs(session=session, spec_ids=[spec.id]).get(spec.id, [])
    listed = scenarios_by_rule(session=session, agent_id=agent.id)
    categories = crud.categories_by_id(session=session)
    uncovered = sorted(
        (
            UncheckedRulePublic(
                key=rule.key,
                text=rule.text,
                category=categories[rule.category_id].name
                if rule.category_id in categories
                else "Other",
                critical=rule.critical,
                why="no_scenario",
            )
            for rule in rules
            if not listed.get(rule.key)
        ),
        key=lambda u: not u.critical,
    )
    covered = len(rules) - len(uncovered)
    return CoveragePublic(
        rules=len(rules),
        covered=covered,
        pct=(covered * 100 // len(rules)) if rules else 0,
        uncovered=uncovered,
    )


def version_results(
    *,
    session: Session,
    agent: Agent,
    version: str | None,
    content_now: str | None = None,
) -> VersionResultsPublic | None:
    """One version's results (see ``version_tested``); ``None`` when ``version`` was
    given and no run tested it."""
    found = version_tested(session, agent, version, content_now)
    if version is not None and not found.results.runs:
        return None
    return found.results
