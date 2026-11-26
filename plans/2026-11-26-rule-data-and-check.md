# A rule says what data it needs and how it is checked, and the guide asks for rules that can be checked

- **Owner:** Dmytro
- **Slice:** Roadmap 105.14, "A rule says what data it needs and how it is checked", with
  105.13, "The spec guide asks the assistant for rules that can be checked", folded in
  (Decided, Dmytro 2026-11-26: "Fold 105.13 into 105.14"). Both rows get this pull
  request.
- **Design:** No UI change. The parts of both rows are the spec model, the MCP tools, the
  checks engine and the guide. Nothing new is shown on a screen.
- **MCP:** `write_spec` takes each rule's `check` and `inputs`; `get_spec` answers them,
  the data each rule needs, and the agent's known inputs. Contract entries, input
  descriptions and the spec guide (`connexity://guides/spec`) are updated.

## Goal

Every spec rule says two things, so the spec check (105.15) and its LLM step (105.16)
can judge it well and cheaply:

1. **The data it needs:** the call alone, short named inputs (values the agent was given
   before the call, such as "first call or not"), or long free text such as the call
   history.
2. **How it is checked:** classifier only, classifier with LLM approval, or LLM only.

A check is given only the inputs its rule names, never all of them. Short inputs go to
the classifier; long ones go only to the LLM step.

The guide the assistant writes the spec from asks for rules that can be checked. That
means terms defined, the condition inside the rule, the boundary where the prompt gives
one, a clarification instead of a guess, a check type and the inputs.

Why (the 2026-11-26 lab test, one agent, 50 calls, 60 rules):

- With its named inputs, the classifier applied "on a first call" correctly. It cleared
  two of the three wrong "invented number" flags.
- Giving each rule only the inputs it names moved the other 55 rules no more than the
  classifier's own noise.
- Giving every rule all the inputs moved 98 unrelated answers.
- Every wrong flag in the review came from one of the gaps the guide now asks the
  assistant to close.

What the hosted database holds (field names and sizes only):

- 1,128 calls on 3 agents, every one with inputs: 30 fields on one agent, 5 on another,
  34 on the third.
- Every value is under 500 characters.
- The only long field is the call history (`previous_conversations`): up to 461
  characters, median about 183.
- Every other field is 150 characters or less. Several are contact details or ids:
  emails, phone numbers, call and lead ids.
- The 2 agents with a spec have 103 rules in their latest versions.

## Changes

**What a rule carries.**

- `check`: `classifier`, `classifier_then_llm` or `llm`. Code checks are not a choice:
  they are Connexity's own pre-defined checks (Decided, Dmytro 2026-11-26).
- `inputs`: the names of the inputs it needs, at most 10. None means the call alone.
- Its data follows from them, and `get_spec` shows it:
  - `call`: no inputs;
  - `short_inputs`: every named input is short;
  - `long_text`: at least one named input is long (decision 1).
- A rule whose data is long cannot be `classifier`: long text goes only to the LLM step.
  `write_spec` refuses it and says to choose `classifier_then_llm` or `llm`.
- Like `critical`, both are carried by key: a kept rule given neither keeps its
  previous values. A new rule given neither is `classifier` on the call alone
  (decision 4). Changing them is a `write_spec`, so a new spec version.

**Which names a rule may use.**

- A name must be one the agent's calls carry: one seen in the inputs of the agent's
  stored calls in the last 30 days. Anything else is refused, with the known names in
  the next steps.
- `get_spec` answers `known_inputs`: each name, whether it is short or long, and on how
  many of those calls it appears. Never a value.
- Secret-looking names are refused, as masking already treats them (headers, and names
  like key, token, secret or password), and so are contact details and ids: names like
  email, phone, number, `id` or ending in `_id` or `sid` (decision 3).

**What a check is given (the checks engine).**

- The function every check reads a rule through (`services/rule_context.py`, from
  105.12) now carries the rule's check type and its input names. It hands a check the
  values for one call:
  - the classifier step gets the short named inputs only;
  - the LLM step gets all of them.
- The rule's fingerprint includes its check type and input names. A stored model answer
  keyed on it goes stale when either changes.
- The judge of simulated calls is an LLM. It is given each rule's named inputs from the
  scenario's agent variables, beside the clarifications it already reads. A name the
  scenario does not set is given as "not set".
- The spec check that uses this for real calls is 105.15. How many classifier requests
  it sends per call is decision 2.

**The spec guide (105.13).** It asks the assistant to:

1. Define any term a reader of the call would not know ("a value beat is …").
2. Put the rule's condition in the rule ("on a first call, never say …").
3. Say where a boundary lies when the prompt does ("more than 50 words in one turn").
4. Raise a clarification, not guess, when the prompt leaves it open.
5. Choose each rule's check type, with how to choose:
   - classifier only when the call alone settles it plainly (a word said or not, a turn
     too long);
   - classifier with LLM approval when the rule has a condition or depends on what kind
     of call it is (unless, only if, a first call, a screener);
   - LLM only when it needs long text or the call history.
6. Name the inputs the rule needs, and only those, from `known_inputs`.

It also says the known weakness plainly. A strange call on a "classifier only" rule is
not verified (accepted as low enough, Dmytro 2026-11-26). Marking false positives will
reduce it later.

