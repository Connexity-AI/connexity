# Require a plan file with every pull request

- **Owner:** Dmytro
- **Slice:** 0.5 (added to `REBUILD.md` by this change)

## Goal

Change what a pull request review is. With AI-written code, a person reading the diff
adds little, while a wrong plan is expensive and only a person can catch it. After this
merges, every pull request carries one plan file, the plan is what people review, and a
branch without a complete plan cannot be opened as a pull request or merged.

## Changes

**The plan file**

- New folder `plans/` with a template and a README that states the rule.
- A plan has seven required sections: Goal, Changes, Decisions, Done when, Out of scope,
  Risks, Outcome. Outcome has three required parts, written after the work: deviations
  from the plan, check results, and what was not done.

**Enforcement**

- `scripts/check_plan.py` is the single definition of "has a complete plan". It fails
  when a branch has no plan, more than one plan, a plan with a missing or empty section,
  or nothing but a plan.
- New CI workflow `Plan` runs it on every pull request.
- `make check` runs it as its first step (skipped on `main`).
- A Claude Code hook blocks `gh pr create` when the check fails.
- Claude Code's plan mode now saves plans into `plans/` (`plansDirectory` setting).

**Workflow and context**

- The `/create-pr` skill checks the plan first, and the pull request body becomes: link
  to the plan, a short summary, and the plan's Outcome. A pull request template says the
  same.
- `CLAUDE.md` and the lifecycle doc describe the new roles: the owner approves the plan
  and answers for plan and execution; the team reviews the plan; machines review code.
- `REBUILD.md` becomes the roadmap only. Its session log is closed; from here the record
  of a slice is its plan file.

**Releases**

- The release-please workflow no longer runs on pushes to `main`, so no CLI release pull
  request is opened or updated during the rebuild. It can still be run by hand.

**Also carried in this pull request**

- The five trace-schema decisions made on 2026-10-08 are added to the `REBUILD.md`
  decision log. They were recorded on the working tree before this branch was cut.

## Decisions

All made by Dmytro on 2026-10-08 unless marked.

- Every pull request carries a committed plan; people review the plan, not the code.
- The plan is approved by whoever opens the pull request. Opening it means they answer
  for both plan and execution. The team then reviews the plan in the pull request.
- A pull request never contains a plan alone, because a separate round of plan review
  would add long delays, and redoing work after review is cheap.
- Code review is automated: CI gates plus an AI reviewer. The AI reviewer is deferred.
  Dmytro will research options and prefers one that is not the same provider or model
  that wrote the code.
- Exemptions: release automation branches, and a `no-plan` label applied by a person.
- Per-slice detail moves from `REBUILD.md` into plan files.
- No releases during the rebuild. The finished rebuild ships as 2.0.0 with one shared
  version across backend, frontend, MCP server and, if it survives, the CLI. The CLI
  release automation is paused until then.
- Proposed (Claude): until an independent reviewer exists, the building session still
  runs `/code-review` and reports its findings in the plan's Outcome.
- Proposed (Claude): merged plans are not edited afterwards.
- Proposed (Claude): plan files are named `plans/YYYY-MM-DD-short-name.md`.

## Done when

- `python3 scripts/check_plan.py` fails on a branch with no plan, with two plans, with an
  empty required section, with an empty Outcome part, and with only a plan; and passes on
  this branch.
- The hook script denies `gh pr create` when the check fails and stays silent for other
  commands.
- `make check` passes on this branch with the new first step.
- The `Plan` workflow passes on this pull request.

## Out of scope

- The AI reviewer that compares a diff with its plan. Open question Q8 in `REBUILD.md`.
- Making the `Plan` check required in GitHub branch protection. That is a repository
  setting only Dmytro can change.
- Closing the open release pull request #118 ("release cli 1.0.0"). Left to Dmytro.
- Unifying the version numbers in the code. That happens when 2.0.0 is cut.
- Rewriting past session-log entries as plan files. Phase 0 history stays in `REBUILD.md`.
- Slice 1.1 itself. Its draft schema document is set aside and comes back with 1.1.

## Risks

- **A plan can be complete and still wrong or vague.** The check verifies that sections
  exist and are not empty. It cannot judge quality. That is the reviewer's job, and
  later partly the AI reviewer's.
- **Nothing yet checks that the code matches the plan.** Until Q8 is resolved, a diff
  could do more or less than its plan says and no machine would notice.
- **The hook is advisory in effect.** It only runs inside Claude Code and only for
  sessions that loaded the settings file. CI is the real gate, and it only blocks a
  merge once the check is marked required in GitHub.
- **The `no-plan` label is an honour system.** Anyone with write access can apply it.

## Outcome

### Deviations from the plan

- The hook runs on every shell command and decides inside the script whether the
  command contains `gh pr create`. The first version used the settings file's own
  command filter, which would have missed a compound command such as
  `cd repo && gh pr create`.
- Added a note to `plans/README.md` that a plan saved by Claude Code's plan mode still
  has to be renamed and given the template's sections, and that a leftover plan-mode
  file must be deleted, since a branch may carry only one plan. This follows from
  pointing plan mode at `plans/` and was not thought through in the plan.

- Pausing the CLI release automation and recording the release decisions were added
  after the plan was first written, when Dmytro raised versioning.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 11s |
| Backend tests and coverage | ok | 86s |
| MCP server tests | ok | 4s |
| Frontend lint | ok | 2s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 11s |

The first run of `make check` was made before this Outcome was written, and its plan
step failed for exactly that reason, which is the intended behaviour. The plan step
was then re-run on its own and passed; the other steps were not re-run after that,
because only this file changed.

`scripts/check_plan.py`, exercised in a throwaway worktree:

| Case | Expected | Got |
|---|---|---|
| No changes against the base | pass | pass |
| A change, no plan | fail | fail |
| A complete plan and a change | pass | pass |
| Only a plan | fail | fail |
| Two plans | fail | fail |
| An empty required section | fail | fail |
| An empty Outcome part | fail | fail |

The hook script, fed sample payloads against a throwaway branch with a commit and no
plan: denies `cd x && gh pr create --base main` with the checker's message, and stays
silent for `git status`.

Review of the diff by the building session found nothing to fix in the code and
produced the plan-mode note above. `/code-review` was not run as a separate pass.

### Not done

- Pull request #118 is still open. Merging it would publish `connexity-cli` 1.0.0 to
  PyPI.
- The `Plan` workflow has not run yet; it runs for the first time on this pull request.
- The hook was not observed firing inside a live Claude Code session, only through
  sample payloads. A new session loads the settings file.
- The `Plan` check is not marked required in GitHub branch protection. Until Dmytro does
  that, a pull request with a failing plan check can still be merged.
- No automated check compares a diff with its plan (open question Q8).
