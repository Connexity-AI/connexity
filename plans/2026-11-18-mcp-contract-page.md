# MCP contract page

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "MCP contract page" (10.17).
- **Design:** `Connexity MCP Docs.dc.html`, from the design review delivered 2026-11-18
  (the only new screen in it; added to `designs/screens/` in this PR).
- **MCP:** no new tool. The MCP server gains a public, read-only `GET /manifest` the page
  is built from; `write_scenario_set` changes annotation.

## Goal

Anyone can open `/mcp-docs`, with no login, and see exactly what an assistant can do in
Connexity: every tool grouped by the work, what each may do, one plain line, its
inputs, how every answer is shaped, and the guides. It is generated from the running
MCP server, so it cannot drift from what the assistant really gets.

## Decisions

- **Accept, build** (Dmytro, 2026-11-18).
- **Public, no login** (Dmytro, 2026-11-18: "Public, no login needed"), not in the
  sidebar, no workspace data.
- **In the style of Jev's MCP card** (Dmytro, 2026-11-18): tools grouped by the work
  (start and tasks, connect, calls and issues, agents and spec, testing), each with
  what it may do (reads, writes, reads your platform, talks to your agent, your
  decision), one plain line, inputs on expand; the answer shape (data, rules,
  next_steps, guide); the guides.
- **"Your decision" is an explicit flag, not an annotation group** (Dmytro, 2026-11-18:
  "yes, add it to 10.17"): set only on `archive_issue`, `unarchive_issue` and
  `answer_clarifications`; `move_task` is marked "only when you ask";
  `write_scenario_set` moves from DECIDES to CREATES, since sets are the assistant's own
  and the gate runs every scenario.
- **Generated from the running MCP server** (Proposed in the row).
- **Every tool input gets a one-line description** (Dmytro, 2026-11-18, question 1).
- **Each tool's plain line is written per tool** in a registry beside the tools,
  checked by a test (Dmytro, 2026-11-18, question 2).
