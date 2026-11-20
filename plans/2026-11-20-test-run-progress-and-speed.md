# Test runs: progress and speed

- **Owner:** Dmytro
- **Slice:** "Fix: test runs the assistant can trust" (roadmap, Test stage), second of two
  pull requests (Decided, Dmytro 2026-11-20: "Two PRs"). The first is
  `plans/2026-11-20-trustworthy-test-runs.md`.
- **Design:** No UI change.
- **MCP:** `get_test_runs` gains one input, `status_only`, and progress, stall, sample
  and timing facts on every run. `run_scenarios` is unchanged. The contract page entry,
  the new input's description, the tool rules and the scenarios guide follow.

Status: **approved by Dmytro on 2026-11-20 ("Accept"; "merged, build")**. Statements are marked Decided (Dmytro's words,
from the roadmap row or his answers on 2026-11-20), Proposed (Claude) or Open. Item
numbers follow the roadmap row.

## Goal

A run in progress says how far it is and whether it is stuck, in a small answer. A
finished run says how much of its sample it lost and where its time went. Nothing about
a run is lost or stuck without the run saying so. Runs make more calls at once, so a run
takes about as long as one call.

## Changes

**4. Nothing is lost or stuck silently**

*Judge errors*
- Today one unreadable judge answer drops the whole simulated call: it gets no verdicts
  and the sample shrinks. The error "answered rule 'None'" is one case: one item of the
  answer had no key.
- The judge is not asked again (Decided, Dmytro 2026-11-20, chose "No retry, only
  count"): the call keeps no verdicts, as today, and is counted.
- A run's counts split what was lost: `stopped` (the conversation failed) and
  `judge_errors` (the conversation is there, the judge gave nothing).

*The sample*
- Every completed run leads its next steps with its sample: "18 of 21 calls judged, 2
  stopped, 1 judge error."
- An on-demand run (a set or a pick) with calls that were not judged reads
  `incomplete`, not `passed` (Decided, Dmytro 2026-11-20). A failure it did find still
  reads `failed`.

*Progress*
- A call's `started_at` is written when the call starts. Today it is written when the
  call ends, so a run in progress cannot tell a queued call from one in flight.
- Counts gain `queued`, `running` and `started`, beside `finished`.
- The run says when it last moved (`last_progress_at`: the latest call start or
  finish).

*Stalls*
- Today a run lives in the process that started it. When a server starts, it marks
  every pending or running run as failed ("stopped by a restart"), whichever server
  owned it. A server that stops with no new one starting leaves its run "running"
  forever.
- The process running a run writes a heartbeat on the run every 30 seconds.
- A running run whose heartbeat is older than 2 minutes reads `stalled`, with since
  when.
- After 15 minutes without a heartbeat it is marked failed: "the server running it
  stopped; run it again". Its finished calls keep their verdicts (Decided, Dmytro
  2026-11-20, chose "Stalled, then failed").
- A starting server fails only runs whose heartbeat is that old, not every running run.
- A slow run is not a stalled run: its heartbeat keeps coming, and its counts show
  calls in flight.

*Cheap polling*
- `get_test_runs` with `run_id` and `status_only` answers status, counts, the sample,
  `stalled` and `last_progress_at`. No rules, no calls, no read of Retell.
- The "still running" next step asks for it, and gives the full read only once the run
  has completed.

**6. Speed**

*The cause*
- Found on production (three runs, timings only). In the slow run the agent's reply
  time per turn went from 5.5 s to 21.9 s, the simulated caller's from 5.2 s to 14.5 s,
  and time belonging to neither from 8 s to 38 s per call.
- Two unrelated providers slowing together by the same factor points at the web process
  waiting for CPU, not at Retell or the caller model. That fits Cloud Run giving a
  service CPU only while a request is handled, since a run works between requests.
- Not confirmed: the service's setting could not be read from this machine. The fix is
  a Cloud Run setting, so it is in Out of scope for Dmytro.

