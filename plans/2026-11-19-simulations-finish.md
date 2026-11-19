# Simulations that finish and get judged

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Simulations that finish and get judged"
  (10.1945). Builds on `plans/2026-11-17-text-runner.md`,
  `plans/2026-11-17-test-results.md` and `plans/2026-11-19-verdict-needs-a-checked-rule.md`.
- **Design:** No UI change. The Tests tab shows the version number it already has a place
  for; today it falls back to "latest".
- **MCP:** `run_scenarios` (a missing model key refuses the run; the turn limit in its
  rules) and `get_test_runs` (why calls stopped, in next steps). Their `contract.py`
  entries and input descriptions follow. No new tools or inputs.

## Goal

Dmytro's two smoke runs on production (set "smoke", 7 scenarios x 3 repeats) gave no test
result: 42 of 42 simulated calls ended in an error, 0 of 43 rules judged. After this
merges the same set runs on production, every conversation ends by itself or at the turn
limit, the judge gives a verdict for every listed rule, and the Tests tab names the
version tested.

## What was found (production logs and the stored runs, 2026-11-19)

| # | Symptom | Cause |
|---|---|---|
| 1 | Run 1: every call failed with "Missing Anthropic API Key" | The key was not yet in production when `SIMULATION_MODEL` moved to Claude Haiku 5.5 (it was added later the same day; `deployment.md` already lists it). Nothing checks for the key before a run starts. |
| 2 | Run 2: every conversation that ended (5 of 5) failed with "The judge's model call failed" | Anthropic rejects the request with a 400: "`temperature` is deprecated for this model". The judge sends `JUDGE_TEMPERATURE` (0.2); Claude Haiku 5.5 takes no sampling settings. The simulated caller sends none, so it works. The stored error drops the reason. |
| 3 | `end_call` answered "not available in this test" | The catch-all fake names no tool, so Retell applies it to every tool, `end_call` included. The runner's own check for a hang-up reads the agent's tool list, which a Retell run never fills in. |
| 4 | 16 of 21 conversations hit the 120 s cap after 8 to 20 turns | One exchange takes about 17 s: the agent's reply through Retell's playground about 10 s, the simulated caller's about 6.6 s. No retries were logged, so the caller is not throttled. It is slow because Claude Haiku 5.5 thinks by default (medium effort). And only 5 conversations run at once, so 21 calls took 11 minutes. |
| 5 | The version reads Failed with no rule judged | `_verdict_of` fails a version on a critical code check whatever else happened (kept on purpose in PR #238). Run 2's code checks found 4 bookings with missing details and 1 double booking on calls that were cut off. |
| 6 | The Tests tab reads "Version latest" | Retell answered `get-agent-versions` with an error on both runs, so no version was pinned (`platform_version` empty). The call screen and component versions read the same agent with `get-agent`, which returns its version number and works. |

## Changes

### The model key (1)

- `run_scenarios` refuses the run before anything is stored when the key the simulation
  model needs (`ANTHROPIC_API_KEY` for `SIMULATION_PROVIDER` "anthropic", `OPENAI_API_KEY`
  for "openai") is not set: "Simulations are not available right now: Connexity's model
  key is missing." The problem line tells the assistant to tell the person; there is
  nothing for it to fix.
- `deployment.md` already names the secret; it gains one line saying a run is refused
  without it.

### The judge (2)

- The model call no longer sends a temperature to models that reject one. Where this is
  decided once in `llm.py` (Proposed): Claude models get no `temperature`, the same
  place that already leaves their thinking alone. `JUDGE_TEMPERATURE` goes if nothing
  else reads it.
- The stored error keeps the real reason: "The judge's model call failed: <provider
  message>", cut to the column length. No transcript or call values go in it (the
  provider's message is about the request, not the call).
- A test sends the judge's request through the same code path with the Claude model and
  checks no `temperature` reaches LiteLLM; another checks the structured answer is
  parsed (LiteLLM turns `response_format` into Anthropic's output format).

### Hanging up (3)

- The catch-all fake names each of the agent's tools instead of none, leaving out
  `end_call` and `transfer_call`, so Retell runs those as it does on a real call. The
  tool names come from the tested version's configuration, read from Retell at the start
  of the run (the run already reads it for the fingerprint).
- When the agent hangs up (Retell reports the chat ended, or `end_call` is called), the
  conversation ends there and is judged. A transfer ends it too: there is no one on the
  other side in a test.
- To verify against Retell while building: that a mock list without `end_call` lets the
  playground end the chat. If Retell still needs a mock for it, `end_call` gets an
  answer that says the call ended instead of "not available".

### Conversations that finish (4)

- **A turn limit instead of two minutes.** A conversation ends when the
  agent hangs up, the simulated caller says goodbye, or the agent has answered 40
  times. A wall-clock cap stays only as a safety net against a stuck platform (10
  minutes), and hitting it is an error, as now.
- Reaching the turn limit is not an error: the conversation is judged on what was said,
  and rules it never reached are Didn't come up.
- **A faster simulated caller.** The simulated caller runs Claude Haiku 5.5
  with thinking off (allowed at effort high or below). A caller's next line needs no
  reasoning. The judge keeps the model's default thinking, because its verdicts need
  it. Measured before and after on a few local calls (a few cents of the key's spend).
- **Conversations in parallel.** A run starts up to 10 conversations at
  once (5 today), so a run of 21 takes about three conversations' time.
  Retell's rate limit answers are retried with backoff like the model's.

### The verdict (5)

- A version with no rule judged is **Not tested**, even when a critical code check found
  something. The findings are still listed, and the next step says they come from calls
  that stopped early or never reached a rule. A critical code check fails a version only
  when at least one rule was judged.
- The full rule ("a verdict only when all rules are checked") comes with 10.196, which
  reads the verdict from the version's latest full run and adds Partially tested. This PR
  stops the false Failed and does not build those states.

- `get_test_runs` next steps say how many calls stopped with an error and the most common
  reason ("21 calls stopped: The judge's model call failed: ..."), and point to one of
  those calls.

### The version tested (6)

- The run pins its version from `get-agent` (its `version` field), the same read the
  fingerprint already makes, instead of `get-agent-versions`. A failure is logged with
  Retell's status and body, not only "returned an error".
- The two production runs already stored stay as they are ("latest"); only new runs
  change.

### MCP

- `run_scenarios`: its rules say a conversation ends when the agent hangs up or after 40
  agent replies, and that hang-ups and transfers are never faked; the missing-key refusal
  is its own error.
- `get_test_runs`: the stopped-calls next step above.
- `contract.py` entries and descriptions follow both.

## Decisions

- **Decided (Dmytro, 2026-11-19, in the roadmap row):** one PR for every simulation bug
  found; the done line above.
- **Decided (Dmytro, 2026-11-18):** the simulated caller and the judge run on
  Connexity's key; workspaces never bring one.
- **Decided (Dmytro, 2026-11-19):** "Verdict only happens when all rules checked so not
  tested": a version with no rule judged is Not tested, whatever the code checks found
  (replaces PR #238's "a critical code check still fails it"). The all-rules part is
  built in 10.196.
- **Decided (Dmytro, 2026-11-19):** a conversation ends after 40 agent replies, with a
  10-minute safety cap counted as an error.
- **Decided (Dmytro, 2026-11-19):** the simulated caller runs with thinking off, the
  judge with the model's default thinking.
- **Decided (Dmytro, 2026-11-19):** up to 10 conversations at once per run.
- **Proposed:** everything else under Changes.

## Done when

- Through the API on the local database (route tests): `run_scenarios` with no model key
  is refused with the new error and stores nothing.
- A unit test: the judge's request for a Claude model carries no temperature, and a 400
  from the model is stored with its reason.
- A unit test with Retell mocked (`respx`): the mocks sent name every tool but `end_call`
  and `transfer_call`; a chat Retell ends stops the conversation and it is judged; the
  41st agent reply never happens and the conversation is judged, not an error.
- A unit test: the run pins the version from `get-agent`; with Retell failing, it logs the
  status and runs on.
- A verdict test: no rule judged with a critical code check found is `not_tested`; one
  rule judged with a critical code check found is `failed`.
- On production after merge, Dmytro's smoke set again: every conversation ends by itself
  or at the turn limit, every listed rule gets a verdict, the Tests tab names version 88
  (or the current one), and `get_test_runs` answers rule totals and coverage.

## Out of scope

- The Tests tab rework, full runs and the new verdict states (10.196).
- Agent versions on calls, issues and spec (10.197).
- The 1.x judge's generic metrics (their own deletion PR).
- Voice simulations and self-hosted agents.
- The Cloud Run settings of `connexity-backend`. Found while building: the service gives
  CPU only while it answers a request, and a run goes on in the background after
  `run_scenarios` returns, so a run gets little CPU and can be stopped with its instance.
  Dmytro (2026-11-19): "its part of cloud deployment and we are working on open source
  repo so its outside of our scope here"; he handles it.

## Risks

- Retell's playground may rate-limit 10 conversations at once. The backoff keeps calls
  from failing; if it is still slow, the number comes down.
- Haiku with thinking off may play a weaker caller. The scenario's goal and behaviour are
  short and explicit, so this should hold; the measurement shows it.
- A rerun on production spends Retell and model credit (cents for a run of 21).

## Outcome

### Deviations from the plan

- **Hang-ups keep the catch-all.** The plan named every tool in the fakes and left out
  `end_call` and `transfer_call`. Review found that a tool the read misses (an MCP tool,
  a tool declared under another key) would then reach the real backend. So the single
  catch-all stays, and the conversation ends at a hang-up or transfer because the runner
  now knows the tested version's tools (read from Retell at the start of the run) and
  stops at any tool that ends the call, whatever Retell answers it. That tool is not
  listed as a default fake or told to the judge as unavailable. Not checked against the
  real Retell playground.
- **The caller's goodbye ends nothing.** A conversation ends at the agent's hang-up or
  transfer, or after 40 agent replies. After a caller's goodbye the agent replies and
  normally hangs up.
- **The simulated caller was not slow because of thinking.** Measured locally with the
  real simulator prompt: Claude Haiku 5.5 answers in about 1 s with thinking on or off,
  also 10 at once. The production slowness comes from Cloud Run (Out of scope). Thinking
  is still off for the caller, as decided, and only on Haiku: Opus 5.5 and Sonnet 5.5
  answer it with a 400.
- **`JUDGE_TEMPERATURE` stays:** the 1.x judge still reads it. Claude models get no
  temperature from any caller.
- **The stopped calls are a field too.** `get_test_runs` answers `stopped` (calls, the
  most common error with request and call ids left out when counting, a run to open)
  beside the next step; the MCP adapter's model and the generated client follow.
- Measured the judge's structured answer locally: LiteLLM passes `response_format` to
  Haiku 5.5 and the answer parses.

### Check results

`make check`, run once before the pull request: every step ok except "Plan present and
complete" before this Outcome was written (backend lint, types, tests and coverage, MCP
server tests, frontend lint and types, generated client fresh).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with Retell and the model mocked:
- `run_scenarios` without the model key is refused and stores nothing;
- a judge refused by the model stores "The judge's model call failed: <reason>";
- an agent calling its hang-up ends the conversation after one exchange, it is judged,
  the hang-up is not a default fake, and the run pins version 88 from `get-agent`;
- a conversation that never ends stops at the turn limit and is judged, not an error;
- a platform failure gives `not_tested` with `stopped` and its next step;
- no rule judged with a critical code check is `not_tested`; one rule judged with it is
  `failed`.
Unit tests: Claude gets no temperature, thinking off only on Haiku; tools read from a
single prompt and from a flow; the same error on many calls counts as one.

### Not done

- Dmytro's smoke set again on production, after merge (the plan's last Done-when line).
  It also depends on the Cloud Run settings above.
- Whether Retell's playground reports the chat ended after a hang-up the catch-all
  answers: not checked against Retell; the runner stops either way.
