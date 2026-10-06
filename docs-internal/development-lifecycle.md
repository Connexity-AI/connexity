# Development lifecycle

How Connexity is built: one human (Dmytro) deciding and approving, Claude Code sessions
doing the engineering. This document is for both.

The rules below come from the same evidence as the product itself (see
[`Connexity 2.0.md`](../Connexity%202.0.md), section 2). Connexity exists because an
assistant that grades its own work, against a stale spec, on an unknown version,
produces confident wrong answers. We do not build the product that way either.

---

## 1. Three documents, three jobs

| Document | Answers | Changes when |
|---|---|---|
| [`Connexity 2.0.md`](../Connexity%202.0.md) | Why, and what the product is | Dmytro changes his mind |
| [`REBUILD.md`](../REBUILD.md) | What order, what is done, what was decided | Every session |
| `CLAUDE.md` (root, `backend/`, `frontend/`) | How to work in this repo | A convention changes |

A session reads `REBUILD.md` first, then only the vision sections its slice cites.
Nothing is restated across the three; they link to each other.

---

## 2. Roles

| | Does | Does not |
|---|---|---|
| **Dmytro** | Decides scope and product behaviour. Approves plans before code and diffs before merge. Answers open questions. | Read every line to find bugs. Remember what the last session did. |
| **Building session** | Investigates, plans, writes code and tests, runs the checks, opens the PR. | Approve its own work. Record a decision Dmytro did not make. Widen its slice. |
| **Reviewing session** | Reviews the diff in a fresh context against the slice's done-when. | Fix what it finds without reporting it. |
| **The machine** (CI, hooks, type checker, tests) | Enforces everything that can be enforced mechanically. | Get overridden to make a change pass. |

---

## 3. The slice loop

One session, one slice from `REBUILD.md`. A slice is small enough to review in one
sitting and ends in a merged PR.

1. **Orient.** Read `REBUILD.md` status and the slice. Read the vision sections it
   cites. Check `git status` and the branch.
2. **Plan.** For anything beyond a mechanical change, state the approach and the
   done-when before writing code. Design slices (schema, API shape) produce a short
   written design that Dmytro approves first.
3. **Build.** Stay inside the slice. Anything discovered outside it becomes a note in
   `REBUILD.md` or a spawned task, not an extra change.
4. **Verify.** Run the checks (section 5). Exercise the change for real where possible:
   hit the endpoint, load the screen, run the check against a real trace.
5. **Review.** Run `/code-review` in a fresh context before asking Dmytro to look.
6. **Record.** Update the status table, the session log, and the decision log in
   `REBUILD.md`. Then commit and open the PR.

A session that cannot finish its slice leaves the status line saying exactly where it
stopped and why.

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

- Done-when criteria are written in the plan before the code exists.
- "Tests pass" is reported with the command and its output, not as a claim.
- A change that loosens, deletes or skips a test, a type check, a lint rule or a CI
  step says so at the top of the PR description, with the reason. It is never bundled
  silently into a fix.
- Review happens in a different context from the build.

### Deterministic before judged

Prefer, in this order: a type or database constraint, a unit test, an integration test
against real Postgres, a manual run. Model-based evaluation of our own code is a last
resort.

### Enforce in code, not in instructions

In case study 1, a prompt rule about money did not hold and a code guard did. The
same applies to this repo. If a rule matters, it becomes a hook, a CI step, a type or a
constraint. `CLAUDE.md` is for what cannot be mechanised.

Current mechanical gates:

| Gate | Where |
|---|---|
| Ruff lint and format, Pyright | pre-commit, CI |
| Backend tests on real Postgres | CI |
| Frontend lint and type check | CI |
| Generated client is fresh | CI |

Planned in slice 0.4: one `make check` command, and a hook that blocks edits to the
generated client.

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
- **No builder features.** If a change adds an editor, a creation form or anything that
  talks back, it contradicts the vision. Stop and ask.
- **The feature test** (vision section 16): does this describe an agent's conversation
  or something that conversation touched? If not, it does not belong.
- **Read-only toward providers.** The product ingests and compares. It does not deploy,
  roll back or write to Retell, n8n or the CRM.

---

## 7. Git

- Branch from `main`, one slice per branch, PR back to `main`.
- Conventional commit messages. Use the `/commit` and `/create-pr` skills.
- No AI attribution anywhere: no co-author trailers, no "generated with" lines.
- Small PRs. Demolition is split so that each deletion is reviewable on its own.

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