*The signal*
- Every finished call says where its time went: waiting for the agent, for the caller
  model, for the judge, and the rest ("waiting for the server").
- Agent and caller times come from the per-turn timings a call already stores, so runs
  made before this change show them too. The judge's time is new.
- A run shows the medians per call. When the server's share is over a third, a next
  step says so: "this run was slowed by the server, not by the agent".

*More in parallel*
- The limit of calls at once becomes a setting, `SIMULATION_CONCURRENCY`, default 25
  (Decided, Dmytro 2026-11-20), so a 21-call run runs all at once.
- Retell's "too many requests" answers are already retried with their wait. Each call
  now counts them, and a run shows the total (`throttled`), so the real limit is read
  from production after merge and recorded.

**Data**
- One migration: `run` gains `heartbeat_at`; `test_case_result` gains `judge_ms` and
  `throttled`. Nothing is backfilled.

**Docs**
- `docs-internal/testing.md`, the scenarios guide, `/mcp-docs` entries, `.env.example`.

## Decisions

| # | Decision | By |
|---|---|---|
| 1 | Items 4 and 6 of the roadmap row | Decided (Dmytro, roadmap row, 2026-11-20) |
| 2 | Concurrency is a setting, `SIMULATION_CONCURRENCY`, default 25 | Decided (Dmytro, 2026-11-20, chose "Setting, default 25") |
| 3 | A Cloud Run setting is reported, not changed | Decided (Dmytro, roadmap row) |
| 4 | No judge retry; judge errors are counted apart from stopped calls | Decided (Dmytro, 2026-11-20, chose "No retry, only count") |
| 5 | An on-demand run with calls that were not judged reads `incomplete` | Decided (Dmytro, 2026-11-20, chose "Incomplete") |
| 6 | Stalled after 2 minutes without a heartbeat; failed after 15, keeping finished calls | Decided (Dmytro, 2026-11-20, chose "Stalled, then failed") |
| 7 | A stopped run is not resumed; the assistant runs it again | Proposed |
| 8 | `status_only` is an input of `get_test_runs`, not a new tool | Proposed (rule 10: extend a tool before adding one) |

## Done when

- A judge answer that cannot be read: the run counts 1 judge error, apart from stopped
  calls, and says "N of M calls judged".
- A pick with one stopped call and no failure reads `incomplete`.
- While a run is in progress, `status_only` answers under 2 KB with queued, running,
  started and finished counts, and makes no request to Retell.
- A run whose heartbeat is 3 minutes old reads `stalled`; at 16 minutes it reads
  failed and its finished calls still have verdicts. A server starting beside a run
  with a fresh heartbeat leaves it running.
- A completed run shows median waits per call for agent, caller, judge and server.
- With `SIMULATION_CONCURRENCY` unset, 21 calls are in flight together.
- The contract tests pass with the new input and its description; `make check` passes.

## Out of scope

- **For Dmytro: Cloud Run CPU.** If `connexity-backend` gives CPU only during requests
  (the default), a run slows whenever nothing is polling it. Setting CPU to always
  allocated (`--no-cpu-throttling`) and one minimum instance is the likely fix. Not
  changed in this pull request.
- Measuring the limit on production: done after merge and the CPU setting, then
  recorded in `docs-internal/testing.md`.
- Moving runs out of the web process (a worker or a queue).
- Resuming a run that stopped.
- Applying the agent's real tool schemas: the next roadmap row.
- Any change to the Tests tab's design. A run that reads `incomplete` or `stalled`
  shows there as it does today until the design says how.

## Risks

- 25 calls at once may meet Retell's or the caller model's rate limit, more so while the
  server is short of CPU. `throttled` will show it, and the setting lowers it without a
  deploy of code.
- A heartbeat needs the server to have CPU. A server starved of CPU for 2 minutes would
  read `stalled` while alive; it recovers on the next heartbeat. 15 minutes before
  failing leaves room for that.
