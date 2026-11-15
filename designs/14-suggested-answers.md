# Prompt for Claude Design: suggested answers, confirmed in a batch

Paste everything below the line into the existing Connexity project in Claude Design. It
changes the **Action items** screen (`Connexity Action items.dc.html`) for roadmap
10.123.

---

Update the Action items screen, in dark and light, using the existing design system.
Keep the page bar, the tiles, the list of clarification cards, and the Answered and
Parked sections as they are.

## Context

When the assistant raises a clarification, it can also suggest an answer: the letter it
would pick, one plain sentence on why, and whether it is confident. A suggestion is not
an answer. Nothing goes into the agent's spec until the person confirms it. The person
confirms the confident ones in one batch, and decides the rest themselves.

## 1. A batch of confident suggestions, at the top of the list

Above the cards, a compact panel when any open clarification has a confident
suggestion:

- **One line:** "Your assistant suggests answers for 6 questions it is confident about."
  The muted line under it: "Check them, then confirm. Each becomes a rule in its
  agent's spec."
- **The suggestions** in a compact list, one row each:
  - a checkbox, ticked by default;
  - the agent's name in muted text;
  - the question in one line, truncated, with the full text on hover;
  - the suggested answer's label in medium weight;
  - under it, in muted text, the rule it writes and the assistant's why: "Never change
    an existing appointment · The prompt lists booking and cancelling only."
- **A primary button** "Confirm 6 answers" (the count follows the ticks), and a quiet
  "Review one by one" that collapses the panel. The suggestions then stay on their cards.
- **After confirming,** the panel goes, the confirmed questions move to Answered, and a
  short muted line says "6 answers confirmed · added to 2 agents' specs".
- **More than 10 suggestions:** show 10, then "and 14 more", which shows the rest in the
  same list. The person never has to open cards one by one to confirm a batch.

## 2. A suggestion on a card

A card whose question has a suggestion that is not confident, or one taken out of the
batch:

- **Above the answer buttons,** one muted line: "Your assistant suggests b: Only when the
  caller asks · not sure: the prompt says nothing about changes."
- **The suggested answer's button** has a subtle outline in the accent colour and a small
  "Suggested" label. Picking it, or any other answer, opens the same confirm as before.

## 3. Answered by whom

An answer confirmed from a suggestion reads, in Answered, "Answered by Dmytro, suggested
by your assistant, 15 Nov". On the agent's Spec tab, the rule's source line stays "From a
clarification, answered by Dmytro on 15 Nov".

## 4. No suggestions

With no suggestions, the screen is exactly as it is today: no empty panel.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking,
Clinic after-hours, Dental reception. All numbers and names are placeholders.
