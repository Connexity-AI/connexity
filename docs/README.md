# Connexity docs

User- and operator-facing documentation. The content of this folder is the source for the public docs site at **[docs.connexity.ai](https://docs.connexity.ai)** — keep it curated for that audience.

> Contributor- and maintainer-only material (release pipeline, DB schema, internal migration workflow, Railway template blueprint) lives in [`../docs-internal/`](../docs-internal) and is **not** published.

## Layout

- [`self-hosting/`](./self-hosting) — running Connexity on your own infrastructure
  - [`docker-compose.md`](./self-hosting/docker-compose.md) — local & VM deployment via Docker Compose
  - [`railway.md`](./self-hosting/railway.md) — deploying to Railway
  - [`kubernetes.md`](./self-hosting/kubernetes.md) — production Helm installs, optional MCP, and optional voice worker scaling
- [`agents/`](./agents) — integrating your agent with the platform
  - [`contract.md`](./agents/contract.md) — the HTTP contract eval agents must implement
- [`evals/`](./evals) — running and interpreting evaluations
  - [`runtimes.md`](./evals/runtimes.md) — evaluation runtime kinds (`connexity`, `retell`, `custom_endpoint`)
  - [`test-case-schema.md`](./evals/test-case-schema.md) — authoring test cases
  - [`judge-criteria.md`](./evals/judge-criteria.md) — LLM-judge metrics and tiers
  - [`scoring-and-thresholds.md`](./evals/scoring-and-thresholds.md) — how `overall_score` and pass/fail are computed

## Writing rules for this folder

- Audience is a user or operator who does not have access to the repo's git history, CI workflows, or internal tooling. Don't reference release-please, GitHub Actions, deploy hooks, or anything that only matters to maintainers — put that in `docs-internal/` instead.
- Relative links between docs are fine. Cross-references into the rest of the repo (`../../examples/...`) work locally but won't resolve on the published site, so prefer self-contained explanation where possible.
- Code symbols (table names, internal module paths) are okay only when the user genuinely needs them (e.g. in the agent contract, the canonical Pydantic models). Don't expose internal schema for its own sake.
