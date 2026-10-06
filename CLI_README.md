# connexity-cli

Command-line client for [Connexity](https://github.com/Connexity-AI/connexity) — drive eval runs, manage agents and test cases, and gate CI on regressions, all from the terminal.

`connexity-cli` is a thin wrapper over the Connexity REST API. It covers the public surface used to drive eval workflows from CI: auth, agents, eval configs, test cases, runs (with SSE streaming), custom metrics, integrations, environments, calls, config, and health. Account self-service (signup, password reset) stays in the web UI.

## Installation

```bash
pip install connexity-cli
```

The wheel pulls in only `click`, `httpx`, and `httpx-sse` — no FastAPI, no SQLModel, no LLM SDKs.

## Authentication

The CLI authenticates against a Connexity API server using a Bearer JWT.

| Source                                                       | When used                                          |
|--------------------------------------------------------------|----------------------------------------------------|
| `--token` / `--api-url` flags                                | Highest precedence — explicit per-invocation       |
| `CONNEXITY_CLI_API_TOKEN` / `CONNEXITY_CLI_API_URL` env vars | Typical CI usage                                   |
| `~/.config/connexity-cli/credentials.json` (mode `0600`)     | Written by `connexity-cli login --save`            |

```bash
# One-time interactive login (writes credentials file)
connexity-cli login --email me@example.com --save

# Or set env vars in CI
export CONNEXITY_CLI_API_URL=https://evals.example.com
export CONNEXITY_CLI_API_TOKEN="$CI_EVALS_TOKEN"
```

## Quick start

```bash
# Inspect resources
connexity-cli agents list
connexity-cli eval-configs list
connexity-cli test-cases list --tag smoke

# Author resources from JSON files (use "-" to read stdin)
connexity-cli agents create --from-file ./agent.json
connexity-cli eval-configs members replace <eval-config-id> --from-file ./members.json

# End-to-end: trigger a run, wait for completion, mark as baseline
connexity-cli run \
  --agent my-agent \
  --eval-config smoke-suite \
  --stream \
  --set-baseline

# CI gate: trigger a run AND fail if it doesn't clear the eval-config thresholds
# (exits 1 when metrics_passed=false or cases_passed=false; --no-fail-on-thresholds opts out)
connexity-cli run \
  --agent my-agent \
  --eval-config smoke-suite \
  --metrics-pass-threshold 80 \
  --cases-pass-threshold 100

# CI gate: regression check against the baseline (exits 1 on regression
# OR when the candidate fails its own metrics or cases threshold)
connexity-cli compare --candidate <run-id> --against-baseline

# Stream agent execution events live
connexity-cli runs stream <run-id>

# JSON output for piping into jq
connexity-cli --output json agents list | jq '.data[].name'
```

## Authoring patterns

Every command that creates or updates a resource takes a single `--from-file PATH` (or `--from-file -` for stdin) with a JSON body that matches the backend Pydantic schema (e.g. `AgentCreate`, `RunCreate`, `EvalConfigCreate`, `CustomMetricCreate`). The CLI does no schema duplication — the server validates and returns clear errors.

```bash
# Create an agent from a file
echo '{"name": "support-bot", "endpoint_url": "https://my-agent.example/api"}' \
  | connexity-cli agents create --from-file -

# Patch an eval config
connexity-cli eval-configs update smoke-suite --from-file ./patch.json

# Run with a full RunConfig (judge_config, simulator_config, metrics_selection, ...)
connexity-cli runs create --from-file ./run.json --auto-execute
```

## Pass/fail thresholds

Every run carries two run-level pass/fail dimensions, snapshotted from the eval config and overridable per run:

| Threshold                  | Meaning                                                                                  | Default |
|----------------------------|------------------------------------------------------------------------------------------|---------|
| `metrics_pass_threshold`   | Weighted average of the judge `overall_score` across cases that produced a verdict (0-100) | 80      |
| `cases_pass_threshold`     | Fraction of cases that pass / total executions, errored cases counting as not-passed (0-100) | 100     |

`connexity-cli run` and `connexity-cli compare` gate their exit code on these by default. Override per invocation:

```bash
connexity-cli run \
  --agent my-agent \
  --eval-config smoke-suite \
  --metrics-pass-threshold 75 \
  --cases-pass-threshold 95
```

Pass `--no-fail-on-thresholds` to print the verdict but exit 0 regardless. Full formula and rationale: [docs/evals/scoring-and-thresholds.md](docs/evals/scoring-and-thresholds.md).

## Output formats

Two formats are supported, switchable per-command via `--output` or globally via `--output` on the root group:

- `table` (default) — human-readable tables with auto-detected column widths
- `json` — pretty-printed JSON, friendly to `jq` / `gron` / scripting

## Command tree

Each top-level group mirrors a backend router:

| Group                   | Purpose                                                                                |
|-------------------------|----------------------------------------------------------------------------------------|
| `login` / `logout` / `whoami` | Auth & session                                                                   |
| `agents`                | CRUD, draft/publish/rollback, versions, version diff                                   |
| `eval-configs`          | CRUD, member (test-case) management                                                    |
| `test-cases`            | CRUD, bulk import/export, generate                                                     |
| `test-case-results`     | Per-test-case run result CRUD                                                          |
| `runs`                  | CRUD, execute, cancel, stream (SSE), baselines, compare, suggestions                   |
| `custom-metrics`        | CRUD plus LLM-backed metric preview generation                                         |
| `integrations`          | Third-party providers (Retell), connection test, list provider-side agents             |
| `environments`          | Bindings between an agent and its provider account (used for call sync)                |
| `calls`                 | Observed external calls (Retell), refresh / mark-seen                                  |
| `config`                | Read-only API metadata, available metrics, LLM models                                  |
| `health`                | Server health probe                                                                    |
| `run` / `compare` / `baseline` | Top-level convenience wrappers for common one-shot CI workflows                 |

Run `connexity-cli <group> --help` (or `connexity-cli <group> <subcommand> --help`) to see flags and arguments.

### Subcommand reference (selected)

Not exhaustive — run `--help` for the full set. These are the commands you'll reach for in CI and day-to-day work:

```text
agents      list | show <ref> | create | update <id> | delete <id>
            versions list <ref> | versions show <ref> <n> | versions diff <ref> <a> <b>
            draft get <ref> | draft set <ref> | draft discard <ref>
            publish <ref> | rollback <ref> --to-version <n>
runs        list | show <id> | create | update <id> | delete <id>
            execute <id> | cancel <id> | stream <id>
            baseline get --agent <ref> --eval-config <ref> | baseline set <id>
            compare --baseline <id> --candidate <id> [--include-analysis] [--fail-on-thresholds]
            compare-suggestions --baseline <id> --candidate <id>
environments list --agent <ref> | create | delete <id>
custom-metrics list | show <id> | create | update <id> | delete <id> | preview | generate
test-cases  list | show <id> | create | update <id> | delete <id>
            import <file> [--overwrite] | export | generate

# Top-level convenience wrappers for the most common CI flows:
run         --agent <ref> --eval-config <ref> [--metrics-pass-threshold N] [--cases-pass-threshold N] [--stream] [--set-baseline]
compare     --candidate <id> (--baseline <id> | --against-baseline)
baseline    get | set <id>
```

## Exit codes

- `0` — success
- `1` — operation completed but indicates failure: run failed / cancelled, regression detected, candidate failed its metrics or cases threshold (default-on, opt out with `--no-fail-on-thresholds`), or `import` returned errors
- `2` — argument / configuration error, timeout, network failure

## License

MIT — see [LICENSE](LICENSE).
