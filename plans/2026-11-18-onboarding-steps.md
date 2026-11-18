# Onboarding steps in one list

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Onboarding steps in one list" (10.18).
- **Design:** `Connexity MCP Docs.dc.html` from the design review delivered 2026-11-18
  (zip 14): the Onboarding section, the answer-shape section removed, the new intro
  line. Work and Readiness look the same as today.
- **MCP:** `get_next_task` gives each onboarding step its own instructions from the
  list, and `get_readiness`'s steps come from it. No new tool. The contract page gains
  the section; no tool's entry changes.

## Goal

The order of onboarding, and everything about each step, lives in one ordered list in
code. Reordering is a one-line change, and Readiness, Work, the assistant's
instructions and the public `/mcp-docs` page all follow it. Dmytro can see the current
order on `/mcp-docs` while he experiments.

## Decisions

- **Accept, build** (Dmytro, 2026-11-18).
- **One ordered list in code** with each step's key, title, who acts (person or
  assistant), when it counts as done, and its instructions; reordering is a one-line
  change (Dmytro, 2026-11-18).
- **Shown as an Onboarding section on the public `/mcp-docs` page, read from the same
  list so it never drifts. No Notion copy** (Dmytro, 2026-11-18).
- **Not in scope:** new steps for the dashboard flow (Dmytro, 2026-11-18).
- **Two small changes to `/mcp-docs` in this PR** (Dmytro, 2026-11-18): remove the
  "Every tool answers the same way." section ("its bs"), and change the intro line to
  "Connexity gives a workspace for your assistant to manage your voice agents".
