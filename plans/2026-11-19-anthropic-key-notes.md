# The Anthropic key in production

- **Owner:** Dmytro
- **Slice:** none (a fix after roadmap 10.193)
- **Design:** No UI change.
- **MCP:** None needed: no tool changes.

## Goal

Runs of scenarios failed in production: every simulated call stopped with "Missing
Anthropic API Key". 10.193 (#235) moved the simulated caller and the judge to Claude
Haiku 5.5 and assumed production had an Anthropic key. It had none; the deploy notes
said so.

## Changes

- **Production (done 2026-11-19, Dmytro: "Add the Anthropic key"):**
  - the key from the local `.env` stored as secret `connexity-anthropic-api-key`;
  - access granted to the runtime account;
  - the secret mounted on `connexity-backend` as `ANTHROPIC_API_KEY` (revision
    `connexity-backend-00176-7jf`).
- **`docs-internal/deployment.md`:**
  - lists the secret and what uses it;
  - says each new secret needs the runtime account's access on the secret itself.

## Decisions

- **Decided (Dmytro, 2026-11-19):** add the Anthropic key, rather than move simulations
  back to OpenAI.

## Done when

- The backend's serving revision has `ANTHROPIC_API_KEY` from the secret.
- Anthropic accepts the key.
- A run of scenarios in production reaches its conversations.

## Out of scope

- Any code change.

## Risks

- Simulations bill Dmytro's Anthropic account; no spending cap (10.193 decision).

## Outcome

### Deviations from the plan

None.

### Check results

- **The serving revision:** `connexity-backend-00176-7jf` serves 100% of traffic, and
  its `ANTHROPIC_API_KEY` comes from `connexity-anthropic-api-key`.
- **The key:** Anthropic's models endpoint answered 200 with it.
- **The plan check** (`scripts/check_plan.py`): ok. The change is docs only, so the
  code gates have nothing new to run; CI runs them all.

### Not done

- **A run of scenarios in production, end to end:** for Dmytro to start again from his
  assistant.
