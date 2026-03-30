#!/usr/bin/env python3
"""End-to-end test script: create a run, stream SSE events, print final results.

Prerequisites:
  1. Backend running:   cd backend && uvicorn app.main:app --reload
  2. Mock agent running: cd examples/mock_agent && uvicorn main:app --port 8001
  3. Database seeded:    cd backend && bash scripts/prestart.sh

The script will:
  - Log in as the superuser to obtain an auth cookie
  - Create (or reuse) an Agent pointing at the mock agent
  - Create scenarios from examples/scenarios/ and bundle them into a ScenarioSet
  - Create a Run with auto_execute=true
  - Subscribe to GET /runs/{run_id}/stream and print every SSE event live
  - Fetch + print the final Run (aggregate metrics including token/cost totals)
  - List GET /scenario-results/?run_id= for per-scenario token usage and estimated_cost_usd

Usage::

    cd backend && uv run python scripts/test_run_sse.py

    # Options:
    uv run python scripts/test_run_sse.py --backend http://localhost:8000 \\
        --agent-url http://localhost:8001/agent/respond \\
        --scenarios ../examples/scenarios/normal-refund-request.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import httpx_sse

_REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = _REPO_ROOT / "examples" / "scenarios"

DEFAULT_BACKEND = "http://localhost:8000"
DEFAULT_AGENT_URL = "http://localhost:8001/agent/respond"
API_PREFIX = "/api/v1"


def _api(base: str, path: str) -> str:
    return f"{base}{API_PREFIX}{path}"


def login(client: httpx.Client, base: str, email: str, password: str) -> None:
    r = client.post(
        _api(base, "/login/access-token"),
        data={"username": email, "password": password},
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    client.cookies.set("auth_cookie", token)
    print(f"[login] Authenticated as {email}")


def find_or_create_agent(client: httpx.Client, base: str, agent_url: str) -> str:
    r = client.get(_api(base, "/agents/"), params={"limit": 100})
    r.raise_for_status()
    for agent in r.json()["data"]:
        if agent["endpoint_url"] == agent_url:
            agent_id = agent["id"]
            print(f"[setup] Reusing agent {agent['name']} ({agent_id})")
            return agent_id

    r = client.post(
        _api(base, "/agents/"),
        json={
            "name": "Mock Agent (SSE test)",
            "description": "Auto-created by test_run_sse.py",
            "endpoint_url": agent_url,
        },
    )
    r.raise_for_status()
    agent_id = r.json()["id"]
    print(f"[setup] Created agent ({agent_id})")
    return agent_id


def create_scenarios(
    client: httpx.Client, base: str, scenario_paths: list[Path]
) -> list[str]:
    scenario_ids: list[str] = []
    for path in scenario_paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw.pop("id", None)
        r = client.post(_api(base, "/scenarios/"), json=raw)
        r.raise_for_status()
        sid = r.json()["id"]
        scenario_ids.append(sid)
        print(f"[setup] Created scenario '{raw['name']}' ({sid})")
    return scenario_ids


def find_or_create_scenario_set(
    client: httpx.Client, base: str, scenario_ids: list[str]
) -> str:
    r = client.post(
        _api(base, "/scenario-sets/"),
        json={
            "name": f"SSE test set ({time.strftime('%H:%M:%S')})",
            "description": "Auto-created by test_run_sse.py",
            "scenario_ids": scenario_ids,
        },
    )
    r.raise_for_status()
    set_id = r.json()["id"]
    print(f"[setup] Created scenario set ({set_id}) with {len(scenario_ids)} scenarios")
    return set_id


def create_run(
    client: httpx.Client,
    base: str,
    agent_id: str,
    agent_url: str,
    scenario_set_id: str,
) -> str:
    r = client.post(
        _api(base, "/runs/"),
        params={"auto_execute": "true"},
        json={
            "agent_id": agent_id,
            "agent_endpoint_url": agent_url,
            "scenario_set_id": scenario_set_id,
            "name": f"SSE test run ({time.strftime('%H:%M:%S')})",
            "config": {
                "concurrency": 5,
                "timeout_per_scenario_ms": 120_000,
            },
        },
    )
    r.raise_for_status()
    run = r.json()
    run_id = run["id"]
    print(f"\n[run] Created run ({run_id}) — status: {run['status']}")
    return run_id


def stream_events(client: httpx.Client, base: str, run_id: str) -> None:
    url = _api(base, f"/runs/{run_id}/stream")
    print(f"\n{'=' * 60}")
    print("SSE STREAM")
    print(f"{'=' * 60}\n")

    event_count = 0
    with client.stream("GET", url, timeout=300.0) as response:
        response.raise_for_status()
        for sse in httpx_sse.EventSource(response).iter_sse():
            event_count += 1
            ts = time.strftime("%H:%M:%S")
            data = json.loads(sse.data) if sse.data else {}
            print(f"  [{ts}] event: {sse.event}")
            if data:
                print(f"         data:  {json.dumps(data, indent=2)}")
            print()

            if sse.event in (
                "stream_closed",
                "run_completed",
                "run_cancelled",
                "run_failed",
            ):
                break

    print(f"[stream] Received {event_count} event(s) total\n")


def fetch_final_run(client: httpx.Client, base: str, run_id: str) -> None:
    r = client.get(_api(base, f"/runs/{run_id}"))
    r.raise_for_status()
    run = r.json()

    print(f"{'=' * 60}")
    print("FINAL RUN RESULT")
    print(f"{'=' * 60}\n")
    print(f"  Run ID:       {run['id']}")
    print(f"  Name:         {run.get('name')}")
    print(f"  Status:       {run['status']}")
    print(f"  Started at:   {run.get('started_at')}")
    print(f"  Completed at: {run.get('completed_at')}")

    metrics = run.get("aggregate_metrics")
    if metrics:
        print("\n  --- Aggregate Metrics ---")
        print(f"  Total scenarios:  {metrics['total_scenarios']}")
        print(f"  Passed:           {metrics['passed_count']}")
        print(f"  Failed:           {metrics['failed_count']}")
        print(f"  Errors:           {metrics['error_count']}")
        print(f"  Pass rate:        {metrics['pass_rate']:.1%}")
        if metrics.get("avg_overall_score") is not None:
            print(f"  Avg score:        {metrics['avg_overall_score']:.1f}")
        if metrics.get("latency_avg_ms") is not None:
            print(f"  Latency avg:      {metrics['latency_avg_ms']:.0f} ms")
        if metrics.get("latency_p50_ms") is not None:
            print(f"  Latency p50:      {metrics['latency_p50_ms']:.0f} ms")
        if metrics.get("latency_p95_ms") is not None:
            print(f"  Latency p95:      {metrics['latency_p95_ms']:.0f} ms")
        tagent = metrics.get("total_agent_token_usage")
        if tagent:
            print(f"  Agent tokens:     {json.dumps(tagent)}")
        tplat = metrics.get("total_platform_token_usage")
        if tplat:
            print(f"  Platform tokens:  {json.dumps(tplat)}")
        if metrics.get("total_estimated_cost_usd") is not None:
            print(f"  Est. cost (run):  ${metrics['total_estimated_cost_usd']:.4f}")
    else:
        print("\n  (no aggregate metrics)")

    print()


def fetch_scenario_results(client: httpx.Client, base: str, run_id: str) -> None:
    r = client.get(
        _api(base, "/scenario-results/"),
        params={"run_id": run_id, "limit": 1000},
    )
    r.raise_for_status()
    payload = r.json()
    items: list[dict[str, object]] = payload.get("data") or []

    print(f"{'=' * 60}")
    print("PER-SCENARIO RESULTS (token / cost tracking)")
    print(f"{'=' * 60}\n")

    if not items:
        print("  (no scenario results)\n")
        return

    for row in items:
        sid = row.get("scenario_id")
        lat = row.get("total_latency_ms")
        cost = row.get("estimated_cost_usd")
        agent_u = row.get("agent_token_usage")
        plat_u = row.get("platform_token_usage")
        print(f"  Scenario {sid}")
        if lat is not None:
            print(f"    total_latency_ms:   {lat}")
        if cost is not None:
            print(f"    estimated_cost_usd: {float(cost):.6f}")
        if agent_u:
            print(f"    agent_token_usage:    {json.dumps(agent_u)}")
        if plat_u:
            print(f"    platform_token_usage: {json.dumps(plat_u)}")
        verdict = row.get("verdict")
        if isinstance(verdict, dict):
            jtu = verdict.get("judge_token_usage")
            jcost = verdict.get("judge_cost_usd")
            if jtu:
                print(f"    judge_token_usage:    {json.dumps(jtu)}")
            if jcost is not None:
                print(f"    judge_cost_usd:       {float(jcost):.6f}")
        print()

    print(f"  ({len(items)} row(s))\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a run, stream SSE events, and print final results."
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help=f"Backend base URL (default: {DEFAULT_BACKEND})",
    )
    parser.add_argument(
        "--agent-url",
        default=DEFAULT_AGENT_URL,
        help=f"Mock agent endpoint URL (default: {DEFAULT_AGENT_URL})",
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Login email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default="password",
        help="Login password (default: password)",
    )
    parser.add_argument(
        "--scenarios",
        nargs="*",
        help="Scenario JSON file paths (default: all files in examples/scenarios/)",
    )
    parser.add_argument(
        "--skip-scenario-details",
        action="store_true",
        help="Do not fetch GET /scenario-results for per-scenario token/cost rows",
    )
    args = parser.parse_args()

    if args.scenarios:
        scenario_paths = [Path(s).resolve() for s in args.scenarios]
    else:
        scenario_paths = sorted(SCENARIOS_DIR.glob("*.json"))

    if not scenario_paths:
        print("[error] No scenario files found", file=sys.stderr)
        return 1

    print(f"[config] Backend:    {args.backend}")
    print(f"[config] Agent URL:  {args.agent_url}")
    print(f"[config] Scenarios:  {len(scenario_paths)} file(s)")
    print()

    with httpx.Client(timeout=30.0) as client:
        login(client, args.backend, args.email, args.password)

        agent_id = find_or_create_agent(client, args.backend, args.agent_url)
        scenario_ids = create_scenarios(client, args.backend, scenario_paths)
        set_id = find_or_create_scenario_set(client, args.backend, scenario_ids)
        run_id = create_run(client, args.backend, agent_id, args.agent_url, set_id)

        time.sleep(0.5)
        stream_events(client, args.backend, run_id)
        fetch_final_run(client, args.backend, run_id)
        if not args.skip_scenario_details:
            fetch_scenario_results(client, args.backend, run_id)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[interrupted]")
        raise SystemExit(130) from None
    except httpx.HTTPStatusError as exc:
        print(
            f"\n[error] HTTP {exc.response.status_code}: {exc.response.text}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
