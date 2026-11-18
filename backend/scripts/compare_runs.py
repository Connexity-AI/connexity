#!/usr/bin/env python3
"""Line up two ``try_check.py`` result files: an A/B test of two ways to decide one
check, run outside the product on the same calls.

A finding is matched by its call and the first event it points at (the turn). Prints
counts, then the call ids and events where the two disagree, never what was said.

    cd backend && uv run python -I scripts/compare_runs.py jev.json judge.json
"""

import argparse
import json
from pathlib import Path


def _findings(path: str) -> tuple[dict, dict[tuple[str, str], dict]]:
    run = json.loads(Path(path).read_text())
    found = {
        (f["call_id"], f["event_ids"][0]): f
        for f in run["findings"]
        if f.get("event_ids")
    }
    return run, found


def _label(finding: dict) -> str:
    detail = finding.get("detail") or {}
    return str(detail.get("action") or finding.get("key") or "")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("a")
    parser.add_argument("b")
    args = parser.parse_args()
    run_a, a = _findings(args.a)
    run_b, b = _findings(args.b)
    for name, run in (("A", run_a), ("B", run_b)):
        print(
            f"{name}: {run['check']} v{run['version']} ({run['kind']}, {run['model']}): "
            f"{len(run['findings'])} findings in {run['calls_with_findings']} of "
            f"{run['calls_checked']} calls, ${run['cost_usd']}"
        )
    both, only_a, only_b = a.keys() & b.keys(), a.keys() - b.keys(), b.keys() - a.keys()
    print(
        f"same turn in both: {len(both)}, only A: {len(only_a)}, only B: {len(only_b)}"
    )
    calls_a = {call for call, _ in a}
    calls_b = {call for call, _ in b}
    print(f"same call in both: {len(calls_a & calls_b)}")
    for title, keys, source in (
        ("BOTH", both, a),
        ("ONLY A", only_a, a),
        ("ONLY B", only_b, b),
    ):
        for call_id, event_id in sorted(keys):
            print(
                f"{title:7} {call_id} {event_id} {_label(source[(call_id, event_id)])}"
            )


if __name__ == "__main__":
    main()
