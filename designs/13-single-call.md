# Prompt for Claude Design: the single call, ready to build

Paste everything below the line into the existing Connexity project in Claude Design. It
brings the **Call** screen (`Connexity Call.dc.html`) up to date for its build (roadmap
10.08). It includes `12-adjustments.md` item 25 (tool calls inline), which the 2026-11-12
export does not show yet, so item 25 does not need pasting separately for this screen.

---

Update the single call screen, in dark and light, using the existing design system. Keep
the page bar, the findings list and the read-only nature as they are. Three changes:

## 1. A speech timeline instead of the waveform

The recording player keeps its full width, play and pause, the time, and seeking by
clicking. Replace the waveform with a **speech timeline**: who was speaking when.

- **Two thin lanes** across the full width: **Agent** on top, **Caller** below, each a
  row of rounded bars where that party spoke. The agent's bars are the ink colour at low
  contrast and the caller's a little lighter, so they are told apart without colour
  meaning anything. Silence is empty track.
- **The played part** is slightly stronger than what is still to come, and a thin
  vertical playhead runs across both lanes.
- **Flagged moments** stay as marks above the lanes: critical ones prominent in the
  critical colour, warnings quiet. Clicking a mark jumps the audio and the transcript.
- **Tool calls** get a small, muted tick between the lanes at their moment (see 2).
  Clicking a tick jumps there.
- **Labels:** the start time ("0:00") and the length ("4:58") at the ends; nothing else.
- **When the recording is unavailable** (deleted, or not stored by the voice platform),
  the timeline still shows from the transcript, with one quiet line where the controls
  were: "Recording unavailable". The transcript still jumps and highlights by time.

## 2. Tool calls inline in the transcript

This is `12-adjustments.md` item 25, shown on this screen:

- **Every tool call appears in the transcript at its moment** as one compact, muted line
  between the turns: a small tool icon, the tool's name, its status and duration
  ("schedule_appointment · ok · 820 ms"). A failed or timed-out one reads in the critical
  colour ("transfer · failed · 3.1 s").
- **Collapsed by default.** Clicking the line expands it in place to show the
  **arguments** and the **result**, each as monospace key-value text. Long values wrap;
  very long ones show the first lines and "Show all". Secret values show as "••••".
- **When the tool ran an n8n workflow,** the expanded block ends with one quiet line,
  "Workflow: quote-lookup v7 · 9 steps", without the workflow's steps.
- **A finding on a tool call** shows on that line, as findings do on a turn.

## 3. Findings say how they were found

Each finding, in the list under the player and inline in the transcript, adds a quiet
"Found by a rule" or "Found by a model" after its category. People always want to know
which.

Show it with a booking call: a booking tool call that succeeded, then a second identical
one flagged "Two bookings for one slot · Booking · Found by a rule"; and one call whose
recording is unavailable.
