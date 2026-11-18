# Onboarding ends with a complete dashboard

- **Owner:** Dmytro
- **Slice:** Roadmap 10.192, Onboarding ends with a complete dashboard
- **Design:** No UI change. The Dashboard's onboarding strip (10.191, PR #233) keeps its
  look and now reads the same finish line as everything else.
- **MCP:** `answer_clarifications` gets a new input, `proposed`, on each answer. Its
  answer, and those of `get_next_task`, `get_readiness` and `list_clarifications`, carry
  the new onboarding step and the "Your dashboard is ready" next step. The `/mcp-docs`
  entries and input descriptions are updated, and its Onboarding section follows the
  list automatically.

## Goal

Today onboarding has no finish. Readiness ends at the first scan, the Dashboard's strip
works out its own "complete", and the score uses Readiness's. Clarifications sit with
"other" work, and the assistant asks them whenever it gets to them.

After this change, onboarding ends when the Dashboard is complete (Dmytro, 2026-11-18):

1. Scan, then specs.
2. The assistant raises the clarifications, proposes answers to the ones it can, and asks
   the person once. The person confirms the proposed answers as one batch and answers
   the rest.
3. When the last answer is in, the assistant tells the person "Your dashboard is ready"
   with the link.

The strip, the score, Work and `get_next_task` all read one finish line.

## Changes

**Onboarding list (`ONBOARDING_STEPS`)**

- **New step after the specs: "Answer the open questions"** (key `answers`). It is the
  assistant's step, and the person confirms. The instruction says to:
  - raise what the specs leave open;
  - propose an answer where the assistant can, saying why;
  - put every question to the person in one message: the proposed answers to confirm
    as a batch, and the rest to answer;
  - then call `answer_clarifications` once.
- Done when no question is open: every question is answered or parked.
- It shows on Work and in `get_next_task` like the other onboarding steps, and on
  `/mcp-docs`. It is not a Readiness step, so Readiness keeps its four.

**One finish line, kept once reached**

- **A workspace's onboarding is complete when every condition holds:**
  - every Readiness step is done;
  - no agent waits for a spec;
  - no question is open.
- **The moment it is first true, it is stored** (`company.onboarding_completed_at`, like
  `first_scan_done_at`). It never goes back: a question raised next month does not hide
  the score or bring the strip back.
- **What reads it:**
  - the score's gate (`onboarding_complete`), today Readiness only;
  - the Dashboard's strip, today its own scan, spec and answers;
  - Work and `get_next_task`.
- **While onboarding runs,** each agent's open questions are Setup tasks, right after the
  spec tasks. They are no longer "other" work below the issues. After it, they go back to
  where they are today.

**Proposed answers, confirmed by the person**

- **New input:** each answer to `answer_clarifications` can carry `proposed: true`. It
  means the assistant proposed this answer and the person confirmed it.
- **It is stored on the clarification and on its decision record.** The answer stays
  recorded as the person's, with the assistant that acted, as today. The 2026-11-12
  rule that the person confirms every answer stands.
- **The rules gain one line:** propose only where the spec, the prompt or the calls
  support the answer; never send a proposed answer the person has not confirmed.

**"Your dashboard is ready"**

- When an `answer_clarifications` call completes onboarding, its first next step tells
  the assistant to say "Your dashboard is ready" with the link
  (`<site>/dashboard`). It names the score and the failed calls, so the message gives
  before it asks.
- After that, `get_next_task` moves on to the usual work.

## Decisions

- **Decided by Dmytro (roadmap row, 2026-11-18):**
  - Onboarding's finish line is a complete Dashboard.
  - "Confirm in batch".
  - The person confirms every answer.
  - New steps go into the single list.
- **Proposed: proposals live in the chat, not in Connexity.** Only the confirmed answer
  is stored, marked `proposed`. Raising stays as it is, with no "suggested answer" field
  a person could mistake for a decision.
- **Proposed: a parked question counts as settled** for the finish line. Parking means
  "not important now"; the strip already counts it that way.
- **Proposed: completion is kept once reached** (above).
- **Proposed: open questions are Setup tasks while onboarding runs.**

## Done when

- A new workspace goes scan → specs → questions. While it does:
  - `get_next_task` hands out the questions step after the specs;
  - the strip shows Answers N of M;
  - the score is hidden.
