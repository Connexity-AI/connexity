# Cheap password hashing in tests

- **Owner:** Dmytro
- **Slice:** none. It came out of the review of why roadmap 105.11 took an hour of
  checks.
- **Design:** No UI change.
- **MCP:** None needed: nothing a user or assistant can do or see changes. Only the
  backend test setup changes.

## Goal

The backend test suite runs in a fraction of its current time. Today it takes 346 s
in `make check`, which makes every task wait on checks. Production password hashing
does not change.

Measured on 2026-11-26:

- Hashing a password with the app's bcrypt context at its default cost takes about
  0.25 s.
- The tests create invented users (and sign them in) hundreds of times, so bcrypt is
  most of the suite's time.
- With the cost at bcrypt's minimum (4 rounds) for the test run only, the 1,208 tests
  passed in 84 s, without coverage. Three of the files went from 9.9 s to 3.3 s.

## Changes

- `backend/app/tests/conftest.py` gains a session-wide autouse fixture that swaps
  `app.core.security.pwd_context` for a bcrypt context at 4 rounds while tests run,
  and puts the original back afterwards. `get_password_hash` and `verify_password` read
  `pwd_context` when called, so every hash made in a test is cheap.
- A test guards production: the app's own context still hashes at bcrypt's default
  cost, and a cheap hash still verifies under it. The speed-up can never leak into the
  app.
- `app/core/security.py` is not changed.

## Decisions

1. **Lower the cost in tests only, not make it a setting.** Proposed: a setting could
   be lowered by mistake in production; a test fixture cannot.
2. **4 rounds,** bcrypt's minimum. Proposed: tests check that a password verifies, not
   how strong the hash is.
3. **No parallel test runs (pytest-xdist) in this change.** Proposed: the suite shares
   one database and wipes it at the end of the session, so running in parallel needs
   its own design.

## Done when

- `make check` passes, and its backend tests step is well under 346 s.
- The guard test fails if the app's own context is ever lowered to the test cost.
- No test, type check or lint rule is weakened.

## Out of scope

- Parallel test runs.
- Any other slow test. The slowest left after this change take under 2 s each.
- Production hashing, its cost and its scheme.

## Risks

- A test that compares a stored hash's cost or prefix would see "$2b$04$" instead of
  "$2b$12$". None does today; the guard test covers the production side.

## Outcome

### Deviations from the plan

None.

### Check results

`make check`, once, after this Outcome was written. "Before" is the same command on
the 105.11 branch earlier the same day.

| Step | Result | Time | Before |
|---|---|---|---|
| Plan present and complete | ok | 0s | 0s |
| Start local database | ok | 0s | 0s |
| Backend lint and format | ok | 0s | 0s |
| Backend types (pyright) | ok | 13s | 10s |
| Backend tests and coverage | ok | 129s | 346s |
| MCP server tests | ok | 5s | 5s |
| Frontend lint | ok | 2s | 2s |
| Frontend types | ok | 1s | 1s |
| Generated client is fresh | ok | 9s | 10s |
| **Total** | | **159s** | **374s** |

No play-through server: nothing the API answers changes. The guard tests
(`app/tests/core/test_security.py`) check both sides: the app's own context hashes at
full cost, and a cheap test hash still verifies under it.

### Not done

- Parallel test runs (Decision 3).
