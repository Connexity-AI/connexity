# Data Model — connexity-evals

## Entity Relationship Diagram

```mermaid
erDiagram
    Agent ||--o{ Run : "tested in"
    EvalSet ||--o{ Run : "evaluated by"
    EvalSet ||--o{ EvalSetMember : "contains"
    TestCase ||--o{ EvalSetMember : "belongs to"
    Run ||--o{ TestCaseResult : "produces"
    TestCase ||--o{ TestCaseResult : "evaluated in"

    Agent {
        uuid id PK
        string name
        string description
        enum mode
        string endpoint_url
        text system_prompt
        jsonb tools
        string agent_model
        string agent_provider
        jsonb metadata
        timestamp created_at
        timestamp updated_at
    }

    TestCase {
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

    EvalSet {
        uuid id PK
        string name
        string description
        int version
        timestamp created_at
        timestamp updated_at
    }

    EvalSetMember {
        uuid eval_set_id FK
        uuid test_case_id FK
        int position
    }

    Run {
        uuid id PK
        string name
        uuid agent_id FK
        string agent_endpoint_url
        text agent_system_prompt
        jsonb agent_tools
        string agent_mode
        string agent_model
        string agent_provider
        uuid eval_set_id FK
        int eval_set_version
        jsonb config
        enum status
        bool is_baseline
        jsonb aggregate_metrics
        timestamp started_at
        timestamp completed_at
        timestamp created_at
        timestamp updated_at
    }

    TestCaseResult {
        uuid id PK
        uuid run_id FK
        uuid test_case_id FK
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
| `TestCaseStatus` | `draft`, `active`, `archived` |
| `RunStatus` | `pending`, `running`, `completed`, `failed`, `cancelled` |
| `TurnRole` | `user`, `assistant`, `system`, `tool` |
| `AgentMode` | `endpoint`, `platform` |

## JSONB Nested Entities

These are stored inside JSONB columns, not as separate tables.

### RunConfig (stored in `runs.config`)

| Field | Type | Default |
|-------|------|---------|
| `concurrency` | `int` | `5` |
| `timeout_per_test_case_ms` | `int` | `120000` |
| `judge` | `JudgeConfig \| None` | `None` |
| `user_simulator` | `UserSimulatorConfig \| None` | `None` |
| `agent_simulator` | `AgentSimulatorConfig \| None` | `None` |

### JudgeConfig (nested in `RunConfig.judge`)

| Field | Type | Default |
|-------|------|---------|
| `metrics` | `list[MetricSelection] \| None` | `None` |
| `pass_threshold` | `float` | `75.0` |
| `model` | `str \| None` | `None` |
| `provider` | `str \| None` | `None` |

### UserSimulatorConfig (nested in `RunConfig.user_simulator`)

| Field | Type | Default |
|-------|------|---------|
| `mode` | `SimulatorMode` | `llm` |
| `scripted_messages` | `list[str]` | `[]` |
| `model` | `str \| None` | `None` |
| `provider` | `str \| None` | `None` |
| `temperature` | `float \| None` | `None` |

### AgentSimulatorConfig (nested in `RunConfig.agent_simulator`)

| Field | Type | Default |
|-------|------|---------|
| `model` | `str \| None` | `None` |
| `provider` | `str \| None` | `None` |
| `temperature` | `float \| None` | `None` |
| `max_tokens` | `int \| None` | `None` |

### ConversationTurn (stored in `test_case_result.transcript`)

| Field | Type |
|-------|------|
| `index` | `int` |
| `role` | `TurnRole` |
| `content` | `str \| None` |
| `tool_calls` | `list[ToolCall] \| None` |
| `tool_call_id` | `str \| None` |
| `latency_ms` | `int \| None` |
| `token_count` | `int \| None` |
| `timestamp` | `datetime` |

### ToolCall (nested in `ConversationTurn.tool_calls`)

OpenAI chat-completions shape, plus optional `tool_result` for platform-stored outcomes.

| Field | Type |
|-------|------|
| `id` | `str` |
| `type` | `function` |
| `function` | `ToolCallFunction` (`name`, `arguments` JSON string) |
| `tool_result` | `Any \| None` |

### JudgeVerdict (stored in `test_case_result.verdict`)

| Field | Type | Default |
|-------|------|---------|
| `passed` | `bool` | — |
| `overall_score` | `float` | — |
| `metric_scores` | `list[MetricScore]` | — |
| `summary` | `str \| None` | `None` |
| `raw_judge_output` | `str \| None` | `None` |
| `judge_model` | `str` | — |
| `judge_provider` | `str` | — |
| `judge_latency_ms` | `int \| None` | `None` |
| `judge_token_usage` | `dict[str, int] \| None` | `None` |

### MetricScore (nested in `JudgeVerdict.metric_scores`)

| Field | Type | Default |
|-------|------|---------|
| `metric` | `str` | — |
| `score` | `int` | — (0–5 scored; 0 or 5 binary) |
| `label` | `str` | — (critical_fail\|fail\|poor\|acceptable\|good\|excellent / pass\|fail) |
| `weight` | `float` | `1.0` |
| `justification` | `str` | — |
| `is_binary` | `bool` | `false` |
| `tier` | `str \| None` | `None` |
| `failure_code` | `str \| None` | `None` — judge-generated label when metric scored poorly |
| `turns` | `list[int]` | `[]` — turn indices where the issue was observed |

### AggregateMetrics (stored in `runs.aggregate_metrics`)

| Field | Type | Default |
|-------|------|---------|
| `unique_test_case_count` | `int` | — |
| `total_executions` | `int` | — |
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
| `avg_overall_score` | `float \| None` | `None` |

### Persona (stored in `test_case.persona`)

| Field | Type |
|-------|------|
| `type` | `str` |
| `description` | `str` |
| `instructions` | `str` |

### ExpectedToolCall (stored in `test_case.expected_tool_calls`)

| Field | Type | Default |
|-------|------|---------|
| `tool` | `str` | — |
| `expected_params` | `dict[str, Any] \| None` | `None` |

### expected_outcomes (stored in `test_case.expected_outcomes`)

Free-form `dict[str, Any]`. Keys are descriptive labels (e.g. `"refund_initiated"`), values are expected state (bool, string, etc.). The judge interprets these semantically.

## Indexes

| Table | Index | Type |
|-------|-------|------|
| `test_case` | `difficulty` | btree |
| `test_case` | `status` | btree |
| `test_case` | `tags` | GIN |
| `eval_set` | `name` | btree |
| `eval_set_member` | `eval_set_id` | btree |
| `run` | `agent_id` | btree |
| `run` | `eval_set_id` | btree |
| `run` | `status` | btree |
| `run` | `is_baseline` | btree |
| `run` | `created_at` | btree |
| `test_case_result` | `run_id` | btree |
| `test_case_result` | `test_case_id` | btree |
| `test_case_result` | `passed` | btree |

## Critical Design Decision

`agent_system_prompt`, `agent_tools`, and related agent snapshot fields live on the **Run** entity (captured at eval time), **NOT** on TestCase. Each run also records `agent_version` / `agent_version_id` pointing at the immutable **AgentVersion** row. This ensures that each evaluation run captures a complete snapshot of the agent configuration at that point in time.
