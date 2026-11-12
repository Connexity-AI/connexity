# Designs

Prompts written for Claude Design, where Dmytro designs the web app's screens, and the
table of who does what. They are reference for the sessions that build each feature;
the screens themselves live in Claude Design.

- **Numbered prompts (`01-` to `12-`)** were pasted into Claude Design in order. Each
  later prompt changes earlier ones, so read a screen's prompts in order: a later prompt
  wins. `12-adjustments.md` holds many small numbered changes across the app; a later
  item wins over an earlier one.
- **`who-does-what.md`** is the job-by-job split between Connexity, the assistant and the
  person. Its short form is [`docs-internal/responsibilities.md`](../docs-internal/responsibilities.md).

Where a prompt and a document in `docs-internal/`, `CLAUDE.md` or `REBUILD.md`
disagree, the document wins and the prompt is history. For example, prompt 03 says the
spec is created on connection; the assistant now writes it as a Readiness step.

A build shows only what works (`CLAUDE.md` rule 14): prompts describe the whole vision,
and a feature builds only its part. All names and numbers in the prompts are
placeholders.
