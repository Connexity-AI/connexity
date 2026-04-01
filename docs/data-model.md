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
        string agent_mode
        string agent_model
        string agent_provider
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
| `TurnRole` | `user`, `assistant`, `system`, `tool` |
| `AgentMode` | `endpoint`, `platform` |

## JSONB Nested Entities

These are stored inside JSONB columns, not as separate tables.

### RunConfig (stored in `runs.config`)

| Field | Type | Default |
|-------|------|---------|
| `concurrency` | `int` | `5` |
| `timeout_per_scenario_ms` | `int` | `120000` |
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

### ConversationTurn (stored in `scenario_results.transcript`)

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

### JudgeVerdict (stored in `scenario_results.verdict`)

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

## Critical Design Decision

`agent_system_prompt`, `agent_tools`, and `tools_snapshot` live on the **Run** entity (captured at eval time), **NOT** on Scenario. This ensures that each evaluation run captures a complete snapshot of the agent configuration at that point in time.
