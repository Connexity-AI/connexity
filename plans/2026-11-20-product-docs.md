# Docs for the product as it is: no more rebuild

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Connexity is the product: no more rebuild"
  (10.198), pull request 2 of 2. The first (#249) deleted the old code.
- **Design:** No UI change.
- **MCP:** None needed. No tool changes; the README links to the public `/mcp-docs` page.

## Goal

The code now holds one product, but the docs still tell a visitor it is "Connexity 1.x
being rebuilt into 2.0". `README.md` describes agent versioning, test case generation
and deploys that no longer exist. `REBUILD.md` is the first file a session reads.

After this merges, someone opening the public repo reads what Connexity does today, how
an assistant connects, and how to run it. The words "rebuild", "1.x" and "2.0" are gone
outside the history in `plans/` and the decision log's own quotes (Dmytro, 2026-11-19:
"i want to get rid of it so anyone checking it dont have impression its not workable").

## Decisions

### In the roadmap row (Dmytro, 2026-11-19)

1. Rewrite `README.md` and `docs/` for what Connexity is now: what it does, how an
   assistant connects through MCP, how to run it locally, a link to `/mcp-docs`.
2. Split `REBUILD.md`: its decision log becomes `docs-internal/decisions.md`, kept
   whole with dates and quotes; its status and phases go; parked ideas become Later
   rows in the roadmap; then the file is deleted.
3. Rewrite `CLAUDE.md`, the backend and frontend `CLAUDE.md` and the lifecycle guide
   without the framing, pointing at `decisions.md`; drop "do not treat existing
   patterns as the direction". Update the skills and hooks that name `REBUILD.md`.
4. Leave `plans/` as history; only links to `REBUILD.md` are repointed.

### Decided while planning (Dmytro, 2026-11-20)

- **The open questions of `REBUILD.md` (Q5, Q8 to Q10, P1 to P7) move to
  `decisions.md`** as "Open questions" ("In decisions.md").
- **The known gaps ("Open, carried from earlier slices") go to the roadmap as Later
  rows,** with the parked ideas, sent to the roadmap session and not written by this
  one ("Roadmap, Later rows"). Nothing about gaps stays in the repo.
- **`make mcp` is fixed here.** It runs a Windows-only path
  (`.venv/Scripts/python.exe`), so the README's "run it locally" would be false on
  macOS and Linux ("Fix it here").

### Proposed

- **`README.md` in this order:** what Connexity is, in the words of the goal at the top
  of `CLAUDE.md`; what works today (calls recorded and checked, issues, the spec,
  clarifications, scenarios and simulated calls, the Work page and dashboards); connect
  your assistant (Claude Code, Claude.ai, ChatGPT) with a link to `/mcp-docs`; run it
  locally with the `make` targets; where the docs are; contributing and licence. It
  names Retell as the one connected voice platform and says simulations run on Retell.
  No feature it lists is missing from the build.
- **`docs/` keeps `traces/` and `self-hosting/docker-compose.md`** and gains one page,
  `docs/connect-your-assistant.md`, taken from the MCP server's connect guide. The index
  loses its banner.
- **What is left of `REBUILD.md` besides the decision log:**
  - The provider strategy and the rules against overfitting to one reference agent
    (section 1) move to the lifecycle guide; they are rules.
  - The status table, the carry-over tables, the phase outlines and the session log
    are deleted; `plans/` and the roadmap hold that history.
- **`CLAUDE.md` rule 7 becomes** "Delete, do not deprecate. Ask before deleting
  anything the plan does not list." The lifecycle guide's section 6 is renamed
  "Working in this codebase" and loses "Frozen code stays frozen".
- **The done check exempts** `plans/`, `docs-internal/decisions.md`, Pydantic's
  `model_rebuild()` and the design export in `designs/screens/`. Harmless uses
  ("rebuild it from migrations", "rebuilds the backend") are reworded so the check
  stays simple.
- **Links in `plans/` are not edited.** They name `REBUILD.md` in code spans, not as
  links, and a merged plan is not edited (`plans/README.md`). Only
  `plans/TEMPLATE.md`'s "Slice" hint changes, to name the roadmap feature.
