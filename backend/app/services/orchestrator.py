"""Run orchestration: load configs, fan out test cases, judge, persist, aggregate.

The orchestrator no longer drives the agent ↔ user-simulator loop itself —
that work lives in the runtime selected via :mod:`app.services.eval_runtimes`.
This module is responsible for:

1. Loading the :class:`Run`, its :class:`EvalConfig`, and the :class:`Agent`.
2. Capturing :class:`AgentSnapshot` / :class:`RunSnapshot` once per run.
3. Running every test case through the selected runtime under a concurrency
   semaphore.
4. Calling the Connexity judge on the runtime's transcript.
5. Computing per-case metrics, persisting results, and aggregating.
"""

import asyncio
import logging
import statistics
import uuid
from datetime import UTC, datetime

from app.models.agent import Agent
from app.models.enums import AgentMode, RunMode, RunStatus, TextRuntimeKind, TurnRole
from app.models.schemas import (
    AggregateMetrics,
    JudgeVerdict,
    RunConfig,
)
from app.models.test_case import TestCase
from app.models.test_case_result import TestCaseResult
from app.services.cost_tracker import (
    sum_platform_usage_dicts,
    sum_usage_dicts,
)
from app.services.eval_runtimes import (
    AgentSnapshot,
    RunSnapshot,
    RuntimeRunArgs,
    get_runtime,
)
from app.services.eval_runtimes.types import TestCaseRunResult
from app.services.judge import JudgeInput, evaluate_transcript

logger = logging.getLogger(__name__)


def _derive_test_case_passed(verdict: JudgeVerdict | None) -> bool:
    """Compute whether a single test case execution passed.

    Per CS-127: a test case passes when *all* of its expected_outcomes pass.
    For legacy test cases without expected_outcomes (or when the judge could
    not produce them), fall back to the judge's overall_score-based verdict.
    """
    if verdict is None:
        return False
    if verdict.expected_outcome_results:
        return all(o.passed for o in verdict.expected_outcome_results)
    return verdict.passed


def compute_aggregate_metrics(
    results: list[TestCaseResult],
    *,
    metrics_pass_threshold: float | None = None,
    cases_pass_threshold: float | None = None,
) -> AggregateMetrics:
    total_executions = len(results)
    if total_executions == 0:
        return AggregateMetrics(
            unique_test_case_count=0,
            total_executions=0,
            passed_count=0,
            failed_count=0,
            error_count=0,
            pass_rate=0.0,
            metrics_pass_threshold=metrics_pass_threshold,
            cases_pass_threshold=cases_pass_threshold,
        )

    unique_test_case_count = len({r.test_case_id for r in results})
    passed = sum(1 for r in results if r.passed is True)
    errored = sum(1 for r in results if r.error_message is not None)
    failed = sum(1 for r in results if r.passed is False and r.error_message is None)

    latencies = [
        r.agent_latency_p50_ms for r in results if r.agent_latency_p50_ms is not None
    ]

    scores = [
        r.verdict.get("overall_score")
        for r in results
        if r.verdict and r.verdict.get("overall_score") is not None
    ]

    agent_parts = [r.agent_token_usage for r in results if r.agent_token_usage]
    total_agent = sum_usage_dicts(*agent_parts) if agent_parts else None
    if not total_agent:
        total_agent = None

    platform_parts = [r.platform_token_usage for r in results if r.platform_token_usage]
    total_platform = (
        sum_platform_usage_dicts(*platform_parts) if platform_parts else None
    )
    if not total_platform:
        total_platform = None

    agent_costs = [r.agent_cost_usd for r in results if r.agent_cost_usd is not None]
    platform_costs = [
        r.platform_cost_usd for r in results if r.platform_cost_usd is not None
    ]
    cost_values = [
        r.estimated_cost_usd for r in results if r.estimated_cost_usd is not None
    ]
    total_cost_usd = sum(cost_values) if cost_values else None

    pass_rate = passed / total_executions if total_executions > 0 else 0.0
    weighted_metrics_score_pct = statistics.mean(scores) if scores else None
    cases_pass_rate_pct = pass_rate * 100.0

    metrics_passed: bool | None
    if metrics_pass_threshold is not None and weighted_metrics_score_pct is not None:
        metrics_passed = weighted_metrics_score_pct >= metrics_pass_threshold
    else:
        metrics_passed = None

    cases_passed: bool | None
    if cases_pass_threshold is not None:
        cases_passed = cases_pass_rate_pct >= cases_pass_threshold
    else:
        cases_passed = None

    return AggregateMetrics(
        unique_test_case_count=unique_test_case_count,
        total_executions=total_executions,
        passed_count=passed,
        failed_count=failed,
        error_count=errored,
        pass_rate=pass_rate,
        latency_p50_ms=statistics.median(latencies) if latencies else None,
        latency_p95_ms=statistics.quantiles(latencies, n=20)[18]
        if len(latencies) >= 20
        else None,
        latency_max_ms=max(latencies) if latencies else None,
        latency_avg_ms=statistics.mean(latencies) if latencies else None,
        total_agent_token_usage=total_agent,
        total_platform_token_usage=total_platform,
        total_agent_cost_usd=sum(agent_costs) if agent_costs else None,
        total_platform_cost_usd=sum(platform_costs) if platform_costs else None,
        total_estimated_cost_usd=total_cost_usd,
        avg_overall_score=weighted_metrics_score_pct,
        weighted_metrics_score_pct=weighted_metrics_score_pct,
        metrics_pass_threshold=metrics_pass_threshold,
        metrics_passed=metrics_passed,
        cases_pass_rate_pct=cases_pass_rate_pct,
        cases_pass_threshold=cases_pass_threshold,
        cases_passed=cases_passed,
    )