- `answer_clarifications` with the last open questions, some `proposed: true`:
  - records each answer as the person's;
  - marks the proposed ones;
  - stores `onboarding_completed_at`;
  - answers with the "Your dashboard is ready" next step and the link.
- Raising a new question afterwards does not hide the score or bring the strip back.
- Readiness still shows four steps, and `/mcp-docs` lists the new step and the
  `proposed` input with its description.
- Route tests run through the API on the local database with invented agents and
  calls. The MCP server tests pass.

## Out of scope

- Any web screen for answering questions, or for showing proposals.
- Telling the person through anything but their assistant (no email or Slack).
- Changing how questions are raised or ranked.

## Risks

- **Existing workspaces:** a workspace already past onboarding with open questions would
  lose its score until they are answered. The migration stores
  `onboarding_completed_at` for every workspace whose Readiness steps are all done
  today, so nothing that shows a score now stops showing it.
- **`proposed` on an old MCP server:** the three services deploy separately. The backend
  treats a missing `proposed` as false, and an old server never sends it, so either
  order works.

## Outcome

### Deviations from the plan

- **Completion needs the questions step to have been gone through.** Without that, the
  last spec written would complete onboarding before the assistant could raise
  anything. So it completes only once questions were answered or parked, or the
  assistant took the "Answer the open questions" step and asked for its next task.
- **The questions row shows until questions are raised.** Then each agent's questions,
  waiting for the person, take its place. Every spec task blocks the row.
- **The cards on Work complete onboarding too** (the web answer route), without a
  message. Only the assistant says "Your dashboard is ready".
- **The migration marks complete every workspace past its first scan**
  (`onboarding_completed_at = first_scan_done_at`). That stands in for "every Readiness
  step done", which only the app can work out. A workspace with a disconnected
  assistant today keeps its score.
- **Completion locks the workspace row,** so two calls finishing at once announce it
  once (`/code-review`).
- **The `proposed` input is sent only when true,** so a backend from before it reads
  every answer as it did.

### Check results

`make check`: every step ok except backend tests, where 2 of 1,551 failed. Both were
in `test_clarifications.py` and expected a plain answer's decision record to hold only
`rule` and `spec_version`. The record now carries `proposed` only for a confirmed
proposal; those tests, `test_onboarding_finish.py` and `test_mcp_clarifications.py`
pass (29). Every other step: ok (lint, format and types; MCP server tests; frontend
lint and types; generated client fresh). Route tests ran through the API on the local
database (`TestClient`), so no separate play-through server was used.

After rebasing onto main (with #233), `make check` ran again: every step ok.

**Tests** (`test_onboarding_finish.py`, 3, invented agents and calls; the assistant
connection is patched in):

- **Questions, then a confirmed batch:**
  - After the specs, `get_next_task` hands out "Answer the open questions", whose
    instruction names `proposed`. Onboarding is not complete, and the strip shows
    Scan, Spec and Answers done but Complete not.
  - Raising two questions makes the strip read "Answers 0 of 2". Each agent's
    questions replace the questions row.
  - Confirming one proposed answer and parking the other completes onboarding. The
    first next step says "Your dashboard is ready" with `/dashboard`.
  - The answer is stored as proposed, on the clarification, on its decision record
    (only when proposed) and in `list_clarifications`. The strip is gone and the score is no longer held back
    by onboarding.
  - A question raised later does not reopen onboarding, and answering it gives no new
    "ready" step.
- **Nothing to ask:** taking the questions step and then asking for the next task
  completes onboarding. The taken step ends done, and the "ready" step comes once.
- **`proposed` only on an answer:** with `park` it is refused, and nothing is stored.

**Updated tests:**

- the public onboarding list has the new step;
- Work's first rows end with "Answer the open questions";
- before onboarding completes, the questions sit in setup after the specs;
- the score's "why none" wording;
- the MCP client sends `proposed` only when set.

**MCP server tests:** 53.

**`/code-review` (high), 2 findings:**

- **Fixed:** two calls finishing at once both announced it.
- **Left:** the link is relative when no site address is configured (`SITE_URL` or
  Railway's frontend host). Production has one.

### Not done

- `guides/spec.md` still says the person can answer "on the Action items page". That
  page became the cards on Work (decision 29), and this change left the line as it
  was.
