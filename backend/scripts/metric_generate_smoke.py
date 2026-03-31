#!/usr/bin/env python3
"""Smoke-test custom metric LLM generation (same path as POST /custom-metrics/generate).

**Direct (default)** — calls :func:`app.services.metric_generator.generate_metric` in-process.
Requires provider API keys (same as ``scripts/llm_smoke.py``). No running API server.

**HTTP mode** — logs in and calls the backend route (like ``scripts/test_run_sse.py``).

Setup::

    cd backend && uv sync && source .venv/bin/activate

Direct::

    uv run python scripts/metric_generate_smoke.py \\
        --description "Judge whether the agent confirms appointment time in user's timezone"

    uv run python scripts/metric_generate_smoke.py \\
        --description "Did the agent avoid inventing policy?" \\
        --score-type binary \\
        --tier knowledge \\
        --model gpt-4.1-mini

HTTP (backend on 8000) — generates via API, then **saves** ``POST /custom-metrics/`` and prints **available metrics** ``GET /config/available-metrics``::

    uv run python scripts/metric_generate_smoke.py --backend http://localhost:8000 \\
        --description "Tool argument accuracy for booking flows"

    # Generate only (no persist / no available-metrics listing)
    uv run python scripts/metric_generate_smoke.py --backend http://localhost:8000 \\
        --no-persist -d "Quick rubric preview"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


def _sync_api_keys_from_settings_to_environ() -> None:
    """LiteLLM reads provider keys from the process environment."""
    from app.core.config import settings

    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
    if settings.ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY


def _any_llm_key_set() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


async def _run_direct(
    *,
    description: str,
    model: str | None,
    score_type: str | None,
    tier: str | None,
) -> int:
    from app.models.enums import MetricTier, ScoreType
    from app.services.metric_generator import MetricGenerateRequest, generate_metric

    st = ScoreType(score_type) if score_type else None
    tr = MetricTier(tier) if tier else None
    request = MetricGenerateRequest(
        description=description,
        model=model,
        score_type=st,
        tier=tr,
    )
    result = await generate_metric(request)

    # Pretty-print: full JSON (rubric is long but valid for piping to jq)
    print(result.model_dump_json(indent=2))

    print("\n--- Metric generation ---")
    print(f"  model_used:            {result.model_used}")
    print(f"  generation_time_ms:    {result.generation_time_ms}")
    print(f"  name / display_name:   {result.name} / {result.display_name}")
    print(f"  tier / score_type:     {result.tier.value} / {result.score_type.value}")
    print(f"  default_weight:        {result.default_weight}")
    rubric_preview = (result.rubric or "").strip().splitlines()
    preview = "\n".join(rubric_preview[:8])
    if len(rubric_preview) > 8:
        preview += "\n  ..."
    print("  rubric (first lines):\n")
    for line in preview.splitlines():
        print(f"    {line}")
    print()
    return 0


def _api(base: str, path: str) -> str:
    return f"{base.rstrip('/')}/api/v1{path}"


def _create_body_from_generate(
    generated: dict[str, object], *, include_in_defaults: bool
) -> dict[str, object]:
    """Map ``MetricGenerateResult`` JSON to ``CustomMetricCreate`` body."""
    keys = (
        "name",
        "display_name",
        "description",
        "tier",
        "score_type",
        "rubric",
        "default_weight",
    )
    out: dict[str, object] = {k: generated[k] for k in keys if k in generated}
    out["include_in_defaults"] = include_in_defaults
    return out


def _print_available_metrics_summary(payload: dict[str, object]) -> None:
    data = payload.get("data") or []
    count = payload.get("count", len(data))
    print(f"\n{'=' * 60}")
    print("AVAILABLE METRICS (GET /config/available-metrics)")
    print(f"{'=' * 60}\n")
    print(f"  count: {count}\n")
    for m in data:
        if not isinstance(m, dict):
            continue
        name = m.get("name", "?")
        dname = m.get("display_name", "")
        tier = m.get("tier", "")
        st = m.get("score_type", "")
        w = m.get("default_weight", "")
        print(f"  - {name}")
        print(f"      display_name: {dname}")
        print(f"      tier / score_type / default_weight: {tier} / {st} / {w}")
    print()


def _run_http(
    *,
    backend: str,
    email: str,
    password: str,
    description: str,
    model: str | None,
    score_type: str | None,
    tier: str | None,
    persist: bool,
    include_in_defaults: bool,
) -> int:
    import httpx

    body: dict[str, object] = {"description": description}
    if model:
        body["model"] = model
    if score_type:
        body["score_type"] = score_type
    if tier:
        body["tier"] = tier

    with httpx.Client(timeout=120.0) as client:
        login_r = client.post(
            _api(backend, "/login/access-token"),
            data={"username": email, "password": password},
        )
        login_r.raise_for_status()
        token = login_r.json()["access_token"]
        client.cookies.set("auth_cookie", token)
        print(f"[login] OK as {email}\n")

        gen_r = client.post(_api(backend, "/custom-metrics/generate"), json=body)
        gen_r.raise_for_status()
        data = gen_r.json()
        print(json.dumps(data, indent=2))

        print("\n--- Metric generation (HTTP) ---")
        print(f"  model_used:            {data.get('model_used')}")
        print(f"  generation_time_ms:    {data.get('generation_time_ms')}")
        print(
            f"  name / display_name:   {data.get('name')} / {data.get('display_name')}"
        )
        print(
            f"  tier / score_type:     {data.get('tier')} / {data.get('score_type')}",
        )
        print()

        if not persist:
            print(
                "[http] --no-persist: skipping POST /custom-metrics/ and available-metrics\n"
            )
            return 0

        required_for_create = (
            "name",
            "display_name",
            "description",
            "tier",
            "score_type",
            "rubric",
            "default_weight",
        )
        missing = [k for k in required_for_create if k not in data]
        if missing:
            print(
                f"[save] Generate response missing keys for create: {missing}",
                file=sys.stderr,
            )
            return 1

        create_body = _create_body_from_generate(
            data, include_in_defaults=include_in_defaults
        )
        exit_code = 0
        save_r = client.post(_api(backend, "/custom-metrics/"), json=create_body)
        if save_r.status_code == 409:
            exit_code = 1
            print(
                "[save] POST /custom-metrics/ conflict (409): "
                f"{save_r.json().get('detail', save_r.text)}",
                file=sys.stderr,
            )
            print(
                "[save] Listing available metrics anyway.\n",
                file=sys.stderr,
            )
        else:
            save_r.raise_for_status()
            saved = save_r.json()
            print(f"{'=' * 60}")
            print("SAVED CUSTOM METRIC (POST /custom-metrics/)")
            print(f"{'=' * 60}\n")
            print(f"  id:   {saved.get('id')}")
            print(f"  name: {saved.get('name')}")
            print()

        avail_r = client.get(_api(backend, "/config/available-metrics"))
        avail_r.raise_for_status()
        avail = avail_r.json()
        _print_available_metrics_summary(avail)

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test LLM custom metric generation (in-process or via HTTP API)."
    )
    parser.add_argument(
        "--description",
        "-d",
        default=os.environ.get("METRIC_SMOKE_DESCRIPTION"),
        help="Natural language: what the metric should measure (or METRIC_SMOKE_DESCRIPTION)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=os.environ.get("METRIC_SMOKE_MODEL"),
        help="LiteLLM model override (default: settings.LLM_DEFAULT_MODEL; env METRIC_SMOKE_MODEL)",
    )
    parser.add_argument(
        "--score-type",
        choices=["scored", "binary"],
        default=None,
        help="Force scored (0-5) or binary pass/fail",
    )
    parser.add_argument(
        "--tier",
        choices=["execution", "knowledge", "process", "delivery"],
        default=None,
        help="Force metric tier",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="If set, call this backend base URL (e.g. http://localhost:8000) instead of in-process LLM",
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="HTTP mode: login email (default: admin@example.com)",
    )
    parser.add_argument(
        "--password",
        default="password",
        help="HTTP mode: login password (default: password)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help=(
            "HTTP mode only: call /custom-metrics/generate only; "
            "do not POST /custom-metrics/ or GET /config/available-metrics"
        ),
    )
    parser.add_argument(
        "--include-in-defaults",
        action="store_true",
        help="HTTP mode: set include_in_defaults=true when saving the generated metric",
    )
    args = parser.parse_args()

    description = (args.description or "").strip()
    if not description:
        parser.error("Provide --description (or set METRIC_SMOKE_DESCRIPTION)")

    model = args.model if args.model else None

    try:
        if args.backend:
            return _run_http(
                backend=args.backend,
                email=args.email,
                password=args.password,
                description=description,
                model=model,
                score_type=args.score_type,
                tier=args.tier,
                persist=not args.no_persist,
                include_in_defaults=args.include_in_defaults,
            )

        _sync_api_keys_from_settings_to_environ()
        if not _any_llm_key_set():
            print(
                "No OPENAI_API_KEY or ANTHROPIC_API_KEY in environment after loading "
                "settings. Set keys in the repo root .env or the environment.",
                file=sys.stderr,
            )
            return 1

        return asyncio.run(
            _run_direct(
                description=description,
                model=model,
                score_type=args.score_type,
                tier=args.tier,
            )
        )
    except KeyboardInterrupt:
        return 130
    except ValueError as exc:
        print(f"Validation/generation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
