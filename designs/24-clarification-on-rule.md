# Prompt for Claude Design: clarifications attached to their rule

Paste everything below the line into the existing Connexity project in Claude Design. It
changes the **Spec tab** of the agent page (`Connexity Agent Profile.dc.html`) and the
**question cards** on Work (`Connexity Work.dc.html`) for roadmap 105.12, "A clarification
is attached to its rule, and checks read both". Plan:
`plans/2026-11-26-clarification-on-rule.md`.

---

Update the agent page's Spec tab and the question cards on Work, in dark and light,
using the existing design system. Keep everything else on both screens as it is.

**What changes.** Until now a person's answer to a question became a new spec rule. Now
a spec rule comes only from the agent's prompt, and an answer is one of two things:

- **A clarification** explains an existing rule: one plain sentence that says where the
  rule's boundary lies ("A voicemail greeting is not an automated call screener; a
  screener asks who is calling before it puts the call through"). It sits under its
  rule. A rule can have several.
- **A prompt gap** is behaviour the prompt does not cover at all. The person's answer is
  kept, and the assistant proposes a prompt change. Once the prompt carries it, the
  rule comes from the prompt and the gap closes.

## 1. The Spec tab

- **A rule with clarifications** shows them under its text, indented, each as one quiet
  line: "Clarified: <sentence>", then in muted text "answered by Alex on Nov 26". Up
  to three show; more fold into "2 more clarifications".
- **A rule from an earlier answer** (made before this change, and waiting for the
  prompt to cover it) reads "From an answer, until the prompt covers it · answered by
  Alex on Nov 18" in place of "From the prompt". It looks like any other rule otherwise.
- **The tiles:** "From clarifications" becomes **"Clarified rules"**: how many rules
  have at least one clarification. Add a quiet **"Prompt gaps"** tile: answers waiting
  for a prompt change. "Open clarifications" stays.

## 2. Question cards on Work

- **A question about a rule** shows that rule above the question, as a small quoted
  line with "About the rule" in muted text. Each answer shows the clarification it
  adds, in muted text under its label ("Adds: A voicemail greeting is not…").
  "Something else" lets the person write the clarification in their own words.
- **A question about a prompt gap** says so above the question: "The prompt doesn't
  cover this". Each answer shows what the prompt would need to say. After it is
  answered, a task "Propose the prompt change: changing appointments" appears in the
  assistant's To do, like any task.
- Everything else about the cards (one at a time, answers sent together after the last
  card) stays.

Show it with: a Spec tab where one Booking rule has two clarifications, one rule from an
earlier answer, and tiles reading 48 rules, 6 clarified rules, 2 prompt gaps, 1 open
clarification; and two Work cards, one about the rule "Never offer a time the
availability tool did not return", one a prompt gap about changing an existing
appointment.
