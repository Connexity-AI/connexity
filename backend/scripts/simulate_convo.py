#!/usr/bin/env python3
"""Print a simulated user ↔ agent conversation using the orchestrator + user simulator.

**Endpoint mode** — POST to a running HTTP agent (e.g. ``examples/mock_agent/main.py``).

**Platform mode** — same system prompt and tool definitions as ``mock_agent/main.py``
(loaded at runtime), but the platform runs the agent turn via
:class:`~app.services.agent_simulator.AgentSimulator` / LiteLLM. Use ``--tool-mode``
to control how tool calls are resolved:

* ``synthetic`` (default) — placeholder acknowledgement (no real data).
* ``mock`` — canned responses from each test case's ``mock_responses``.
* ``live`` — Python sandbox execution with hardcoded logic and
  ``context.test_case_context`` (mirrors ``mock_agent`` tool registry).

Setup and run (repo root paths shown; run from ``backend/``)::

    cd backend && uv sync && source .venv/bin/activate

    # Terminal A — optional: mock HTTP agent
    uv run python ../examples/mock_agent/main.py

    # Endpoint mode (LLM user from test case persona; needs LLM keys)
    uv run python scripts/simulate_convo.py \\
        --agent-url http://127.0.0.1:8001/agent/respond \\
        --test-case ../examples/test-cases/normal-refund-request.json

    # Platform mode — synthetic tool results (default, backward compat)
    uv run python scripts/simulate_convo.py \\
        --platform-agent \\
        --test-case ../examples/test-cases/normal-refund-request.json

    # Platform mode — mock tool responses from test case JSON
    uv run python scripts/simulate_convo.py \\
        --platform-agent --tool-mode mock \\
        --test-case ../examples/test-cases/normal-refund-request.json

    # Platform mode — live Python tool execution
    uv run python scripts/simulate_convo.py \\
        --platform-agent --tool-mode live \\
        --test-case ../examples/test-cases/normal-refund-request.json

Fixed replay lines instead of an LLM user (no simulator LLM calls)::

    uv run python scripts/simulate_convo.py --agent-url ... --test-case ... --scripted
"""

import argparse
import asyncio
import importlib.util
import json
import os
import uuid
from pathlib import Path
from typing import Any

from app.models.enums import AgentMode, SimulatorMode, TurnRole
from app.models.schemas import (
    AgentSimulatorConfig,
    ConversationTurn,
    JudgeConfig,
    JudgeVerdict,
    RunConfig,
    UserSimulatorConfig,
)
from app.models.test_case import TestCase
from app.services.orchestrator import (
    TestCaseRunResult,
    run_test_case,
    run_test_case_with_evaluation,
)

