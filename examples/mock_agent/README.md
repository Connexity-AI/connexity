# Mock agent

LLM-backed FastAPI service that implements the [agent HTTP contract](../../docs/agents/contract.md). Uses [LiteLLM](https://docs.litellm.ai/) — the same library as the backend's `app.services.llm` module — so it works with OpenAI, Anthropic, or any LiteLLM-supported provider.

Use it to verify your setup, run the eval suite against a real agent, or copy the patterns into your own service.

## Quick start

```bash
cd examples/mock_agent
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
uvicorn main:app --reload --port 8001
```

- **Health:** http://127.0.0.1:8001/health
- **Respond:** `POST http://127.0.0.1:8001/agent/respond`
- **OpenAPI:** http://127.0.0.1:8001/docs

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for the default model. |
| `MOCK_AGENT_MODEL` | `gpt-4o-mini` | Any LiteLLM model string (e.g. `anthropic/claude-3-5-haiku-20241022`). |

## Behavior

The agent has a customer-support system prompt and a `check_service_area` tool definition. When a user provides a postal code, the LLM will typically invoke the tool; this service **executes the tool locally** (mock implementation), calls the model again with the tool result, and returns the full turn as multiple messages (assistant → tool → assistant, etc.) per the [agent contract](../../docs/agents/contract.md). Token usage is aggregated across internal LLM calls. Response bodies include `model`, `provider`, `usage`, and `metadata`.

Point an `Agent` record's `endpoint_url` at `http://127.0.0.1:8001/agent/respond` when running evals.

## Note on model duplication

This example intentionally defines its own Pydantic request/response models so it stays self-contained and easy to copy. The canonical models live in `app.models.agent_contract` (`AgentRequest`, `AgentResponse`, `ChatMessage`, `TokenUsage`, etc.).
