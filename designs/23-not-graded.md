# Prompt for Claude Design: calls that are not graded

Paste everything below the line into the existing Connexity project in Claude Design. It
changes the **Call** screen (`Connexity Call.dc.html`) and the **Calls** list
(`Connexity Calls.dc.html`) for roadmap 105.11, "A call must qualify before it is judged
against the spec". Plan: `plans/2026-11-26-call-must-qualify.md`.

---

Update the single call screen and the calls list, in dark and light, using the existing
design system. Keep everything else on both screens as it is.

**What changes.** A call where the agent spoke fewer than 10 words is not graded: it is
never judged against the agent's spec, and it does not count in the score, so it cannot
make an agent look better than it is. Nearly four in ten real calls are like this
(voicemail greetings cut off, hang-ups after the first line), so this result is common
and should look calm, not alarming.

Today a call's result is one of Failed, Degraded, Clean or Unchecked. Add a fifth,
**Not graded**:

- A short call with nothing found reads **Not graded**, in the same quiet, neutral style
  as Unchecked (not the clean green, because it did not pass anything).
- A short call where a check did find something (a tool failed) keeps **Failed** or
  **Degraded**, because that failure is real and counts. It still says it was not judged
  against the spec (below).

## 1. The single call

- **The result label** next to the call's title shows "Not graded" for a short call with
  nothing found.
- **One short explainer line** on every call under the floor, whatever its result, near
  the result and above the findings: "Not graded: the agent spoke fewer than 10 words.
  It isn't judged against the spec and doesn't count in the score." Quiet text with a
  small info icon, no banner colour, no button.
- On a short call that Failed, the line reads the same; the failed finding shows as it
  does today.

## 2. The calls list

- **The Result column** shows "Not graded" for those calls, in the neutral style.
- **The result filter** gains "Not graded", after Clean and before Unchecked.
- **The tiles** above the list count Not graded calls too, as their own quiet tile next
  to Unchecked, so the numbers still add up to the total.

Show it with: a call screen for a 4-second voicemail where the agent said "Hi, this is
Sam from" (5 words) and nothing was found; a call screen for a 6-second call where the
agent said 3 words and a tool call failed (Failed, with the explainer line); and the
calls list over 30 days with 120 calls: 6 Failed, 14 Degraded, 52 Clean, 46 Not graded,
2 Unchecked.
