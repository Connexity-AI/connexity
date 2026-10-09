# Which version served this call

- **Owner:** Dmytro
- **Slice:** 1.5

## Goal

Answer "which version was this call on?" exactly. Today a call knows one number, the
voice agent's version, and nothing about what that version contained. After this merges,
every call lists the version of each thing that served it (agent settings, prompt,
model, and each workflow that ran), each with a fingerprint of its content, and
Connexity keeps the content of every version it has seen.

## Changes

**A catalogue of observed versions**

- New table: one row per version of a component that Connexity has seen for an agent.
  It holds the kind (agent, prompt, model, skill), the provider's id for the thing, the
  provider's version, a fingerprint, the content, and when it was first seen.
- The fingerprint is a hash of the content, with the fields that change without the
  content changing (timestamps, version numbers, publish flags) left out. Two versions
  with the same content have the same fingerprint.
- Content is stored, with values that look like credentials masked: the values of
  request headers on tool definitions and on workflow nodes, and any field whose name
  says it is a key, token, secret or password.

**From Retell**

- When a call arrives on an agent version not yet in the catalogue, Connexity reads that
  version from Retell once and records:
  - **agent**: its settings (voice, language, timeouts and the like);
  - **prompt**: the prompt text, the opening message, and the tool definitions, from the
    prompt version that agent version points to (a single-prompt agent or a
    conversation flow);
  - **model**: the model's name.
- Later calls on the same agent version read nothing from Retell.
- If Retell cannot be read, the call is stored with the agent's version number only, as
  today, and is resolved later.

**From n8n**

- When an execution is copied, the workflow it carried (its nodes, their code and
  connections) is fingerprinted and recorded as a **skill** version. n8n can only return
  a workflow's current version, so this is the only moment a past version can be
  captured.

**Per call**

- A call's components are: agent, prompt and model, each with version and fingerprint,
  and one skill for each workflow that ran on that call.
- A call also gets one combined fingerprint over agent, prompt and model. Every call has
  those three, so calls can be grouped by it. Skills are not part of it, because a call
  only knows the versions of the workflows it used.

**Backfill**

- New: an action on an agent that resolves the versions of its stored calls. Every
  Retell version can be recovered. A workflow version can be recovered only for an
  execution n8n still holds.

**API and screen**

- The call in the API gains its agent version and its combined fingerprint.
- The trace response lists the components with their fingerprints, including skills.
- New: `GET` one catalogue entry with its content, for a component of a call.
- The call drawer gains a "Served by" block: agent, prompt, model and each skill, with
  version and a short fingerprint. The calls list gains a version column.

## Decisions

Made by Dmytro on 2026-10-09:

- **Content is stored, not only the fingerprint.** A fingerprint says something changed;
  only content can later say what.
- **Fingerprints are per component, plus one combined fingerprint per call over agent,
  prompt and model.** Skills stay out of the combined one.
- **The old `AgentVersion` model and the draft, publish and rollback routes are left
  alone.** They are tied into the frozen eval stack and are decided with it in Phase 4.
  This changes the earlier note that they are reshaped in this slice.
- **Using tool addresses from the prompt version to suggest tool-to-workflow mapping is
  not in this slice.** Recorded for later.

Proposed by Claude, not yet confirmed:

- What is masked in stored content (see above). Masked values are replaced before the
  fingerprint is taken, so rotating a token does not look like a new version.
- The fields left out of a fingerprint: timestamps, the version number itself, publish
  flags and version titles.
- Skills are named after the workflow, with the workflow's id as the reference.

## Done when

- With invented Retell responses: a call on a new agent version records agent, prompt
  and model with fingerprints; a second call on the same version reads nothing from
  Retell; both a single-prompt agent and a conversation flow are handled.
- Two agent versions whose content is identical have the same fingerprint; changing the
  prompt text changes the prompt's fingerprint and the call's combined fingerprint, and
  leaves the agent's and the model's alone.
- Retell being slow, returning nothing, or returning something malformed does not stop
  the call from being stored; the call keeps its version number and is resolved by the
  backfill.
