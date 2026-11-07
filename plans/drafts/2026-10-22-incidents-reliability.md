# Incidents and reliability

> **Draft, never approved, parked (2026-11-07).** Written for slice 2.4 before the
> roadmap was paused. It is kept for reference, not as a plan. If incidents come back,
> they are planned again from the design.

- **Owner:** Dmytro
- **Slice:** 2.4

## Goal

Slice 2.3 groups what is wrong with calls into issues and gives each call a status. What
it cannot say is when an issue was hurting real calls, who closed it and why, or what an
agent's reliability is. After this merges:

- every failed real call belongs to an incident that a person can review and close, with
  a cause and what was done written down;
- an agent's reliability and quality can be read per period and per agent version, and a
  figure can be explained by listing the incidents behind it.

The model is in the vision, section 7.

## Changes

**Incidents**

- A new record, the incident. It belongs to one issue and holds: when it opened, when it
  was closed and by whom, the reason for closing, and three texts a person writes: the
  cause, what was done, and the version that carried the fix. A recurrence points to the
  incident before it on the same issue.
- **Opening.** The first failed real call of an issue that has no open incident opens
  one. A failed call is one with a finding whose effect was "fails the call" when it was
  raised. A real call is one whose source is production.
- **Joining.** Later failed real calls of that issue join the open incident. A failing
  call that started before a close joins the closed incident without reopening it.
- **Two issues on one call.** The call belongs to both incidents.
- **Closing.** Only a person closes an incident, and a reason is required. Closing is a
  decision record. Nothing closes an incident on its own.
- **Recurrence.** A failed real call that started after a close opens a new incident on
  the same issue, marked as a recurrence of the previous one.
- **Not counted.** Findings raised by running a check over calls stored before it existed
  (marked retroactive since slice 2.3) open no incident. They stay visible on the issue.
- **An accepted issue still opens incidents.** Accepting means "known", not "harmless";
  to stop an issue failing calls, the check's setting is the place.
- **Derived when read, not stored:** the calls affected, the distinct callers, the agent
  versions involved, time to detect, how long it was open, and what changed just before
  it started (the component versions on the first failed call compared with those on the
  last call before it that did not fail).
- **Calls already stored** that failed get their incidents when the migration runs.

**Reliability**

- Per agent, over a period, grouped by day or by agent version: calls counted; failed,
  degraded, clean and unchecked; reliability (the share not failed) and quality (the
  share clean); and the incidents behind the failed calls.
- **Left out of the count:** calls whose end reason is "no answer" or "voicemail", calls
  where the caller never spoke, and calls that are not real. Unchecked calls are left out
  of both shares and shown as their own number.
- **"Per version" means the agent's version number**, as the provider reports it. A call
  with no version number is grouped as "unknown".
- **The past stays as it was reported.** A finding keeps the effect it had when it was
  raised, so changing a check's setting later changes no past figure, and retroactive
  findings do not count.
- **Marks.** Every change to a check's setting and every new version of a check inside the
  period is returned with the figures, for slice 2.5 to draw on the chart.

**API**

- List an agent's incidents, open or closed.
- Read one incident: its calls, its timeline, and what changed before it started.
- Close an incident, with a reason.
- Write an incident's cause, what was done, and the fix version.
- Read an agent's reliability for a period, by day or by version.

No screens. They are slice 2.5.

## Decisions

Made by Dmytro on 2026-10-22:

- Retroactive findings open no incident and do not count in reliability.
- An accepted issue's failing calls still open incidents.
- Reliability leaves out calls with end reason "no answer" or "voicemail", and calls
  where the caller never spoke. Unchecked calls are left out and shown on their own.
- "Per version" is the agent's version number. Dmytro asked why anything more complicated
  was needed; grouping by content fingerprint was dropped.

Open, to be discussed separately:

- How an issue's state and its incidents relate: whether resolving an issue should close
  its open incident, or closing an incident should offer to resolve the issue. In this
  slice they are independent: neither changes the other.

## Done when

Played through the API against the running local server, with invented calls on a
throwaway agent:

- Every failed real call is in at least one incident.
- An incident stays open until a person closes it; closing without a reason is refused.
- A failed call that started after the close opens a new incident marked as a
  recurrence; a failed call that started before the close and arrives late joins the
  closed incident and does not reopen it.
- A call failing for two issues is in both incidents and counted once in reliability.
- A test call, a call with no answer, a voicemail and a call where the caller never spoke
  are left out of reliability; an unchecked call is counted on its own line.
- Changing a check's setting does not change reliability for calls before the change,
  and the change appears as a mark.
- For a period, the number of failed calls equals the number of distinct calls across
  the incidents behind it.
- Another company cannot read or close an incident.

Then on Dmytro's machine, counts only: the stored real calls give their reliability and
incidents.

`make check` passes.

## Out of scope

- Screens (slice 2.5).
- Any link between an issue's state and its incidents (to be discussed).
- Closing incidents automatically, or a queue of incidents that look fixed.
- Alerting, the inbox, tools for the assistant.
- Latency (Q9), and any new check.

## Risks

- **The connected agents have no failed calls**, so the real-call run will show 100% and
  no incidents. The behaviour is proven on invented calls only, until the fault agent is
  set up.
- **"The caller never spoke" depends on speech-to-text.** A caller drowned out by noise
  is left out of the count, which can hide a broken line.
- **Version numbers are the provider's.** Retell raises the number on every republish,
  even with nothing changed, so two numbers can mean the same agent. Accepted for
  simplicity.
- **What changed before an incident** compares only what Connexity recorded: agent
  settings, prompt, model and workflows that ran. A change elsewhere looks like "nothing
  changed".
- **A reviewer should push back if** an incident that only a person can close will pile
  up unread without an inbox, or if leaving out silent calls hides real failures.

## Outcome

### Deviations from the plan

<!-- filled in after the work -->

### Check results

<!-- filled in after the work -->

### Not done

<!-- filled in after the work -->
