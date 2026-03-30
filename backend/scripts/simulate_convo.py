#!/usr/bin/env python3
"""Print a simulated user ↔ agent conversation using the orchestrator + user simulator.

Requires a running agent HTTP server. Use ``examples/mock_agent/main.py`` (LiteLLM +
tools; set provider API keys like the rest of the backend). Default listen URL:
``http://127.0.0.1:8001/agent/respond``. Optional: ``MOCK_AGENT_MODEL`` (default
``gpt-4o-mini``).

Setup and run (two terminals from repo root)::

    cd backend && uv sync && source .venv/bin/activate

    # Terminal A — mock agent (needs LLM credentials)
    uv run python ../examples/mock_agent/main.py

    # Terminal B — simulation (default: LLM user from scenario persona; needs platform LLM keys)
    uv run python scripts/simulate_convo.py \\
        --agent-url http://127.0.0.1:8001/agent/respond \\
        --scenario ../examples/scenarios/normal-refund-request.json

Fixed replay lines instead of an LLM user (no simulator LLM calls)::

    uv run python scripts/simulate_convo.py --agent-url ... --scenario ... --scripted
"""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from app.models.enums import SimulatorMode, TurnRole
from app.models.scenario import Scenario
from app.models.schemas import (
    ConversationTurn,
    JudgeConfig,
    JudgeVerdict,
    RunConfig,
    SimulatorConfig,
)
from app.services.orchestrator import (
    ScenarioRunResult,
    run_scenario,
    run_scenario_with_evaluation,
)


def _load_scenario(path: Path) -> Scenario:
    raw: dict = json.loads(path.read_text(encoding="utf-8"))
    if "id" not in raw:
        raw["id"] = str(uuid.uuid4())
    return Scenario.model_validate(raw)


def _print_transcript(transcript: list[ConversationTurn]) -> None:
    role_labels = {
        TurnRole.USER: "User",
        TurnRole.ASSISTANT: "Agent",
        TurnRole.SYSTEM: "System",
        TurnRole.TOOL: "Tool",
    }
    for turn in transcript:
        label = role_labels.get(turn.role, turn.role.value)
        body = (turn.content or "").strip() or "(no text)"
        print(f"\n[{label}]")
        print(body)
    print()


async def _run(args: argparse.Namespace) -> int:
    scenario_path = Path(args.scenario).resolve()
    scenario = _load_scenario(scenario_path)

    if args.scripted:
        scripted = [s.strip() for s in args.scripted_user.split("|") if s.strip()]
        simulator = SimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=scripted,
        )
    else:
        simulator = SimulatorConfig(
            mode=SimulatorMode.LLM,
            model=args.simulator_model,
            provider=args.simulator_provider,
            temperature=args.simulator_temperature,
        )

    run_cfg = RunConfig(
        timeout_per_scenario_ms=args.timeout_ms,
        judge=JudgeConfig(
            model=args.judge_model,
            provider=args.judge_provider,
        ),
        simulator=simulator,
    )

    if args.judge:
        run_out, verdict = await run_scenario_with_evaluation(
            scenario,
            args.agent_url,
            run_cfg,
            agent_system_prompt=None,
            agent_tools=None,
        )
        transcript = run_out.transcript
    else:
        run_out = await run_scenario(
            scenario,
            args.agent_url,
            run_cfg,
        )
        transcript = run_out.transcript
        verdict = None

    print(f"Scenario: {scenario.name} ({scenario_path})")
    print(f"Turns: {len(transcript)}")
    _print_transcript(transcript)
    _print_run_tracking(run_out, verdict)
    if verdict is not None:
        _print_verdict(verdict)
    return 0


def _print_run_tracking(
    run_out: ScenarioRunResult, verdict: JudgeVerdict | None
) -> None:
    print("\n--- Token & cost (same fields persisted on scenario_result) ---")
    print(f"  Agent tokens:      {json.dumps(run_out.agent_token_usage)}")
    print(f"  Platform tokens:   {json.dumps(run_out.platform_token_usage)}")
    print(f"  Agent cost USD:    {run_out.agent_cost_usd:.6f}")
    print(f"  Platform cost USD: {run_out.platform_cost_usd:.6f}")
    total = run_out.agent_cost_usd + run_out.platform_cost_usd
    if verdict is not None:
        if verdict.judge_token_usage:
            print(f"  Judge tokens:      {json.dumps(verdict.judge_token_usage)}")
        if verdict.judge_latency_ms is not None:
            print(f"  Judge latency ms:  {verdict.judge_latency_ms}")
        if verdict.judge_cost_usd is not None:
            print(f"  Judge cost USD:    {verdict.judge_cost_usd:.6f}")
            total += verdict.judge_cost_usd
    print(f"  Scenario total USD: {total:.6f}")
    print()


def _print_verdict(verdict: JudgeVerdict) -> None:
    print("\n--- Judge verdict ---")
    print(f"Passed: {verdict.passed}")
    print(f"Overall score: {verdict.overall_score}")
    for ms in verdict.metric_scores:
        kind = "binary" if ms.is_binary else "scored"
        j = ms.justification
        fc = f" failure_code={ms.failure_code}" if ms.failure_code else ""
        turns = f" turns={ms.turns}" if ms.turns else ""
        print(
            f"  - {ms.metric} ({kind}): {ms.score} ({ms.label}) "
            f"weight={ms.weight:.4f}{fc}{turns} — {j}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-url",
        required=True,
        help="Full URL for POST (e.g. http://127.0.0.1:8001/agent/respond for mock_agent/main.py)",
    )
    parser.add_argument(
        "--scenario",
        required=True,
        type=Path,
        help="Path to scenario JSON (e.g. examples/scenarios/normal-refund-request.json)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=120_000,
        help="Per-scenario timeout for agent HTTP calls",
    )
    parser.add_argument(
        "--scripted",
        action="store_true",
        help=(
            "Replay fixed user lines from --scripted-user after initial_message "
            "(no LLM user simulator)"
        ),
    )
    parser.add_argument(
        "--scripted-user",
        default="My order number is ORD-12345.|Yes, a full refund to the original card please.|That's perfect, thank you!",
        help="With --scripted: user replies after the first message, separated by |",
    )
    parser.add_argument(
        "--simulator-model",
        default=None,
        help="Simulator LLM model (default user mode; RunConfig.simulator.model)",
    )
    parser.add_argument(
        "--simulator-provider",
        default=None,
        help="Simulator LLM provider override",
    )
    parser.add_argument(
        "--simulator-temperature",
        type=float,
        default=None,
        help="Simulator temperature (default LLM user mode)",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Run LLM judge after simulation (needs LLM credentials; uses RunConfig judge_model/provider)",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help="Judge model override (passed into RunConfig.judge_model)",
    )
    parser.add_argument(
        "--judge-provider",
        default=None,
        help="Judge provider override (passed into RunConfig.judge_provider)",
    )
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
