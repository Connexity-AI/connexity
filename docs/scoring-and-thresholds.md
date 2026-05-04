# Scoring & Thresholds

## Per-test-case scoring

### How `overall_score` is calculated

Each test case is evaluated by a Judge LLM across 8 default metrics, each scored 0-5:

| Metric | Default Weight | Tier |
|---|---|---|
| Tool Routing | 15% | Execution |
| Parameter Extraction | 15% | Execution |
| Result Interpretation | 15% | Execution |
| Grounding Fidelity | 12.5% | Knowledge |
| Instruction Compliance | 12.5% | Knowledge |
| Information Gathering | 10% | Process |
| Conversation Management | 10% | Process |
| Response Delivery | 10% | Delivery |

The `overall_score` formula:

```
overall_score = Σ (metric_score / 5) × normalized_weight × 100
```

So if every metric scores 5/5, you get 100. If every metric scores 3/5, you get 60.

### Per-metric scoring (no per-metric pass/fail gate)

There is no per-metric pass/fail threshold. Individual metrics produce descriptive labels only:

- **Scored metrics (0-5):** `critical_fail` (0), `fail` (1), `poor` (2), `acceptable` (3), `good` (4), `excellent` (5) — these labels are purely descriptive. A metric scoring 0 does not independently fail the test case.
- **Binary metrics** (like `task_completion`): have explicit `pass`/`fail`, but this still just maps to score 5 or 0 and feeds into the weighted sum like any other metric.

The only pass/fail gate is at the **test case level**: `overall_score >= pass_threshold`. A test case can have a metric at 0/5 and still pass if other metrics compensate.

### Pass/fail per test case

A test case passes when **all of its `expected_outcomes` pass** (CS-127).

- `expected_outcome_results` — produced by the judge per statement (pass/fail + justification)
- A test case passes ⇔ every entry in `expected_outcome_results` has `passed: true`
- For legacy test cases without `expected_outcomes` (or when the judge could not produce outcomes), the system falls back to `overall_score >= eval_config.config.judge.pass_threshold` (default **75/100**)

`overall_score` and the per-metric scores are still recorded for observability, but the *test case pass/fail gate* is the expected-outcomes checklist, not the weighted score.

### What can be overridden per eval config / per run

- Which metrics to include (you can remove or add metrics, including binary ones like `task_completion`)
- Metric weights (renormalized to sum to 1.0 after override)
- `pass_threshold` (e.g., set to 50 for lenient evals or 90 for strict) — only used as a fallback for test cases that have no `expected_outcomes`
- Judge LLM model and provider (e.g., use a cheaper model for faster iteration)

### Expected outcomes

The checkmark/X list in the UI. The judge checks each statement independently and returns pass/fail + justification.

They are now the **primary pass/fail gate at the test-case level** (see above). They still do not factor into the `overall_score` calculation — that score remains the weighted metrics number used at the run level.

## Run-level pass thresholds (CS-127)

Each eval run produces two independent pass/fail dimensions, evaluated against thresholds stored on the eval config (`eval_config.config.metrics_pass_threshold` and `eval_config.config.cases_pass_threshold`).

| Dimension | What it measures | Default threshold |
|---|---|---|
| Metrics | Mean of per-test-case `overall_score` across all results that produced a verdict | **80%** |
| Cases | `passed_count / total_executions × 100` (errored results count as not-passed) | **100%** |

After a run completes, the aggregate metrics include:

- `weighted_metrics_score_pct`, `metrics_pass_threshold`, `metrics_passed`
- `cases_pass_rate_pct`, `cases_pass_threshold`, `cases_passed`

`metrics_passed` is `true` when `weighted_metrics_score_pct >= metrics_pass_threshold`. `cases_passed` is `true` when `cases_pass_rate_pct >= cases_pass_threshold`. A run can fail on either dimension independently.

The thresholds are part of `RunConfig` and are snapshotted into `run.config` at run-creation time, so changes to the eval config after a run starts do not retroactively shift its pass criteria.

## Run comparison thresholds

Only used when comparing two runs via `GET /runs/compare`:

| Threshold | Default | What it does |
|---|---|---|
| `max_pass_rate_drop` | 0.0 (strict) | Any pass-rate drop flags regression |
| `max_avg_score_drop` | 5.0 pts | Tolerates 5pt noise on the 0-100 scale |
| `max_latency_increase_pct` | 20% | Tolerates up to 20% latency growth |

These are overridable via query params on the compare endpoint. They determine if `regression_detected = true` at the suite level.

### Per-test-case comparison

Uses a hardcoded 5pt threshold — when pass/fail didn't flip between runs, a score delta > 5pts classifies the case as regression or improvement. Not configurable via API currently.
