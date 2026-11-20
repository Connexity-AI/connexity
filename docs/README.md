# Connexity docs

User- and operator-facing documentation. The content of this folder is the source for the public docs site at **[docs.connexity.ai](https://docs.connexity.ai)** — keep it curated for that audience.

> Contributor- and maintainer-only material (release pipeline, DB schema, internal migration workflow) lives in [`../docs-internal/`](../docs-internal) and is **not** published.

## Layout

- [`connect-your-assistant.md`](./connect-your-assistant.md) — connecting Claude Code, Claude or ChatGPT through MCP
- [`self-hosting/`](./self-hosting) — running Connexity on your own infrastructure
  - [`docker-compose.md`](./self-hosting/docker-compose.md) — local & VM deployment via Docker Compose
- [`traces/`](./traces) — how a call is recorded
  - [`trace-schema.md`](./traces/trace-schema.md) — the trace format
  - [`ingest.md`](./traces/ingest.md) — sending a call to Connexity
  - [`retell.md`](./traces/retell.md), [`n8n.md`](./traces/n8n.md) — what is read from each system
  - [`versions.md`](./traces/versions.md) — component versions

## Writing rules for this folder

- Audience is a user or operator who does not have access to the repo's git history, CI workflows, or internal tooling. Don't reference release-please, GitHub Actions, deploy hooks, or anything that only matters to maintainers — put that in `docs-internal/` instead.
- Relative links between docs are fine. Cross-references into the rest of the repo work locally but won't resolve on the published site, so prefer self-contained explanation where possible.
- Code symbols (table names, internal module paths) are okay only when the user genuinely needs them (e.g. the trace format). Don't expose internal schema for its own sake.