- **The `/mcp-docs` section is designed first** (Dmytro, 2026-11-18, question 1: "Design
  first"). The design arrived the same day, so the section is built in this PR.

## What exists

The order is spread over four places:

- **Readiness** (`crud/readiness.py`): four steps in a fixed list (assistant, voice
  platform, sync, first scan), each with its name ("Assistant connected") and how its
  state is worked out.
- **Work** (`services/work.py`): each step's task title ("Connect your AI assistant")
  in a separate dict; who acts (only the assistant step is the person's); the specs
  step ("Write the spec for each agent") added by hand before the first scan; each
  open step blocking the next.
- **`get_next_task`** (`routes/mcp.py`): one generic instruction for every onboarding
  step ("call `get_readiness` and do its first next step").
- **`get_readiness`** (`routes/mcp.py`): the real per-step instructions, written inline.

## Changes

### The list

- **`app/services/onboarding.py`, `ONBOARDING_STEPS`,** in order: assistant, voice
  platform, sync, first scan, specs. Each step:
  - `key`;
  - `title`, the Work task's title;
  - `readiness_name`, its name on Readiness (none for specs, which Readiness does not
    show);
  - `who`: person or assistant;
  - `done_when`: one plain sentence ("A member holds a working assistant connection.");
  - `instructions`: the numbered steps the assistant gets for it.
- **How each state is worked out stays code** (it reads the database), one function per
  key, next to the list; a test fails when a step has no state function or a state
  function no step.

### Everything follows it

- **Readiness** builds its steps in the list's order, with their names from it.
- **Work** takes titles, who acts and the order from it; each open step still blocks
  the next. The specs step is in the list ("until the first scan is done; then each
  agent's own spec task takes its place"), no longer added by hand.
- **`get_next_task`** answers an onboarding task with that step's own instructions,
  in place of the generic one.
- **`get_readiness`** answers its next steps from the list. Steps whose instruction
  depends on the state (sync: add agents first, or scan the added ones) keep that choice
  in code, with both texts in the list.

### On `/mcp-docs`

- **A public backend route, `GET /api/v1/onboarding/steps`** (no login, no workspace
  data): the list in order, with key, title, who acts, when it is done and the
  instructions.
- **The Onboarding section** on `/mcp-docs`, as designed, after the "What a tool may do"
  legend: "Onboarding", "The steps a new workspace goes through, in order. Your
  assistant does them with you.", then one row per step: its number, title, a chip
  ("You" or "Your assistant"), the done line, and on expand "Instructions for your
  assistant" as a numbered list. Tool names in instructions are written `like_this`
  and shown as code; a guide is written `[[spec]]` and opens in the page's guide panel.
  Read from the route when the page renders; if it cannot be read, the section is left
  out and the server log says why.

### `/mcp-docs` tweaks

- **"Every tool answers the same way." is removed** from the page, and the answer
  shape from the manifest (`answer_shape`), which only that section used.
- **The intro line** under "What your assistant can do in Connexity" becomes
  "Connexity gives a workspace for your assistant to manage your voice agents".
- **The design file** is replaced by the delivered one, which already has both changes.

### Docs

- `docs-internal/work.md`: onboarding's order lives in `ONBOARDING_STEPS`.
- `mcp_server/.../guides/readiness.md`: unchanged steps, now in the list's words.

## Done when

- Swapping two steps in `ONBOARDING_STEPS` (in a test) swaps them on Readiness, on Work,
  in `get_next_task`'s order and in `GET /api/v1/onboarding/steps`.
- `get_next_task` on each onboarding step answers that step's instructions.
- Readiness, Work and `get_readiness` answer what they answer today for the same
  workspace (the existing tests pass unchanged).
- `GET /api/v1/onboarding/steps` answers without a login.
- `make check` passes.
- **For Dmytro on screen:** Work and the Readiness ring look as before; `/mcp-docs` has
  the new intro line, no answer-shape section, and the Onboarding section with the five
  steps in order, one expanded, a guide link opening the panel, dark and light, narrow.

## Out of scope

- New onboarding steps (the dashboard flow's come with that feature).
- Changing the current order or wording, beyond moving it into the list.

## Risks

- **Moving text can change it by accident.** The existing Readiness, Work and MCP tests
  pin today's wording and order, and must pass unchanged.

## Questions

None left: the design question was answered (see Decisions).

## Outcome

### Deviations from the plan

- **Instructions are written once for both readers:** `like_this` for a tool, `[[spec]]`
  for a guide (`connexity://guides/spec` for the assistant, a link on the page), and
  `{scan_days}` and `{agents}` filled from the workspace for the assistant and with
  neutral words on the page. `get_readiness`'s texts are unchanged word for word.
- **`get_next_task`** gives an onboarding task all its step's instructions, then "Call
  `get_readiness` to see where setup stands and do its next step". For the sync step
  that is both "add the agents" and "scan their calls"; `get_readiness` picks the one
  that applies (review finding, left as is).
- **The page reads the steps with zod,** as it reads the manifest, and leaves the
  section out when they cannot be read, logging why.
- **The first step's instruction** on the page is "Add Connexity's MCP server to your
  assistant, then sign in." (the design's sample said "(the Server URL above)"; the list
  is read by the assistant too, where "above" means nothing).
- **`answer_shape` is gone from the manifest** as well as the page; nothing else used it.

### Check results

`make check`, before this Outcome was written:

| Step | Result |
|---|---|
| Plan present and complete | failed: Outcome empty; filled now |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok (new: `test_onboarding_steps.py`, 5; the Readiness, Work and next-task tests pass unchanged, 34) |
| MCP server tests | ok (53) |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

The frontend build passes (`ƒ /mcp-docs`); while building it logged "could not read the
MCP manifest: MCP_URL is not set" and "could not read the onboarding steps: 404" (no
local services during the build), so the logging works.

**`/code-review` (high), 2 findings:** fixed one (the steps are now checked with zod);
skipped one (the sync step's two instructions, above). After the fix: frontend lint
and types pass; the whole `make check` was not run again.

**For Dmytro on screen** (with `make dev` and `make mcp` running):

- `/mcp-docs`: the intro reads "Connexity gives a workspace for your assistant to manage
  your voice agents"; no "Every tool answers the same way." section; the Onboarding
  section after "What a tool may do": five steps in order, "You" on the first, "Your
  assistant" on the rest, each with its done line; expand one: "Instructions for your
  assistant", tools as code, `connexity://guides/spec` on step 5 opening the guide panel.
- Dark and light; a narrow window (done line under the title, chip below).
- Work's onboarding rows and the Readiness ring look as before.

### Not done

- **Production:** the web app reads the steps from `API_URL`, already set on
  `connexity-ui`; nothing to set.
- Not checked on screen (Dmytro checks screens).