- Without a retry, a judge error still costs the call its verdicts; the run now says
  so, and the assistant runs that scenario again.
- `incomplete` is a new value of an on-demand run's result; the Tests tab shows no label
  for it until designed.

## Outcome

### Deviations from the plan

- **A simulated call no longer holds a database connection for its whole
  conversation.** Not in the plan, found in code review: each call kept one for
  minutes, and the pool holds 15, so 25 calls at once would have run out. The runtime
  now gives the connection back right after its one read.
- **Runs whose server stopped are marked failed in three places:** when a server
  starts, on the minute call pull, and when `get_test_runs` is asked about the agent.
  The plan named only the rule, not where it runs.
- **After a restart, a run stays "running" (then stalled) for up to 15 minutes** before
  it is failed. Before, a starting server failed it at once. This follows from failing
  only runs with no sign of life.
- **A judge error is told from a stopped call by whether the judge was asked**
  (`judge_ms` is set), with no extra column. Calls made before this change count as
  stopped.
- **In a run that is no longer in progress, `queued` and `running` are 0;** calls it
  never finished are only missing from `finished`. Found in code review.
- **The slow-server next step does not ask for a feedback report.** It says the run was
  slowed by Connexity's server and that its results stand. Found in code review.
- **`status_only` without `run_id` is refused** (422) with what to send instead.
- **The second throttle count is per call too** (`throttled` on each simulated call).

### Check results

`make check` on the final code:

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

Route tests send the requests through the API on the local test database
(`TestClient`); no separate play-through server was used.

| Request | Expected | Came back |
|---|---|---|
| `GET test-runs?run_id=&status_only=true` on a run not started, with no Retell mock | `status` only: 2 queued, 0 running, 0 finished; under 2 KB beside the rules; no request to Retell; next step asks for `status_only` again | as expected |
| `GET test-runs?status_only=true` without `run_id` | 422 naming `run_id` | as expected |
| Same run, last sign of life 1, 3 and 16 minutes ago | not stalled; `stalled` with since when; failed, "server running it stopped", nothing queued or running | as expected |
| A server starting beside a run 1 minute old and one 16 minutes old | only the old one is failed | as expected |
| A run in progress, read while the judge is asked | its call is started and not finished; no database connection held during the conversation; the run has a heartbeat | as expected |
| The heartbeat loop | writes a newer heartbeat, stops when the run ends | as expected |
| A pick of 2 repeats, the judge unreadable for one | judge asked twice in all (no retry); 1 error, 1 judge error; `result` `incomplete`; first step "1 of 2 calls judged, 1 judge error" | as expected |
| A run where Retell answers "too many requests" once | `throttled` 1 on the run and the call, no error, a next step says so | as expected |
| Call and run timing from invented calls | agent, caller, judge and server seconds; server share 65% and 2% | as expected |
| A run started with the setting unset | stored with 25 calls at once | as expected |
| MCP server: `get_test_runs` with `status_only` | forwards `status_only=true`, reads the status | as expected |

Existing tests changed: `test_a_restart_fails_runs_it_stopped` is replaced by
`test_a_run_whose_server_stopped_is_failed_and_a_live_one_is_left_alone`, because the
rule it pinned (a starting server fails every running run) is the one this plan
replaces. The startup test in `test_lifespan.py` is rewritten for the same reason, and
gained a case: a run with a recent sign of life is left alone. One exact-counts
assertion gained the new counts. Nothing else was loosened.

### Not done

- **Not measured on production.** The real limit of calls at once, and whether the
  server's share falls once the Cloud Run CPU setting is changed, are read from the
  first runs after merge and then recorded in `docs-internal/testing.md`.
- **Cloud Run CPU setting:** for Dmytro (see Out of scope). Until it changes, 25 calls
  at once on a server short of CPU may be slower per call, and the run will say so.
- **The Tests tab shows no label for `incomplete` or `stalled`** (see Out of scope).
- **A stalled run is not resumed** (decision 7).