- **The `announce-release` skill is rewritten for platform releases only,** and the
  `tanstack-streaming` skill's examples use a current screen in place of Environments.

## Changes

### Public docs

- `README.md` rewritten as above. The banner, the old feature list, the integrations
  table, the five-step quickstart and the Railway section go.
- `docs/README.md` loses its banner; `docs/connect-your-assistant.md` is new.
- `CONTRIBUTING.md` gains `make mcp` and the plan-per-pull-request rule, and loses
  "rebuild it".

### Internal docs

- `REBUILD.md` is deleted. `docs-internal/decisions.md` holds its decision log,
  unchanged row for row, and the open questions.
- `docs-internal/development-lifecycle.md`: every reference to `REBUILD.md` points at
  `decisions.md`, the roadmap or the plan; section 6 as above; it gains the provider
  strategy and the overfitting rules.
- `docs-internal/README.md` lists every document that exists and none that does not.
- `data-model.md` (its "Rebuild status" column becomes "Since"), `testing.md`,
  `migrations.md`, `deployment.md`, `checks-and-incidents.md`, `call-ingestion.md`,
  `releases/cycle.md`, `designs/README.md` and `designs/12-adjustments.md` lose the
  framing and their `REBUILD.md` references.

### Instructions for sessions

- `CLAUDE.md`: "What this is" ends without the 1.x paragraph; "Read first" lists
  `decisions.md` in place of `REBUILD.md` and drops the row that called the README
  and `docs/` old; rule 7 as above; the architecture heading loses "that survives the
  rebuild".
- `frontend/CLAUDE.md`: one line.
- `.claude/skills/announce-release` and `.claude/skills/tanstack-streaming` as above.
  No hook names `REBUILD.md`.

### Code

- Comments and docstrings that say "1.x" in 15 backend files are reworded. One is in
  an enum docstring, so the generated client is regenerated.
- The docstring of migration `0001_baseline` is reworded; the migration is unchanged.
- `Makefile`: `make mcp` runs with `uv run`; the `db-reset` help text is reworded.

## Done when

- `git grep -i -E "rebuild|1\.x|connexity 2\.0" -- . ':!plans' ':!docs-internal/decisions.md' ':!designs/screens'`
  finds only `model_rebuild()`.
- `git grep -n "REBUILD.md" -- . ':!plans' ':!docs-internal/decisions.md'` finds nothing.
- `REBUILD.md` does not exist; every row of its decision log is in `decisions.md`,
  compared line for line.
- Every relative link in `README.md`, `docs/`, `docs-internal/`, `CLAUDE.md` and
  `CONTRIBUTING.md` resolves to a file in the repo.
- Every feature the README names has a route or an MCP tool in the code, listed in the
  Outcome.
- `make mcp` starts the MCP server on macOS.
- `make check` passes.

## Out of scope

- The parked ideas and known gaps as roadmap rows: written by the roadmap session from
  the list this one hands over.
- Whether the published Docker images are current; `docs/self-hosting/docker-compose.md`
  keeps its content.
- The MCP connect guide still names the Readiness screen, which is now the Work page;
  it is served to assistants and is not part of this feature.
- The five review findings left open in #249.
- The website and the docs site.

## Risks

- **A README that promises too much.** Each feature it names is checked against the
  code and listed in the Outcome; a reviewer should still read it as a visitor would.
- **A decision lost in the split.** The decision log is moved whole and compared line
  for line. What is deleted (status, phases, session log) is history that `plans/`
  already holds, but a note that lives nowhere else could go with it; the known gaps
  list is handed to the roadmap session for that reason.
- **Sessions that still look for `REBUILD.md`.** Old plans name it. The root
  `CLAUDE.md` is what a session reads first, and it will name `decisions.md`.

## Outcome

### Deviations from the plan

- **The ladder moved to the lifecycle guide too,** with the provider strategy, marked
  Proposed as it was. The plan named only the provider strategy and the overfitting
  rules; the ladder sat between them and the roadmap's stages follow it.
