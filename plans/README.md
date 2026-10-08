# Plans

Every pull request carries one plan file from this folder. **The plan is what gets
reviewed.** Nobody is expected to read the diff: code quality is checked by automation,
and people review intent and outcome.

## How it works

1. **Write the plan before the code.** Copy [`TEMPLATE.md`](./TEMPLATE.md) to
   `plans/YYYY-MM-DD-short-name.md`. Claude Code's plan mode saves its plans into this
   folder too; such a file still has to be renamed and given the template's sections
   before it counts, and a leftover plan-mode file must be deleted, because a branch
   may carry only one plan.
2. **The owner approves it.** The owner is whoever will open the pull request. Approving
   the plan is their call; no one else has to sign off before work starts.
3. **Do the work.**
4. **Fill in the Outcome section**: what deviated from the plan, the check results, and
   what was not done.
5. **Open the pull request.** Opening it means the owner takes responsibility for both
   the plan and its execution.
6. **The team reviews the plan** in the pull request, including the Outcome. If the
   review changes the plan, the work is redone to match. That is cheap; a wrong plan
   that merges is not.

## Rules

- **One plan per pull request**, and a plan is never merged on its own. A pull request
  that contains only a plan would add a round of waiting for no benefit.
- **A plan says what happened, not only what was intended.** The Outcome section is
  required. An honest "this part of the plan was wrong" is the most useful thing a
  reviewer can read.
- **Do not edit a merged plan.** It is the record of that change. A later change gets
  its own plan.
- **Decisions carry a name.** Mark anything the owner did not explicitly decide as
  "Proposed".

## Enforcement

`scripts/check_plan.py` defines what counts as a complete plan. It runs in three
places:

| Where | When |
|---|---|
| CI (`Plan` workflow) | On every pull request. Required to merge. |
| `make check` | Before every push. |
| Claude Code hook | When a session runs `gh pr create`. |

## Exemptions

- Pull requests opened by the release automation (branches starting with
  `release-please--`).
- Pull requests labelled `no-plan`, for changes with nothing to plan, such as a typo.
  The label is applied by a person, not by the assistant.
