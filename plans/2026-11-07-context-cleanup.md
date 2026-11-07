# Context clean-up: design first, a thinner CLAUDE.md, and no `Connexity 2.0.md`

- **Owner:** Dmytro
- **Slice:** none (how we work)
- **Design:** No UI change.
- **MCP:** None needed: documents only.

## Goal

Make the design the place every UI change starts, and keep it current. Today a session
can change a screen straight in code, so any design drifts behind what is built. After
this merges, every session knows that a change to what a person sees is made in Claude
Design first, approved there, and only then built, and that the design is never allowed
to fall behind.

Also: make the root `CLAUDE.md` short. It repeated much of the lifecycle guide, and its
description of the product ("system of record and independent verifier") was Claude's
framing, not Dmytro's. After this merges it opens with the goal Dmytro set in his vision
on 2026-11-07, keeps one line per rule, and points to the lifecycle guide for the rest.

And: delete `Connexity 2.0.md`. It repeated what `REBUILD.md`, the lifecycle guide and
the design docs say. What only it said moves to the file whose job it is, so nothing a
session needs is lost.

Documents only. No code changes.

## Changes

- **The lifecycle guide** (`docs-internal/development-lifecycle.md`) gains a subsection in
  the slice loop, "UI: the design comes first, and stays current", and the Plan step
  points to it.
- **`CLAUDE.md`** gains a rule: UI changes start in the design (rule 9 in the final list).
- **The plan template** gains a "Design" line: the artifact and the approved version, or
  "No UI change".
- **`REBUILD.md`** records the decisions.
- **`CLAUDE.md` is rewritten short:**
  - It opens with the goal: an AI assistant runs operations for an entire fleet of
    conversational AI agents, with people approving where it matters, and Connexity as
    the framework that equips it. "System of record and independent verifier" is gone.
  - The rules are one line each, with the lifecycle section that explains them.
  - The hooks section, the "what to run before committing" section and the Git section
    are gone; the lifecycle guide covers them.
- **The lifecycle guide gains what only `CLAUDE.md` said:** checks grow only when Dmytro
  asks (section 6), the full public-repo rule (section 6), the reminder hook in the table
  of gates (section 5), where personal settings go (section 8), and a new section 10,
  "How a session talks to Dmytro".

- **`Connexity 2.0.md` is deleted.** Its content goes:

  | Section | Goes to |
  |---|---|
  | 7, checks, findings, issues and incidents | New `docs-internal/checks-and-incidents.md`, as written |
  | 4 no chat, 8 skills and CRM attached to an agent, 16 what it is not | Lifecycle section 6, "What Connexity does not build" |
  | 9 provider strategy, 13 the ladder | `REBUILD.md` ground rules |
  | 5 bypass detection, 6 spec, 10 client feedback, 11 dispatch, 12 incident response, 13 onboarding | `REBUILD.md` phase outlines, condensed |
  | 18 open questions | `REBUILD.md` section 8, as P1 to P7 (question 6 was already answered) |
  | 2 case study | Dmytro's private `Vision.md`, not committed |
  | 1 idea, 3 roles, 14 working on an agent, 15 UI structure, 17 moat | Dropped: the goal in `CLAUDE.md` replaces 1 and 17; 3, 14 and 15 are covered by the lifecycle guide and the phase outlines |

- Every "§N" reference in `REBUILD.md`, the lifecycle guide, `CLAUDE.md`, `README.md` and
  the checks package docstring points at the new place. Closed plans in `plans/` keep
  their references as history.

- **The roadmap is paused.** `REBUILD.md` keeps every built slice, its write-up and
  what it left open. The slices not started (1.3b, 1.6, 1.7, 1.8, 2.4, 2.5), the
  postponed items, the Milestone 1 exit review and the Phase 3 to 6 outlines move to a
  new section 7, "Parked ideas (not a plan)". The status table lists only what is built.
- The unapproved 2.4 plan draft is kept in `plans/drafts/`, which the plan check
  ignores, and `plans/README.md` says so.