# ---------------------------------------------------------------------------
# Python tool implementations for --tool-mode live
#
# Each value is an ``async def execute(args, context) -> dict`` body.  The
# sandbox receives ``args`` (parsed JSON) and a ``ToolContext`` whose
# ``test_case_context`` carries the test case's ``user_context``.
# ---------------------------------------------------------------------------
_TOOL_PYTHON_IMPLEMENTATIONS: dict[str, str] = {
    "check_service_area": (
        "async def execute(args, context):\n"
        '    z = args.get("zone", "").replace(" ", "").upper()\n'
        '    return {"serviced": True, "region": "Metro Vancouver", "zone": z}\n'
    ),
    "lookup_order": (
        "async def execute(args, context):\n"
        '    oid = args.get("order_id", "").strip().upper()\n'
        "    ctx = context.test_case_context\n"
        '    if ctx.get("order_id", "").upper() == oid:\n'
        "        return {\n"
        '            "order_id": oid,\n'
        '            "status": ctx.get("order_status", "delivered"),\n'
        '            "amount": ctx.get("amount", 0),\n'
        '            "product": ctx.get("product", "Unknown"),\n'
        '            "purchase_date": ctx.get("purchase_date", ""),\n'
        '            "payment_method": ctx.get("payment_method", ""),\n'
        '            "eligible_refund": True,\n'
        '            "order_total": ctx.get("order_total"),\n'
        '            "shipping_address": ctx.get("current_address"),\n'
        "        }\n"
        '    return {"order_id": oid, "status": "not_found"}\n'
    ),
    "process_refund": (
        "async def execute(args, context):\n"
        '    oid = args.get("order_id", "").strip().upper()\n'
        "    try:\n"
        '        amt = float(args.get("amount", 0))\n'
        "    except (TypeError, ValueError):\n"
        "        amt = 0.0\n"
        "    return {\n"
        '        "status": "completed", "refund_id": "RF-MOCK-001",\n'
        '        "order_id": oid, "amount": amt,\n'
        '        "message": "Refund submitted to payment provider; 5-7 business days",\n'
        "    }\n"
    ),
    "update_shipping_address": (
        "async def execute(args, context):\n"
        "    return {\n"
        '        "order_id": args.get("order_id", "").strip().upper(),\n'
        '        "address": args.get("address", "").strip(),\n'
        '        "updated": True,\n'
        "    }\n"
    ),
    "apply_discount": (
        "async def execute(args, context):\n"
        '    code = args.get("code", "").strip().upper()\n'
        '    pct = 20 if "SAVE20" in code else 10 if code else 0\n'
        "    return {\n"
        '        "order_id": args.get("order_id", "").strip().upper(),\n'
        '        "code": args.get("code", "").strip(),\n'
        '        "applied": True, "percent_off": pct,\n'
        "    }\n"
    ),
    "add_order_item": (
        "async def execute(args, context):\n"
        "    return {\n"
        '        "order_id": args.get("order_id", "").strip().upper(),\n'
        '        "item_name": args.get("item_name", "").strip(),\n'
        '        "added": True, "line_id": "LINE-MOCK",\n'
        "    }\n"
    ),
    "lookup_account": (
        "async def execute(args, context):\n"
        '    aid = args.get("account_id", "").strip().upper()\n'
        "    ctx = context.test_case_context\n"
        '    if ctx.get("account_id", "").upper() == aid:\n'
        "        return {\n"
        '            "account_id": aid,\n'
        '            "subscription_plan": ctx.get("subscription_plan", ""),\n'
        '            "customer_since": ctx.get("customer_since", ""),\n'
        '            "lifetime_value": ctx.get("lifetime_value", 0),\n'
        '            "support_notes": f"Customer reported recurring billing overcharge;"\n'
        "            f\" {ctx.get('prior_contacts', 0)} prior contacts logged\",\n"
        "        }\n"
        '    return {"account_id": aid, "status": "active", "support_notes": ""}\n'
    ),
    "get_billing_history": (
        "async def execute(args, context):\n"
        '    aid = args.get("account_id", "").strip().upper()\n'
        "    ctx = context.test_case_context\n"
        '    if ctx.get("account_id", "").upper() == aid:\n'
        '        overcharge = ctx.get("monthly_overcharge", 50.0)\n'
        '        months = ctx.get("months_affected", 3)\n'
        "        charges = [\n"
        "            {\n"
        '                "period": f"2026-{i+1:02d}",\n'
        '                "billed": 49.0 + overcharge,\n'
        '                "plan_expected": 49.0,\n'
        '                "variance": overcharge,\n'
        "            }\n"
        "            for i in range(months)\n"
        "        ]\n"
        "        return {\n"
        '            "account_id": aid, "charges": charges,\n'
        '            "total_overcharge": ctx.get("total_overcharge", overcharge * months),\n'
        '            "summary": f"{months} consecutive months show"\n'
        '            f" ${overcharge:.0f} overcharge vs plan",\n'
        "        }\n"
        '    return {"account_id": aid, "charges": [], "summary": "No billing rows"}\n'
    ),
    "escalate_to_supervisor": (
        "async def execute(args, context):\n"
        "    return {\n"
        '        "ticket_id": "ESC-MOCK-001", "status": "queued",\n'
        '        "eta_minutes": 15,\n'
        '        "reason": args.get("reason", "customer_requested"),\n'
        '        "account_id": args.get("account_id"),\n'
        "    }\n"
    ),
}


