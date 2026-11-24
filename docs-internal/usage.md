# Usage

What a workspace used, counted in units, and what that comes to at list price. Where
paying is set up, the same records are what an agency's included amount and balance are
drawn down by: see [`billing.md`](./billing.md).

Code: `backend/app/models/usage.py` (the table), `backend/app/crud/usage.py` (counting
and recording), `backend/app/services/usage.py` (prices and reading). Plan:
`plans/2026-11-21-usage-per-workspace.md`.

## Meters and list prices

| Meter | One unit | List price | Recorded |
|---|---|---|---|
| `observed_minutes` | A minute of a real call, each started minute whole | $0.03 | Yes |
| `simulated_caller_messages` | A message the simulated caller sent in a text simulation | $0.02 | Yes |
| `voice_simulation_minutes` | A minute of a voice simulation | $0.25 | No: voice simulations do not exist yet |

The prices live in one place, `PRICES` in `app/services/usage.py`. Dollars are always
units times the price at the time of reading; a record holds units only, so a price
can change without touching history.

## What counts

- **A real call** counts once it has an end time: its length rounded up to a whole
  minute (95 seconds is 2 minutes). A call stored with the source `test_call` or
  `simulation` counts nothing.
- **No call is recognised as a test call yet.** Every call brought in from the voice
  platform is stored as a real call, so it counts.
- **A simulated call** counts each turn of its transcript the simulated caller wrote,
  also when the call later stopped with an error. A simulated call that never ran has
  no transcript and counts nothing.
- **The agent's replies are not counted.** The voice platform bills them on the team's
  own account.

## Recording

One row of `usage_record` per real call and per simulated call, found again by its
`source_key` (`call:<id>` or `simulated:<id>`), so a source is never counted twice.

- **A real call** writes its row whenever it is stored (`store_trace`) and whenever a
  model check on it is paid for (`save_model_answer`). Storing it again replaces the
  row; a call that no longer counts loses it.
- **A simulated call** writes its row when it finishes, in the same commit as its
  transcript.
- **A row outlives its source.** Deleting the call, the simulated call or the run
  empties the row's link and keeps the row.
- **History** before the table existed was filled in by migration `0044_usage_record`,
  with the same counting.

## Connexity's own cost

Each row also carries what the models behind it cost Connexity (`own_cost_usd`), the
model, and the token counts by kind (in, out, cache read, cache write) that cost was
worked out from:

- **A real call:** the model checks that ran on it, summed from `model_answer`.
- **A simulated call:** the simulated caller and the judge.

The provider answers each request with token counts, never dollars, so the cost is
tokens times a price list (LiteLLM's, and `_PRICES` in `app/services/checks/judge.py`
for models it cannot price). The only proof it is right is the provider's own cost
report for the whole account, which is stored beside it: see "Billed beside recorded".

Two limits of these columns:

- **Rows filled in by the migration have no model name** for simulated calls: the
  model they ran on was not stored.
- **A real call's row names one model** even when checks on it used several; the
  detail per check stays in `model_answer`.

A simulated call that broke after its conversation ran keeps its transcript, so what
the caller sent counts and what the models cost is kept. A failure while writing a
usage record is logged and never stops the call being stored.

No workspace route and no MCP tool returns these columns. They are read from the
database.

## Billed beside recorded

`provider_cost_day` has one row per day (UTC) and model: what Anthropic billed and what
Connexity recorded, each as dollars and tokens in, out, cache read and cache write
(`plans/2026-11-23-anthropic-cost-comparison.md`; code in
`app/services/provider_cost.py`).

- **Billed** comes from Anthropic's cost report (dollars; the report answers in cents)
  and usage report (tokens), for the whole organisation, read with
  `ANTHROPIC_ADMIN_KEY`. Without the key nothing is read.
- **Recorded** is the sum of every workspace's `usage_record` rows of that day whose
  model is one of Anthropic's (its name starts with `claude`).
- **When:** the scheduled call pull reads it, at most once every six hours. Each read
  covers today and the three days before, replacing their rows, because the report
  runs some hours behind; older days are final.
- **Nothing is judged.** There is no tolerance, no flag and no warning (Decided,
  Dmytro 2026-11-23). Reading a row: the same tokens with different dollars is a wrong
  price; more billed tokens than recorded is requests that were never recorded.
- **A failed read** (timeout, refusal, an answer in another shape) is logged and
  leaves the table as it was; the next due read tries again.

What the numbers cannot say:

- **Local development is billed too.** One key serves production and developers'
  machines (Decided, Dmytro 2026-11-23). A run from a developer's machine is recorded
  in that machine's database only, so that day shows more billed than recorded.
- **Other providers are not compared:** the classifier behind model checks on real
  calls has no report read here.
- **Billed input tokens leave out tokens read from a cache**, which have their own
  column; no call uses a cache today.
- **Days before 21 Nov 2026** hold the simulated caller's tokens only on the recorded
  side, and no model name, so they do not line up.

To read it:

```sql
SELECT day, model, billed_usd, recorded_usd, billed_input_tokens,
       recorded_input_tokens, billed_output_tokens, recorded_output_tokens
FROM provider_cost_day ORDER BY day DESC;
```

## Reading

- `get_usage` (MCP) answers a calendar month in UTC, or the last 7 or 30 days: totals
  per meter, the same per agent, each run with its caller messages (paged), and the
  three things that added most (a run, or one agent's real calls on a day).
- `run_scenarios` says the price per caller message and what the last completed run of
  the same set, or of every scenario, came to.
- `get_test_runs` shows each run's and each simulated call's caller messages and
  list-price cost. Before this, `cost_usd` there was Connexity's own model cost.

There is no usage screen; one comes with Billing, design first.