**Docs.** `docs-internal/checks-and-incidents.md` (the spec check's inputs and check
types) and `docs-internal/data-model.md` (the new rule columns).

## Decisions

1. **"Long" is measured: an input whose longest value on the agent's calls is over 200
   characters.** Decided, Dmytro 2026-11-26 (chose "Measured, over 200 chars"). On
   today's data only the call history is; the next longest field is 148.
2. **The number of classifier requests per call is decided in 105.15,** where the spec
   check is built and its cost measured. Decided, Dmytro 2026-11-26 (chose "Decide in
   105.15"). This change only fixes what each rule names and what a check is given. Lab
   numbers for that plan: one request per distinct set of inputs cost $0.31 per 1,000
   observed minutes, a single request with every input $0.18; two requests was not
   tried.
3. **Contact details and ids are refused as inputs, like secrets.** Decided, Dmytro
   2026-11-26 (chose "Refuse contact and ids"). Field names that look like an email, a
   phone number or an id are refused, so no customer's email or number is sent to a
   model for a check. Names and addresses stay allowed.
4. **The 103 existing rules become `classifier` on the call alone, and so does a new
   rule given neither.** Decided, Dmytro 2026-11-26 (chose "Classifier by default").
   `get_spec` tells the assistant how many rules are still on that default; no Work task.
5. **Shape, and that the assistant sets the type.** Decided, Dmytro 2026-11-26. The known
   weakness (a strange call on a "classifier only" rule skips verification) is accepted
   as low enough.
6. **Code checks are not a check type the assistant chooses.** Decided, Dmytro
   2026-11-26.

## Done when

- `write_spec` stores each rule's `check` and `inputs`, and `get_spec` answers them with
  the data each rule needs.
- A kept rule given neither keeps its previous values; a new rule given neither is
  `classifier` on the call alone.
- Refusals, each with the known names or the fix in the next steps:
  - an unknown input name;
  - a secret-looking name, an email, a phone number or an id;
  - more than 10 inputs;
  - a rule with long data typed `classifier`.
- `get_spec` lists `known_inputs` with short or long and how many calls carry each, and
  no values.
- The function every check reads a rule through gives the classifier only the rule's
  short named inputs and the LLM step all of them. Changing a check type or input names
  changes the fingerprint.
- A test run's judge is given each rule's named inputs from the scenario, and "not set"
  for one the scenario lacks.
- The migration gives the existing rules `classifier` and no inputs.
- The guide asks for the six things, and says how to choose a check type.
- The `write_spec` and `get_spec` contract entries and input descriptions are updated,
  and the contract tests pass.

## Out of scope

- The spec check itself (105.15) and the LLM approval step (105.16). Nothing judges real
  calls against the spec yet.
- Showing check types or inputs on the Spec tab. Neither row lists the screen, and
  nothing on screen would act on them yet.
- Facts written in the prompt itself, such as approved claims. They are neither inputs
  nor rules, and 105.15 leaves them open.

## Risks

- Rules stay on the default `classifier` until the assistant revisits them. A
  conditional rule left there will raise wrong flags in 105.15 until it does. `get_spec`
  says how many are on the default.
- A field that is short today can grow (a longer call history) and turn long after a
  rule was written. Long is measured each time `write_spec` checks it. A rule typed
  `classifier` on a field that turned long is caught only when the spec is next written.
- Input names differ by agent and platform. Names are checked against the agent's own
  calls, so a spec copied from another agent is refused until its names fit.

## Outcome

### Deviations from the plan

- **The fingerprint also covers which named inputs are long** (from `/code-review`). If
  an input grows past 200 characters, what the classifier is given changes, so a stored
  answer must go stale too.
- **`get_spec` marks each known input `allowed`** (false for contact details, ids and
  secrets), so the assistant sees which names it may use without trying them.
- **What counts as a contact detail or an id is a name pattern:** email, phone, mobile,
  caller number, a SIP asserted identity, uuid, `id` or a name ending in `_id` or
  `sid`. `customer_name` and address fields stay allowed, as decided.
- **Built on the 105.12 branch** (#273, now merged), because both change the spec
  model, `write_spec` and the guide.

### Check results

`make check`, once, after this Outcome was written:

| Step | Result | Time |
|---|---|---|
| Plan present and complete | ok | 0s |
| Start local database | ok | 1s |
| Backend lint and format | ok | 0s |
| Backend types (pyright) | ok | 19s |
| Backend tests and coverage | ok | 177s |
| MCP server tests | ok | 7s |
| Frontend lint | ok | 11s |
| Frontend types | ok | 2s |
| Generated client is fresh | ok | 13s |

No separate play-through server: the tests send `write_spec` and `get_spec` through
the API (`TestClient` on the local database). Invented calls carry inputs. The tests
cover:
- each refusal: an unknown name, a contact detail, an id, more than 10 inputs, and
  long text on a classifier rule;
- the defaults, and carrying by key;
- `known_inputs` with short or long, never a value;
- what the classifier and the LLM step are each given;
- a test run's judge reading a scenario's input, and "not set" for one the scenario
  lacks.

No screen changes, so nothing for Dmytro to check on screen.

### Not done

- **Nothing judges real calls against the spec yet;** that is 105.15. The 103 hosted
  rules become `classifier` on the call alone when migration `0057` runs, and wait for
  the assistant to revisit them.