- **`make mcp` needs two settings the plan did not know about.** With the Windows path
  fixed, the server still refuses to start without `MCP_PUBLIC_BASE_URL` and
  `MCP_OAUTH_ISSUER_URL`. The README, `CONTRIBUTING.md` and `.env.example` now give the
  local values.
- **A local run pulls no calls on its own,** and the README says so: the scheduled pull
  accepts only a Google Cloud Scheduler token.
- **The generated client did not change.** The enum docstring that said "1.x" was
  already reworded in #249.
- **One quote of Dmytro's in `docs-internal/testing.md` reads "[the earlier version]"**
  where he said "1.x", in square brackets, so the done check holds outside the decision
  log. His words are unchanged in `decisions.md`.
- **`docs-internal/README.md` lost its link to `railway-template.md`,** a file that does
  not exist, and the README lost its Railway section for the same reason.
- **The `announce-release` skill's kept example no longer mentions a staging step;**
  there is no staging (review finding).

### Check results

`make check`, run once after the build:

| Step | Result |
|---|---|
| Plan present and complete | failed then, on the empty Outcome; passes with this section |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

After it, three review fixes changed text in `README.md`, `docs-internal/data-model.md`
and a skill; no code.

Done-when:

- `git grep -i -E "rebuild|1\.x|connexity 2\.0" -- . ':!plans' ':!docs-internal/decisions.md' ':!designs/screens'`
  finds two lines, both `model_rebuild()` in `backend/app/models/test_run.py`.
- `git grep -n "REBUILD.md" -- . ':!plans' ':!docs-internal/decisions.md'` finds nothing.
- `REBUILD.md` does not exist. Its decision log had 144 rows on `main`; all 144 are in
  `decisions.md` unchanged, compared line for line, plus one new row for this change.
- Relative links: 55 Markdown files checked (`README.md`, `CLAUDE.md` files,
  `CONTRIBUTING.md`, `docs/`, `docs-internal/`, `designs/`, the skills); every link
  resolves except a placeholder inside the `create-pr` skill's template.
- `make mcp` on macOS, with the two addresses set: the server starts and
  `GET http://localhost:8001/manifest` answers 200. Connecting an assistant to a local
  server was not tried.
- `https://app.connexity.ai/mcp-docs` answers 200.

What the README names, and where it is in the build:

| README | In the build |
|---|---|
| Calls recorded, tool calls, versions, n8n executions | `scan_calls`, `list_calls`, `get_call`; the Calls page and the single call |
| Checks and issues, fixed, reopened, archived | `list_issues`, `get_issue`, `mark_issue_fixed`, `archive_issue`, `unarchive_issue`; the Issues page |
| The spec and questions | `write_spec`, `get_spec`, `raise_clarifications`, `answer_clarifications`; the Spec tab, question cards on Work |
| Scenarios, simulated calls, Verified | `write_scenarios`, `write_scenario_set`, `run_scenarios`, `get_test_runs`; the Tests tab |
| The next task | `get_next_task`, `list_tasks`, `move_task`; the Work page |
| Dashboard and score | `get_dashboard`; the Dashboard, Agents list and agent page |
| Connecting Claude Code, Claude, ChatGPT | the Work page's "Show how", Account › Assistant access, the OAuth routes |

The tool names were read from the running MCP server's manifest (32 tools).

`/code-review` (medium) reported 4 findings: the README misstated how a local run can
pull calls (fixed), the renamed "Since" column still said "Keep" (fixed), the skill
example mentioned a staging that does not exist (fixed), and the connect steps now
live in two places, the new docs page and the MCP server's guide (left).

The parked ideas and the known gaps were sent to the roadmap session on 2026-11-20,
with the five findings left open in #249.

For Dmytro to check on screen: nothing changed on any screen. Read `README.md` as a
visitor would.

### Not done

- The roadmap rows for the parked ideas and known gaps: handed over, not written here.
- The MCP server's connect guide still names the Readiness screen. The new docs page
  does not, so the two differ.
- Whether the published Docker images are current was not checked;
  `docs/self-hosting/docker-compose.md` is unchanged.
- An assistant was not connected to a local MCP server end to end.
- Old plans still name `REBUILD.md`; they are records and were not edited.