- With invented n8n executions: two executions of one workflow with different node code
  give two skill versions with different fingerprints; the same workflow content gives
  one.
- Stored content contains no header value and no value of a field named like a
  credential, and masking does not depend on the value.
- The backfill resolves stored calls, reads each version from Retell once, and can be
  run twice without duplicating anything.
- A catalogue entry can be read with its content; another company cannot read it.
- The drawer code compiles with the "Served by" block; the list shows the version.
- **On real calls** (Dmytro's machine, counts only): the connected agent's calls are
  backfilled; reported are how many distinct agent versions, how many distinct prompt
  fingerprints among them, how many skill versions, how many calls could not be
  resolved and why, and that no stored content contains a header value.
- `make check` passes.

## Out of scope

- "Verified" and "unverified" versions, and flagging a call on an unverified version
  (Phase 5).
- A timeline of versions, a diff between two versions, alerts when something changes.
- Polling live state to notice a change before a call arrives.
- Versions for Vapi and ElevenLabs calls (their calls are not traces yet, slice 1.3b).
- The old `AgentVersion` model and its routes.
- Suggesting tool mappings from tool addresses.
- Knowledge bases, voices as content, and anything else Retell versions beyond the
  agent, its prompt and its model.

## Risks

- **Stored content is sensitive.** Prompts and workflow code are the client's work
  product, and may contain business rules, phone numbers or hard-coded tokens that
  masking by field name will miss. It all goes into Connexity's database.
- **A fingerprint is only as good as the list of fields left out.** If Retell adds a
  field that changes on every read, every version will look different. If a field that
  matters is left out, a real change is missed.
- **Workflow versions are only seen when a workflow runs on a call of a mapped tool.**
  A change to a workflow that no call has used yet is invisible. A change to a
  sub-workflow called by the mapped workflow is invisible too, unless n8n includes it.
- **The backfill reads Retell once per version**, about 40 for the connected agent, and
  up to three requests each. Retell rate limits are not known to me.
- **A reviewer should push back if** storing prompt and workflow content is not
  acceptable, or if leaving `AgentVersion` in place beside a second notion of "version"
  is too confusing to carry until Phase 4.

## Outcome

### Deviations from the plan

- **A prompt and a flow are two kinds.** A single-prompt agent's prompt is recorded as
  `prompt`; a conversation flow as `flow`. The plan called both "prompt".
- **The model's fingerprint covers its settings too** (temperature and the like), not
  only its name. A model has no version number, so it is shown without one.
- **The link from an agent version to its prompt is not part of the agent's
  fingerprint.** Otherwise every agent version would look different even with identical
  settings. On the real agent, 39 agent versions came down to 17 distinct settings.
- **Skills are listed for a call from its executions, not stored again as call
  components.** The trace response's `served_by` joins the two.
- **A version with no number from the provider is filed under a hash of its content**:
  a prompt whose agent names no prompt version, and a workflow from an n8n that sends no
  version id.
- **More is masked than planned.** Besides headers and fields named like a credential:
  the value of a name and value pair whose name is such a name, and fields named
  access key, cookie, signature or passphrase. Found in review.
- **Calls already stored get their agent's version number from the migration itself.**
  Not in the plan; without it the new column would stay empty for calls the backfill
  does not cover.
- **Retell version reads time out after 4 seconds**, because a webhook waits on them and
  Retell gives a webhook ten.
- **Stored calls are resolved in the background, without anyone asking**, when the
  agent's calls are next synced (Dmytro, 2026-10-09, after asking what a Resolve button
  was for). The plan had it as an action only. The action remains in the API. After a
  pass that could not finish, the next automatic one waits ten minutes.
- **A list of an agent's versions** (`GET .../component-versions`, without content) was
  added. The plan named only the single-entry read.
- **Tests never reach Retell.** A shared fixture makes the version lookup fail by
  default, the way an unreachable provider does; tests about versions opt out of it.
- A public page was added, `docs/traces/versions.md`.

### Check results

