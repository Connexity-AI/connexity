# Metrics

How Connexity measures what it shows as numbers. Each measure works the same for every
provider, because it is read from the call's trace, not from what a platform reports.

## Latency (basic, 2026-11-14)

A basic first measure, to be made more useful later (Dmytro, 2026-11-14: "do basic
latency and we will work on it in future to make it more useful").

- **A reply gap** is the time from the end of a caller's turn to the start of the agent's
  next turn, read from the turns' start and end times.
- **Not a gap:** an agent turn that starts before the caller has finished (talking over,
  or the caller's "yeah" while the agent speaks), and a caller turn the agent never
  answers.
- **A call's latency** is the median of its reply gaps. A call with no gap has none.
- **An agent's latency** for a period is the average of its calls' latencies. The page
  says how many calls that covers.
- **Per day:** the average of that day's calls' latencies.

Code: `backend/app/crud/latency.py`. It is worked out when asked for, from the stored
turns; nothing is stored per call yet.

Not measured yet: the platform's own reported latency (Retell keeps one in the call's
extensions), time to first word, tool-call waits, and a goal to compare against.

## Score (basic, 2026-11-18)

How an agent, or a whole workspace, did on its checked calls in a period (7, 30 or 90
days). A basic formula for now, to be replaced (Dmytro, 2026-11-18: "we can do very basic
score formula for now to not hardcode it and later devise something better"; "formula
ok"). It lives in one function, `score_of` in `backend/app/services/score.py`.

    score = 100 × (1 − (failed + 0.5 × degraded) / checked calls), rounded

- **Checked calls** are calls with a result other than unchecked, counted as the Calls
  page counts them. No checked call: no score, never 100 by default.
- **Archived issues** are hidden on every call (2026-11-14), so archiving lifts the score
  for the whole period and unarchiving lowers it back.
- **Its change** is against the previous period of the same length.
- **What moves it:** for each issue, how much the score would rise if its findings were
  gone from every call; the five that cost most, worst first.
- **Shown only once onboarding is complete** (every Readiness step done). Readiness never
  changes it.
- **Only fixes and improvements should raise it.** One gap in the basic formula:
  turning a check off, or down to "flags", raises the score of later calls although it
  fixes nothing. It is recorded as a decision and never changes past calls.
- **Where:** `get_agent` (the agent's score, change and what moves it), `list_agents`
  (each agent's score and change) and `list_workspaces` (each workspace's score and
  change over 30 days). The Dashboard (10.191) shows it on screen.
