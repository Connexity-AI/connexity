# Designs

Prompts written for Claude Design, where Dmytro designs the web app's screens, and the
table of who does what. They are reference for the sessions that build each feature;
the screens themselves live in Claude Design.

- **Numbered prompts (`01-` to `12-`)** were pasted into Claude Design in order. Each
  later prompt changes earlier ones, so read a screen's prompts in order: a later prompt
  wins. `12-adjustments.md` holds many small numbered changes across the app; a later
  item wins over an earlier one.
- **`who-does-what.md`** is the job-by-job split between Connexity, the assistant and the
  person. Its short form is [`docs-internal/responsibilities.md`](../docs-internal/responsibilities.md).

## Screens

`screens/` is an export of the Connexity project from Claude Design (HTML, one file per
page, plus `support.js`, the runtime they need). Open a page in a browser, or read its
markup. Pages link to each other by file name, so keep the names as they are. For how a
screen looks, the exported page wins over the prompts that produced it.

| Page | What it shows | Roadmap |
|---|---|---|
| `Connexity Design System.dc.html` | Tokens, type, components | Every UI feature |
| `Connexity Sidebar.dc.html` | The app shell: sidebar, profile menu, workspace picker | Milestone 1 |
| `Connexity Onboarding.dc.html` | Readiness as the first screen after sign-up | Milestone 1 |
| `Connexity Readiness Bar.dc.html` | The Readiness stripe and ring | Milestones 1 and 5 |
| `Connexity Calls.dc.html`, `Connexity Call.dc.html` | The calls list and a single call | Milestone 1 |
| `Connexity Agents.dc.html` | The agents list | Milestones 1 and 2 |
| `Connexity Agent Profile.dc.html` | The agent page and its tabs (`... v1` is an older version; ignore it) | Milestones 2 and 6 |
| `Connexity Action items.dc.html` | Clarifications and other items that need a person | Milestone 2 |
| `Connexity Issues.dc.html`, `Connexity Issue.dc.html` | The issues list and a single issue | Milestones 3 and 4 |
| `Connexity Incidents.dc.html`, `Connexity Incident.dc.html` | Incidents and the Playbook | Milestone 5 (Playbook later) |
| `Connexity Settings.dc.html` | Workspace settings | Milestones 7, 8 and 10 |
| `Connexity Account.dc.html`, `Connexity Agency.dc.html` | Personal settings, agency settings and billing | Milestone 9 |
| `Connexity Home.dc.html` | Home | Milestone 10 |
| `Connexity Roadmap.dc.html` | The roadmap page | Not scheduled |
| `Connexity.dc.html` | The whole project on one canvas | Reference |

The export is a snapshot (2026-11-13). When Dmytro changes a screen in Claude Design, he
exports again and the files here are replaced in a pull request. A feature's plan names
the page and the export date it was built against.

## Which source wins

Where a prompt and a document in `docs-internal/`, `CLAUDE.md` or `REBUILD.md`
disagree, the document wins and the prompt is history. For example, prompt 03 says the
spec is created on connection; the assistant now writes it as a Readiness step.

A build shows only what works (`CLAUDE.md` rule 14): prompts describe the whole vision,
and a feature builds only its part. All names and numbers in the prompts are
placeholders.
