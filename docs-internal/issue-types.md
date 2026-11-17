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
