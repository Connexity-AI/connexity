# Internal docs

Contributor- and maintainer-only documentation. **Not** published to
[docs.connexity.ai](https://docs.connexity.ai) - the public docs site only syncs
[`../docs/`](../docs).

This is the right home for anything that:

- describes the release / deploy pipeline, GitHub Actions workflows, or PyPI publishing setup
- documents internal data model, migration mechanics, or schema details that operators don't need
- captures repo conventions for maintainers (for example, MCP extension workflow or the Railway template blueprint)

If you find yourself writing about how a user runs Connexity, configures their
agent, or interprets eval results, that belongs in [`../docs/`](../docs)
instead.

## Layout

- [`data-model.md`](./data-model.md) - ER diagram and table-level schema reference
- [`mcp-architecture.md`](./mcp-architecture.md) - MCP adapter architecture and how to add new tools
- [`issue-types.md`](./issue-types.md) - every check: what it finds, found by a rule or a model, category, default severity
- [`call-ingestion.md`](./call-ingestion.md) - how calls reach Connexity: the Retell webhook now, the first scan for history, a safety-net pull later
- [`deployment.md`](./deployment.md) - how `main` reaches Google Cloud Run: services, triggers, secrets, the database
- [`migrations.md`](./migrations.md) - Alembic workflow, conventions, gotchas
- [`railway-template.md`](./railway-template.md) - source-controlled blueprint for the Railway template composer
- [`releases/`](./releases) - release pipeline
  - [`cycle.md`](./releases/cycle.md) - end-to-end release walkthrough (PR -> tag -> deploy -> announce)
  - [`platform.md`](./releases/platform.md) - platform release workflow (backend + frontend, `vX.Y.Z` tags)
  - [`pypi.md`](./releases/pypi.md) - `connexity-cli` PyPI publishing setup and troubleshooting
