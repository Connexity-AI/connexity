# Issue types

Every check Connexity runs, what it finds and how, its category and its default
severity. This is the start of the issue type library (roadmap feature 23). A test
(`test_issue_types_doc.py`) fails when a registered check is missing here.

**Found by:** a **code-based** check is plain code over the call's stored trace:
deterministic, free to run, and each finding points at the exact tool call or sentence.
A **classifier** asks a small model typed questions (Jev) and code turns the labels into
findings; an **LLM judge** asks a language model. Every check and finding carries which
one it is (`CheckKind`), and the assistant sees it as `found_by`. How model checks run
is in [`checks-and-incidents.md`](./checks-and-incidents.md).

**Severity:** a check that fails the call makes its issues **Critical**; one that only
flags it makes them a **Warning**. The default is below, from the Issue library, and
does not depend on what decides the check; a person can change it per agent (a
decision record).

Checks are a library: a check is added only when Dmytro names it.

| Type | Title | Found by | Category | Default | Key |
|---|---|---|---|---|---|
| `tool_call_failed` | Tool call failed | Code-based | Tools and integrations | Critical | The tool's name |
| `booking_details_missing` | Booking with missing or placeholder details | Code-based | Booking | Critical | The booking tool's name |
| `booking_duplicated` | Two bookings for one slot | Code-based | Booking | Critical | The booking tool's name |
| `action_claimed_without_tool` | Action claimed without a tool call | Classifier | Tools and integrations | Critical | None: one issue per agent |
| `spec_rule_broken` | Spec rule broken | Classifier | The rule's category | Critical | The spec rule's key: one issue per rule, titled by the rule. Only a critical rule fails the call; any other is a Warning |

## Tool call failed

A tool the agent called returned an error or timed out (the trace's tool call status).
"No result" is not a failure. Needs tool results in the trace.

## Booking with missing or placeholder details

A booking tool was called with an empty or placeholder name, street address or zip.

- **Booking tool:** its name says it books (`book`, `schedul`, `appointment`, `reserv`)
  and not that it only looks or changes one (`availab`, `slot`, `get_`, `list`, `find`,
  `check`, `search`, `cancel`, `reschedul`).
- **Name, street address or zip:** arguments whose name contains `name`, `address`,
  `street`, `zip` or `postal`.
- **Empty or placeholder:** empty, `{{...}}`, a bracketed note (`[address pending]`), a
  run of zeros (`00000`), or a word such as missing, pending, unknown, tbd, n/a.
- **The finding** names the empty arguments, never their values.
- **Limits:** a tool whose name says nothing about booking is not seen. A real value that
  contains one of those words (a street called "Pending Lane") is flagged.

## Two bookings for one slot

A booking tool was called twice or more in one call, without error, with the same time.

- **Time:** the first argument whose name contains `start`, `slot`, `datetime`, `time` or
  `date`, in that order, ignoring time zones.
- **The finding** points at both bookings.
- **Limits:** a second booking at a different time (a change of mind) is not flagged,
  though it also leaves two appointments.

## Action claimed without a tool call

The agent told the caller it did something, with no tool call that did it, or after
that tool call failed. Covers changes and read-only lookups with an invented answer
(renamed from "A change confirmed without a tool", Dmytro 2026-11-17). Decided by a
classifier (Jev), Dmytro 2026-11-17.

- **Jev** labels each agent turn with what it says is already done: booked, cancelled,
  moved, notified, looked up, or nothing. The state it reads is that turn and the
  caller's turn before it. A label counts at a probability of 0.5 or more.
- **Code** then looks for a tool call that could do it, earlier in the call or during
  that turn, that did not fail. Which tools can back a claim is read from their names,
  as the booking checks do.
- **The finding** points at the turn, and at the failed tool calls when there were
  some. Its detail has the action, Jev's probability, why (no tool call, or the tool
  failed) and the model.
- **Limits:** a tool whose name says nothing about what it does backs nothing, so a
  claim it did back is flagged. A made-up fact the agent never says it looked up is a
  different type. Needs the trace to report tool calls.
- **Tried on real calls (2026-11-17):** 12 of 85 calls flagged, $0.015; not yet
  reviewed by a person.

## Spec rule broken

The agent broke one of its spec rules in a call (roadmap 105.15,
`plans/2026-11-26-spec-check.md`).

- **How:** a classifier (Jev) answers one yes or no question per rule, "did the agent
  break this rule in this call?". Each rule is read with its clarifications in force.
  The rules that name no input are asked about the call alone, in one request. The rules
  that name inputs are asked in a second request, with the union of their short inputs.
- **Bar:** a "yes" at 0.8 or above is a finding (Decided, Dmytro 2026-11-26). Every
  probability is stored, so a new bar is a new version that reads the stored answers.
- **Which rules:** `classifier` rules raise findings. `classifier_then_llm` rules are
  asked and stored, but raise nothing until the LLM step (105.16) confirms them. `llm`
  rules are not asked.
- **Which calls:** real calls where the agent said 10 words or more, on an agent version
  a spec covers.
  - A call is judged once, against the spec in force when it is judged; changing a rule
    does not judge it again.
  - Calls are judged from the check's release. An agent's first spec, written after
    that, judges its last 30 days once; those findings are retroactive.
- **The finding** judges the whole call. It points at no event and gives no reason. It
  carries the rule's key and text, the probability and the model.
- **Severity:** a critical rule's finding fails the call (when the check is set to
  fail calls, its default); any other only flags it.
- **Limits:**
  - The classifier never sees the prompt, so a rule that rests on facts written in the
    prompt (approved claims) is typed `llm`.
  - A strange call on a `classifier` rule is not verified (accepted, Dmytro
    2026-11-26).
  - Measured on two agents of one platform in the lab.
