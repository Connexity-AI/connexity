# Development lifecycle

How Connexity is built: one human (Dmytro) deciding and approving, Claude Code sessions
doing the engineering. This document is for both.

The rules below come from the same evidence as the product itself: the first build with
Claude Code (case study 1, in Dmytro's private `Vision.md`). Connexity exists because an
assistant that grades its own work, against a stale spec, on an unknown version,
produces confident wrong answers. We do not build the product that way either.

---

## 1. The documents and their jobs

| Document | Answers | Changes when |
|---|---|---|
| `Vision.md` (Dmytro's, kept out of the repo) and the goal at the top of `CLAUDE.md` | Why, and what the product is for | Dmytro changes his mind |
| `docs-internal/` design docs, such as [`checks-and-incidents.md`](./checks-and-incidents.md) and [`data-model.md`](./data-model.md) | How a part of the product is designed | That part changes |
| [`REBUILD.md`](../REBUILD.md) | What order, what is done, what was decided | A slice starts or finishes |
| [`plans/`](../plans/README.md) | What one pull request set out to do and what it did | Once per pull request |
| `CLAUDE.md` (root, `backend/`, `frontend/`) | How to work in this repo | A convention changes |

A session reads `REBUILD.md` first, then only the design docs its slice cites.
Nothing is restated across them; they link to each other.

---

## 2. Roles

| | Does | Does not |
|---|---|---|
| **Owner** (whoever opens the pull request; today Dmytro) | Approves the plan before work starts. Answers for both the plan and its execution once the pull request is open. | Read the diff line by line. |
| **Reviewers** (the team) | Review the plan and its Outcome in the pull request. | Review code. Wait on a plan-only pull request; there are none. |
| **Building session** | Investigates, writes the plan, writes code and tests, runs the checks, records the Outcome, opens the pull request. | Approve its own plan. Record a decision the owner did not make. Widen its slice. |
| **Automated review** | Checks the code: tests, types, lint, coverage, drift, and a reviewer that compares the diff with the plan. | Get overridden to make a change pass. |

**People review plans; machines review code.** A wrong plan is expensive and only a
person can catch it. Wrong code under a right plan is cheap to regenerate, so it is
not worth a person's reading time.

The automated reviewer that compares a diff with its plan is not in place yet. Which
tool does it is an open decision (Dmytro wants one that is not the same model that
wrote the code). Until then, CI covers what tests and types can, and the building
session runs `/code-review` and reports its findings in the plan.

---

## 3. The slice loop

One session, one slice from `REBUILD.md`, one plan, one pull request.

1. **Orient.** Read `REBUILD.md` status and the slice. Read the design docs it
   cites. Check `git status` and the branch.
2. **Plan.** Write the plan file (`plans/`, from the template) before any code: goal,
   changes, decisions, done-when, out of scope, risks. The owner approves it. A design
   slice (schema, API shape) settles its open questions with the owner here. A slice
   that changes the UI updates the design first and links the approved version (see
   "UI: the design comes first" below).
3. **Build.** Stay inside the plan. Anything discovered outside it becomes a note in
   `REBUILD.md` or a spawned task, not an extra change. If the plan turns out to be
   wrong, stop and say so; do not quietly build something else.
4. **Verify.** Run `make check`. Then exercise the backend for real through its API
   (section 5, "Who tests what"). The session does not test screens; it lists what
   Dmytro should look at.
5. **Record the outcome.** Fill in the plan's Outcome: deviations from the plan, check
   results, what was not done. Update the status table and decision log in
   `REBUILD.md`.
6. **Open the pull request.** It carries the plan and the work together, never the plan
   alone. Opening it is the owner taking responsibility for both.
7. **Review.** Reviewers read the plan. If the review changes the plan, the work is
   redone to match.

A session that cannot finish its slice leaves the plan's Outcome saying exactly where
it stopped and why.

### UI: the design comes first, and stays current (Decided 2026-11-07)

Any change to what a person sees, whether Dmytro or the session suggests it, is made in
the design before it is made in code. This is a hard requirement.

- **The design lives in Claude** as Design artifacts, not on the standalone
  claude.ai/design site, which closes on 2026-12-14.
- **The design is split into files:** one per screen or component, plus shared files for
  colours, spacing and type. No single file grows too large to edit or upload.
- **The order is fixed:** the session updates the design, Dmytro reviews and approves it
  there, and only then does frontend code change. A slice that touches the UI names the
  design and the version Dmytro approved in its plan.
- **The design never falls behind the code.** If building shows that something has to be
  different from the approved design, the session stops, changes the design first, and
  gets it approved again before changing the code. Nothing reaches the screen that is not
  in the design.
- **The design system** is the Connexity Design System artifact in Claude: tokens, the
  brand book, the logo and the components, with live previews. It was created in its own
  session, led by Dmytro, before any screen design (2026-11-09). Every screen design is
  built on it; a screen that needs a piece the system lacks adds the piece to the system
  first. The design may be ahead of the code, never behind it.

---

## 4. Decisions and provenance

In case study 1, the assistant once recorded a client as agreeing to a design he
had only restated a concern about. The same failure is possible here.

- Every design statement is one of **Decided** (Dmytro said so, in his words),
  **Proposed** (Claude's suggestion, not yet confirmed), or **Open**.
- Claude never promotes Proposed to Decided. Silence, "ok", or moving on to the next
  topic is not a decision about the previous one.
- A decision goes in the `REBUILD.md` decision log with its date. If it changes the
  product, the design doc for that part is updated too.
- When a slice depends on an Open item, the session asks before building, with a
  recommendation.

---

## 5. Verification

### The assistant does not grade its own work

- Done-when criteria are written in the plan file before the code exists.
- "Tests pass" is reported with the command and its output, not as a claim.
- A change that loosens, deletes or skips a test, a type check, a lint rule or a CI
  step says so at the top of the PR description, with the reason. It is never bundled
  silently into a fix.
- A person reviews the plan, never the session's own account of the code. The code is
  judged by checks the session cannot edit its way around.

### Who tests what

**The session tests the backend through the API. Dmytro tests the frontend.**

Backend, every slice that changes a route or what a route returns:

- Start the server locally and call the changed endpoints over HTTP, as an API caller
  would: the main path, a refusal, and another company's attempt where it applies. The
  test suite does not count as this; it runs inside the process.
- Local database only. Before the first request, confirm the running server is on the
  local Postgres, not a hosted one.
- Work on a throwaway agent created for the run, so invented calls never mix with real
  ones. Log in with the local seed user from `.env`; the login answers with a token to
  send as a bearer. Remove the throwaway agent and its calls afterwards.
- Report it in the plan's Outcome as a table: request, expected, what came back. Status
  codes, counts and field names only; nothing from a real call.

Frontend:

- The session runs lint, types and the build, and does not open a browser, take
  screenshots or click through screens.
- The plan's Outcome ends with **"For Dmytro to check on screen"**: the pages to open and
  what should be true on each. Until he has, the Outcome says the screens were not looked
  at.

### Deterministic before judged

Prefer, in this order: a type or database constraint, a unit test, an integration test
against real Postgres, a manual run. Model-based evaluation of our own code is a last
resort.

### Enforce in code, not in instructions

In case study 1, a prompt rule about money did not hold and a code guard did. The
same applies to this repo. If a rule matters, it becomes a hook, a CI step, a type or a
constraint. `CLAUDE.md` is for what cannot be mechanised.

Current mechanical gates. `make check` runs all of the "make check" ones locally in
one command, with per-step timings; run it before every push.

| Gate | Where |
|---|---|
| Every pull request has one complete plan, and is not a plan alone | CI (`Plan` workflow), `make check`, hook on `gh pr create` |
| Ruff lint and format, Pyright | pre-commit, `make check`, CI |
| Backend tests on real Postgres, coverage floor of 90% | `make check`, CI |
| Models match migrations | test suite, CI (`alembic check`) |
| Enum columns follow the storage rule | test suite |
| MCP server tests | `make check`, CI |
| Frontend lint and type check | `make check`, CI |
| Generated client is fresh | `make check`, CI |
| Generated client cannot be hand-edited | hook in `.claude/settings.json` |
| A reminder to add a migration and regenerate the client after a model or route change | hook in `.claude/settings.json` (reminds, does not block) |
| Tests cannot reach a hosted database | `backend/conftest.py` |

### Test against reality

- Tests for ingestion and checks are built from real traces, with a failing and a
  passing example each. Hand-written "plausible" fixtures hide the cases that matter.
- The repo is public. Real call data, client names and secrets never enter it, not in
  code, tests, plans or pull requests. See `REBUILD.md` Q5.
- Milestones are judged on a reference agent's actual calls, not on synthetic ones.
- A reference agent is an example, not the product. Stack-specific logic stays in
  mapping and connector modules; see the overfitting rules in `REBUILD.md` section 1.

### Failure paths are part of the change

Twice in case study 1 a correct main-path fix broke the degraded path. Every
slice that touches an external call (provider API, n8n, CRM, model) includes tests for
timeout, empty response and malformed response.

---

## 6. Working in a codebase that is being rebuilt

- **Delete, do not deprecate.** No compatibility is owed. Dead code misleads every
  later session, so remove it with its tests, routes, generated client and docs in the
  same PR.
- **Frozen code stays frozen.** Areas marked Freeze in `REBUILD.md` keep compiling and
  passing tests, but get no new features until their phase.
- **Checks are a library that grows only when Dmytro asks.** Do not add, propose or plan
  a check he did not ask for by name, even one listed in a design doc or in `REBUILD.md`.
  Build the foundation the checks run on.
- **Everything ships with its MCP tools (Decided 2026-11-07).** Anything a person can
  do or see on the platform, a user's assistant (Claude, ChatGPT or similar) can do or
  see through MCP. A feature is not done until its MCP tools are: the slice that adds a
  route, a screen or a setting adds the tools for it in the same pull request, and the
  plan's "MCP" line names them. The reverse does not hold: the web app is not a second
  way to do everything (see "What the web app is for" below).
- **Read-only toward providers.** The product ingests and compares. It does not deploy,
  roll back or write to Retell, n8n or the CRM.


### What Connexity does not build

**No builder features.** If a change adds an editor for the agent's prompts or workflows,
AI inside the product that writes the agent's content (prompts, tests, fixes), anything
that talks back or acts like an agent, or brings back
something the rebuild removed, it contradicts the product. Stop and ask.

**What the web app is for (Decided 2026-11-09).** The assistant does all of the work.
Next to it, the web app's value is the quick glance: "the only value of the system vs ai
assistant is to have a quick glance of whats going on and thats what dashboards are
for" (Dmytro). Screens are dashboards: numbers that show their base (agents, calls,
period), findings and progress before anything that asks the person, a score for the
fleet and each agent, and a single call's recording and transcript as the deepest view.
The sidebar is Home, Agents, Roadmap, Issues and Settings. It is still not an
observability tool: no trace explorers, no drilling down from an incident to the moment.
This replaces the same morning's "reports and things to do". The rule that the UI may do
anything the API does (2026-10-09) is retired. Forms stay only where a person
has to act themselves, such as signing in and their own account (Proposed); connections,
agents and settings are the assistant's, through MCP.

**No chat in the product (Decided).** Nothing in the product talks back. Chat means the user's own assistant, and the user
should never be unsure about that.

Nothing the user types gets a reply. The places that matter most are:

- a comment on a moment in a call
- an answer to a decision question
- an edit to a spec rule

The few forms the web app keeps are forms, not conversation.

The product's own use of models (triage, judges, classifiers) is background work. Its
output is always an artifact: a metric, an insight, an issue, a verification result, a
spec entry. Connexity uses AI, but never as an agent (Decided 2026-11-07).

**Skills and the CRM are always attached to an agent (Decided).** The agent is central. A workflow or a CRM record exists in the product only as
something an agent used. It is not possible to test a workflow or browse the CRM
without an agent.

This is a rule about the entry point, not about depth. Technical depth is wanted: a
voice engineer must be able to recognise an issue instantly.

**Path:** agent → call → tool call → n8n execution → node-by-node detail. That depth
lives in the record and is reached through MCP; the screens stop at a single call
(Decided 2026-11-09).

In scope:

- Full execution detail for every tool call, attached to the call that triggered it.
- Skill tests that belong to an agent and run against its spec rules.
- Per-call CRM data: what came in, what was written back, and the later outcome.
- Versions of every skill the agent uses, as part of its verified state.

Out of scope:

- A list of all workflows in an account.
- Running or testing a workflow no agent uses.
- Browsing CRM records unrelated to a call.
- General observability for n8n. Connexity is not Langfuse.

A workflow shared by several agents appears under each one. A change to it re-verifies
every agent attached.

**What Connexity is not:**

- A chat assistant.
- A workflow builder, a CRM, or a proxy to them.
- General observability for n8n or any backend.
- A deploy pipeline. The assistant deploys.
- A simulator that replaces the agent's own engine.
- A product for teams that deploy manually.
- Business analytics. Conversion, revenue and return on investment belong to a
  company's own tools.

Test for any future feature: does it describe an agent's conversation, or something
that conversation touched? If yes, it can belong. If it describes another system on its
own, it belongs to the assistant and that system's tools.

---

## 7. Git

- Branch from `main`, one slice per branch, PR back to `main`.
- Conventional commit messages. Use the `/commit` and `/create-pr` skills.
- No AI attribution anywhere: no co-author trailers, no "generated with" lines.
- Small pull requests: one slice, one plan.

---

## 8. Keeping the context healthy

Context is the only thing a new session knows. Treat it as code.

- Root `CLAUDE.md` holds product context, the doc map and rules that apply everywhere.
  Language conventions live in `backend/CLAUDE.md` and `frontend/CLAUDE.md`, which load
  only when a session works in those directories.
- A convention goes in `CLAUDE.md` only if a session would otherwise get it wrong. If
  the code already shows it, leave it out.
- When a session is corrected on something that will recur, the correction goes into
  `CLAUDE.md` or a skill in the same session.
- Repeated multi-step workflows become skills in `.claude/skills/`.
- `.claude/settings.json` is tracked and applies to every session. Personal settings go
  in `.claude/settings.local.json`, which git ignores.
- Docs that describe removed behaviour are deleted in the PR that removes it.
- After each milestone: reread `CLAUDE.md`, this document and the skills, and remove
  what is no longer true.

---

## 9. When to stop and ask

- The slice needs an Open question answered.
- Something outside the Delete table looks like it should be deleted.
- A check can only pass by weakening a test or a rule.
- The change would send data to, or write to, an external system.
- The vision and the plan disagree.

---

## 10. How a session talks to Dmytro

- **Every reply ends with "Next step from you:"** and the one thing Dmytro has to do next:
  answer a numbered question, approve, test something, merge. If nothing is needed from
  him, say so and say what happens next.
- Show the picture first, then the questions: a draft or a recommendation, followed by a
  short numbered list of what he needs to decide.
