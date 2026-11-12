# Docs catch up with the 2026-11-11 and 2026-11-12 design decisions

- **Owner:** Dmytro
- **Slice:** none (documents only; prepares the repo for the new roadmap)
- **Design:** No UI change. The design prompts written for Claude Design are committed
  under `designs/` as reference; the screens themselves are designed in Claude Design.
- **MCP:** None needed: documents only. The MCP rule is restated more precisely (see
  Changes).

## Goal

Execution sessions can start on the new roadmap without being misled by the repo.

Today the repo contradicts what Dmytro decided over the last two days:

- `CLAUDE.md` rule 1 sends every session to "a slice from `REBUILD.md`", and
  `REBUILD.md` says the roadmap is paused with no next slice. The order of work now
  lives in Dmytro's feature roadmap, outside the repo.
- The design docs still describe the old model (incidents tied to one issue,
  "regressed", "accepted", calls pulled only on request, a spec created on connection
  with no versions, tool calls kept off the call screen).
- The design prompts that roadmap entries point to sit in an untracked `designs/`
  folder, invisible to sessions that work in their own worktree.

After this merges, a session that reads `CLAUDE.md`, `REBUILD.md` and `docs-internal/`
plans from the current decisions, and finds the design prompts in the repo.

## Changes

Documents only.

- **`designs/` committed.** The twelve numbered Claude Design prompts and
  `who-does-what.md` (who does what between Connexity, the assistant and the person).
  They hold placeholder names only, no call data. A short `designs/README.md` says what
  the folder is: prompts for Claude Design and the responsibility table, not code specs;
  where a prompt and a design doc disagree, the design doc wins and the prompt is
  history.
- **`CLAUDE.md`:**
  - Rule 1 becomes: one session, one feature from the roadmap Dmytro names; do not
    widen it.
  - The "Read first" table says the order of work is Dmytro's feature roadmap, kept
    outside the repo; `REBUILD.md` keeps status, decisions and open questions.
  - Two new rules: nothing appears in the UI that does not work end to end and is
    tested; every feature extends MCP with few, workflow-shaped tools scoped to a
    workspace the user can access.
- **`REBUILD.md`:**
  - Section 2: "Roadmap paused" replaced by a pointer to the feature roadmap (no link;
    the repo is public), with the milestone names in one line each (Proposed).
  - Decision log: one row per decision below, quoting Dmytro.
- **`docs-internal/checks-and-incidents.md`:** incidents group issues across agents by
  issue type and key; "regressed" becomes "reopened"; "accepted as known" becomes
  "archived", which stops counting from that day and is always recorded; issue
  severity is Critical (fails the call) or Warning (flags it); a person or the
  assistant corrects grouping later (merge and split are not built yet).
- **`docs-internal/` new doc, `responsibilities.md`:** the default rule (the assistant
  does what it can, guided by Connexity; Connexity watches and verifies; a person
  approves) and its exceptions, pointing to `designs/who-does-what.md` for the full
  table. (Proposed: or fold this into the lifecycle guide instead.)
- **Lifecycle guide:** section 3 follows the new rule 1 (one feature from the roadmap);
  section 6 gets the "nothing on screen that does not work" rule, the new sidebar, and
  tool calls on the single call.
- **`docs-internal/data-model.md`:** the `issue` row notes that "regressed" and
  "accepted" are the code's names until the fix-loop feature renames them.
- **`frontend/CLAUDE.md`:** the sidebar is Home, Incidents, Action items, Agents, Calls,
  Roadmap, Issues, Settings; calls can be browsed and searched (search by phone number
  or call ID, plus agent, result, category, period and source filters); the single call
  shows tool calls inline; the workspace picker lives in the profile menu; no
  white-labelling.

