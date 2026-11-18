#!/usr/bin/env python3
"""Try a check on real calls before it ships, or A/B two versions of one, outside the
product.

Runs one check, registered or a draft, over calls in a database opened read-only. It
asks the check's model when it has one, within ``--budget`` dollars, then runs the
check's code on each answer. Nothing is written to any database. Results (call ids,
event ids, finding details, counts and cost, never what was said) go to ``--out``;
counts are printed.

    cd backend && uv run python -I scripts/try_check.py action_claimed_without_tool
    cd backend && uv run python -I scripts/try_check.py \\
        --draft scripts/check_drafts/action_claimed_judge.py --out judge.json

An A/B test is two runs on the same calls, compared with ``scripts/compare_runs.py``.

The database URL is read from an environment variable or the root ``.env``
(``--database-env``, default ``HOSTED_DATABASE_URL``) and split into parts, which the
hosted pooler needs. The connection is read only.
"""

import argparse
import asyncio
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _env_value(name: str) -> str:
    if os.environ.get(name):
        return os.environ[name]
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip("'\"")
    msg = f"{name} is not set in the environment or the root .env"
    raise SystemExit(msg)


def _read_only_session(env_name: str):  # noqa: ANN202 - a SQLModel Session
    import psycopg
    from sqlalchemy import create_engine
    from sqlmodel import Session

    parts = urlsplit(_env_value(env_name))

    def connect() -> psycopg.Connection:
        return psycopg.connect(
            host=parts.hostname,
            port=parts.port or 5432,
            user=unquote(parts.username or ""),
            password=unquote(parts.password or ""),
            dbname=(parts.path or "/postgres").lstrip("/") or "postgres",
            options="-c default_transaction_read_only=on",
        )

    return Session(create_engine("postgresql+psycopg://", creator=connect))


def _load_check(check_type: str | None, draft: str | None):  # noqa: ANN202
    from app.services.checks.registry import get_check

    if draft:
        spec = importlib.util.spec_from_file_location("check_draft", draft)
        if spec is None or spec.loader is None:
            raise SystemExit(f"Cannot load {draft}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.CHECK
    check = get_check(check_type or "")
    if check is None:
        raise SystemExit(f"No registered check '{check_type}'")
    return check


async def _main(args: argparse.Namespace) -> None:
    from sqlmodel import col, select

    from app import crud
    from app.core.config import settings
    from app.models.call import Call
    from app.services.checks.base import ModelCheck
    from app.services.checks.engine import run_checks
    from app.services.trace_capabilities import derive_capabilities

    # LiteLLM reads provider keys from the process environment.
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if getattr(settings, name):
            os.environ[name] = getattr(settings, name)

    check = _load_check(args.check, args.draft)
    with _read_only_session(args.database_env) as session:
        query = select(Call).where(
            col(Call.schema_version).is_not(None), col(Call.deleted_at).is_(None)
        )
        if args.agent:
            query = query.where(Call.agent_id == args.agent)
        query = query.order_by(col(Call.started_at).desc()).limit(args.limit)
        calls = list(session.exec(query).all())
        traces = [(call, crud.get_trace(session=session, call=call)) for call in calls]
    traces = [(call, trace) for call, trace in traces if trace is not None]
    usable = [
        (call, trace)
        for call, trace in traces
        if all(need in set(derive_capabilities(trace)) for need in check.needs)
    ]

    spent = 0.0
    stopped = False
    limiter = asyncio.Semaphore(settings.MODEL_CHECK_CONCURRENCY)
    started = time.monotonic()

    async def answer(trace):  # noqa: ANN001, ANN202
        nonlocal spent, stopped
        if not isinstance(check, ModelCheck):
            return None
        async with limiter:
            if spent >= args.budget:
                stopped = True
                return False
            try:
                reply = await check.ask(trace)
            except Exception as exc:  # noqa: BLE001 - one call's failure is reported
                return exc
            spent += reply.cost_usd
            return reply

    replies = await asyncio.gather(*(answer(trace) for _, trace in usable))

    findings = []
    model = check.model if isinstance(check, ModelCheck) else None
    checked = 0
    for (call, trace), reply in zip(usable, replies, strict=True):
        if reply is False:
            continue
        if isinstance(reply, BaseException):
            findings.append({"call_id": str(call.id), "broke": type(reply).__name__})
            continue
        checked += 1
        answers = {}
        if reply is not None:
            answers[check.type] = reply.answer
            model = reply.model
        run = run_checks(trace=trace, executions=[], checks=[check], answers=answers)
        if run.broken:
            findings.append(
                {"call_id": str(call.id), "broke": repr(run.broken[check.type])}
            )
            continue
        for _, raised in run.found:
            findings.append(
                {
                    "call_id": str(call.id),
                    "event_ids": list(raised.event_ids),
                    "key": raised.key,
                    "detail": raised.detail,
                }
            )

    real = [f for f in findings if "event_ids" in f]
    out = {
        "check": check.type,
        "version": check.version,
        "kind": check.kind.value,
        "model": model,
        "calls": len(traces),
        "calls_checked": checked,
        "calls_skipped_for_needs": len(traces) - len(usable),
        "stopped_at_budget": stopped,
        "cost_usd": round(spent, 5),
        "seconds": round(time.monotonic() - started, 1),
        "calls_with_findings": len({f["call_id"] for f in real}),
        "findings": findings,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "findings"}, indent=2))
    whys = Counter(
        str((f["detail"] or {}).get("action") or f["key"] or "") for f in real
    )
    print("findings:", len(real), dict(whys))
    print("broke on:", len(findings) - len(real), "calls")
    print("written to", args.out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("check", nargs="?", help="A registered check type")
    parser.add_argument("--draft", help="A draft check file that defines CHECK")
    parser.add_argument("--agent", help="Only this agent's calls (its Connexity id)")
    parser.add_argument("--limit", type=int, default=200, help="Newest calls to try")
    parser.add_argument("--budget", type=float, default=1.0, help="Dollars, at most")
    parser.add_argument("--database-env", default="HOSTED_DATABASE_URL")
    parser.add_argument("--out", default="try_check.json")
    args = parser.parse_args()
    if not args.check and not args.draft:
        parser.error("name a check or give --draft")
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
