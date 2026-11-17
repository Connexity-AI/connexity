# Testing: decisions

- **Owner:** Dmytro
- **Slice:** none. Docs only. They are the reference for the roadmap rows that build testing, starting with test cases linked to spec rules.
- **Design:** No UI change. The Tests tab design (prompt 08) still needs an adjustment, which is listed as open.
- **MCP:** None needed. This is documents only. The MCP tools for scenarios and runs come with the rows that build them.

## Goal

The dev session starting on test cases can read how tests work in 2.0 before it plans. Today those decisions exist only in a design conversation. Prompt 08 and the 1.x code both describe tests as cases with their own pass or fail, and that is no longer the direction.

## Changes

- **`docs-internal/testing.md`** (new): the words it uses (scenario, spec rule, rule verdict, code check), then 15 decisions, each with Dmytro's words. Then what is only Proposed: scenario contents, rule verdicts, repeats and flaky rules, code checks on simulated calls, the gate, issues from the gate, and what 1.x code is reused. Then seven open questions.
- **`docs-internal/README.md`:** links the new doc.
- **`designs/08-testing.md`:** one line at the top pointing to the new doc, which wins over the prompt.
- **`REBUILD.md` decision log:** one line for 2026-11-17.

## Decisions

- Everything under "Decided" in `docs-internal/testing.md` is Dmytro's, quoted there (2026-11-16 and 2026-11-17).
- The decisions live in `docs-internal/`, so they win over the prompt, as `work.md` does for prompt 16 (Proposed).
- "Scenario" is the product's word for a test case (Proposed).

## Done when

- `make check` passes.
- Every Decided row quotes Dmytro.
- No committed file links to Notion, quotes Dmytro's private vision, or contains real client names or call data.

## Out of scope

- Any code: reshaping the 1.x test case model, the judge, the runners or the gate.
- The Tests tab design adjustment.
- Notion roadmap rows (updated separately, outside the repo).

## Risks

- Decisions 5, 10 and 14 quote Dmytro's questions, and 13 is a bare "Yes" with the question in brackets. The decisions after them build on them, but a reviewer should confirm they are Decided.
- Decision 12 replaces the 2026-11-11 decision that what the gate runs is customizable.
- Several things a builder will rely on are only Proposed: the three verdicts, faked tools, and how gate issues behave. The first testing plan should settle the ones it touches.

## Outcome

### Deviations from the plan

- After a separate review:
  - `docs-internal/testing.md` gained a "Words" section. In the existing docs, "rule check" means a deterministic check; Dmytro calls those code checks, and here "rule" means a spec rule.
  - Decision 7 no longer says "nothing is person-only"; it keeps the 2026-11-11 rule that shipping a failed version needs the person.
  - Decision 12 says it replaces the 2026-11-11 decision on what the gate runs.
  - Decisions 1, 10 and 13 carry the question they answered.
  - Proposed lines that clashed with existing docs now say what they replace (coverage) or moved to Open (how a gate issue moves through the chain and is resolved, and its issue type).
  - The reuse section is corrected: the 1.x Retell runtime fakes no tools, so faked tool results are new work, and 1.x fields not yet placed are listed.

### Check results

| Step | Result |
|---|---|
| Plan present and complete | ok |
| Start local database | ok |
| Backend lint and format | ok |
| Backend types (pyright) | ok |
| Backend tests and coverage | ok |
| MCP server tests | ok |
| Frontend lint | ok |
| Frontend types | ok |
| Generated client is fresh | ok |

No code changed. The review found no public-repo concerns and no broken links.

### Not done

- The seven open questions in `docs-internal/testing.md`.
