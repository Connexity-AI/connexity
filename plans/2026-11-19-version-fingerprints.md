# Version fingerprints and verified state

- **Owner:** Dmytro
- **Slice:** Demo milestone, roadmap feature "Version fingerprints and verified state"
  (10.1996). Builds on `run.version_fingerprint` (10.1293), the Tests tab's verdict
  (10.196) and its fix (10.1991, PR #244); this branch starts once #244 merges.
- **Design:** No UI change (Decided): the reason reaches the assistant through MCP.
- **MCP:** `get_test_runs` says what content a verdict covers and why a version is not
  verified (edited since its full run). Its rules, next steps and `contract.py`
  descriptions follow. No new tool: verifying a candidate is 10.1997.

## Goal

A version is its number and its content. On Retell an unpublished version is edited in
place under the same number, and the same content can sit under two numbers. Today the
verdict reads the latest full run of a version number and ignores what that run
tested (10.196 dropped the "edited" grouping). So a draft edited after its full run
still reads Verified. After this merges, Verified belongs to the content that passed:
a version is Verified only while its content is the content a full run verified, and a
version with content that already passed is Verified too.

## Decisions

### In the roadmap row

- A version's fingerprint covers everything that was tested: prompt, flow, tools and
  settings. "A fingerprint that passed its tests is Verified."
- Moved into Demo by Dmytro, 2026-11-19, with the gate features ("lets move those to
  current development so we fix it for good").

### Decided while planning (Dmytro, 2026-11-19)

- A version's current content is the fingerprint of its **newest run**: no extra Retell
  reads; an edit shows once something runs on it again (the gate reads Retell fresh).
- **The same content under another number is Verified**, "same content as version 88,
  verified 19 Nov".
- **No change on screen** in this PR: backend and MCP only, as the row says; the tile
  shows the verdict as today.

### Already built

- Each run stores the fingerprint of the content it tested (`run.version_fingerprint`,
  read from Retell when the run starts). It leaves out version numbers, titles,
  timestamps and the published flag, so the same content under two numbers has the same
  fingerprint.

## Changes

### Every run knows its content

- `run_scenarios` stores the fingerprint it reads with the version before storing the
  run (since 10.1991, when no version is given). For a version the assistant names, the
  run's own read at its start stores it, as today.

### Verified belongs to the content

- **A version's current content** is the fingerprint of its newest run.
- **Its verdict** comes from the latest completed full run of that content, under any
  version number:
  - a full run of this version with this content: its verdict, as today;
  - none, but a full run of the same content under another number: that verdict,
    "same content as version 88, verified 19 Nov";
  - a full run of this version, but of earlier content: **Not verified, edited since
    its full run of 19 Nov**.
- A run's verdict and totals do not change: a run says what it found on what it tested.
- `edited` returns on the version's results (`edited_since`: when the full run that no
  longer counts ran), and `verified_content` says which run and version verified the
  content.

### MCP

- `get_test_runs`: next steps say "Version 89 was edited after its full run of 19 Nov;
  run every scenario again to verify what it does now", or "Version 89 has the same
  content as version 88, which a full run verified".
- Rules: Verified belongs to the content; an edit under the same number needs a new
  full run.

## Done when

- Route tests through the API (local database), with Retell and the model mocked:
  - a full run verifies 89; a later run of 89 with other content makes 89 Not verified,
    edited since that full run; a new full run verifies it again;
  - a version with the same content as a verified one is Verified, naming it;
  - `run_scenarios` without `version` stores the fingerprint it read;
  - `get_test_runs` answers `edited_since` and `verified_content` with the next steps.

## Out of scope

- Verifying a candidate before deploy, the pre-deploy hook and overrides (10.1997 to
  10.1999).
- Fingerprints of n8n workflows or other systems a version calls: their tools are faked
  in tests, so they are not part of what a run verifies.

## Risks

- Retell adding a field that changes on every read would make every run look like an
  edit. The fingerprint already leaves out the volatile fields; a test pins what it
  covers.

## Outcome

### Deviations from the plan

- **The fingerprint is read with the version only when no version is given.** For a
  version the assistant names, the run's own read at its start stores it, as before.
  Reading it twice would only repeat that read.
- **Unknown content never reads as an edit.** When the newest run could not read its
  content, nothing is known to have changed. A full run that could not read its content
  still counts.
- **The steps name the other version's run:** "verified by version 15's full run of
  the same content (run …, 19 Nov 14:00)".

### Check results

`make check`, run before the pull request, after #244 merged and main was merged in:
every step ok (plan, local database, backend lint and format, pyright, backend tests and
coverage, MCP server tests, frontend lint and types, generated client fresh).

No separate play-through server: the route tests send the same requests through the API
(`TestClient` on the local database), with Retell and the model mocked:
- a full run verifies version 15. A pick on edited content makes it Not verified, with
  `edited_since` and a step to run every scenario again. A full run of the new content
  verifies it again;
- version 16 with the same content as 15, with only a pick on it, is Verified by 15's
  full run (`same_content`, the step names it);
- a full run whose content could not be read still verifies;
- every earlier results, runs and Tests tab test passes unchanged.

No UI change (Decided), so nothing to check on screen.

### Not done

- None.
