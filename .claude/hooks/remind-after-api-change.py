#!/usr/bin/env python3
"""PostToolUse hook: remind the session what a route or model edit obliges it to do."""

import json
import sys

payload = json.load(sys.stdin)
tool_input = payload.get("tool_input", {})
tool_response = payload.get("tool_response", {})
path = str(
    tool_input.get("file_path")
    or (tool_response.get("filePath") if isinstance(tool_response, dict) else "")
    or ""
).replace("\\", "/")

reminders = []
if "backend/app/models/" in path:
    reminders.append(
        "A model changed. If a table model changed, add a migration "
        '(`make db-migrate MSG="..."`); the test test_models_match_migrated_schema '
        "fails on drift."
    )
if "backend/app/models/" in path or "backend/app/api/routes/" in path:
    reminders.append(
        "The OpenAPI schema may have changed. Before committing, run "
        "`bash scripts/generate-client.sh`; CI fails if the client is stale."
    )

if reminders:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": " ".join(reminders),
                }
            }
        )
    )
