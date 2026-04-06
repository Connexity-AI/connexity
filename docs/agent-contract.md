# Agent HTTP contract

Eval agents expose a single HTTP endpoint that accepts an OpenAI-style chat history and returns **all messages produced in that turn** (assistant with optional tool calls, `tool` role results, final assistant reply), plus optional `model`, `provider`, `usage`, and `metadata`. This is **not** a custom protocol: it matches OpenAI-compatible chat message shapes so frameworks can adapt with thin wrappers.

Canonical Pydantic models live in the backend at `app.models.agent_contract` (`AgentRequest`, `AgentResponse`, `ChatMessage`, `TokenUsage`, …) and reuse `ToolCall` / `ToolCallFunction` from `app.models.schemas` for tool-call shape.

## Endpoint

| | |
|---|---|
| **Method / path** | `POST /agent/respond` |
| **Content-Type** | `application/json` |
| **Auth** | Your deployment (API key, mTLS, etc.) — not defined by this contract |

The platform stores the full URL on the `Agent` record (e.g. `https://your-host/agent/respond`). The path segment `/agent/respond` is the recommended convention used by the reference [mock agent](../examples/mock_agent/).

## Request body (`AgentRequest`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | `array` | yes | Ordered chat messages (OpenAI roles). |
| `metadata` | `object` | no | Platform context for logging / evaluation. |

### `messages[]` (`ChatMessage`)

The platform sends **conversation history** between the user simulator and the agent. Typical roles in requests are `system` (optional), `user`, and `assistant` (prior turns). The platform does **not** send `role: tool` messages or inject tool results — the agent executes tools internally and returns those steps in the **response**.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | yes | One of `system`, `user`, `assistant`, `tool`. |
| `content` | string \| null | no | Text body; may be omitted when `tool_calls` is present on `assistant`. |
| `tool_calls` | array | no | On `assistant`, OpenAI-style tool calls from **prior** assistant turns (if you echo them in history). |
| `tool_call_id` | string \| null | no | On `tool`, id of the call this message answers (normally not sent by the platform). |
| `name` | string \| null | no | On `tool`, optional function name (OpenAI convention). |

### `metadata` (`AgentRequestMetadata`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_case_id` | string \| null | no | Test case identifier from the eval platform. |
| `turn_index` | integer \| null | no | Zero-based turn index in the conversation. |

### Tool call object (`ToolCall`)

Same shape as OpenAI chat completions, plus an optional platform field on **stored transcripts** (not required on the wire from the agent):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique id (e.g. `call_abc123`). |
| `type` | string | yes | Must be `function`. |
| `function` | object | yes | `name` (string), `arguments` (JSON **string**). |
| `tool_result` | any | no | Filled by the platform when persisting transcript turns after ingestion (optional). |

## Response body (`AgentResponse`)

The agent runs its own tool loop. One `POST /agent/respond` may include multiple LLM steps; the response lists **every** assistant and `tool` message produced before the turn completes (final assistant message without pending tool calls).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `messages` | `array` | yes | Ordered `ChatMessage` items for this turn (see below). |
| `model` | string \| null | no | Model identifier used (e.g. `gpt-4o`). |
| `provider` | string \| null | no | Provider identifier (e.g. `openai`, `anthropic`). |
| `usage` | object \| null | no | Aggregate token usage for the whole turn (optional). |
| `metadata` | object \| null | no | Agent-defined key/value metadata for observability (optional). |

### Typical `messages` sequence when tools are used

1. `role: assistant` — may include `content` and/or `tool_calls`.
2. One `role: tool` message per executed call (`tool_call_id`, `name`, `content` with string output).
3. Repeat 1–2 if the model chains multiple tool rounds.
4. Final `role: assistant` with the user-facing reply (usually no `tool_calls`).

For a simple reply with no tools, `messages` is a **single** assistant message.

### `usage` (`TokenUsage`)

All fields optional; include whatever your stack reports (often **summed** across internal LLM calls in the turn).

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | integer | Tokens in prompts for this turn. |
| `completion_tokens` | integer | Tokens in completions for this turn. |
| `total_tokens` | integer | Total if available. |

## Example payloads

### 1. Simple text reply

**Request**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hi, I'd like to book a duct cleaning."
    }
  ],
  "metadata": {
    "test_case_id": "residential_duct_cleaning_happy_path",
    "turn_index": 0
  }
}
```

**Response**

```json
{
  "messages": [
    {
      "role": "assistant",
      "content": "I can help with that. What is your postal code?"
    }
  ],
  "model": "gpt-4o",
  "provider": "openai",
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 18
  },
  "metadata": {}
}
```

### 2. Tool call, tool result, and final reply (agent-side execution)

**Request**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hi, I'd like to book a duct cleaning."
    },
    {
      "role": "assistant",
      "content": "Sure! Can I get your postal code?"
    },
    {
      "role": "user",
      "content": "V4T 0A7"
    }
  ],
  "metadata": {
    "test_case_id": "residential_duct_cleaning_happy_path",
    "turn_index": 2
  }
}
```

**Response**

```json
{
  "messages": [
    {
      "role": "assistant",
      "content": "Let me check if we service your area.",
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "check_service_area",
            "arguments": "{\"zone\": \"V4T0A7\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "name": "check_service_area",
      "content": "{\"serviced\": true, \"region\": \"Metro Vancouver\"}"
    },
    {
      "role": "assistant",
      "content": "Great news — we service V4T 0A7 in Metro Vancouver. What day works best for you?"
    }
  ],
  "model": "gpt-4o",
  "provider": "openai",
  "usage": {
    "prompt_tokens": 245,
    "completion_tokens": 82
  },
  "metadata": {}
}
```

### 3. Refusal / error-style response (HTTP 200)

Agents should still return valid JSON when they refuse or explain an error, unless you use HTTP error codes intentionally.

**Response**

```json
{
  "messages": [
    {
      "role": "assistant",
      "content": "I can't help with that request. I can only assist with duct cleaning bookings and service area questions."
    }
  ],
  "model": "gpt-4o",
  "provider": "openai",
  "metadata": {}
}
```

For hard transport failures (timeout, 5xx), the platform run records an appropriate error category.

## OpenAPI (machine-readable)

- **Reference implementation:** run the mock agent (`examples/mock_agent/`) and open its `/docs` — FastAPI generates OpenAPI from the same request/response shapes.
- **Backend models:** `AgentRequest` / `AgentResponse` are part of the Python package for the runner and tests; the main Connexity API OpenAPI documents test-case/run resources that *reference* transcript types (`ConversationTurn`, `ToolCall`).

## Examples in this repo

| Path | Purpose |
|------|---------|
| [examples/mock_agent/](../examples/mock_agent/) | Tiny FastAPI agent for local testing and onboarding. |
| [examples/integrations/raw_python_agent.py](../examples/integrations/raw_python_agent.py) | Wrap the OpenAI SDK with an internal tool loop. |
| [examples/integrations/langchain_agent.py](../examples/integrations/langchain_agent.py) | LangChain chat model + tools, mapped to this contract. |

## What this is not

- Not a separate proprietary protocol — OpenAI-compatible messages and tool calls.
- Not an SDK — HTTP + JSON only.
- Not tied to a single framework — any stack that can parse and emit JSON can implement `POST /agent/respond`.
- Not platform-executed tools — the eval platform does not run your tools; the agent returns tool results in `messages`.
