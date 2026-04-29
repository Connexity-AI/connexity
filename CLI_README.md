# connexity-cli

Command-line client for [Connexity Evals](https://github.com/Connexity-AI/connexity-evals) — drive eval runs, manage agents and test cases, and gate CI on regressions, all from the terminal.

`connexity-cli` is a thin wrapper over the Connexity Evals REST API. It covers every backend route — auth, agents, eval configs, test cases, runs (with SSE streaming), custom metrics, prompt editor, integrations, environments, calls, config, and health — so you can fully automate eval workflows without touching the web UI.

## Installation

```bash
pip install connexity-cli
```

The wheel pulls in only `click`, `httpx`, and `httpx-sse` — no FastAPI, no SQLModel, no LLM SDKs.

## Authentication

The CLI authenticates against a Connexity Evals API server using a Bearer JWT.

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

# CI gate: regression check (exits 1 on regression, 0 on pass)
connexity-cli compare --candidate <run-id> --against-baseline

# Stream agent execution events live
connexity-cli runs stream <run-id>

# AI-assisted prompt editing — SSE events go to stderr, final assistant
# message + edited_prompt to stdout (drops to non-streaming when piping)
connexity-cli prompt-editor chat <session-id> --message "tighten the refusal prose"

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

## Output formats

Two formats are supported, switchable per-command via `--output` or globally via `--output` on the root group:

- `table` (default) — human-readable tables with auto-detected column widths
- `json` — pretty-printed JSON, friendly to `jq` / `gron` / scripting

## Command tree

Each top-level group mirrors a backend router:

| Group                   | Purpose                                                                                |
|-------------------------|----------------------------------------------------------------------------------------|
| `login` / `logout` / `whoami` | Auth & session                                                                   |
| `agents`                | CRUD, draft/publish/rollback, versions, version diff, guidelines                       |
| `eval-configs`          | CRUD, member (test-case) management                                                    |
| `test-cases`            | CRUD, bulk import/export, generate, AI editor                                          |
| `test-case-results`     | Per-test-case run result CRUD                                                          |
| `runs`                  | CRUD, execute, cancel, stream (SSE), baselines, compare, suggestions                   |
| `custom-metrics`        | CRUD plus LLM-backed metric preview generation                                         |
| `prompt-editor`         | Sessions, messages, presets, streaming chat                                            |
| `integrations`          | Third-party providers (Retell), connection test, list provider-side agents             |
| `environments`          | Agent deployment-target bindings                                                       |
| `calls`                 | Observed external calls (Retell), refresh / mark-seen                                  |
| `config`                | Read-only API metadata, available metrics, LLM models                                  |
| `health`                | Server health probe                                                                    |
| `run` / `compare` / `baseline` | Top-level convenience wrappers for common one-shot CI workflows                 |

Run `connexity-cli <group> --help` (or `connexity-cli <group> <subcommand> --help`) to see flags and arguments.

## Exit codes

- `0` — success
- `1` — operation completed but indicates failure (run failed/cancelled, regression detected, `import` returned errors)
- `2` — argument / configuration error, timeout

## License

MIT — see [LICENSE](LICENSE).
