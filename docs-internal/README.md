# Internal docs

Contributor- and maintainer-only documentation. **Not** published to
[docs.connexity.ai](https://docs.connexity.ai) - the public docs site only syncs
[`../docs/`](../docs).

This is the right home for anything that:

- describes the release / deploy pipeline, or GitHub Actions workflows
- documents internal data model, migration mechanics, or schema details that operators don't need
- captures repo conventions for maintainers (for example, the MCP extension workflow)

If you find yourself writing about how a user runs Connexity, configures their
agent, or interprets eval results, that belongs in [`../docs/`](../docs)
instead.

## Layout

- [`decisions.md`](./decisions.md) - the decision log and the open questions
- [`development-lifecycle.md`](./development-lifecycle.md) - how the project is built: plans, roles, verification, what Connexity does not build
- [`responsibilities.md`](./responsibilities.md) - who does what between Connexity, the assistant and the person
- [`checks-and-incidents.md`](./checks-and-incidents.md) - the model behind checks, findings, issues and incidents
- [`metrics.md`](./metrics.md) - how the numbers on screen are measured
- [`data-model.md`](./data-model.md) - ER diagram and table-level schema reference
- [`mcp-architecture.md`](./mcp-architecture.md) - MCP adapter architecture and how to add new tools
- [`work.md`](./work.md) - the Work page: the assistant's tasks, what waits for the person, Blocks and Blocked by; decisions and open questions
- [`testing.md`](./testing.md) - test scenarios, rule verdicts, Critical rules, sets and the gate; decisions and open questions
- [`issue-types.md`](./issue-types.md) - every check: what it finds, found by a rule or a model, category, default severity
- [`call-ingestion.md`](./call-ingestion.md) - how calls reach Connexity: the scheduled pull, the first scan for history, the optional webhook
- [`deployment.md`](./deployment.md) - how `main` reaches Google Cloud Run: services, triggers, secrets, the database
- [`migrations.md`](./migrations.md) - Alembic workflow, conventions, gotchas
- [`releases/`](./releases) - release pipeline
  - [`cycle.md`](./releases/cycle.md) - end-to-end release walkthrough (PR -> tag -> deploy -> announce)
  - [`platform.md`](./releases/platform.md) - platform release workflow (backend + frontend, `vX.Y.Z` tags)
