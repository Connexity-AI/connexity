# Prompt for Claude Design: spec findings

Paste everything below the line into the existing Connexity project in Claude Design. It
changes the **Call** screen (`Connexity Call.dc.html`), the **Issue** page
(`Connexity Issue.dc.html`) and the **Issues** list (`Connexity Issues.dc.html`) for
roadmap 105.15, "Spec check: every call judged against the agent's spec". Plan:
`plans/2026-11-26-spec-check.md`.

---

Update the single call screen, the issue page and the issues list, in dark and light,
using the existing design system. Keep everything else on these screens as it is.

**What changes.** Connexity now judges every real call against its agent's spec. A
classifier answers one yes or no question per rule: "did the agent break this rule in
this call?" A "yes" at 0.8 probability or above becomes a finding of the type **Spec
rule broken**. All findings for one rule on one agent make one issue.

Two things make these findings different from today's:

- **No moment in the call and no reason.** The classifier says only that the rule was
  broken somewhere in the call, with a probability. It doesn't say where or why. Show
  this honestly; never point at a turn the classifier didn't name.
- **The rule is the title.** The issue is named by the spec rule it is about, e.g.
  "Never offer a time the availability tool did not return".

A broken **critical** rule fails the call (Critical, as today's critical findings). Any
other rule is a Warning.

## 1. The single call

- **A spec finding sits in the findings list** with the others, in the same row style.
  Its text is the rule. Under it, in muted text: "Spec rule broken · no moment in the
  call · found by the classifier, 0.93".
- It has **no "jump to moment" link** and no highlight in the transcript. Put spec
  findings after the findings that have a moment, within their severity.
- Clicking it opens its issue, as other findings do.

## 2. The issue page

- **Title:** the rule's text. **Type line:** "Spec rule broken", with the rule's
  category and Critical or Warning as today.
- **Under the title, the rule's clarifications,** each as one quiet line: "Clarified:
  <sentence>", answered by whom and when (the same style as the Spec tab). None when the
  rule has none.
- **One quiet line** where today's issues explain how they were found: "Found by a
  classifier that reads the whole call. It gives no moment or reason."
- **The calls list** shows each call's probability in place of a moment ("0.91").
- Everything else (state, archive, mark fixed, size, first and last seen) stays.

## 3. The issues list

- A spec issue's row shows the rule's text as its title and "Spec rule broken" as its
  type, like any other issue type. Nothing else changes.

Show it with:

- **A call screen** with two findings: a tool-call failure at 0:42, and a critical spec
  finding "Book only after the address and zip code are provided", found by the
  classifier at 0.95. The call is Failed.
- **The issue page** for the warning rule "Ask one question at a time". It has one
  clarification ("An either/or question is one question", answered by Alex on Nov 26)
  and 7 calls, at probabilities from 0.81 to 0.94.
- **The issues list** with that issue among two code-found ones.