Decisions to record (all Dmytro's words, 2026-11-11 and 2026-11-12):

| Area | Decision |
|---|---|
| Testing | Strict chain: production issues, then spec, then test cases, then tests. Three test levels (text, audio, phone), built one at a time. The gate is customizable; only a person overrides a failed gate. |
| Responsibilities | Whatever the assistant can do is its job by default; verification and watching calls stay with Connexity. |
| Spec | The assistant writes the spec as a Readiness step, not on connection. Specs are versioned. A new agent version adopts the previous spec and raises clarifications for what changed. Spec drift (an internal term) means behaviour the spec does not cover or goes against. |
| Clarifications | Answered in the app or by the assistant, which confirms a batch with the person first. No criticality for now. |
| Calls | Calls sync continuously (replaces "no scheduler, pull on request"). Calls can be browsed and searched in the app and through MCP. Tool calls show on the single call. |
| Issues | One symptom on one agent, with occurrences. Reopened, Archived (stops counting, recorded). |
| Incidents | One outage, grouped across agents by issue type and key; closing an incident (damage stopped) is separate from resolving an issue (cause fixed); only a person closes it, the assistant may propose. Alerts go to Slack and are kept in the app for MCP. |
| Offline approval | An allow list predefined by Connexity, incidents only to start (the Playbook, built later). |
| Readiness | A second number besides the score, loud only while below 100%; onboarding is its first part. |
| Workspaces | One workspace per client under a thin agency account for billing and members; MCP connections are per user and reach that user's workspaces. |
| Billing | Free (limited) and Paid with credits top-ups; when credits run out, recording, checks and alerts keep running. |
| Categories | One fixed, Connexity-wide set, kept in a database table. |

## Decisions

- Put the roadmap's order outside the repo and point to it without a link (Dmytro: the
  roadmap lives in Notion; the repo is public).
- Commit `designs/` as reference (Proposed by Claude, because worktree sessions cannot
  see untracked files).
- List milestone names in `REBUILD.md` (Proposed; drop if Dmytro prefers the roadmap to
  stay fully private).
- The decision log keeps superseded rows and marks them, as it does today.

## Done when

- `make check` passes.
- `CLAUDE.md` rule 1 no longer mentions a slice from `REBUILD.md`.
- Searching `docs-internal/` and `CLAUDE.md` files for "regressed", "accepted as known"
  and "pull on request" finds them only in superseded or historical lines.
- `designs/` is tracked and every design prompt named in a roadmap entry exists in it.
- No file in the diff names a client or contains call data.

## Out of scope

- Any code, migration or MCP tool. The roadmap's first feature starts in its own
  session.
- Rewriting the parked ideas in `REBUILD.md` section 7; they stay as history.
- The 1.x docs (`README.md`, `CLI_README.md`, `docs/`).

## Risks

- `designs/` prompts contain decisions that were later changed inside the same prompt
  series (for example prompt 03 says the spec is created on connection). The README
  must say which wins, or a session may follow an old prompt.
- Listing milestones in a public repo shows the plan to anyone; Dmytro may prefer not.

## Outcome

### Deviations from the plan

- The lifecycle guide and `docs-internal/data-model.md` were also changed, so rule 1's
  long form and the issue table match; both are now listed under Changes.
- `REBUILD.md`'s header line "This file: the roadmap" now says the file holds status,
  decisions and open questions.
- `checks-and-incidents.md` now says the 2026-11-12 decisions are ahead of the code
  until their features are built, and covers alerts (its intro used to exclude them).
- `frontend/CLAUDE.md`'s "no forms" rule now allows controls for decisions only a
  person confirms (check and gate settings, archiving, closing an incident), so it does
  not forbid the designed Settings screens.
- The plan said thirteen prompts; there are twelve.

### Check results

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

`/code-review` (high) found seven issues in the docs (a stale claim that the code
implements the whole model, an intro excluding alerts, the "no settings forms" rule,
the prompt count, two edited files missing from the plan, decision-log order, a leftover
"slice"); all seven are fixed.

Searching `CLAUDE.md`, `frontend/CLAUDE.md`, `backend/CLAUDE.md` and `docs-internal/`
for "regressed", "accepted as known", "pull on request" and "slice from `REBUILD.md`"
finds them only where a line says what they were replaced by. No file names a client
or holds call data; the prompts use placeholder agents and people.

### Not done

- `REBUILD.md` section 7 ("Parked ideas") still describes older plans, for example the
  single call without tool calls; it is marked as history, not a plan.
- The milestone list in `REBUILD.md` is Proposed; drop it if the roadmap should stay
  fully private.
