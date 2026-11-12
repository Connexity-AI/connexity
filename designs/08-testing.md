# Prompt for Claude Design: testing and the gate

Paste everything below the line into the existing Connexity project in Claude Design. It adds a Tests tab to the agent profile from prompt 04.

---

Add a **Tests** tab to the agent profile, in dark and light, using the existing design system, page bar and tabs: Overview, Issues, Spec, **Tests**. The tab label shows coverage: "Tests 86%".

## Context

Testing happens before a version reaches real callers, and it follows one strict chain: **production issues → spec → test cases → tests.** An issue found on real calls becomes a rule in the spec; every rule gets test cases; a test is one run of a test case. Nothing skips a step: a test always proves a rule, never an issue directly.

Tests run at three levels:
- **Text:** a simulated caller talks to the agent in text. Every test case, every version.
- **Audio:** a simulated caller talks to the agent's real voice stack over a web call. Speech recognition, latency, interruptions, real tools in a test environment.
- **Phone:** a few real phone calls to the agent's number before a release, to prove the phone path works.

Every new agent version passes through the **gate**: its tests run, and the version is either Verified or Failed. A failed version can still ship, but only when a person decides it (directly or through their AI assistant), like a force push, and every such override is recorded with who and why.

## The Tests tab

1. **Number tiles:** Coverage 86% (shown as "114 of 132 rules"), Test cases 240, Passing 97%, Flaky 4, Version 15 Failed.
2. **Versions:** a compact list, newest first, one row per version with its gate result:
   - "Version 15 · Failed · 3 rules failing · today"
   - "Version 14 · Verified · live since 6 Nov"
   - "Version 13 · Shipped despite failure by Alex through the assistant, 2 Nov · 'Holiday hours had to go live'"
   - Rows are quiet except Failed and overrides, which stand out. An override always shows who, when and the reason.
3. **Latest run** of the selected version: one row per level, Text, Audio and Phone, each with passed, failed and flaky counts and its duration. A level that is not set up for this agent shows "Not set up" in muted text.
4. **Failing rules first,** grouped by the fixed categories (prompt 06), each group collapsed to its name and count. Inside, one row per rule: the rule in one plain sentence, the level it failed at, and "Passed 2 of 5 runs". Expanding a rule shows its test cases, each with its result and a link to the simulated call, which opens like any call.
5. **The chain on every row:** a rule shows where it came from ("From the issue 'Transfers that drop the call', 2 Nov" or "From the prompt"); a test case shows the rule it proves. The person can always trace a test back to the issue that started it.
6. **Rules without tests:** a collapsed section, grouped by category with counts: the gap in coverage.
7. **Run tests:** a small button in the tab's top right that runs the tests for a version on demand, with a menu to pick the levels. Everything here can also be done by the assistant through MCP.

Read only otherwise: no editing of test cases on screen; the assistant writes them.

Placeholder agents: Insurance renewals, Restaurant reservations, Car service booking, Clinic after-hours, Dental reception. All numbers and names are placeholders.