def _agent_mode_from_run_config(cfg: RunConfig) -> AgentMode:
    """Infer simulator-facing agent mode from the frozen run configuration.

    ``Run.agent_mode`` remains an audit snapshot of the agent row; execution uses
    ``cfg.mode`` + ``cfg.runtime`` only.
    """

    if cfg.mode != RunMode.TEXT:
        return AgentMode.ENDPOINT
    if cfg.runtime.kind == TextRuntimeKind.CUSTOM_ENDPOINT:
        return AgentMode.ENDPOINT
    return AgentMode.PLATFORM


def _build_agent_snapshot(agent: Agent, run, run_config: RunConfig) -> AgentSnapshot:  # noqa: ANN001
    """Capture the frozen agent state used by every test case in a run.

    ``run`` is the SQLModel :class:`Run` row; importing it would create a
    layering wart in tests that don't construct full Run rows, so we duck-type.
    Effective ``AgentSnapshot.mode`` follows ``run_config`` (see
    :func:`_agent_mode_from_run_config`), not ``run.agent_mode``.
    """
    return AgentSnapshot(
        agent=agent,
        agent_id=agent.id,
        platform=agent.platform,
        integration_id=agent.integration_id,
        platform_agent_id=agent.platform_agent_id,
        endpoint_url=run.agent_endpoint_url,
        system_prompt=run.agent_system_prompt,
        tools=run.agent_tools,
        mode=_agent_mode_from_run_config(run_config),
        model=run.agent_model,
        provider=run.agent_provider,
        version=run.agent_version,
    )


async def _judge_transcript(
    test_case: TestCase,
    run_out: TestCaseRunResult,
    config: RunConfig,
    agent_system_prompt: str | None,
    agent_tools: list[dict] | None,
    company_id: uuid.UUID,
) -> JudgeVerdict | None:
    """Run the Connexity judge on a runtime's transcript; ``None`` if empty."""
    if not run_out.transcript:
        return None
    return await evaluate_transcript(
        JudgeInput(
            transcript=run_out.transcript,
            test_case=test_case,
            agent_system_prompt=agent_system_prompt,
            agent_tools=agent_tools,
            judge_config=config.judge,
            company_id=company_id,
        )
    )


