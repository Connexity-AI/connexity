# One check system for code-based checks, classifiers and LLM judges

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Classifiers and judges (incl. check 3)"
  (10.14).
- **Design:** No UI change. Model findings already show on the issue page with their
  `found_by`.
- **MCP:** `list_issues` and `get_issue` answer `found_by: code-based`, `classifier` or
  `judge`, and for a model finding the model and version. No new tool.

## Goal

Adding a new issue check is the same work whatever decides it: code, a classifier
(Jev) or an LLM judge. The check says what it asks and how answers become findings;
the system runs it on every call, stores what the model said, counts the cost and
keeps the budget. Each check has one way of deciding. Comparing ways (A/B) happens
outside the product, in a session, when Dmytro asks for it. The first check on it is
"Action claimed without a tool call".

## Decisions

- **Three kinds: code-based, classifier, LLM judge.** "Rule" means a spec rule only
  (Dmytro, 2026-11-17).
- **The kind is what the check returns, not the model; mixing kinds makes no new kind;
  a judge only when the question cannot be split into labelled facts plus code**
  (Dmytro, 2026-11-17).
- **Integrate Jev; development complexity is not a concern** (Dmytro, 2026-11-17).
- **Each issue check is one thing: code-based, classifier or judge. No shadow methods
  in the product. A/B tests run outside the product, in sessions, on demand, when
  Dmytro decides** (Dmytro, "we dont run any shadows", 2026-11-17).
- **"Don't destroy my budget"** (Dmytro, 2026-11-17): every model check has a spend
  cap.
- **Checks are a library:** a check is added only when Dmytro names it.
- **The first check is decided by Jev** (Dmytro, 2026-11-17).
- **The spend cap is an internal safety measure for the whole product, $1 a day**
  (Dmytro, 2026-11-17: "If latter then 1$").
- **The kind of check does not affect severity.** Severity comes from the issue type's
  default (Issue library, "Default severity"), whatever decides it (Dmytro, 2026-11-17).
  This replaces "a classifier or a judge defaults to flags" in
  `checks-and-incidents.md`.
- **Model checks run on all calls; ask TypeSafe for zero data retention** (Dmytro,
  2026-11-17).

## What exists

- **Code-based checks** (`checks/base.py`, `engine.py`): pure, synchronous, run inline
  when a call is stored. Findings carry `kind`, shown as `found_by`.
- **The Jev client** (`services/jev.py`, branch `jev-integration`): typed questions and
  answers, pinned `jev-1.14.0`, retries, cost per request, 11 tests. Tried on the 85
  calls in the hosted database: 679 agent turns for $0.015.
- **The LLM plumbing** (`services/llm.py`): `call_llm` through LiteLLM. With an Anthropic
  model it currently fails before sending (LiteLLM reads an empty `thinking`), so it
  needs a fix.
- **A first comparison, by hand:** Jev plus code flagged 12 calls, a Haiku 5.5 judge 47,
  8 turns both. Not yet labelled.

## Changes

### One check, any kind

- **A check declares its kind and its version.** Changing how it decides, including
  the model, is a new version.
- **A code-based check** stays as today: pure code over the trace.
- **A classifier check** says what to ask about each piece of the call it cares about
  (each agent turn, the whole call, each tool call), with typed questions, and gives
  code that turns the answers plus the trace into findings.
- **A judge check** gives its question, what counts, the answer's shape, and code that
  turns the answer into findings.
- **Every finding points at events and has a key,** as today, whatever the kind.

### Running model checks

- **Model checks run after the code-based ones, in the background,** never while a call
  is being stored. A call shows code-based findings at once, model findings when the
  model has answered.
- **Every model answer is stored** (a new table): the call, the check and its version,
  the pinned model, the answer, tokens, cost and latency. Checking a call again reuses
  it, so a re-check is free and cannot flip a finding by chance. A new check version
  asks again.
- **A failed model call** marks the check broken for that call, and it is retried
  later. Broken never counts as clean.
- **No key for a provider:** its checks are skipped and recorded as skipped.
- **Earlier calls** are checked on request (a backfill), within the budget.

### Budget

- **A daily spend cap for the whole product, all model checks together**
  (`MODEL_CHECKS_DAILY_BUDGET_USD`, default $1). When it is reached, model checks
  stop for the day and the calls are recorded as skipped for budget; they are picked
  up the next day.
- **Each check's cost per call is stored,** so the assistant can say what a check
  costs before it is turned on for more agents.

### Providers

- **Jev** through `services/jev.py`.
- **LLM judges** through `call_llm`, fixed for Anthropic models, with the model pinned
  per check.
- **Connexity's own keys** (`TYPESAFE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).

### Trying and comparing checks outside the product

- **`scripts/try_check.py <check> [--agent] [--limit] [--budget]`** runs a check, or a
  draft of one not yet registered, over calls in a database opened read-only. It writes
  ids, labels and numbers to a file and prints counts, never call text. Nothing is
  stored in the product.
- **An A/B test** is two runs of it on the same calls, in a session, when Dmytro asks;
  `scripts/compare_runs.py` lines the two result files up turn by turn. This is how
  today's Jev and Haiku runs were compared by hand.

### The first check: Action claimed without a tool call

- **A classifier (Jev):** each agent turn is labelled with what it claims
  was done (booked, cancelled, moved, notified, looked up, or nothing); code then looks
  for a tool call that could do it, earlier in the call, that did not fail.
