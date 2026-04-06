import json
from typing import Any, Literal

from fastapi import FastAPI
from openai import AsyncOpenAI
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# NOTE: Models below mirror app.models.agent_contract (canonical source).
# They are duplicated here so this example stays self-contained / copy-paste
# friendly.  See docs/agent-contract.md for the authoritative spec.
# ---------------------------------------------------------------------------

app = FastAPI(title="Raw Python agent (OpenAI SDK)", version="0.1.0")
client = AsyncOpenAI()

MODEL_NAME = "gpt-4o-mini"
MAX_TOOL_ROUNDS = 10

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_service_area",
            "description": "Check whether we service a given postal/zip code area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {
                        "type": "string",
                        "description": "Postal or zip code (whitespace stripped)",
                    }
                },
                "required": ["zone"],
            },
        },
    }
]


class ToolFn(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: ToolFn


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class AgentRequest(BaseModel):
    messages: list[ChatMessage]
    # Platform sends {"test_case_id": "...", "turn_index": 0}
    # We accept any dict here for simplicity; see app.models.agent_contract.AgentRequestMetadata
    metadata: dict[str, Any] | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class AgentResponse(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    provider: str | None = None
    usage: TokenUsage | None = None
    metadata: dict[str, Any] | None = None


def check_service_area(zone: str) -> dict[str, Any]:
    z = zone.replace(" ", "").upper()
    return {"serviced": True, "region": "Metro Vancouver", "zone": z}


TOOL_REGISTRY: dict[str, Any] = {"check_service_area": check_service_area}


def _run_tool(name: str, arguments_json: str) -> str:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "invalid JSON arguments"})
    try:
        out = fn(**args) if isinstance(args, dict) else fn(args)
        return json.dumps(out) if not isinstance(out, str) else out
    except TypeError:
        return json.dumps({"error": "tool argument mismatch"})


def _sum_tokens(a: int | None, b: int | None) -> int | None:
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def _merge_usage(acc: TokenUsage | None, usage: Any) -> TokenUsage | None:
    if not usage:
        return acc
    pt = usage.prompt_tokens
    ct = usage.completion_tokens
    tt = usage.total_tokens
    if acc is None:
        if pt is None and ct is None and tt is None:
            return None
        return TokenUsage(prompt_tokens=pt, completion_tokens=ct, total_tokens=tt)
    return TokenUsage(
        prompt_tokens=_sum_tokens(acc.prompt_tokens, pt),
        completion_tokens=_sum_tokens(acc.completion_tokens, ct),
        total_tokens=_sum_tokens(acc.total_tokens, tt),
    )


@app.post("/agent/respond", response_model=AgentResponse)
async def respond(request: AgentRequest) -> AgentResponse:
    openai_messages: list[dict[str, Any]] = [
        m.model_dump(exclude_none=True) for m in request.messages
    ]
    turn_messages: list[ChatMessage] = []
    usage_acc: TokenUsage | None = None

    for _ in range(MAX_TOOL_ROUNDS):
        completion = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=openai_messages,
            tools=OPENAI_TOOLS,
            temperature=0,
        )
        usage_acc = _merge_usage(usage_acc, completion.usage)
        choice = completion.choices[0].message

        tool_calls_out: list[ToolCall] | None = None
        if choice.tool_calls:
            tool_calls_out = [
                ToolCall(
                    id=tc.id,
                    function=ToolFn(name=tc.function.name, arguments=tc.function.arguments),
                )
                for tc in choice.tool_calls
            ]

        assistant_cm = ChatMessage(
            role="assistant",
            content=choice.content,
            tool_calls=tool_calls_out,
        )
        turn_messages.append(assistant_cm)
        openai_messages.append(choice.model_dump(exclude_none=True))

        if not choice.tool_calls:
            break

        for tc in choice.tool_calls:
            result_str = _run_tool(tc.function.name, tc.function.arguments)
            openai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result_str,
                }
            )
            turn_messages.append(
                ChatMessage(
                    role="tool",
                    tool_call_id=tc.id,
                    name=tc.function.name,
                    content=result_str,
                )
            )

    if turn_messages and turn_messages[-1].tool_calls:
        turn_messages.append(
            ChatMessage(
                role="assistant",
                content="[Agent stopped: maximum tool rounds reached]",
            )
        )

    return AgentResponse(
        messages=turn_messages,
        model=MODEL_NAME,
        provider="openai",
        usage=usage_acc,
        metadata={},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("raw_python_agent:app", host="0.0.0.0", port=8002, reload=True)
