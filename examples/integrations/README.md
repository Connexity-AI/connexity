# Agent integration examples

Runnable adapters that match the [text agent HTTP contract](../../docs/text-agent-contract.md). Both call real LLMs, run an **internal tool loop** (execute tools on the agent side, then continue the model), and return a `messages` array plus `model`, `provider`, `usage`, and `metadata`.

## `raw_python_agent.py`

Uses the OpenAI Python SDK directly. Loops: chat completion → if `tool_calls`, run `check_service_area` locally → append tool messages → call again until the model returns text only. Aggregates token usage across steps.

```bash
cd examples/integrations
pip install fastapi uvicorn pydantic openai
export OPENAI_API_KEY=sk-...
uvicorn raw_python_agent:app --reload --port 8002
```

## `langchain_agent.py`

Converts platform messages to LangChain `BaseMessage` types, uses `ChatOpenAI` with `bind_tools`, runs the same assistant/tool loop, and maps every step to the contract `messages` list. Usage is merged from `response_metadata` / `usage_metadata` when present.

```bash
cd examples/integrations
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
uvicorn langchain_agent:app --reload --port 8003
```

Swap `ChatOpenAI` for another LangChain chat model that supports tool calling if you use a different provider.

## Note on model duplication

Both examples intentionally define their own Pydantic request/response models so they stay self-contained and easy to copy. The canonical models live in `app.models.agent_contract` (`AgentRequest`, `AgentResponse`, `ChatMessage`, `TokenUsage`, etc.).

## Contract reference

See [docs/text-agent-contract.md](../../docs/text-agent-contract.md) and the [mock text agent](../mock-text-agent/) OpenAPI at `/docs`.
