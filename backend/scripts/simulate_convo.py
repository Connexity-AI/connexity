#!/usr/bin/env python3
"""Print a simulated user ↔ agent conversation using the orchestrator + user simulator.

**Endpoint agent** — POST to a running HTTP agent (e.g. ``examples/mock_agent/main.py``).
Default URL: ``http://127.0.0.1:8001/agent/respond``. Set provider API keys like the
rest of the backend.

**Platform agent** — same system prompt and tool definitions as ``mock_agent/main.py``
(loaded at runtime; that file is not modified), but the platform runs the agent turn via
:class:`~app.services.agent_simulator.AgentSimulator` / LiteLLM. Tool results are
synthetic placeholders (see agent simulator), not the mock server's tool registry.

Setup and run (repo root paths shown; run from ``backend/``)::

    cd backend && uv sync && source .venv/bin/activate

    # Terminal A — optional: mock HTTP agent
    uv run python ../examples/mock_agent/main.py

    # Terminal B — HTTP agent (LLM user from scenario persona; needs LLM keys)
    uv run python scripts/simulate_convo.py \\
        --agent-url http://127.0.0.1:8001/agent/respond \\
        --scenario ../examples/scenarios/normal-refund-request.json

    # Same scenario, agent simulated on-platform (mock_agent prompt + tools JSON)
    uv run python scripts/simulate_convo.py \\
        --platform-agent \\
        --scenario ../examples/scenarios/normal-refund-request.json

Fixed replay lines instead of an LLM user (no simulator LLM calls)::

    uv run python scripts/simulate_convo.py --agent-url ... --scenario ... --scripted
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import uuid
from pathlib import Path
from typing import Any

from app.models.enums import AgentMode, SimulatorMode, TurnRole
from app.models.scenario import Scenario
from app.models.schemas import (
    AgentSimulatorConfig,
    ConversationTurn,
    JudgeConfig,
    JudgeVerdict,
    RunConfig,
    UserSimulatorConfig,
)
from app.services.orchestrator import (
    ScenarioRunResult,
    run_scenario,
    run_scenario_with_evaluation,
)


def _repo_root() -> Path:
    """``backend/scripts/simulate_convo.py`` → repository root."""
    return Path(__file__).resolve().parents[2]


def _load_mock_agent_prompt_tools() -> tuple[str, list[dict[str, Any]]]:
    """Import ``SYSTEM_PROMPT`` and ``TOOLS`` from ``examples/mock_agent/main.py``."""
    main_py = _repo_root() / "examples" / "mock_agent" / "main.py"
    if not main_py.is_file():
        msg = f"Mock agent example not found at {main_py}"
        raise FileNotFoundError(msg)
    spec = importlib.util.spec_from_file_location(
        "connexity_mock_agent_example",
        main_py,
    )
    if spec is None or spec.loader is None:
        msg = f"Could not load module spec for {main_py}"
        raise RuntimeError(msg)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prompt = getattr(mod, "SYSTEM_PROMPT", None)
    tools = getattr(mod, "TOOLS", None)
    if not isinstance(prompt, str) or not prompt.strip():
        msg = "examples/mock_agent/main.py must define non-empty SYSTEM_PROMPT"
        raise RuntimeError(msg)
    if not isinstance(tools, list):
        msg = "examples/mock_agent/main.py must define TOOLS as a list"
        raise RuntimeError(msg)
    return prompt, tools


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
        user_simulator = UserSimulatorConfig(
            mode=SimulatorMode.SCRIPTED,
            scripted_messages=scripted,
        )
    else:
        user_simulator = UserSimulatorConfig(
            mode=SimulatorMode.LLM,
            model=args.simulator_model,
            provider=args.simulator_provider,
            temperature=args.simulator_temperature,
        )

    agent_mode = AgentMode.PLATFORM if args.platform_agent else AgentMode.ENDPOINT
    agent_url: str | None = None if args.platform_agent else args.agent_url
    agent_system_prompt: str | None = None
    agent_tools: list[dict[str, Any]] | None = None
    agent_model: str | None = None
    agent_provider: str | None = None
    agent_sim_cfg: AgentSimulatorConfig | None = None

    if args.platform_agent:
        agent_system_prompt, agent_tools = _load_mock_agent_prompt_tools()
        agent_model = args.agent_model or os.getenv("MOCK_AGENT_MODEL", "gpt-4o-mini")
        agent_provider = args.agent_provider
        if args.agent_temperature is not None or args.agent_max_tokens is not None:
            agent_sim_cfg = AgentSimulatorConfig(
                temperature=args.agent_temperature,
                max_tokens=args.agent_max_tokens,
            )

    run_cfg = RunConfig(
        timeout_per_scenario_ms=args.timeout_ms,
        judge=JudgeConfig(
            model=args.judge_model,
            provider=args.judge_provider,
        ),
        user_simulator=user_simulator,
        agent_simulator=agent_sim_cfg,
    )

    run_kw: dict[str, Any] = {
        "agent_mode": agent_mode,
        "agent_model": agent_model,
        "agent_provider": agent_provider,
        "agent_system_prompt": agent_system_prompt,
        "agent_tools": agent_tools,
    }

    if args.judge:
        run_out, verdict = await run_scenario_with_evaluation(
            scenario,
            agent_url,
            run_cfg,
            **run_kw,
        )
        transcript = run_out.transcript
    else:
        run_out = await run_scenario(
            scenario,
            agent_url,
            run_cfg,
            **run_kw,
        )
        transcript = run_out.transcript
        verdict = None

    mode_note = (
        "platform (mock_agent prompt+tools)" if args.platform_agent else "endpoint"
    )
    print(f"Scenario: {scenario.name} ({scenario_path})  [agent: {mode_note}]")
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
        default=None,
        help=(
            "Full URL for POST (e.g. http://127.0.0.1:8001/agent/respond). "
            "Required unless --platform-agent."
        ),
    )
    parser.add_argument(
        "--platform-agent",
        action="store_true",
        help=(
            "Run the agent via the platform simulator using SYSTEM_PROMPT and TOOLS "
            "from examples/mock_agent/main.py (no HTTP agent; needs LLM keys)."
        ),
    )
    parser.add_argument(
        "--agent-model",
        default=None,
        help=(
            "Platform agent model (default: MOCK_AGENT_MODEL env or gpt-4o-mini). "
            "Only used with --platform-agent."
        ),
    )
    parser.add_argument(
        "--agent-provider",
        default=None,
        help="LiteLLM provider for platform agent (e.g. openai). Only with --platform-agent.",
    )
    parser.add_argument(
        "--agent-temperature",
        type=float,
        default=None,
        help="Optional temperature for platform agent LLM (RunConfig.agent_simulator).",
    )
    parser.add_argument(
        "--agent-max-tokens",
        type=int,
        default=None,
        help="Optional max_tokens for platform agent LLM (RunConfig.agent_simulator).",
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
        help="Per-scenario timeout (orchestrator wall clock; agent HTTP or platform LLM)",
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
        help="User simulator LLM model (RunConfig.user_simulator.model)",
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
    if args.platform_agent == (args.agent_url is not None):
        parser.error("Specify exactly one of: --platform-agent OR --agent-url")
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
