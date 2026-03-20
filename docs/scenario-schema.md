# Scenario Schema Specification

**Schema version:** 1.0.0

## Design Principles

1. Scenarios do **NOT** contain `agent_system_prompt` or `agent_tools`. Those are captured on the **Run** entity at eval execution time.
2. `user_context` is a **free-form dict** — the simulator prompt receives it as a JSON dump. Any domain-specific fields work automatically.
3. `expected_outcomes` is also **free-form** — keys are descriptive labels the judge interprets semantically, not code-parsed enums.
4. `expected_tool_calls` defines which tools the agent should (or should not) call, and what parameters are expected. The platform handles mock dispatch and response injection separately from the scenario definition.
5. Simulation is always **LLM-persona-driven**: the LLM imitates a specific user via a system prompt built from `persona` + `user_context`.
6. `max_turns` is **nullable** — when omitted or set to `null`, the conversation runs until the agent or simulator terminates it naturally (no cap).

---

## Field Reference

### Top-level Fields

| Field | Type | Default | Required | Description |
|-------|------|---------|----------|-------------|
| `name` | `str` | — | Yes | Human-readable short name (max 255 chars) |
| `description` | `str \| null` | `null` | No | What this scenario tests (for humans) |
| `difficulty` | `"normal" \| "hard"` | `"normal"` | No | Two-level difficulty for filtering and weighting |
| `tags` | `list[str]` | `[]` | No | Free-form tags for grouping/filtering. Pre-seeded: `"normal"`, `"red-team"`, `"edge-case"` |
| `status` | `"draft" \| "active" \| "archived"` | `"active"` | No | Lifecycle state. Only `active` scenarios run by default |
| `persona` | `Persona \| null` | `null` | No | Who the simulated user is (see nested type below) |
| `initial_message` | `str \| null` | `null` | No | First message the simulated user sends to the agent |
| `user_context` | `dict[str, Any] \| null` | `null` | No | Free-form knowledge the user "has". JSON-dumped into simulator prompt. Domain-specific: add any fields needed |
| `max_turns` | `int \| null` | `null` | No | Max conversation turns. `null` = no cap, conversation runs until agent or simulator terminates naturally |
| `expected_outcomes` | `dict[str, Any] \| null` | `null` | No | Free-form success criteria. Keys = descriptive labels, values = expected state (bool, string, etc.). Judge interprets semantically |
| `expected_tool_calls` | `list[ExpectedToolCall] \| null` | `null` | No | Tool call expectations for judge evaluation (see nested type below) |
| `evaluation_criteria_override` | `str \| null` | `null` | No | Custom judge prompt section. Overrides default criteria for this scenario |

### Database-only Fields (auto-generated)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `uuid` | Primary key, auto-generated |
| `created_at` | `datetime` | Server-set on creation |
| `updated_at` | `datetime` | Server-set on each update |

---

## Nested Types

### Persona

Controls who the simulated user is. Dumped into the LLM simulator's system prompt.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Short persona archetype label (e.g. `"polite-customer"`, `"frustrated-user"`) |
| `description` | `str` | Yes | Detailed persona description |
| `instructions` | `str` | Yes | Behavioral directives for the LLM simulator |

### ExpectedToolCall

Defines which tools the agent should call during the scenario.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool` | `str` | Yes | Tool/function name the agent should invoke |
| `expected_params` | `dict[str, Any] \| null` | No | Key parameters the judge verifies. `null` = any params acceptable |

---

## How Attributes Are Consumed

| Attribute | Consumer | Purpose |
|-----------|----------|---------|
| `id` | Runner, DB, dashboard | Unique identification, logging, storage |
| `name`, `description` | Dashboard, docs | Human-readable display |
| `difficulty` | Selector, dashboard | Filtering, distribution weighting |
| `tags` | Selector, dashboard | Grouping, filtering |
| `status` | CRUD API, selector | Lifecycle — only `active` scenarios run by default |
| `persona` | Simulator prompt builder | Dumped into LLM system prompt — controls behavior and tone |
| `initial_message` | Simulator, judge | First turn sent to agent; shown to judge as context |
| `user_context` | Simulator prompt builder | JSON-dumped into simulator prompt as domain knowledge |
| `max_turns` | Runner | Caps conversation length; `null` = unlimited |
| `expected_outcomes` | Judge | Free-form criteria the judge evaluates against |
| `expected_tool_calls` | Judge | Verifies correct tool usage and parameters |
| `evaluation_criteria_override` | Judge | Replaces default judge criteria for this scenario |

---

## Validation Constraints

- `name` is required and must be ≤ 255 characters.
- `difficulty` must be one of: `normal`, `hard`.
- `status` must be one of: `draft`, `active`, `archived`.
- `tags` is a PostgreSQL `TEXT[]` column with a GIN index for efficient containment queries.
- `persona`, `user_context`, `expected_outcomes`, `expected_tool_calls` are stored as JSONB columns.
- All JSONB fields are nullable — omitting them is valid for draft or minimal scenarios.

---

## Example

```json
{
  "name": "Refund Request — Valid",
  "description": "Customer requests refund within 30-day window",
  "difficulty": "normal",
  "tags": ["billing", "refund", "happy-path"],
  "status": "active",
  "persona": {
    "type": "polite-customer",
    "description": "Polite customer who purchased 5 days ago",
    "instructions": "Be cooperative but insistent on getting a full refund. Provide order number when asked."
  },
  "initial_message": "Hi, I'd like to request a refund for my recent order.",
  "user_context": {
    "order_id": "ORD-12345",
    "purchase_date": "2026-03-15",
    "amount": 49.99
  },
  "max_turns": 10,
  "expected_outcomes": {
    "refund_initiated": true,
    "customer_satisfied": true
  },
  "expected_tool_calls": [
    {
      "tool": "lookup_order",
      "expected_params": { "order_id": "ORD-12345" }
    }
  ]
}
```

See `examples/scenarios/` for more examples covering normal, red-team, edge-case, tool-heavy, and multi-turn scenarios.
