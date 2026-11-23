# Compare each day's recorded model cost with Anthropic's cost report

- **Owner:** Dmytro
- **Slice:** "Usage per workspace" (roadmap, Platform stage), pull request 2 of 2
- **Design:** none. No screen; Connexity's own cost is not shown to customers.
- **MCP:** no tool. This is Connexity's own account, read from the database
  (Decided, Dmytro 2026-11-21, "Database only"). Nothing a workspace's assistant can
  do changes with it.

Status: **approved by Dmytro, 2026-11-23 ("Accept, build")**. Statements are marked Decided
(Dmytro), Proposed (Claude) or Open.

## What was found before planning

Read on 2026-11-23 from Anthropic's reports (admin key) and the hosted database (read
only, totals only).

- **The admin key works.** The cost report gives dollars per day by model and
  workspace; the usage report gives tokens per day by model, API key and workspace.
  Amounts in the cost report are in cents.
- **Our price list is right.** On 20 Nov Anthropic's tokens times our prices give
  $0.0579, and Anthropic billed $0.0579.
- **One API key does everything.** The organisation has one workspace and one key in
  use, so production and local development land in the same report:

  | Day (UTC) | Anthropic billed | Connexity recorded |
  |---|---|---|
  | 17 Nov | $0.037 | $0 |
  | 19 Nov | $0.024 | $0.007 |
  | 20 Nov | $0.058 | $0.057 |

  The gap on 17 and 19 Nov is most likely runs from a developer's machine, which the
  hosted database never sees. It cannot be told apart from a recording bug today.
- **Token counts before 21 Nov are not comparable.** Rows filled in by the migration
  hold the simulated caller's tokens only; the judge's tokens are stored since pull
  request 255.
- **Only Anthropic is covered.** Model checks on real calls run on another provider's
  model (about $0.001 a day); its cost has no report to compare with here.

## Goal

Every day Connexity knows, per model, what Anthropic billed and what Connexity
recorded for the same day, in dollars and in tokens by kind, and whether they agree.
The two sets of numbers sit side by side; reading them is enough to see a wrong
price (tokens agree, dollars do not) or requests never recorded (tokens differ).

## Changes

**A table, one row per day and model (`provider_cost_day`)**
- The day (UTC), the provider (`anthropic`), the model.
- Billed: dollars, and tokens in, out, cache read and cache write, from Anthropic.
- Recorded: the same five numbers summed from `usage_record` for that day and model.
- When it was read. A day is read again until it is three days old, since the report
  runs some hours behind; then it is final.
- Nothing is judged: no tolerance, no "agrees" flag, no cause, no warning (decision
  3).

**Reading the reports (`services/provider_cost.py`)**
- Anthropic's cost report and usage report for the days not final yet, with the admin
  key from a new setting `ANTHROPIC_ADMIN_KEY`. Without the key nothing runs.
- The whole organisation is read: one key serves everything (decision 1).
- Timeout, empty answer and malformed answer each have a test (backend rule for
  external calls); a failure is logged and tried again on the next run.

**When it runs** (decision 2)
- Inside the scheduled call pull that Cloud Scheduler already triggers every minute:
  at most once every six hours it reads the reports. No new scheduler job.

**Docs**
- `docs-internal/usage.md` (the comparison, how to read the table),
  `docs-internal/deployment.md` (the new setting, as a step for Dmytro),
  `.env.example`.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | One Anthropic key stays; the whole organisation is compared. The account is used for Connexity only | Decided (Dmytro, 2026-11-23: "keep one key we dont use this account for api anything else but connexity") |
| 2 | The comparison runs inside the existing scheduled call pull, at most once every six hours | Decided (Dmytro, 2026-11-23, chose "Inside the call pull") |
| 3 | The table holds the two sets of numbers only. No tolerance, no flag for a day that does not agree, no warning line; added later if needed. Replaces his earlier choice "Table and a log line", which needed a tolerance | Decided (Dmytro, 2026-11-23: "dont overcomplicate with tolerance or other stuff we will do it if needed") |
| 4 | No MCP tool and no screen: Connexity's own cost is read from the database | Decided (Dmytro, 2026-11-21, "Database only") |
| 5 | Only Anthropic is compared; other providers' model checks are left out | Proposed |

## Done when

- With invented report answers: each day and model gets one row with the billed
  numbers from the report and the recorded numbers from `usage_record`.
- A day is read again until it is three days old, then no more.
- No admin key: nothing is read and nothing fails. A timeout, an empty and a
  malformed answer are logged and leave the table as it was.
- Read once against the real report (read only) and the stored rows match the totals
  above.
- `make check` passes.

## Out of scope

- Setting the admin key in Cloud Run: Dmytro's, as every cloud setting is. The
  deployment doc lists the step.
- Costs of other providers, hosting and the database.
- A screen, an alert by email or chat, billing.

## Risks

- One key serves production and local development (decision 1). A run from a
  developer's machine is billed by Anthropic and recorded only in that machine's
  local database, so that day shows more billed than recorded, and the numbers
  cannot say whether it was local work or a recording bug.
- Anthropic may change the report's shape; the malformed-answer path keeps the job
  from failing the call pull.

## Outcome

Built as planned, with the deviations below.

- Table `provider_cost_day` (migration `0045_provider_cost_day`): one row per day
  (UTC) and model, billed and recorded, each as dollars and four token counts.
- `app/services/provider_cost.py` reads Anthropic's cost report and usage report for
  today and the three days before, sums `usage_record` for the same days, and
  replaces the rows.
- The scheduled call pull runs it, at most once every six hours.
- New setting `ANTHROPIC_ADMIN_KEY` (`.env.example`, deployment doc). Without it
  nothing is read.
- Docs: `usage.md` (how to read the table and what it cannot say), `data-model.md`,
  `deployment.md`.

### Deviations from the plan

- **A failed read is tried again after ten minutes,** not at the next six-hour slot,
  and the whole read has a 12-second limit so it cannot push the call pull past
  Cloud Scheduler's minute (both from code review).
- **Tests never use the developer's admin key:** a fixture in `app/tests/conftest.py`
  unsets it, because the call pull's tests would otherwise ask Anthropic.
- **The six-hour clock is kept in the process,** as the call pull's backlog clock is:
  a second instance or a restart may read once more, which only replaces the same
  rows.

### Check results

- `make check` (every gate, run once on 2026-11-23 on the finished branch): all
  passed, backend tests with coverage, MCP server tests, lint, types, client codegen
  freshness and the plan check included.
- `test_provider_cost.py` (10 tests, invented report answers): billed beside
  recorded for a day; a day read again is replaced, not doubled; pages; no key;
  timeout, refusal, empty, malformed and an answer without an amount leave the table
  as it was; the scheduled call pull reads it once.
- One real read of Anthropic's reports through the new code, storing nothing
  (2026-11-23): 17 Nov $0.0368, 19 Nov $0.0241, 20 Nov $0.0579, the totals found
  before planning.

### Not done

- **The key is not in Cloud Run.** Dmytro creates the secret
  `connexity-anthropic-admin-key` and mounts it as `ANTHROPIC_ADMIN_KEY`; until then
  production reads nothing.
- **Nothing was written to the hosted database from here,** so the table is empty
  until production runs with the key.
- Code review (5 findings): 3 fixed (retry after a failure, the time limit, the HTTP
  status in the log); 2 left: a row is not cleared when a day's numbers disappear
  on both sides, and the recorded side trusts the one model name a usage record
  carries.
