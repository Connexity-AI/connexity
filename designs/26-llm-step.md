# Prompt for Claude Design: spec findings with a moment and a reason

Paste everything below the line into the existing Connexity project in Claude Design. It
changes the **Call** screen (`Connexity Call.dc.html`) and the **Issue** page
(`Connexity Issue.dc.html`) for roadmap 105.16, "LLM approval step for spec findings".
Plan: `plans/2026-11-27-llm-step.md`.

---

Update the single call screen and the issue page, in dark and light, using the existing
design system. Keep everything else on these screens as it is, including how a spec
finding with no moment looks today.

**What changes.** Spec findings (type **Spec rule broken**) are now found in one of
three ways, depending on the rule:

- **By the classifier alone,** as today: no moment in the call, no reason, a
  probability. Nothing changes for these.
- **By the classifier, confirmed by an LLM.** The classifier flags the rule, then an LLM
  reads the call and the rule and confirms it. If the LLM says the rule wasn't broken,
  there is no finding and nothing is shown.
- **By an LLM alone,** for rules the classifier can't judge.

A finding the LLM gave has **a moment and a reason**: the turns the reason rests on,
and one or two plain sentences on why the rule was broken. Rarely, the LLM names no
turn; then the finding has a reason but no moment.

A broken critical rule is Critical, any other a Warning, as today.

## 1. The single call

- **A spec finding with a moment** looks like any finding with a moment: a mark on the
  timeline, its time, and "jump to moment" highlights the turns it rests on. It is
  ordered by time like the others.
- **Its row:**
  - the rule's text;
  - under it, the reason, in normal text;
  - then, in muted text, one of:
    - "Spec rule broken · found by the classifier, 0.91 · confirmed by Claude Haiku
      5.5";
    - "Spec rule broken · found by Claude Haiku 5.5".
- **A finding with a reason but no moment** keeps today's "—" in place of the time and
  no timeline mark, and shows its reason.
- Clicking a spec finding opens its issue, as today.

## 2. The issue page

- **The affected calls list:**
  - A call shows its moment ("at 1:12") when its finding has one, and "—" when not.
  - It shows the finding's reason as a quiet second line, cut to one line.
  - The Probability column stays; it is empty for an LLM-only rule.
- **The line on how it was found** names what the rule uses:
  - classifier only: "Found by a classifier that reads the whole call. It gives no
    moment or reason." (as today);
  - confirmed: "Found by a classifier, confirmed by an LLM that gives the moment and
    the reason.";
  - LLM only: "Found by an LLM that reads the whole call and gives the moment and the
    reason."
- Everything else stays.

Show it with:

- **A call screen** with three findings:
  - a tool-call failure at 0:42;
  - a critical spec finding at 1:12, "On a reschedule, never book a new appointment",
    found by the classifier at 0.93 and confirmed by Claude Haiku 5.5. Reason: "The
    caller asked to move Tuesday's visit, and the agent booked a second appointment
    for Thursday without cancelling the first.";
  - a warning spec finding with no moment, "Ask one question at a time", found by the
    classifier at 0.88.

  The call is Failed.
- **The issue page** for the LLM-only warning rule "On a first call, never say the form
  was just filled out". It has 5 calls, each with a moment and a reason, one with no
  moment.
