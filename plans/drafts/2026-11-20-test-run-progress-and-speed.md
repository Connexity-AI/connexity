# Test runs: progress and speed

- **Owner:** Dmytro
- **Slice:** "Fix: test runs the assistant can trust" (roadmap, Test stage), second of two
  pull requests (Decided, Dmytro 2026-11-20: "Two PRs")
- **Design:** No UI change.
- **MCP:** `get_test_runs` gains a `status_only` input and progress, stall and timing
  facts on every run; contract page entries, input descriptions and the guide follow.

Status: **draft**, kept here until the first pull request
(`plans/2026-11-20-trustworthy-test-runs.md`) merges. Numbers follow the roadmap row.

## Changes

**4. Nothing is lost or stuck silently**
- A judge error is retried once. The answer "rule 'None'" is one case: an item without a
  key is dropped and the rule judged again, instead of failing the whole call.
- A run's totals lead with its sample: "18 of 21 calls judged, 2 stopped, 1 judge
  error". An on-demand run's `result` is `passed` only when every call was judged;
  otherwise `incomplete` (Proposed).
- A call's `started_at` is written when the call starts. Counts gain `queued`,
  `running` and `started`.
- The process running a run writes a heartbeat on the run every 30 seconds. A run that
  is running with a heartbeat older than 2 minutes is `stalled`, with when it last
  moved; after 15 minutes it is marked failed ("the server running it stopped"), and its
  finished calls keep their verdicts (Proposed). A restart or a deploy is the known way
  a run dies today, and it then says "running" forever.
- `get_test_runs` with `run_id` and `status_only` answers only status, counts,
  `stalled` and the last progress time: no rules, no calls. The "still running" next
  step asks for it.

**6. Speed: the cause, a signal, then more in parallel**
- Found on production (three runs, timings only): in the slow run the agent's reply
  time per turn went from 5.5 s to 21.9 s and the simulated caller's from 5.2 s to
  14.5 s, in the same run, and time belonging to neither went from 8 s to 38 s per
  call. Two unrelated providers slowing together by the same factor points at the web
  process waiting for CPU, not at Retell or the caller model. That fits Cloud Run
  giving a service CPU only while a request is being handled, since a run works between
  requests. Not confirmed: the service's setting could not be read from this machine.
- The fix is a Cloud Run setting, so it is in Out of scope for Dmytro.
- The signal, in this pull request: each call stores its time waiting for the agent,
  for the caller model, for the judge, and the rest ("waiting for the server"). A run
  shows the medians, and says so in a next step when the server's share is over a
  third.
- More in parallel: the limit becomes a setting, `SIMULATION_CONCURRENCY`, default 25
  (Decided, Dmytro 2026-11-20), so 21 calls run at once. Retell's 429 answers are already
  retried with their wait; calls that hit one are counted on the run, so the limit
  found on production is recorded from real numbers after merge.

**Data**
- One migration: `test_case_result` gains the four waits and a rate-limit count; `run`
  gains `heartbeat_at`.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | Items 4 and 6 of the roadmap row | Decided (Dmytro, roadmap row, 2026-11-20) |
| 2 | Concurrency is a setting, `SIMULATION_CONCURRENCY`, default 25 | Decided (Dmytro, 2026-11-20, chose "Setting, default 25") |
| 3 | A Cloud Run setting is reported, not changed | Decided (Dmytro, roadmap row) |
| 4 | Stalled after 2 minutes without a heartbeat, failed after 15 | Proposed |
| 5 | An on-demand run with calls that were not judged reads `incomplete`, not `passed` | Proposed |

## Out of scope

- **For Dmytro: Cloud Run CPU.** If `connexity-backend` gives CPU only during requests
  (the default), a run slows whenever nothing is polling it. Setting CPU to always
  allocated (`--no-cpu-throttling`) and one minimum instance is the likely fix. Not
  changed in this pull request.
- Moving runs out of the web process (a worker or a queue).
