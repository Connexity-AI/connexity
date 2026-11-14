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
