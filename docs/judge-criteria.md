# LLM Judge Evaluation Criteria (CE-015 / CS-22)

This document describes the evaluation metrics used by the LLM-as-a-judge module
to score agent conversation transcripts. The canonical definitions live in
`backend/app/services/judge_metrics.py`; this document provides a human-readable
reference for the criteria, tiers, scoring rules, and configuration options.

## Overview

The judge evaluates completed transcripts against a set of **metrics**. Each
metric belongs to a **tier** and uses either a **scored** (0-5 integer) or
**binary** (pass/fail) scale. Metrics carry configurable **weights** that
determine their contribution to the overall score.

| Property | Description |
|---|---|
| **Overall score** | Weighted sum of normalized metric scores, 0-100. |
| **Pass/fail** | `overall_score >= pass_threshold AND NOT critical_failure`. |
| **Critical failure** | Any execution-tier scored metric at or below `critical_failure_threshold`. |
| **Error category** | Derived from the lowest-scoring metric when the scenario fails. |

## Metric Tiers

| Tier | Purpose | Metrics |
|---|---|---|
| **Execution** | Did the agent use the right tools correctly? | tool_routing, parameter_extraction, result_interpretation, task_completion |
| **Knowledge** | Did the agent stay grounded and follow rules? | grounding_fidelity, instruction_compliance |
| **Process** | Did the agent manage the conversation well? | information_gathering, conversation_management |
| **Delivery** | Was the response natural and TTS-friendly? | response_delivery |

## Default Metrics (8 scored)

The following metrics are included by default when no custom metric selection is
provided. All use the 0-5 scored scale.

### 1. Tool Routing

- **ID:** `tool_routing`
- **Tier:** Execution
- **Default weight:** 0.15
- **Measures:** Correct tool names and call sequence.
- **What to fix:** Tool descriptions, selection logic, flow graph.
- **Error category on failure:** `tool_misuse`

| Score | Criteria |
|---|---|
| 5 | All expected tools called in correct sequence. No unnecessary calls. |
| 4 | All critical tools called. Minor sequence deviation or one redundant call. |
| 3 | One expected tool missed OR one wrong tool called, but core flow mostly intact. |
| 2 | Multiple tool errors. Flow significantly impacted but partially functional. |
| 1 | Most tool calls incorrect or missing. Only 1 of N expected tools called. |
| 0 | No tools called when required, or entirely wrong tool set used. |

### 2. Parameter Extraction

- **ID:** `parameter_extraction`
- **Tier:** Execution
- **Default weight:** 0.15
- **Measures:** Argument values correctly extracted from conversation for tools.
- **What to fix:** Slot-filling prompts, parameter parsing, formatting.
- **Error category on failure:** `tool_misuse`

| Score | Criteria |
|---|---|
| 5 | All parameters correct. Values accurately extracted from user input. |
| 4 | All critical parameters correct. One minor parameter slightly off. |
| 3 | One critical parameter wrong or missing, affecting tool outcome. |
| 2 | Multiple parameter errors. Tool may have returned wrong results or failed. |
| 1 | Most parameters fabricated or missing. Values not grounded in conversation. |
| 0 | No parameters extracted from conversation. All values fabricated or empty. |

### 3. Result Interpretation

- **ID:** `result_interpretation`
- **Tier:** Execution
- **Default weight:** 0.15
- **Measures:** Tool output accurately reflected in agent response.
- **What to fix:** Response generation prompt, output formatting rules.
- **Error category on failure:** `hallucination`

| Score | Criteria |
|---|---|
| 5 | Tool output accurately and completely reflected. Errors handled gracefully. |
| 4 | Tool output mostly accurate. Minor omission that doesn't mislead user. |
| 3 | One meaningful inaccuracy in conveying tool results. |
| 2 | Significant misrepresentation of tool output. |
| 1 | Tool output largely ignored or contradicted. |
| 0 | Tool output completely ignored. No connection to what the tool returned. |

### 4. Grounding Fidelity

- **ID:** `grounding_fidelity`
- **Tier:** Knowledge
- **Default weight:** 0.125
- **Measures:** Every agent claim traceable to context, tools, or business rules.
- **What to fix:** Grounding instructions, retrieval, citation rules.
- **Error category on failure:** `hallucination`

| Score | Criteria |
|---|---|
| 5 | Every specific claim grounded. Appropriate hedging for uncertain info. |
| 4 | All critical claims grounded. One minor unverifiable statement. |
| 3 | One meaningful ungrounded claim that could mislead user. |
| 2 | Multiple ungrounded claims. Mix of fabricated facts and invented policies. |
| 1 | Most claims ungrounded. Agent is largely confabulating. |
| 0 | Response is entirely fabricated with no connection to provided context. |

### 5. Instruction Compliance

- **ID:** `instruction_compliance`
- **Tier:** Knowledge
- **Default weight:** 0.125
- **Measures:** Agent follows explicit rules from system prompt and business rules.
- **What to fix:** The specific violated rule; clarify ambiguous instructions.
- **Error category on failure:** `prompt_violation`

