# Data Model — connexity-evals

## Entity Relationship Diagram

```mermaid
erDiagram
    Agent ||--o{ Run : "tested in"
    ScenarioSet ||--o{ Run : "evaluated by"
    ScenarioSet ||--o{ ScenarioSetMember : "contains"
    Scenario ||--o{ ScenarioSetMember : "belongs to"
    Run ||--o{ ScenarioResult : "produces"
    Scenario ||--o{ ScenarioResult : "evaluated in"

    Agent {
        uuid id PK
        string name
        string description
        string endpoint_url
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    Scenario {
        uuid id PK
        string name
        string description
        enum difficulty
        text_array tags
        enum status
        jsonb persona
        string initial_message
        jsonb user_context
        int max_turns
        jsonb expected_outcomes
        jsonb expected_tool_calls
        string evaluation_criteria_override
        timestamp created_at
        timestamp updated_at
    }

    ScenarioSet {
        uuid id PK
        string name
        string description
        int version
        timestamp created_at
        timestamp updated_at
    }

    ScenarioSetMember {
        uuid scenario_set_id FK
        uuid scenario_id FK
        int position
    }

    Run {
        uuid id PK
        string name
        uuid agent_id FK
        string agent_endpoint_url
        text agent_system_prompt
        jsonb agent_tools
        string prompt_version
        text prompt_snapshot
        jsonb tools_snapshot
        string tools_snapshot_hash
        uuid scenario_set_id FK
        int scenario_set_version
        jsonb config
        enum status
        bool is_baseline
        jsonb aggregate_metrics
        timestamp started_at
        timestamp completed_at
        timestamp created_at
        timestamp updated_at
    }

    ScenarioResult {
        uuid id PK
        uuid run_id FK
        uuid scenario_id FK
        jsonb transcript
        int turn_count
        jsonb verdict
        int total_latency_ms
        int agent_latency_p50_ms
        int agent_latency_p95_ms
        int agent_latency_max_ms
        jsonb agent_token_usage
        jsonb platform_token_usage
        float estimated_cost_usd
        bool passed
        enum error_category
        text error_message
        timestamp started_at
        timestamp completed_at
        timestamp created_at
        timestamp updated_at
    }
```

## Enums

| Enum | Values |
|------|--------|
| `Difficulty` | `normal`, `hard` |
| `ScenarioStatus` | `draft`, `active`, `archived` |
| `RunStatus` | `pending`, `running`, `completed`, `failed`, `cancelled` |
| `ErrorCategory` | `none`, `off_topic`, `hallucination`, `refusal`, `tool_misuse`, `safety_violation`, `prompt_violation`, `incomplete`, `latency_timeout`, `agent_error`, `other` |
| `TurnRole` | `user`, `agent`, `system` |

## JSONB Nested Entities

These are stored inside JSONB columns, not as separate tables.

### RunConfig (stored in `runs.config`)

| Field | Type | Default |
|-------|------|---------|
| `judge_model` | `str \| None` | `None` |
| `judge_provider` | `str \| None` | `None` |
| `simulator_model` | `str \| None` | `None` |
| `simulator_provider` | `str \| None` | `None` |
| `concurrency` | `int` | `5` |
| `timeout_per_scenario_ms` | `int` | `120000` |

### ConversationTurn (stored in `scenario_results.transcript`)

| Field | Type |
|-------|------|
| `index` | `int` |
| `role` | `TurnRole` |
| `content` | `str` |
| `tool_calls` | `list[ToolCall] \| None` |
| `latency_ms` | `int \| None` |
| `token_count` | `int \| None` |
| `timestamp` | `datetime` |

### ToolCall (nested in `ConversationTurn.tool_calls`)

| Field | Type |
|-------|------|
| `tool_name` | `str` |
| `tool_input` | `dict[str, Any]` |
| `tool_result` | `Any \| None` |

### JudgeVerdict (stored in `scenario_results.verdict`)

| Field | Type | Default |
|-------|------|---------|
| `passed` | `bool` | — |
| `overall_score` | `float` | — |
| `criterion_scores` | `list[CriterionScore]` | — |
| `error_category` | `ErrorCategory` | `none` |
| `summary` | `str` | — |
| `raw_judge_output` | `str \| None` | `None` |
| `judge_model` | `str` | — |
| `judge_provider` | `str` | — |
| `judge_latency_ms` | `int \| None` | `None` |
| `judge_token_usage` | `dict[str, int] \| None` | `None` |

### CriterionScore (nested in `JudgeVerdict.criterion_scores`)

| Field | Type | Default |
|-------|------|---------|
| `criterion` | `str` | — |
| `score` | `float` | — (1.0–5.0) |
| `label` | `str` | — (fail\|poor\|acceptable\|good\|excellent) |
| `weight` | `float` | `1.0` |
| `justification` | `str` | — |

### AggregateMetrics (stored in `runs.aggregate_metrics`)

| Field | Type | Default |
|-------|------|---------|
| `total_scenarios` | `int` | — |
| `passed_count` | `int` | — |
| `failed_count` | `int` | — |
| `error_count` | `int` | — |
| `pass_rate` | `float` | — |
| `latency_p50_ms` | `float \| None` | `None` |
| `latency_p95_ms` | `float \| None` | `None` |
| `latency_max_ms` | `float \| None` | `None` |
| `latency_avg_ms` | `float \| None` | `None` |
| `total_agent_token_usage` | `dict[str, int] \| None` | `None` |
| `total_platform_token_usage` | `dict[str, int] \| None` | `None` |
| `total_estimated_cost_usd` | `float \| None` | `None` |
| `error_category_distribution` | `list[ErrorCategoryCount]` | `[]` |
| `avg_overall_score` | `float \| None` | `None` |

### Persona (stored in `scenarios.persona`)

| Field | Type |
|-------|------|
| `type` | `str` |
| `description` | `str` |
| `instructions` | `str` |

### ExpectedToolCall (stored in `scenarios.expected_tool_calls`)

| Field | Type | Default |
|-------|------|---------|
| `tool` | `str` | — |
| `expected_params` | `dict[str, Any] \| None` | `None` |

### expected_outcomes (stored in `scenarios.expected_outcomes`)

Free-form `dict[str, Any]`. Keys are descriptive labels (e.g. `"refund_initiated"`), values are expected state (bool, string, etc.). The judge interprets these semantically.

## Indexes

| Table | Index | Type |
|-------|-------|------|
| `scenario` | `difficulty` | btree |
| `scenario` | `status` | btree |
| `scenario` | `tags` | GIN |
| `scenario_set` | `name` | btree |
| `scenario_set_member` | `scenario_set_id` | btree |
| `run` | `agent_id` | btree |
| `run` | `scenario_set_id` | btree |
| `run` | `status` | btree |
| `run` | `is_baseline` | btree |
| `run` | `created_at` | btree |
| `scenario_result` | `run_id` | btree |
| `scenario_result` | `scenario_id` | btree |
| `scenario_result` | `passed` | btree |
| `scenario_result` | `error_category` | btree |

## Critical Design Decision

`agent_system_prompt`, `agent_tools`, and `tools_snapshot` live on the **Run** entity (captured at eval time), **NOT** on Scenario. This ensures that each evaluation run captures a complete snapshot of the agent configuration at that point in time.