`make check` on this branch:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 21s |
| Backend tests and coverage | ok | 74s |
| MCP server tests | ok | 3s |
| Frontend lint | ok | 8s |
| Frontend types | ok | 8s |
| Generated client is fresh | ok | 13s |

All steps passed in one run, after the last change.

Against the done-when:

| Done when | Result |
|---|---|
| A call on a new version records agent, prompt and model; a second call reads nothing; single-prompt and flow agents both handled | Yes |
| Identical content gives identical fingerprints; a new prompt changes the prompt's and the call's, not the agent's or model's | Yes. Also: a new model changes only the model's and the call's |
| Retell slow, empty or malformed does not stop the call; the backfill resolves it later | Yes: at the client (timeout, error, empty, not JSON, wrong shape) and end to end through a pull |
| Two executions with different node code give two skill versions; the same content gives one | Yes, including a node moved on the canvas counting as the same content |
| Stored content has no header value and no credential-named value; masking does not depend on the value | Yes |
| The backfill resolves stored calls, reads each version once, and can be run twice | Yes. A version Retell no longer has is reported, and its calls counted as unresolved |
| A catalogue entry can be read with content; another company cannot | Yes. Also not through another agent of the same company |
| The drawer compiles with "Served by"; the list shows the version | Compiles and lints. **Not looked at in a browser** |
| Real calls | See below |
| `make check` passes | Yes, with the note above |

Real calls, on Dmytro's machine, counts only. The built backfill was run on the
connected agent, from an empty catalogue, after the review fixes:

| Measure | Result |
|---|---|
| Calls resolved | 597 of 597 |
| Agent versions read from Retell | 39, none failed |
| Distinct agent settings among them | 17 |
| Distinct prompts among them | 33 |
| Distinct models | 4 |
| Distinct states across calls | 38 |
| Workflow versions recorded from stored executions | 5, across two workflows |
| Time | 52 seconds |
| Second run | Nothing to do: 0 calls, 0 reads |
| Values masked in stored content | 20 |
| Unmasked header values, credential-named values, or strings that look like a key or bearer token | 0 |
| Stored content | about 710 KB for 87 versions |

So 39 version numbers were really 38 distinct states: one version was republished with
nothing changed. And the agent's settings changed far less often than its prompt.

Migration `0006_component_versions` applies, reverses and re-applies on the local test
database, and `alembic check` reports no drift.

**`/code-review`** was run on the whole diff before the fixes below. Seven findings, all
fixed:

| Finding | Outcome |
|---|---|
| A credential in a name and value pair outside a header was not masked | Fixed |
| Opening a call loaded the content of every version of the agent | Fixed: content is read one entry at a time |
| A workflow with no version id never matched its execution | Fixed |
| A prompt with no version number kept the first content seen | Fixed |
| Version reads could outlast the webhook's ten seconds | Fixed: 4 second timeout |
| The new version column was empty for calls already stored | Fixed in the migration |
| Resolving versions runs inside one request | Fixed: it runs in the background sync; only the API action still runs in its request |

The review was done by the session that wrote the code, not an independent reviewer.

### Not done

- **Not seen in a browser.** The "Served by" block and the version column are
  type-checked only.
- **The API action still runs inside its request** (52 seconds for 39 versions). The
  background pass covers the normal case; the action is for the assistant.
- **The retry wait is kept in memory**, per server process. A restart forgets it, and
  each process keeps its own. The cost is at most one extra attempt.
- **Masking goes by names only.** A credential written into a prompt, or hard-coded in a
  workflow's code node, is stored as it is. The check on real content found no string
  that looks like a key, but that check is a pattern match, not proof.
- **Conversation flows are tested on invented responses only.** The connected agent is a
  single-prompt agent.
- **A sub-workflow called by a mapped workflow is not recorded.** n8n runs it as its own
  execution, which Connexity does not read.
- **A workflow change is seen only once a call uses it**, as the plan said.
- **No content viewer on the screen.** A version's content is available through the API
  only.
- **The old `AgentVersion` model is untouched**, as decided. There are now two things
  called a version until Phase 4.
- The local development database was migrated to `0006` by this session.