| Score | Criteria |
|---|---|
| 5 | All instructions followed precisely. Stayed within role/scope. |
| 4 | All critical instructions followed. One minor deviation. |
| 3 | One meaningful instruction violated. Core functionality intact. |
| 2 | Multiple instructions violated. Partially outside defined boundaries. |
| 1 | Most instructions ignored. Largely operating outside its defined role. |
| 0 | Agent completely disregards system prompt and business rules. |

### 6. Information Gathering

- **ID:** `information_gathering`
- **Tier:** Process
- **Default weight:** 0.10
- **Measures:** Required info collected before action; previously stated info reused.
- **What to fix:** Required-fields checklist, context window, slot prompts.
- **Error category on failure:** `incomplete`

| Score | Criteria |
|---|---|
| 5 | All required info collected before action. No redundant questions. |
| 4 | All critical info collected. One redundant question or minor missed detail. |
| 3 | One required field missing before action, or forgot one previously stated detail. |
| 2 | Multiple gaps in info collection. Acted on incomplete data. |
| 1 | Most required info not collected. Acted with largely incomplete data. |
| 0 | No info gathering attempted. |

### 7. Conversation Management

- **ID:** `conversation_management`
- **Tier:** Process
- **Default weight:** 0.10
- **Measures:** Ambiguity handling, error recovery, and conversation closure.
- **What to fix:** Flow logic, clarification prompts, closing sequence.
- **Error category on failure:** `incomplete`

| Score | Criteria |
|---|---|
| 5 | Ambiguity clarified. Errors acknowledged and corrected. Proper goodbye. |
| 4 | Good management overall. One minor missed opportunity. |
| 3 | One meaningful management failure. |
| 2 | Multiple management failures. Conversation disjointed. |
| 1 | Conversation poorly managed throughout. |
| 0 | No conversation management. Agent froze or produced incoherent sequence. |

### 8. Response Delivery

- **ID:** `response_delivery`
- **Tier:** Delivery
- **Default weight:** 0.10
- **Measures:** Concise, natural, TTS-friendly, non-repetitive responses.
- **What to fix:** Output formatting, max length, style instructions.
- **Error category on failure:** `other`

| Score | Criteria |
|---|---|
| 5 | All responses concise. Natural phrasing. No TTS-hostile formatting. |
| 4 | Mostly natural and concise. One minor issue. |
| 3 | One meaningful delivery issue (e.g. 2+ questions in one turn). |
| 2 | Multiple delivery issues. Robotic or verbose. |
| 1 | Pervasive delivery problems. |
| 0 | Responses entirely unsuitable for voice delivery. |

## Opt-in Metrics

### Task Completion (binary)

- **ID:** `task_completion`
- **Tier:** Execution
- **Default weight:** 0 (must supply explicit weight when selected)
- **Scale:** Binary pass/fail
- **Measures:** Whether the agent completed the primary task from `expected_outcomes`.
- **Error category on failure:** `incomplete`

To include this metric, add it to `JudgeConfig.metrics` with an explicit weight:

```json
{
  "metrics": [
    { "metric": "tool_routing", "weight": 1.0 },
    { "metric": "task_completion", "weight": 0.5 }
  ]
}
```

## Configuration

### JudgeConfig

| Field | Type | Default | Description |
|---|---|---|---|
| `metrics` | `list[MetricSelection] \| null` | `null` (use defaults) | Selected metrics with optional weight overrides. |
| `pass_threshold` | `float` | `75.0` | Minimum overall score (0-100) to pass. |
| `critical_failure_threshold` | `int` | `1` | Execution-tier scored metric at or below this triggers critical failure. |
| `model` | `string \| null` | `null` | Judge LLM model override. |
| `provider` | `string \| null` | `null` | Judge LLM provider override. |

### Weight Resolution

1. If `metrics` is `null` or empty, the 8 default scored metrics are used with
   their `default_weight` values.
2. Weights are **renormalized** to sum to 1.0 after selection.
3. `task_completion` requires an explicit weight when selected (its default
   weight is 0).

### Scenario-level Override

Each scenario can carry an `evaluation_criteria_override` (free text) that is
appended to the judge user prompt as a "Scenario-specific evaluation emphasis"
section. This allows scenario authors to add context without changing which
metrics are evaluated.

## API

### `GET /config/available-metrics`

Returns all registered metrics (including opt-in) for UI discovery.

```json
{
  "data": [
    {
      "name": "tool_routing",
      "display_name": "Tool Routing",
      "description": "Correct tool names and call sequence.",
      "what_to_fix": "Tool descriptions, selection logic, flow graph.",
      "tier": "execution",
      "default_weight": 0.15,
      "score_type": "scored",
      "rubric": "...",
      "failure_error_category": "tool_misuse",
      "include_in_defaults": true
    }
  ],
  "count": 9
}
```
