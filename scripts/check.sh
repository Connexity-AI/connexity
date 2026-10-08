#!/usr/bin/env bash
# Run every gate a pull request must pass, and report how long each one took.
#
# Usage: bash scripts/check.sh   (or: make check)
#
# Every step runs even if an earlier one fails, so one run shows everything that
# is broken. Exits non-zero if any step failed.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$(mktemp -d)"
COVERAGE_MIN=90

names=()
results=()
durations=()
failed=0

run_step() {
  local name="$1"
  shift
  local log="$LOG_DIR/${#names[@]}.log"
  local start=$SECONDS

  printf '▶ %s\n' "$name"
  if (cd "$ROOT" && "$@") >"$log" 2>&1; then
    results+=("ok")
  else
    results+=("FAILED")
    failed=1
    # Show the tail of a failing step right away; the full log path is printed too.
    # Credentials in connection strings are masked before anything is printed.
    tail -n 40 "$log" | sed -E 's#://[^:/@[:space:]]+:[^@[:space:]]+@#://<redacted>@#g; s/^/    /'
    printf '    (full log: %s)\n' "$log"
  fi
  names+=("$name")
  durations+=($((SECONDS - start)))
}

start_database() {
  # Tests need the local Postgres from docker-compose. Harmless if it is already up.
  if docker compose up -d --wait database; then
    return 0
  fi
  # Compose could not start it (for example a .env it cannot parse). That is fine
  # as long as a Postgres is already listening where the tests will look.
  local port
  port="$(grep -E '^POSTGRES_PORT=' .env 2>/dev/null | tail -n 1 | cut -d= -f2 | tr -d '[:space:]')"
  port="${port:-5432}"
  if nc -z localhost "$port" >/dev/null 2>&1; then
    echo "docker compose failed, but a Postgres is already listening on port $port."
    return 0
  fi
  return 1
}

backend_lint() {
  cd backend && uv run ruff check app cli scripts && uv run ruff format --check app cli scripts
}

backend_types() {
  cd backend && uv run pyright
}

backend_tests() {
  # Same command and coverage floor as the CI job. The suite includes the test that
  # fails when models and migrations disagree.
  cd backend && uv run coverage run --source=app -m pytest -q &&
    uv run coverage report --fail-under="$COVERAGE_MIN" >/dev/null
}

mcp_tests() {
  cd mcp_server && uv run --extra dev pytest -q
}

frontend_lint() {
  cd frontend && pnpm lint
}

frontend_types() {
  cd frontend && pnpm turbo check-types
}

plan_is_present() {
  # Reviewers read the plan, not the diff. Skipped on main, where there is no branch
  # to plan for.
  if [ "$(git branch --show-current)" = "main" ]; then
    echo "On main: no plan required."
    return 0
  fi
  python3 scripts/check_plan.py --include-working-tree
}

client_is_fresh() {
  # Regenerate the API client and fail if that changed anything.
  local client_dir="frontend/apps/web/src/client"
  local before after
  before="$(find "$client_dir" -type f -exec shasum {} + | sort | shasum)"
  bash scripts/generate-client.sh || return 1
  after="$(find "$client_dir" -type f -exec shasum {} + | sort | shasum)"
  if [ "$before" != "$after" ]; then
    echo "The generated API client was out of date. It has been regenerated: review and commit it."
    return 1
  fi
}

total_start=$SECONDS

run_step "Plan present and complete" plan_is_present
run_step "Start local database" start_database
run_step "Backend lint and format" backend_lint
run_step "Backend types (pyright)" backend_types
run_step "Backend tests and coverage" backend_tests
run_step "MCP server tests" mcp_tests
run_step "Frontend lint" frontend_lint
run_step "Frontend types" frontend_types
run_step "Generated client is fresh" client_is_fresh

printf '\n%-32s %-8s %s\n' "Step" "Result" "Time"
printf '%-32s %-8s %s\n' "--------------------------------" "------" "----"
for i in "${!names[@]}"; do
  printf '%-32s %-8s %ss\n' "${names[$i]}" "${results[$i]}" "${durations[$i]}"
done
printf '%-32s %-8s %ss\n' "Total" "" "$((SECONDS - total_start))"

if [ "$failed" -ne 0 ]; then
  printf '\nSome checks failed. Logs: %s\n' "$LOG_DIR"
  exit 1
fi

rm -rf "$LOG_DIR"
printf '\nAll checks passed.\n'
