# Write down how checks, issues and incidents work

- **Owner:** Dmytro
- **Slice:** 2.0 (design; documents only)

## Goal

Phase 2 was about to be built on a two-line idea of a "check" and an inbox. Dmytro paused
development to design it properly first. This pull request writes the agreed design into
the documents every later session reads, so that Phase 2 is built from it and not from a
conversation that will be gone.

No code changes.

## Changes

**The vision (`Connexity 2.0.md`)**

- Section 7: "Three tiers" is replaced by the model for real calls: check, fact,
  finding, issue, incident, metric and decision record; the three kinds of check; the
  per-agent setting (off, flags, fails the call); failed, degraded and clean calls;
  reliability and quality; how an issue is identified; how an incident opens and closes
  and what it holds; the starting issue types; who makes checks. What Dmytro decided is
  marked Decided; what he has not confirmed is listed as Proposed; what is unresolved is
  listed as Open.
- Section 7, "Who creates and who verifies": the line on judges now matches (a judge
  starts as "flags", and the user decides when it may fail a call).
- Section 12: an incident is redefined as a record of a period, pointing to section 7.
  The severity table is withdrawn, with the reason.
- Section 15: the Overview screen is reliability and quality per version, not "outcomes
  in business terms".
- Section 16: business analytics is added to what the product is not.

**The roadmap (`REBUILD.md`)**

- Phase 2 is rewritten as: 2.0 design (this), 2.1 check engine, 2.2 first rule checks
  and facts, 2.3 issues, incidents and reliability, 2.4 findings, issues and incidents
  on screen.
- The inbox (was 2.4), tests against issues, and alerting are listed as postponed, each
  to its own design.
- The status table, the next step, the open questions and the decision log are updated.
  Q6 (who may write checks) is closed. Two questions are added: Q9 (always-present
  measures such as latency) and Q10 (the Milestone 1 exit criteria).
- The Milestone 1 exit review is marked as needing a revisit. It is not rewritten.

## Decisions

Made by Dmytro in conversation on 2026-10-10. Each is in the decision log with his words
where he gave them:

- An incident is its own record, not a type of issue; one issue can have many.
- Every failed call belongs to an incident; issues that only flag never become one.
- The user controls what fails a call; every such decision is audited, takes effect when
  made, and needs a reason when it improves the number.
- Business outcomes are not this product.
- Tests, the inbox, alerting, shifts and team assignment are postponed.

Proposed by Claude and agreed by Dmytro: identity by symptom; every finding from a named
check; one "check" concept with three kinds and a facts layer; judges answer pass or
fail; off, flags, fails the call; failed, degraded, clean; the closing rule and the
reliability denominator; metrics as numbers only; the answer to Q6.

Proposed by Claude and **not** confirmed, written into the vision as Proposed:

- Titles built from a template, following Type, then Title, then Description.
- The exact meaning of "resolved in a version" and when a recurrence is a regression.
- Merging and splitting issues by hand, later.
- The detailed contents of an incident record. Dmytro named its three jobs (response,
  remediation, post-mortem); the list of fields under each is Claude's.

## Done when

- The vision states the model, and nothing in it still describes the old one (three
  tiers, incident as a severity, business outcomes on the Overview screen).
- Each statement in the new text is marked Decided, Proposed or Open, and nothing Dmytro
  did not decide is marked Decided.
- The roadmap's Phase 2 matches the model and no longer contains the inbox slice.
- The decision log has an entry for each decision above.
- `make check` passes.

## Out of scope

- Any code.
- The design of tests, the inbox and alerting.
- Where a person sees findings, issues and incidents (slice 2.4 designs it).
- Trying the checks on real calls (the first step of Phase 2).
- Rewriting the Milestone 1 exit criteria.

## Risks

- **The design has not met real calls.** The type list and its defaults were agreed in
  conversation. The first step of Phase 2 runs them on stored calls and may change them.
- **One problem is knowingly unsolved**: measures that are always slightly present, such
  as latency (Q9). The slow-response check cannot fail calls sensibly until it is.
- **The vision now has a long section 7.** It was a short list; it is now the densest
  part of the document.
- **Sections 11 and 12 still mention severities** in their Proposed parts (containment,
  onboarding, dispatch per severity). Those belong to alerting and the inbox and were
  left for their own designs.
- **A reviewer should push back if** anything marked Decided was not decided, or if the
  starting type list is wrong for the agents actually connected.

## Outcome

### Deviations from the plan

- **The starting type list was split after the pull request was opened.** The candidate
  checks were tried on stored real calls the same day. Dmytro then decided that checks
  depending on what the agent was instructed to do wait for the spec. The vision's list
  is now two groups, and the roadmap's slice 2.2 records what the run showed. Which
  group three of the types belong in is Claude's split and is marked as unconfirmed.

### Check results

`make check` on this branch. No code changed, so the code steps confirm only that
nothing was disturbed.

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 1s |
| Backend lint and format | ok | 1s |
| Backend types (pyright) | ok | 9s |
| Backend tests and coverage | ok | 77s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 1s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 9s |

Against the done-when:

| Done when | Result |
|---|---|
| The vision states the model and nothing describes the old one | Yes for sections 7, 12, 15 and 16. Sections 11 and 12 still use "severity" in Proposed parts that belong to alerting and the inbox; left on purpose |
| Each statement marked Decided, Proposed or Open | Yes |
| Phase 2 matches the model, without the inbox slice | Yes |
| A decision-log entry for each decision | Yes, 15 entries dated 2026-10-10 |
| `make check` passes | Yes, every step |

`/code-review` was not run: no code changed.

### Not done

- The Milestone 1 exit criteria are flagged, not rewritten (Q10).
- The Proposed items in section 7 are not confirmed.
- `frontend/CLAUDE.md` and the lifecycle guide were not changed; nothing in them
  contradicts the model.