- **Every change to the MCP part also updates this page** (Dmytro, 2026-11-18: "add to
  operational context that every time we do changes to MCP part of the task should be
  to update this page").

## What exists

- **The MCP server** (`mcp_server/`) is a FastAPI app around FastMCP, with public routes
  already (`/healthz`, OAuth discovery). 30 tools, each with an annotation group
  (READ_ONLY 14, CREATES 8, DECIDES 5, CONNECTS 1, SCANS 1, RUNS 1), a docstring, and
  inputs from the function's signature (most without per-input descriptions). 9 guides
  as `connexity://guides/<name>` resources.
- **The web app** gates sign-in in `(app)/layout.tsx`, so a page outside `(app)` is
  public. It knows the MCP URL only through the backend (`mcp_url` on Work).

## Changes

### The contract, on the MCP server

- **One registry beside the tools** (`contract.py`): for each tool, its group, its
  effect (reads, writes, reads your platform, talks to your agent), whether it needs the
  person's yes (the three above), `move_task`'s "only when you ask", its one plain line
  and its guide. A test fails when a tool has no entry or an entry names
  no tool.
- **Effect from the annotation, decision from the flag:** READ_ONLY reads; CREATES and
  DECIDES write; SCANS and CONNECTS read your platform; RUNS talks to your agent. "Your
  decision" is shown only where the flag is set.
- **`write_scenario_set`** becomes CREATES.
- **`GET /manifest`**, public and read-only: the server version, its public URL, the
  answer shape, the groups with their tools (name, effect, decision, line, guide,
  inputs from each tool's input schema: name, type, required, description), and the
  guides (URI, title). No workspace data, no auth.

### Inputs

- Every tool input gets a one-line description in its signature, so the schema the
  assistant reads and the page both carry it.

### The page

- **`/mcp-docs`** in the web app, outside the signed-in area, built on the server from
  `GET /manifest` (cached for a few minutes), as designed: the header with tool and
  guide counts, the server URL with how to add it, the answer shape, the effect legend,
  the groups with expandable tools, the guides, and "Generated from the live MCP
  server" with the version.
- **If the manifest cannot be read,** the page says so plainly; it never shows the
  design's stand-in tools.
- **New setting:** `MCP_SERVER_URL` for the web app's server (Zod), in `.env.example`.
- **Dark and light,** from the design's tokens.

### Docs

- `docs-internal/mcp-architecture.md`: the manifest, the contract registry, and that the
  page is generated from it.

### The rule for every later MCP change

- **`CLAUDE.md` rule 10** gains: a change to an MCP tool (added, removed, renamed, new
  inputs or behaviour) also updates the contract page: its entry in the registry (group,
  effect, decision, line, guide) and a description for every input.
- **`docs-internal/development-lifecycle.md` section 6,** the same, beside "Everything
  ships with its MCP tools".
- **`plans/TEMPLATE.md`'s "MCP" line** asks for the contract page change too.
- **Enforced by tests:** the registry test fails for a tool without an entry, and a
  second test fails for any tool input without a description.

## Done when

- `GET /manifest` answers all 30 tools in their groups with effect, decision, line,
  guide and inputs, and the 9 guides; the three decision tools and `move_task` are
  marked; `write_scenario_set` is a write. Tested in `mcp_server/tests`.
- The registry test fails for a tool without an entry, and the inputs test fails for
  an input without a description.
- `CLAUDE.md`, the lifecycle guide and the plan template carry the rule.
- `/mcp-docs` renders without a login from a running MCP server, and says so when the
  manifest is unreachable.
- `make check` passes.
- **For Dmytro on screen:** `/mcp-docs` signed out, dark and light, a tool expanded.

## Out of scope

- A link to the page from the sidebar or the website.
- Any workspace data on the page.
- Per-input examples.

## Risks

- **The design marks `connect_voice_platform` and `mark_critical_rules` as "Your
  decision"; the roadmap row (Dmytro's words) sets the flag on three tools only.** The
  build follows the row; the design should be brought in line in the design session
  (rule 9).
- **A public manifest lists every tool and its inputs,** which today an MCP client sees
  only after signing in. Making the list public is the point of the page; it holds no
  data and no secrets.

## Questions

None left: both were answered (see Decisions).

## Outcome

### Deviations from the plan

- **The manifest also carries each guide's text,** because the design opens a guide in a
  side panel. The page renders it with a small renderer (headings, paragraphs, lists,
  `code`, bold), enough for the nine guides; it uses no markdown library.
- **Only top-level inputs** have descriptions and are tested. Inputs that are lists of
  objects (`AgentToAdd`, `SpecRuleToWrite`, `ScenarioToWrite`, `QuestionToRaise`,
  `AnswerToGive`) show as `object[]` with one line; their fields are not on the page.
- **What a tool may do comes from its annotations,** not from the registry, so the two
  cannot disagree: read only reads; reaching out reads the platform (idempotent) or
  talks to the agent (not); everything else writes. So `add_agents` shows Writes and
  `connect_voice_platform` Reads your platform.
- **The design marks `connect_voice_platform` and `mark_critical_rules` as "Your
  decision";** the build follows the roadmap row (three tools). The design needs that
  change in the design session (rule 9); not done here.
- **The page is rendered on request** (`ƒ /mcp-docs`) and the manifest fetch is cached
  for five minutes, rather than built static and revalidated.
- **`move_task`** shows "Only when you ask." after its line, in place of a chip the
  design does not have.

### Check results

`make check`:

| Step | Result |
|---|---|
| Plan present and complete | failed: this Outcome was still empty; filled now |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok (53; new `test_contract.py`, 6) |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

The frontend build compiles, with `/mcp-docs` server-rendered.

**`/code-review` (high), 6 findings:** fixed two (`list_tasks` and `list_agents` again
take a page size that cannot be null; Escape closes the guide panel); one was not a
change (the guides becoming public is the plan); three skipped (the design's two extra
decision chips, nested input fields, a copy timer not cleared on unmount). After the
fixes: frontend lint and types, and the MCP server tests (53), pass; the whole `make
check` was not run again.

**For Dmytro on screen** (signed out, with `make mcp` running and `MCP_URL` set):

- `/mcp-docs`: the header says 30 tools and 9 guides, the server URL and the Claude Code
  command copy; the five groups list every tool with its chip, and only
  `archive_issue`, `unarchive_issue` and `answer_clarifications` say "Your decision";
  `move_task` says "Only when you ask."
- Expand a tool: its inputs with type, required and description, and its guide; the
  guide opens in the side panel and Escape closes it.
- With the MCP server stopped: the page says the contract could not be read.
- Dark and light.

### Not done

- **`MCP_URL` is not set in the deployed web app.** Until it is, the live `/mcp-docs`
  says the contract could not be read. Set it to the MCP server's public base URL.
- **The design's two extra "Your decision" chips** are for the design session.
- **Nested input fields** are not described on the page.
- **Not checked on screen** (Dmytro checks screens).
