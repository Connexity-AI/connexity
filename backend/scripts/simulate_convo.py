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

    # Terminal B — simulation (scripted user lines; no user LLM)
    uv run python scripts/simulate_convo.py \\
        --agent-url http://127.0.0.1:8001/agent/respond \\
        --scenario ../examples/scenarios/normal-refund-request.json

LLM user simulator (needs ``LITELLM_*`` / provider keys as for the rest of the app)::

    uv run python scripts/simulate_convo.py --agent-url ... --scenario ... --llm-user
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
from app.services.orchestrator import run_scenario, run_scenario_with_evaluation


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

    if args.llm_user:
        simulator = SimulatorConfig(
            mode=SimulatorMode.LLM,
            model=args.simulator_model,
            provider=args.simulator_provider,
            temperature=args.simulator_temperature,
        )
    else:
        scripted = [s.strip() for s in args.scripted_user.split("|") if s.strip()]
        simulator = SimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=scripted,
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
        transcript, verdict = await run_scenario_with_evaluation(
            scenario,
            args.agent_url,
            run_cfg,
            agent_system_prompt=None,
            agent_tools=None,
        )
    else:
        transcript = await run_scenario(
            scenario,
            args.agent_url,
            run_cfg,
        )
        verdict = None

    print(f"Scenario: {scenario.name} ({scenario_path})")
    print(f"Turns: {len(transcript)}")
    _print_transcript(transcript)
    if verdict is not None:
        _print_verdict(verdict)
    return 0


def _print_verdict(verdict: JudgeVerdict) -> None:
    print("\n--- Judge verdict ---")
    print(f"Passed: {verdict.passed}")
    print(f"Overall score: {verdict.overall_score}")
    print(f"Critical failure: {verdict.critical_failure}")
    print(f"Error category: {verdict.error_category.value}")
    for ms in verdict.metric_scores:
        kind = "binary" if ms.is_binary else "scored"
        j = ms.justification
        print(
            f"  - {ms.metric} ({kind}): {ms.score} ({ms.label}) "
            f"weight={ms.weight:.4f} — {j}"
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
        "--llm-user",
        action="store_true",
        help="Use LLM user simulator instead of scripted lines",
    )
    parser.add_argument(
        "--scripted-user",
        default="My order number is ORD-12345.|Yes, a full refund to the original card please.|That's perfect, thank you!",
        help="Scripted user replies after the first message, separated by |",
    )
    parser.add_argument(
        "--simulator-model",
        default=None,
        help="Simulator LLM model (LLM user mode; becomes RunConfig.simulator.model)",
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
        help="Simulator temperature (LLM user mode)",
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