async def _execute_single_test_case(
    run_id: uuid.UUID,
    test_case: TestCase,
    agent_snapshot: AgentSnapshot,
    run_snapshot: RunSnapshot,
    semaphore: asyncio.Semaphore,
    *,
    repetition_index: int = 0,
) -> TestCaseResult:
    from sqlmodel import Session

    from app import crud
    from app.core.db import engine
    from app.models import TestCaseResultCreate, TestCaseResultUpdate
    from app.models.schemas import TestCaseProgressData
    from app.services.run_manager import run_manager

    config = run_snapshot.run_config
    cancel_event = run_snapshot.cancel_event

    with Session(engine) as session:
        result = crud.create_test_case_result(
            session=session,
            result_in=TestCaseResultCreate(
                run_id=run_id,
                test_case_id=test_case.id,
                repetition_index=repetition_index,
            ),
            company_id=run_snapshot.company_id,
        )
        result_id = result.id

    async with semaphore:
        if cancel_event is not None and cancel_event.is_set():
            return result

        run_manager.emit(
            run_id,
            "test_case_started",
            {"test_case_id": str(test_case.id), "test_case_name": test_case.name},
        )

        started_at = datetime.now(UTC)
        try:
            runtime_impl = get_runtime(config.mode, config.runtime.kind)
            runtime_args = RuntimeRunArgs(
                test_case=test_case,
                agent_snapshot=agent_snapshot,
                run_snapshot=run_snapshot,
            )
            with Session(engine) as engine_session:
                run_out = await runtime_impl.run_test_case(
                    config.runtime,
                    runtime_args,
                    engine_session,
                )

            verdict = await _judge_transcript(
                test_case,
                run_out,
                config,
                agent_snapshot.system_prompt,
                agent_snapshot.tools,
                run_snapshot.company_id,
            )

            transcript = run_out.transcript
            completed_at = datetime.now(UTC)

            turn_count = len(transcript)
            total_latency_ms = int((completed_at - started_at).total_seconds() * 1000)

            agent_latencies = [
                t.latency_ms
                for t in transcript
                if t.role == TurnRole.ASSISTANT and t.latency_ms is not None
            ]
            p50 = int(statistics.median(agent_latencies)) if agent_latencies else None
            p95 = (
                int(statistics.quantiles(agent_latencies, n=20)[18])
                if len(agent_latencies) >= 20
                else (max(agent_latencies) if agent_latencies else None)
            )
            max_lat = max(agent_latencies) if agent_latencies else None

            platform_usage = sum_platform_usage_dicts(
                run_out.platform_token_usage,
                verdict.judge_token_usage if verdict else None,
            )
            judge_cost = (verdict.judge_cost_usd or 0.0) if verdict else 0.0
            if verdict and verdict.judge_cost_usd is None:
                logger.warning(
                    "Judge cost unavailable for test_case %s — LiteLLM may lack "
                    "pricing for model %s; judge cost excluded from totals",
                    test_case.id,
                    verdict.judge_model,
                )
            platform_cost = run_out.platform_cost_usd + judge_cost
            agent_cost = run_out.agent_cost_usd
            total_cost = agent_cost + platform_cost
            agent_usage_out = (
                run_out.agent_token_usage if run_out.agent_token_usage else None
            )
            platform_usage_out = platform_usage if platform_usage else None

            update_data = TestCaseResultUpdate(
                transcript=transcript,
                turn_count=turn_count,
                verdict=verdict,
                total_latency_ms=total_latency_ms,
                agent_latency_p50_ms=p50,
                agent_latency_p95_ms=p95,
                agent_latency_max_ms=max_lat,
                agent_latency_per_turn_ms=agent_latencies or None,
                agent_token_usage=agent_usage_out,
                platform_token_usage=platform_usage_out,
                agent_cost_usd=agent_cost or None,
                platform_cost_usd=platform_cost or None,
                estimated_cost_usd=total_cost or None,
                passed=_derive_test_case_passed(verdict),
                started_at=started_at,
                completed_at=completed_at,
            )

        except Exception as e:
            logger.exception("TestCase %s failed unexpectedly", test_case.id)
            completed_at = datetime.now(UTC)
            update_data = TestCaseResultUpdate(
                passed=False,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
            )

        db_persist_failed = False
        try:

            def _update_db():
                with Session(engine) as session:
                    db_result = crud.get_test_case_result(
                        session=session, result_id=result_id
                    )
                    if db_result:
                        return crud.update_test_case_result(
                            session=session,
                            db_result=db_result,
                            result_in=update_data,
                        )
                    return None

            updated_result = await asyncio.to_thread(_update_db)
        except Exception:
            logger.exception(
                "Failed to persist result for test_case %s in run %s",
                test_case.id,
                run_id,
            )
            db_persist_failed = True
            try:

                def _mark_db_error():
                    with Session(engine) as session:
                        db_result = crud.get_test_case_result(
                            session=session, result_id=result_id
                        )
                        if db_result:
                            return crud.update_test_case_result(
                                session=session,
                                db_result=db_result,
                                result_in=TestCaseResultUpdate(
                                    passed=False,
                                    error_message="DB persistence failed for test_case result",
                                    started_at=started_at,
                                    completed_at=datetime.now(UTC),
                                ),
                            )
                        return None

                updated_result = await asyncio.to_thread(_mark_db_error)
            except Exception:
                logger.exception(
                    "Failed to mark DB error for test_case %s in run %s",
                    test_case.id,
                    run_id,
                )
                updated_result = None

        try:
            state = run_manager.get_state(run_id)
            if state:
                async with state.progress_lock:
                    progress = state.progress
                    progress.completed_count += 1
                    if updated_result is None or db_persist_failed:
                        progress.error_count += 1
                    elif updated_result.passed:
                        progress.passed_count += 1
                    elif updated_result.error_message is not None:
                        progress.error_count += 1
                    else:
                        progress.failed_count += 1

                    run_manager.emit(
                        run_id,
                        "test_case_completed",
                        TestCaseProgressData(
                            run_id=run_id,
                            test_case_id=test_case.id,
                            test_case_name=test_case.name,
                            completed_count=progress.completed_count,
                            total_count=progress.total_test_cases,
                            passed=updated_result.passed if updated_result else False,
                            overall_score=updated_result.verdict.get("overall_score")
                            if updated_result and updated_result.verdict
                            else None,
                            error_message=updated_result.error_message
                            if updated_result
                            else "DB persistence failed",
                        ).model_dump(mode="json"),
                    )
        except Exception:
            logger.exception(
                "Failed to emit progress for test_case %s in run %s",
                test_case.id,
                run_id,
            )

        return updated_result or result


