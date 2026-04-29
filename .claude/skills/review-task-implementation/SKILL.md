---
name: review-task-implementation
description: >
  Use this skill whenever the user types /review-task-implementation or asks to "review the
  implementation", "check if the task was implemented correctly", "review PR changes against the
  Jira task", "does this PR implement the ticket", or similar. This skill fetches Jira task
  details and PR context (comments, conversations, review threads), then performs a structured
  review of the local branch changes against the requirements. Use this skill any time someone
  wants to validate that code changes satisfy a Jira ticket, even if they phrase it casually like
  "does this look right for CS-42" or "check my work against the ticket".
---

# /review-task-implementation — PR Implementation Review

## Overview

Reviews whether the current branch's changes correctly and completely implement what a Jira task
requires. Combines three sources of truth — the Jira ticket, the PR discussion, and the actual
diff — into a single structured review.

This skill assumes you already have the repo checked out on the relevant branch with the
implementation changes present (committed or uncommitted).

### Prerequisites

- **`gh` CLI** is installed via Homebrew (`brew install gh`). Always invoke it as `gh`
  (Homebrew puts it on PATH at `/opt/homebrew/bin/gh` on Apple Silicon or `/usr/local/bin/gh`
  on Intel). If `gh` is not found, check that the Homebrew bin directory is on PATH and
  suggest `eval "$(/opt/homebrew/bin/brew shellenv)"` as a fix.
- `gh` must be authenticated — if commands fail with auth errors, direct to `gh auth login`.
- `git` available on the current repo.

---

## Step 1 — Parse the user's input

The user provides a PR URL and optionally a Jira ticket key. Extract both:

- **PR URL**: e.g. `https://github.com/Adventis-Intelligence/voicevalet_v1/pull/967`
- **Jira ticket**: If not provided explicitly, look for it in the branch name or PR title
  (common patterns: `CS-42`, `PROJ-123`, branch names like `feature/CS-42-add-eval-metrics`)

If neither is found, ask the user for the Jira ticket key.

---

## Step 2 — Gather context (do all of these before starting the review)

### 2a. Fetch PR conversations and review threads

```bash
# PR metadata, comments, and reviews
gh pr view <PR_NUMBER> --json title,body,comments,reviews,reviewThreads,additions,deletions,files

# Unresolved review threads (detailed)
gh api graphql -f query='
{
  repository(owner: "<OWNER>", name: "<REPO>") {
    pullRequest(number: <PR_NUMBER>) {
      reviewThreads(first: 50) {
        nodes {
          isResolved
          isOutdated
          path
          line
          comments(first: 10) {
            nodes {
              author { login }
              body
              createdAt
            }
          }
        }
      }
    }
  }
}'
```

### 2b. Fetch Jira task details

Use the Jira MCP tool if available, or ask the user to paste the task description:

- Summary, description, acceptance criteria
- Subtasks or linked issues
- Any comments with clarifications from stakeholders

### 2c. Inspect the local changes

```bash
# Determine base branch
git remote show origin | grep "HEAD branch"

# Fetch latest
git fetch origin <base-branch>

# What changed — overview
git diff origin/<base-branch>...HEAD --stat

# Full diff for detailed review
git diff origin/<base-branch>...HEAD

# If there are also uncommitted changes, include those
git diff HEAD --stat
git diff HEAD
```

If there are both committed and uncommitted changes, review the complete picture
(base → HEAD + working tree).

---

## Step 3 — Perform the review

Go through the changes methodically. Structure your analysis around these dimensions:

### Completeness
- Does the implementation address every requirement from the Jira task?
- Are all acceptance criteria met?
- Are there requirements mentioned in PR comments or review threads that still need attention?

### Correctness
- Does the logic look sound?
- Are edge cases handled?
- Are there obvious bugs or race conditions?

### Unresolved feedback
- Are there unresolved PR review threads that haven't been addressed?
- Did reviewers request changes that are still missing?

### Code quality (light touch — flag only notable issues)
- Naming consistency with the existing codebase
- Missing error handling in critical paths
- Leftover debug code, TODOs, or commented-out blocks

Do NOT nitpick style or formatting unless it's egregious. The goal is implementation
correctness, not a style audit.

---

## Step 4 — Present the review

Use this structure for the output:

```
## Implementation Review: <Jira ticket key> — <short title>

### Verdict: ✅ Looks good / ⚠️ Needs attention / ❌ Issues found

### Requirements Coverage
For each requirement from the Jira task:
- ✅ <Requirement> — How it's implemented (brief)
- ⚠️ <Requirement> — Partially addressed: <what's missing>
- ❌ <Requirement> — Not implemented

### Unresolved PR Feedback
- <reviewer comment summary> — Status: addressed / still open / partially addressed

### Observations
Things that look good, potential concerns, suggestions — written as a fellow
engineer reviewing, not as a checklist robot.

### Recommended Actions (if any)
Concrete next steps if anything needs fixing.
```

### Tone guidance

Write the review like a senior engineer talking to a peer:
- Direct and specific, not vague ("the retry logic in `_handle_disconnect` doesn't cover
  the timeout case" — not "there might be some edge cases")
- Give credit where it's due — if the implementation is clean, say so
- If everything looks good, keep it short. Don't pad the review with filler observations.

---

## Edge Cases

- **PR has no Jira ticket**: Review the changes against the PR description instead. Note
  that you couldn't cross-reference with a ticket.
- **Branch has no changes vs base**: Report it clearly.
- **Jira task has vague requirements**: Flag this in the review — "the ticket doesn't specify
  X, so I reviewed against what the PR description states."
- **Large PR (50+ files)**: Focus on the files most relevant to the Jira task requirements.
  Mention that you concentrated on core changes and list files you skimmed.
- **`gh` not found or not authenticated**: If `gh` is not on PATH, it's likely a Homebrew
  path issue — try running `eval "$(/opt/homebrew/bin/brew shellenv)"` first. For auth
  errors, direct to `gh auth login`.
- **Multiple Jira tickets**: If the PR implements several tickets, review against each one
  separately.
