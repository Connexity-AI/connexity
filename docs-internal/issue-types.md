# Issue types

Every check Connexity runs, what it finds and how, its category and its default
severity. This is the start of the issue type library (roadmap feature 23). A test
(`test_issue_types_doc.py`) fails when a registered check is missing here.

**Found by:** a **rule** is plain code over the call's stored trace: deterministic, free
to run, and each finding points at the exact tool call or sentence. A **model** check (a
classifier or a judge) asks a model; none exists yet (roadmap 10.16). Every check and
finding carries which one it is (`CheckKind`), and the assistant sees it as `found_by`.

**Severity:** a check that fails the call makes its issues **Critical**; one that only
flags it makes them a **Warning**. The default is below; a person can change it per
agent (a decision record).

Checks are a library: a check is added only when Dmytro names it.

| Type | Title | Found by | Category | Default | Key |
|---|---|---|---|---|---|
| `tool_call_failed` | Tool call failed | Rule | Tools and integrations | Critical | The tool's name |
| `booking_details_missing` | Booking with missing or placeholder details | Rule | Booking | Critical | The booking tool's name |
| `booking_duplicated` | Two bookings for one slot | Rule | Booking | Critical | The booking tool's name |

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

## Later: found by a model (10.16)

- **A change confirmed without a tool:** the agent told the caller an appointment was
  cancelled or moved, with no tool that could do it. A phrase rule was not good enough;
  a classifier or an LLM is still to be decided (Dmytro, 2026-11-13).