async def execute_run(run_id: uuid.UUID) -> None:
    """Top-level orchestration: load run + test cases, execute concurrently, persist."""
    from sqlmodel import Session

    from app import crud
    from app.core.db import engine
    from app.models import RunUpdate
    from app.services.run_manager import run_manager
    from app.services.tenant_llm import (
        CompanyMissingLLMKeyError,
        load_tenant_context,
        set_current_tenant,
    )

    state = run_manager.register(run_id)

    try:
        with Session(engine) as session:
            run = crud.get_run(session=session, run_id=run_id)
            if not run or run.status not in (
                RunStatus.PENDING,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
            ):
                logger.error("Run %s not found or not in executable state", run_id)
                return

            # Bind the tenant LLM context for this entire run so every
            # ``call_llm`` from the judge, simulators, etc. uses the right
            # per-company API key without further plumbing.
            try:
                tenant_ctx = load_tenant_context(
                    session=session, company_id=run.company_id
                )
                set_current_tenant(tenant_ctx)
            except CompanyMissingLLMKeyError as exc:
                logger.error("Run %s blocked: %s", run_id, exc)
                crud.update_run(
                    session=session,
                    db_run=run,
                    run_in=RunUpdate(
                        status=RunStatus.FAILED,
                        completed_at=datetime.now(UTC),
                    ),
                )
                return

            eval_config = crud.get_eval_config(
                session=session, eval_config_id=run.eval_config_id
            )
            if not eval_config:
                logger.error("Run %s references missing eval config", run_id)
                crud.update_run(
                    session=session,
                    db_run=run,
                    run_in=RunUpdate(
                        status=RunStatus.FAILED,
                        completed_at=datetime.now(UTC),
                    ),
                )
                return

            agent = crud.get_agent(session=session, agent_id=run.agent_id)
            if not agent:
                logger.error("Run %s references missing agent", run_id)
                crud.update_run(
                    session=session,
                    db_run=run,
                    run_in=RunUpdate(
                        status=RunStatus.FAILED,
                        completed_at=datetime.now(UTC),
                    ),
                )
                return

            crud.update_run(
                session=session,
                db_run=run,
                run_in=RunUpdate(
                    status=RunStatus.RUNNING, started_at=datetime.now(UTC)
                ),
            )

            execution_plan = crud.get_test_cases_for_config(
                session=session, eval_config_id=run.eval_config_id
            )

            config = RunConfig.model_validate(run.config) if run.config else RunConfig()
            agent_snapshot = _build_agent_snapshot(agent, run, config)
            # Detach from session so background tasks can read attrs without an
            # open Session — only the snapshot fields are touched by runtimes.
            session.expunge(agent)

        run_snapshot = RunSnapshot(
            run_id=run_id,
            company_id=run.company_id,
            run_config=config,
            cancel_event=state.cancel_event,
        )

        total_expanded = sum(entry.repetitions for entry in execution_plan)
        state.progress.total_test_cases = total_expanded
        run_manager.emit(
            run_id,
            "run_started",
            {"run_id": str(run_id), "total_test_cases": total_expanded},
        )

        semaphore = asyncio.Semaphore(config.concurrency)
        tasks = [
            _execute_single_test_case(
                run_id=run_id,
                test_case=entry.test_case,
                agent_snapshot=agent_snapshot,
                run_snapshot=run_snapshot,
                semaphore=semaphore,
                repetition_index=rep,
            )
            for entry in execution_plan
            for rep in range(entry.repetitions)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results: list[TestCaseResult] = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.exception(
                    "TestCase task %d failed for run %s: %s",
                    i,
                    run_id,
                    r,
                    exc_info=r,
                )
            else:
                valid_results.append(r)

        aggregate_metrics = compute_aggregate_metrics(
            valid_results,
            metrics_pass_threshold=config.metrics_pass_threshold,
            cases_pass_threshold=config.cases_pass_threshold,
        )

        with Session(engine) as session:
            db_run = crud.get_run(session=session, run_id=run_id)
            if db_run:
                final_status = (
                    RunStatus.CANCELLED
                    if state.cancel_event.is_set()
                    else RunStatus.COMPLETED
                )
                crud.update_run(
                    session=session,
                    db_run=db_run,
                    run_in=RunUpdate(
                        status=final_status,
                        completed_at=datetime.now(UTC),
                        aggregate_metrics=aggregate_metrics,
                    ),
                )

        event_name = "run_cancelled" if state.cancel_event.is_set() else "run_completed"
        run_manager.emit(run_id, event_name, {"run_id": str(run_id)})

    except Exception as e:
        logger.exception("Run %s failed unexpectedly", run_id)
        with Session(engine) as session:
            db_run = crud.get_run(session=session, run_id=run_id)
            if db_run:
                crud.update_run(
                    session=session,
                    db_run=db_run,
                    run_in=RunUpdate(
                        status=RunStatus.FAILED, completed_at=datetime.now(UTC)
                    ),
                )
        run_manager.emit(run_id, "run_failed", {"run_id": str(run_id), "error": str(e)})
    finally:
        run_manager.unregister(run_id)
