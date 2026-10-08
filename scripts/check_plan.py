#!/usr/bin/env python3
"""Check that a branch carries a plan file, and that the plan is complete.

Every pull request is reviewed through its plan, not its diff. This script is the
single definition of "has a plan"; CI, `make check` and the Claude Code hook all call it.

Usage:
    python3 scripts/check_plan.py [--base origin/main] [--include-working-tree]

Exit codes: 0 the branch has one complete plan, 1 it does not.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PLANS_DIR = "plans"
NOT_PLANS = {"README.md", "TEMPLATE.md"}

# Sections every plan must have, in this order, each with real content.
REQUIRED_SECTIONS = [
    "Goal",
    "Changes",
    "Decisions",
    "Done when",
    "Out of scope",
    "Risks",
    "Outcome",
]
# Filled in after the work, before the pull request is opened.
OUTCOME_SUBSECTIONS = ["Deviations from the plan", "Check results", "Not done"]

PLACEHOLDER = re.compile(r"<!--.*?-->", re.DOTALL)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def changed_files(base: str, include_working_tree: bool) -> list[str]:
    files = set(git("diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD").split("\n"))
    if include_working_tree:
        files |= set(git("diff", "--name-only", "--diff-filter=AMR", "HEAD").split("\n"))
        files |= set(git("ls-files", "--others", "--exclude-standard").split("\n"))
    return sorted(f for f in files if f)


def is_plan(path: str) -> bool:
    parts = Path(path).parts
    return (
        len(parts) == 2
        and parts[0] == PLANS_DIR
        and path.endswith(".md")
        and parts[1] not in NOT_PLANS
    )


def section_bodies(text: str, level: str) -> dict[str, str]:
    """Map each heading of the given level (e.g. '##') to the text beneath it."""
    pattern = re.compile(rf"^{re.escape(level)} +(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    bodies: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        bodies[match.group(1)] = text[match.end() : end]
    return bodies


def has_content(body: str) -> bool:
    return bool(PLACEHOLDER.sub("", body).strip())


def problems_in(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    problems: list[str] = []

    sections = section_bodies(text, "##")
    for name in REQUIRED_SECTIONS:
        if name not in sections:
            problems.append(f"missing section '## {name}'")
        elif name != "Outcome" and not has_content(sections[name]):
            problems.append(f"section '## {name}' is empty")

    if "Outcome" in sections:
        subsections = section_bodies(sections["Outcome"], "###")
        for name in OUTCOME_SUBSECTIONS:
            if name not in subsections:
                problems.append(f"missing '### {name}' under '## Outcome'")
            elif not has_content(subsections[name]):
                problems.append(
                    f"'### {name}' is empty: fill it in before opening the pull "
                    "request (write 'None.' if there is nothing to report)"
                )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base", default="origin/main")
    parser.add_argument(
        "--include-working-tree",
        action="store_true",
        help="also count uncommitted and untracked files (for local runs)",
    )
    args = parser.parse_args()

    files = changed_files(args.base, args.include_working_tree)
    if not files:
        print("No changes against the base branch; nothing to check.")
        return 0

    plans = [f for f in files if is_plan(f)]
    other = [f for f in files if not is_plan(f)]

    if not plans:
        print(
            f"This branch has no plan. Add one under {PLANS_DIR}/ "
            f"(copy {PLANS_DIR}/TEMPLATE.md). See {PLANS_DIR}/README.md."
        )
        return 1
    if len(plans) > 1:
        print("A pull request carries exactly one plan. Found: " + ", ".join(plans))
        return 1
    if not other:
        print(
            "This branch changes only its plan. A plan is never merged on its own: "
            "the pull request carries the plan together with the work."
        )
        return 1

    plan = plans[0]
    problems = problems_in(plan)
    if problems:
        print(f"{plan} is incomplete:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"Plan found and complete: {plan}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