- **Every feature ships with its MCP tools.** A new bullet in lifecycle section 6, rule 10
  in `CLAUDE.md` (later rules renumber), and an "MCP" line in the plan template. The gap
  today (built features with no MCP tools) is listed in `REBUILD.md` status as open.

- **Connexity's own AI is narrowed, not banned.** Lifecycle section 6 now rules out AI
  that writes the agent's content or acts like an agent, and lists metrics and insights
  among the artifacts the product's own models may produce.

## Decisions

Made by Dmytro on 2026-11-07:

- Any UI change, suggested by him or by the session, is made in the design first. A hard
  requirement ("if we want to add or adjust we need to do first in design").
- The design is always kept current, whatever happens during building.
- The design lives in Claude as Design artifacts, not on the standalone site that closes
  on 2026-12-14, and is split into several files so no single file has to be re-uploaded
  by hand.
- The design system is created in its own session, which he will lead.
- `CLAUDE.md` should be thinner, refer to the lifecycle guide rather than repeat it, and
  describe the product the way his vision now does, not as "system of record and
  independent verifier" ("its generate by claude, i want it to focus on what we just did
  in vision").
- `Connexity 2.0.md` is dropped and anything essential moves into other files ("can we
  drop it and if there is anything essential move it in other mds"). The case study may
  go private ("its ok to go private"). Notion is out of scope ("lets ignore notion").
- Every feature ships with MCP, so everything on the platform can be done through
  ChatGPT or Claude ("we need to make sure with every feature we build MCP so
  EVERYTHING can be done through chatgpt/claude whats on connexity platform"). A
  critical rule.
- Connexity uses AI for metrics, evals and insights, "but never in the appearance of
  agent". Insights probably come from Connexity; settled during development.
- Keep everything that is built and leave the planned work behind; he switches to
  design first and rewrites the roadmap later ("keep everything thats built but we will
  go away from what's done now"). The later plans become parked ideas, and the 2.4 draft
  is kept.

Proposed by Claude, not separately confirmed:

- When building shows the design must change, the session stops, changes the design, and
  gets it approved again before changing the code.
- One file per screen or component, plus shared files for colours, spacing and type.

Open:

- Whether UI work waits for the design system, or starts designs without it and moves
  them onto it afterwards.

## Done when

- The lifecycle guide, `CLAUDE.md` and the plan template say the same thing, and a new
  session reading `CLAUDE.md` alone learns the rule.
- Every rule the old `CLAUDE.md` stated is still stated, in `CLAUDE.md`'s short list or
  in the lifecycle guide.
- The decision log has the two decisions in Dmytro's words.
- No file outside `plans/` and the decision-log history links to `Connexity 2.0.md`.
- `make check` passes.

## Out of scope

- Notion.
- Rewriting closed plans that cite vision sections.
- Creating the design system or any design.
- A mechanical check that a UI change has a design. For now it is a rule; it can become
  a hook later.

## Risks

- **It is a rule, not a gate.** Nothing stops a session from changing a screen without a
  design except the rule itself. The lifecycle guide says rules that matter should become
  checks; this one does not have a check yet.
- **UI work may stall** until the design system exists, depending on the open question.
- **Something is lost in the move.** Mitigation: the table above names a home for every
  section, and the dropped ones are listed with the reason.

## Outcome

### Deviations from the plan

- The plan started as "design first" and widened in the same session, at Dmytro's
  request, to the thinner `CLAUDE.md` and the removal of `Connexity 2.0.md`. The file was
  renamed from `2026-11-07-design-first.md`. Pausing the roadmap was added the same
  way.

### Check results

`make check` on this branch: every step passed in one run.

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 1s |
| Backend types (pyright) | ok | 30s |
| Backend tests and coverage | ok | 267s |
| MCP server tests | ok | 9s |
| Frontend lint | ok | 4s |
| Frontend types | ok | 4s |
| Generated client is fresh | ok | 24s |

`/code-review` was not run: no code changed beyond one docstring.

### Not done

- No hook enforces the rule yet.