- **The judge version stays a draft** for `try_check.py`, not registered.
- **Default severity:** Critical, from the Issue library row, like any other type.

### Naming

- **`CheckKind.RULE` becomes `CODE_BASED`**, shown as `code-based`, across the backend,
  MCP, frontend labels and `docs-internal/`, with a migration for stored values.

### MCP

- **`list_issues`, `get_issue`:** `found_by` per finding, and for a model finding the
  model, the check version and the turn.

### Docs

- `docs-internal/checks-and-incidents.md`: how a check of each kind is written and run,
  stored answers, budget; severity from the type, not the kind.
- `docs-internal/issue-types.md`: the new type and how it decides.
- A short "adding a check" guide: pick the kind, try it with `try_check.py`, A/B in a
  session if Dmytro asks, then register.

## Done when

- A code-based check, a classifier check and a judge check are each written the same
  way and run on a test call; findings carry the right `found_by`.
- For the first check, on invented calls: a claim with no tool call gets one finding
  on that turn; with a successful tool call, none; with a failed one, one.
- A re-check makes no model calls and changes nothing.
- A failed model call leaves the check broken, not clean; no key leaves it skipped.
- With the daily cap reached, model checks stop and calls are recorded as skipped for
  budget.
- `try_check.py` runs the Jev check and the judge draft on the hosted calls read-only,
  and `compare_runs.py` lines them up, printing counts only.
- `make check` passes. Model calls are faked in tests.

## Out of scope

- Other model checks; each comes when Dmytro names it.
- Model checks on simulated calls.
- Shadow methods, comparison screens or tools, and labels in the product.
- Checks defined as data by the assistant or a person (the vision's later step); here
  a check is code in the library.
- Training our own small judge.

## Risks

- **Real client calls go to TypeSafe and Anthropic.** TypeSafe offers zero data
  retention to enterprise customers only; a request for it is drafted for Dmytro.
- **Cost grows with call volume.** The cap stops it; the comparison shows cost per call.
- **Jev is in early access;** its version is pinned and its checks can be turned off.

## Questions

1. **The rename to code-based in this PR.** Decided yes (Dmytro, "Yes, build",
   2026-11-17).

## Outcome

### Deviations from the plan

- **Budget and waiting calls stay `pending`,** not "skipped for budget": a call the
  budget or the pass's time did not reach is simply still waiting, and the next pass
  (or tomorrow's budget) picks it up, newest first. No separate reason is recorded.
- **No separate backfill request.** A new model check version leaves every stored call
  pending through the existing "calls a current check version never ran on" pass, and
  the model pass then answers them newest first within the budget. So once deployed,
  production calls are checked by Jev automatically, about 5,000 calls a day at today's
  cost before the $1 cap stops it.
- **Latency is not stored** on a model answer; tokens, requests, cost and attempts are.
- **Names in code:** the base class is `Check` (was `RuleCheck`) for every kind, and
  code-based checks moved from `checks/rules/` to `checks/code/`. Model checks live in
  `checks/model/`.
- **MCP:** a model finding's detail names the model; `check_version` was already on
  each finding, so no new field. `found_by` is now `code_based`, `classifier` or
  `judge` everywhere (issues, the issue page, the call screen, the call list).
- **The Claude fix changes existing behaviour:** `call_llm` no longer asks LiteLLM to
  turn reasoning off for Claude models (it failed before sending, and current Claude
  models cannot turn thinking off). Anthropic runs of the test judge and the simulated
  caller now think by default, at more tokens.
- **No judge check is registered.** The judge path is tested through its helper
  (`test_judge_helper.py`) and the draft run on real calls, not through the engine with
  a registered judge.

### Check results

`make check`:

| Step | Result |
|---|---|
| Plan present and complete | ok (rerun after moving the unapproved tips plan to `plans/drafts/`) |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok (new: `test_model_checks.py` 15, `test_judge_helper.py` 6, one in `test_llm.py`) |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

**Tried on the hosted calls (read only, counts only), 2026-11-17:**

| Run | Kind, model | Calls flagged | Findings | Cost |
|---|---|---|---|---|
| `try_check.py action_claimed_without_tool` | classifier, jev-1.14.0 | 12 of 85 | 12 | $0.015 |
| `try_check.py --draft check_drafts/action_claimed_judge.py` | judge, claude-haiku-5-5 | 44 of 85 | 71 | $0.016 |

`compare_runs.py`: 5 turns flagged by both, 7 only by Jev, 66 only by the judge. None
reviewed by a person yet.

No separate play-through server: the route and service tests send the same requests
through the API on the local database, and the scripts ran against the hosted one read
only.

**`/code-review` (high), 8 findings:** fixed six (calls skipped for a missing key are
checked once it is added; each model ask is bounded by the pass's deadline; an issue
with no findings left takes `found_by` from its check; `try_check.py` survives one
failed ask; a tool with no result backs a claim; an outdated answer naming another
event is ignored instead of breaking the check). One was not a bug (only an OK answer
carries cost, and it is never updated). One skipped: each waiting call's trace is
read twice per pass, cheap enough for now. The affected tests were rerun after the
fixes, not the whole `make check`.

### Not done

- **Nobody has reviewed the 12 flagged calls** to say how many are right.
- **The zero data retention request to TypeSafe** is drafted for Dmytro, not sent.
- **The Issue library row** has its method, code and "How to check" filled; its Status
  moves to Built after merge.
- **Not checked on screen:** the call screen's "Found by code / a classifier / an LLM
  judge" label (Dmytro checks screens).
