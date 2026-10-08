#!/usr/bin/env python3
"""PreToolUse hook: refuse `gh pr create` on a branch without a complete plan."""

import json
import os
import subprocess
import sys

payload = json.load(sys.stdin)
command = str(payload.get("tool_input", {}).get("command", ""))

if "gh pr create" not in command:
    sys.exit(0)

project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
result = subprocess.run(
    [sys.executable, os.path.join(project_dir, "scripts", "check_plan.py")],
    cwd=project_dir,
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    reason = (result.stdout or result.stderr).strip()
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        "Every pull request carries a committed plan, and the plan is "
                        f"what gets reviewed. {reason} Commit the plan with the work, "
                        "then open the pull request. See plans/README.md."
                    ),
                }
            }
        )
    )
