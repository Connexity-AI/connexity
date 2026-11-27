# Prompt for Claude Design: false positives and dismissed flags

Paste everything below the line into the existing Connexity project in Claude Design. It
changes the **Issue** page (`Connexity Issue.dc.html`) for roadmap 105.17, "The assistant
resolves a doubtful finding with the person". Plan: `plans/2026-11-27-false-positives.md`.
The second prompt is the fix Dmytro ran on the first export.

---

Update the issue page, in dark and light, using the existing design system. Keep
everything else on the page as it is. The single call screen does not change.

**What changes.** A finding can now be marked as a false positive, by the assistant or
by a person. A marked finding disappears from its call and stops counting in the score.
It is kept, and anyone can bring it back. Separately, for some spec rules a classifier
flags a call and an LLM then confirms or dismisses the flag; a dismissed flag never
became a finding. Both kinds are shown on the issue page, so a wrong marking or a wrong
dismissal can be seen and undone. Nothing is shown anywhere else.

## 1. The summary line

- Near the issue's size (calls affected, first and last seen), one quiet line:
  "8 findings marked as false positives · 2 flags dismissed by the model".
- Each half shows only when its number is above zero. With both at zero, there is no
  line and no empty section.
- Clicking the line opens the list below.

## 2. The list

- One list on the issue page, below the affected calls, titled "Not counted" and
  collapsed by default. Its rows load only when it is opened, so show a short loading
  state inside it. It has two groups, each with its own heading and count.
- "Marked as false positives". Each row:
  - the call (its date and time, linking to the call), and the moment in the call when
    the finding had one;
  - who marked it and when: a person's name, or the assistant's name;
  - the reason, one line;
  - when it rests on a clarification, a quiet line: "Rests on: Clarified: <sentence>";
  - when the person's approval was needed, a quiet line: "Approved by <name>";
  - an Undo action.
- "Dismissed by the model". Each row:
  - the call, as above;
  - "Dismissed by Claude Haiku 5.5", and the classifier's probability that raised the
    flag;
  - the model's reason, one line;
  - a "Bring back" action.
- Undo and Bring back ask once before acting, in one sentence: "This finding will show
  on its call again and count in the score."
- Rows are newest first. Past ten in a group, the rest sit behind "Show all".

## 3. What the rest of the page counts

- The affected calls list, the calls-affected number and the chart leave out findings
  marked as false positives.
- When every finding of an issue is marked, the affected calls list says: "No calls
  affected now." The list of markings stays.

Show it with:

- The issue page for the critical spec rule "Whenever the agent tells a caller someone
  will call them back, notify the technician first". It has one clarification
  ("Telling the caller the technician will call about 30 minutes before the appointment
  is a notice, not a callback promise", answered by Alex on Nov 27). 1 call affected. 8
  findings marked as false positives by the assistant "Claude Code" on Nov 27, each
  resting on that clarification and approved by Alex. 2 flags dismissed by the model.
  The list open.
- The same page with the list closed.
- An issue from a code check ("Tool call failed") with 1 finding marked as a false
  positive by Alex, with a reason and no clarification, and nothing dismissed by a
  model.
- An issue where every finding is marked: "No calls affected now."

---

Two fixes to the issue page's "Not counted" list. Change nothing else.

1. Loading state. The list's rows load only when it is opened. Between opening it and
   the rows arriving, show one quiet line inside the open list, in place of the groups:
   "Loading…". Show it with the critical callback issue, list just opened.

2. Probabilities of dismissed flags. A flag reaches the model only when the classifier
   scored it 0.80 or above, so a dismissed flag's probability is always 0.80 or higher.
   In the critical callback issue, change the two dismissed flags from 0.71 and 0.64 to
   0.86 and 0.81.
