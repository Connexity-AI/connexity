#!/usr/bin/env python3
"""Benchmark test case generation: timing and context-window limits.

Usage:
    # 1. Make sure the backend is running (uvicorn app.main:app --reload)
    # 2. Run:
    python scripts/benchmark_generation.py \
        --prompt /Users/maxillin/Downloads/MPA-prompt.txt \
        --counts 10 25 50 \
        --api-url http://localhost:8000

    # Optional: override model, skip login, or save results
    python scripts/benchmark_generation.py \
        --prompt /Users/maxillin/Downloads/MPA-prompt.txt \
        --counts 10 25 50 100 \
        --model gpt-4o \
        --token "eyJ..." \
        --output results.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import tiktoken


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Approximate token count using tiktoken (cl100k_base for GPT-4 family)."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def login(base_url: str, email: str, password: str) -> str:
    """Get JWT token from the API."""
    resp = httpx.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": email, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def generate(
    base_url: str,
    token: str,
    prompt: str,
    count: int,
    model: str | None = None,
    tools: list[dict] | None = None,
) -> dict:
    """Call POST /api/v1/test-cases/generate and return the full response."""
    body: dict = {
        "agent_prompt": prompt,
        "count": count,
        "persist": False,
        "tools": tools or [],
    }
    if model:
        body["model"] = model

    start = time.perf_counter()
    resp = httpx.post(
        f"{base_url}/api/v1/test-cases/generate",
        json=body,
        cookies={"auth_cookie": token},
        timeout=600,  # generous timeout for large counts
    )
    wall_time_ms = int((time.perf_counter() - start) * 1000)

    if resp.status_code != 200:
        return {
            "count_requested": count,
            "status": resp.status_code,
            "error": resp.text[:500],
            "wall_time_ms": wall_time_ms,
        }

    data = resp.json()
    return {
        "count_requested": count,
        "count_returned": data["count"],
        "model_used": data["model_used"],
        "generation_time_ms": data["generation_time_ms"],
        "wall_time_ms": wall_time_ms,
        "test_cases": data["test_cases"],
    }


def estimate_limits(prompt: str, tools_json: str | None) -> dict:
    """Estimate context window usage and max test case counts."""

    # --- Token budget constants (common models) ---
    models = {
        "gpt-4o": {"context": 128_000, "max_output": 16_384},
        "gpt-4.1": {"context": 1_047_576, "max_output": 32_768},
        "gpt-4.1-mini": {"context": 1_047_576, "max_output": 32_768},
        "claude-sonnet-4-20250514": {"context": 200_000, "max_output": 16_000},
        "claude-3-5-sonnet-20241022": {"context": 200_000, "max_output": 8_192},
    }

    # Count input tokens
    prompt_tokens = count_tokens(prompt)
    tools_tokens = count_tokens(tools_json) if tools_json else 0

    # System prompt overhead (the test-case-gen system prompt + schema)
    # Approximate — the actual system prompt is ~600 tokens + schema ~400 tokens
    system_overhead_tokens = 1_200

    # User prompt wrapper overhead (~50 tokens for "Generate N..." + markers)
    user_overhead_tokens = 80

    total_input_tokens = (
        prompt_tokens + tools_tokens + system_overhead_tokens + user_overhead_tokens
    )

    # Estimate output tokens per test case
    # A typical generated test case is ~250-400 tokens of JSON
    tokens_per_case_low = 250
    tokens_per_case_high = 450

    estimates = {}
    for model_name, limits in models.items():
        remaining_for_output = limits["context"] - total_input_tokens
        effective_output = min(remaining_for_output, limits["max_output"])

        # The GENERATOR_MAX_TOKENS is 16_000 by default
        effective_output = min(effective_output, 16_000)

        max_cases_optimistic = effective_output // tokens_per_case_low
        max_cases_conservative = effective_output // tokens_per_case_high

        estimates[model_name] = {
            "context_window": limits["context"],
            "max_output_tokens": limits["max_output"],
            "effective_output_budget": effective_output,
            "remaining_for_output": remaining_for_output,
            "max_cases_optimistic": max_cases_optimistic,
            "max_cases_conservative": max_cases_conservative,
        }

    return {
        "input_tokens": {
            "agent_prompt": prompt_tokens,
            "tools": tools_tokens,
            "system_overhead_est": system_overhead_tokens,
            "user_overhead_est": user_overhead_tokens,
            "total": total_input_tokens,
        },
        "output_per_case_tokens": {
            "low": tokens_per_case_low,
            "high": tokens_per_case_high,
        },
        "generator_max_tokens_setting": 16_000,
        "model_estimates": estimates,
    }


def measure_actual_output(test_cases: list[dict]) -> dict:
    """Measure actual tokens per test case from real output."""
    if not test_cases:
        return {"count": 0}

    per_case_tokens = []
    for tc in test_cases:
        # Serialize just the test case fields (exclude id/timestamps)
        tc_copy = {
            k: v
            for k, v in tc.items()
            if k not in ("id", "created_at", "updated_at")
        }
        tc_json = json.dumps(tc_copy, indent=2)
        per_case_tokens.append(count_tokens(tc_json))

    total_json = json.dumps(test_cases, indent=2)
    total_tokens = count_tokens(total_json)

    return {
        "count": len(test_cases),
        "total_output_tokens": total_tokens,
        "avg_tokens_per_case": round(sum(per_case_tokens) / len(per_case_tokens)),
        "min_tokens_per_case": min(per_case_tokens),
        "max_tokens_per_case": max(per_case_tokens),
        "tokens_per_case_distribution": per_case_tokens,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark test case generation timing and limits"
    )
    parser.add_argument(
        "--prompt", required=True, help="Path to agent system prompt file"
    )
    parser.add_argument(
        "--tools", default=None, help="Path to tools JSON file (optional)"
    )
    parser.add_argument(
        "--counts",
        nargs="+",
        type=int,
        default=[10, 25, 50],
        help="Number of test cases to generate (default: 10 25 50)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API base URL",
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Login email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default="password",
        help="Login password",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="JWT token (skip login)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override LLM model (e.g. gpt-4o, claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save full results to JSON file",
    )
    parser.add_argument(
        "--save-cases",
        default=None,
        help="Directory to save generated test cases (one JSON file per count, e.g. cases_10.json)",
    )

    args = parser.parse_args()

    # Read prompt
    prompt_text = Path(args.prompt).read_text()
    print(f"Loaded prompt: {len(prompt_text)} chars")

    # Read tools
    tools_json_str = None
    tools_list = []
    if args.tools:
        tools_json_str = Path(args.tools).read_text()
        tools_list = json.loads(tools_json_str)
        print(f"Loaded tools: {len(tools_list)} tool definitions")

    # --- Phase 1: Estimate limits ---
    print("\n" + "=" * 70)
    print("PHASE 1: Context Window & Limit Estimates")
    print("=" * 70)

    estimates = estimate_limits(prompt_text, tools_json_str)

    inp = estimates["input_tokens"]
    print(f"\nInput tokens breakdown:")
    print(f"  Agent prompt:      {inp['agent_prompt']:>7,} tokens")
    print(f"  Tools:             {inp['tools']:>7,} tokens")
    print(f"  System overhead:  ~{inp['system_overhead_est']:>7,} tokens")
    print(f"  User overhead:    ~{inp['user_overhead_est']:>7,} tokens")
    print(f"  TOTAL INPUT:      ~{inp['total']:>7,} tokens")

    opc = estimates["output_per_case_tokens"]
    print(f"\nEstimated output per test case: {opc['low']}-{opc['high']} tokens")
    print(f"GENERATOR_MAX_TOKENS setting:  {estimates['generator_max_tokens_setting']:,}")

    print(f"\nMax test cases by model (with GENERATOR_MAX_TOKENS={estimates['generator_max_tokens_setting']:,}):")
    print(f"  {'Model':<40} {'Budget':>8} {'Conservative':>14} {'Optimistic':>12}")
    print(f"  {'-'*40} {'-'*8} {'-'*14} {'-'*12}")
    for model_name, est in estimates["model_estimates"].items():
        print(
            f"  {model_name:<40} {est['effective_output_budget']:>7,}t "
            f"{est['max_cases_conservative']:>12} "
            f"{est['max_cases_optimistic']:>12}"
        )

    # --- Phase 2: Actual generation benchmarks ---
    print("\n" + "=" * 70)
    print("PHASE 2: Generation Benchmarks")
    print("=" * 70)

    # Login
    token = args.token
    if not token:
        print(f"\nLogging in as {args.email}...")
        try:
            token = login(args.api_url, args.email, args.password)
            print("  Login successful")
        except Exception as e:
            print(f"  Login failed: {e}")
            print("  Skipping generation benchmarks. Use --token to provide a JWT.")
            sys.exit(1)

    results = []
    for count in args.counts:
        print(f"\nGenerating {count} test cases...")
        result = generate(
            base_url=args.api_url,
            token=token,
            prompt=prompt_text,
            count=count,
            model=args.model,
            tools=tools_list,
        )

        if "error" in result:
            print(f"  FAILED (HTTP {result['status']}): {result['error'][:200]}")
            results.append(result)
            continue

        # Measure actual output
        actual = measure_actual_output(result["test_cases"])

        result["actual_output"] = actual
        results.append(result)

        # Save test cases to file
        if args.save_cases:
            cases_dir = Path(args.save_cases)
            cases_dir.mkdir(parents=True, exist_ok=True)
            cases_file = cases_dir / f"cases_{count}.json"
            # Strip ephemeral fields (id, created_at, updated_at) for clean output
            clean_cases = []
            for tc in result["test_cases"]:
                clean = {
                    k: v
                    for k, v in tc.items()
                    if k not in ("id", "created_at", "updated_at", "agent_id")
                }
                clean_cases.append(clean)
            cases_file.write_text(json.dumps(clean_cases, indent=2))
            print(f"  Saved {len(clean_cases)} cases -> {cases_file}")

        print(f"  Requested:         {result['count_requested']}")
        print(f"  Returned:          {result['count_returned']}")
        print(f"  Model:             {result['model_used']}")
        print(f"  Server time:       {result['generation_time_ms']:,} ms ({result['generation_time_ms'] / 1000:.1f}s)")
        print(f"  Wall time:         {result['wall_time_ms']:,} ms ({result['wall_time_ms'] / 1000:.1f}s)")
        print(f"  Avg tokens/case:   {actual['avg_tokens_per_case']}")
        print(f"  Min/Max tokens:    {actual['min_tokens_per_case']}/{actual['max_tokens_per_case']}")
        print(f"  Total output tok:  {actual['total_output_tokens']:,}")

        # Estimate based on actual measurements
        avg_tok = actual["avg_tokens_per_case"]
        max_tok = actual["max_tokens_per_case"]
        budget = 16_000  # GENERATOR_MAX_TOKENS
        print(f"  -> Est max cases (avg):  {budget // avg_tok} (at {avg_tok} tok/case)")
        print(f"  -> Est max cases (safe): {budget // max_tok} (at {max_tok} tok/case)")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Count':>6} | {'Returned':>8} | {'Server (s)':>10} | {'Wall (s)':>10} | {'Avg tok/case':>12} | {'Status'}")
    print(f"{'-'*6}-+-{'-'*8}-+-{'-'*10}-+-{'-'*10}-+-{'-'*12}-+-{'-'*10}")
    for r in results:
        if "error" in r:
            print(f"{r['count_requested']:>6} | {'---':>8} | {r['wall_time_ms']/1000:>10.1f} | {r['wall_time_ms']/1000:>10.1f} | {'---':>12} | FAILED")
        else:
            a = r["actual_output"]
            print(
                f"{r['count_requested']:>6} | {r['count_returned']:>8} | "
                f"{r['generation_time_ms']/1000:>10.1f} | {r['wall_time_ms']/1000:>10.1f} | "
                f"{a['avg_tokens_per_case']:>12} | OK"
            )

    # --- Save full results ---
    if args.output:
        full_output = {
            "estimates": estimates,
            "benchmarks": [
                {k: v for k, v in r.items() if k != "test_cases"} for r in results
            ],
        }
        Path(args.output).write_text(json.dumps(full_output, indent=2, default=str))
        print(f"\nFull results saved to {args.output}")


if __name__ == "__main__":
    main()
