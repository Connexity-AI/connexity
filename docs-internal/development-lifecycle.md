# Development lifecycle

How Connexity is built: one human (Dmytro) deciding and approving, Claude Code sessions
doing the engineering. This document is for both.

The rules below come from the same evidence as the product itself (see
[`Connexity 2.0.md`](../Connexity%202.0.md), section 2). Connexity exists because an
assistant that grades its own work, against a stale spec, on an unknown version,
produces confident wrong answers. We do not build the product that way either.

---

## 1. Four documents, four jobs

| Document | Answers | Changes when |
|---|---|---|
| [`Connexity 2.0.md`](../Connexity%202.0.md) | Why, and what the product is | Dmytro changes his mind |
| [`REBUILD.md`](../REBUILD.md) | What order, what is done, what was decided | A slice starts or finishes |
| [`plans/`](../plans/README.md) | What one pull request set out to do and what it did | Once per pull request |
| `CLAUDE.md` (root, `backend/`, `frontend/`) | How to work in this repo | A convention changes |

A session reads `REBUILD.md` first, then only the vision sections its slice cites.
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

1. **Orient.** Read `REBUILD.md` status and the slice. Read the vision sections it
   cites. Check `git status` and the branch.
2. **Plan.** Write the plan file (`plans/`, from the template) before any code: goal,
   changes, decisions, done-when, out of scope, risks. The owner approves it. A design
   slice (schema, API shape) settles its open questions with the owner here.
3. **Build.** Stay inside the plan. Anything discovered outside it becomes a note in
   `REBUILD.md` or a spawned task, not an extra change. If the plan turns out to be
   wrong, stop and say so; do not quietly build something else.
4. **Verify.** Run `make check`. Exercise the change for real where possible: hit the
   endpoint, load the screen, run the check against a real trace.
5. **Record the outcome.** Fill in the plan's Outcome: deviations from the plan, check
   results, what was not done. Update the status table and decision log in
   `REBUILD.md`.
6. **Open the pull request.** It carries the plan and the work together, never the plan
   alone. Opening it is the owner taking responsibility for both.
7. **Review.** Reviewers read the plan. If the review changes the plan, the work is
   redone to match.

A session that cannot finish its slice leaves the plan's Outcome saying exactly where
it stopped and why.

---

## 4. Decisions and provenance

In case study 1, the assistant once recorded a client as agreeing to a design he
had only restated a concern about. The same failure is possible here.

- Every design statement is one of **Decided** (Dmytro said so, in his words),
  **Proposed** (Claude's suggestion, not yet confirmed), or **Open**.
- Claude never promotes Proposed to Decided. Silence, "ok", or moving on to the next
  topic is not a decision about the previous one.
- A decision goes in the `REBUILD.md` decision log with its date. If it changes the
  product, the vision is updated too.
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
| Tests cannot reach a hosted database | `backend/conftest.py` |

### Test against reality

- Tests for ingestion and checks are built from real traces, with a failing and a
  passing example each. Hand-written "plausible" fixtures hide the cases that matter.
- Real client data never enters the public repo. See `REBUILD.md` Q5.
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
- **No builder features.** If a change adds an editor for the agent's prompts or
  workflows, AI that generates content inside the product, anything that talks back, or
  brings back something the rebuild removed, it contradicts the vision. Stop and ask.
  Forms for what Connexity itself holds are fine: the UI may do anything the API does.
- **The feature test** (vision section 16): does this describe an agent's conversation
  or something that conversation touched? If not, it does not belong.
- **Read-only toward providers.** The product ingests and compares. It does not deploy,
  roll back or write to Retell, n8n or the CRM.

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