def _inject_live_platform_python(tools: list[dict[str, Any]]) -> None:
    """Ensure each tool has ``platform_config.implementation`` for live scripted runs."""
    for tool in tools:
        fn = tool.get("function", {})
        name = fn.get("name", "") if isinstance(fn, dict) else ""
        code = _TOOL_PYTHON_IMPLEMENTATIONS.get(name)
        if code:
            tool["platform_config"] = {
                "implementation": {
                    "type": "python",
                    "code": code,
                    "timeout_s": 30.0,
                }
            }


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


def _load_test_case(path: Path) -> TestCase:
    raw: dict = json.loads(path.read_text(encoding="utf-8"))
    if "id" not in raw:
        raw["id"] = str(uuid.uuid4())
    return TestCase.model_validate(raw)


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
    test_case_path = Path(args.test_case).resolve()
    test_case = _load_test_case(test_case_path)

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
        if args.tool_mode == "live":
            _inject_live_platform_python(agent_tools)
        agent_model = args.agent_model or os.getenv("MOCK_AGENT_MODEL", "gpt-4o-mini")
        agent_provider = args.agent_provider
        if args.agent_temperature is not None or args.agent_max_tokens is not None:
            agent_sim_cfg = AgentSimulatorConfig(
                temperature=args.agent_temperature,
                max_tokens=args.agent_max_tokens,
            )

    resolved_tool_mode = "live" if args.tool_mode == "live" else "mock"

    run_cfg = RunConfig(
        timeout_per_test_case_ms=args.timeout_ms,
        tool_mode=resolved_tool_mode,
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
    if args.tool_mode == "synthetic":
        run_kw["platform_tool_executor_mode"] = "synthetic"

    if args.judge:
        run_out, verdict = await run_test_case_with_evaluation(
            test_case,
            agent_url,
            run_cfg,
            **run_kw,
        )
        transcript = run_out.transcript
    else:
        run_out = await run_test_case(
            test_case,
            agent_url,
            run_cfg,
            **run_kw,
        )
        transcript = run_out.transcript
        verdict = None

    tool_label = (
        f", tool-mode={args.tool_mode}"
        if args.platform_agent and args.tool_mode != "synthetic"
        else ""
    )
    mode_note = (
        f"platform (mock_agent prompt+tools{tool_label})"
        if args.platform_agent
        else "endpoint"
    )
    print(f"TestCase: {test_case.name} ({test_case_path})  [agent: {mode_note}]")
    print(f"Turns: {len(transcript)}")
    _print_transcript(transcript)
    _print_run_tracking(run_out, verdict)
    if verdict is not None:
        _print_verdict(verdict)
    return 0


def _print_run_tracking(
    run_out: TestCaseRunResult, verdict: JudgeVerdict | None
) -> None:
    print("\n--- Token & cost (same fields persisted on test_case_result) ---")
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
    print(f"  TestCase total USD: {total:.6f}")
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
        "--tool-mode",
        choices=["synthetic", "mock", "live"],
        default="synthetic",
        help=(
            "Runs as RunConfig.tool_mode for the platform simulator (only with "
            "--platform-agent). synthetic: omit tool routing (SyntheticToolExecutor-like). "
            "mock: use test-case mock_responses via MockToolExecutor. "
            "live: attach Python stubs from this script and run implementations."
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
        "--test-case",
        required=True,
        type=Path,
        dest="test_case",
        help="Path to test case JSON (e.g. examples/test-cases/normal-refund-request.json)",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=120_000,
        help="Per-test-case timeout (orchestrator wall clock; agent HTTP or platform LLM)",
    )
    parser.add_argument(
        "--scripted",
        action="store_true",
        help=(
            "Replay fixed user lines from --scripted-user after first_message "
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
    if args.tool_mode != "synthetic" and not args.platform_agent:
        parser.error("--tool-mode requires --platform-agent")
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
