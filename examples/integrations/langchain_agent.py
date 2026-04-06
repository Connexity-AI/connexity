import json
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# NOTE: Models below mirror app.models.agent_contract (canonical source).
# They are duplicated here so this example stays self-contained / copy-paste
# friendly.  See docs/agent-contract.md for the authoritative spec.
# ---------------------------------------------------------------------------

app = FastAPI(title="LangChain agent adapter", version="0.1.0")

MODEL_NAME = "gpt-4o-mini"
MAX_TOOL_ROUNDS = 10


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


def platform_to_langchain(messages: list[ChatMessage]) -> list[Any]:
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
        ToolMessage,
    )

    out: list[Any] = []
    for m in messages:
        if m.role == "system":
            out.append(SystemMessage(content=m.content or ""))
        elif m.role == "user":
            out.append(HumanMessage(content=m.content or ""))
        elif m.role == "assistant":
            if m.tool_calls:
                lc_tool_calls = [
                    {
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments),
                        "id": tc.id,
                        "type": "tool_call",
                    }
                    for tc in m.tool_calls
                ]
                out.append(AIMessage(content=m.content or "", tool_calls=lc_tool_calls))
            else:
                out.append(AIMessage(content=m.content or ""))
        elif m.role == "tool":
            out.append(
                ToolMessage(
                    content=m.content or "",
                    tool_call_id=m.tool_call_id or "",
                    name=m.name or "",
                )
            )
    return out


def ai_message_to_contract(msg: Any) -> ChatMessage:
    content = msg.content if isinstance(msg.content, str) else None
    tool_calls_out: list[ToolCall] | None = None
    raw = getattr(msg, "tool_calls", None) or []
    if raw:
        tool_calls_out = []
        for tc in raw:
            if isinstance(tc, dict):
                name = tc.get("name", "")
                tid = tc.get("id", "")
                args = tc.get("args", {})
            else:
                name = getattr(tc, "name", "") or ""
                tid = getattr(tc, "id", "") or ""
                args = getattr(tc, "args", {}) or {}
            tool_calls_out.append(
                ToolCall(
                    id=tid or "call_unknown",
                    function=ToolFn(
                        name=name,
                        arguments=json.dumps(args)
                        if isinstance(args, dict)
                        else str(args),
                    ),
                )
            )
    return ChatMessage(role="assistant", content=content, tool_calls=tool_calls_out)


def merge_usage(acc: TokenUsage | None, msg: Any) -> TokenUsage | None:
    def _sum(a: int | None, b: int | None) -> int | None:
        if a is None and b is None:
            return None
        return (a or 0) + (b or 0)

    meta = getattr(msg, "response_metadata", {}) or {}
    token_usage = meta.get("token_usage") or {}
    pt = token_usage.get("prompt_tokens")
    ct = token_usage.get("completion_tokens")
    tt = token_usage.get("total_tokens")
    if pt is None and ct is None and tt is None:
        usage_meta = getattr(msg, "usage_metadata", None)
        if usage_meta:
            pt = getattr(usage_meta, "input_tokens", None)
            ct = getattr(usage_meta, "output_tokens", None)
            tt = getattr(usage_meta, "total_tokens", None)

    if pt is None and ct is None and tt is None:
        return acc
    if acc is None:
        return TokenUsage(prompt_tokens=pt, completion_tokens=ct, total_tokens=tt)
    return TokenUsage(
        prompt_tokens=_sum(acc.prompt_tokens, pt),
        completion_tokens=_sum(acc.completion_tokens, ct),
        total_tokens=_sum(acc.total_tokens, tt),
    )


@app.post("/agent/respond", response_model=AgentResponse)
async def respond(body: AgentRequest) -> AgentResponse:
    from langchain_core.messages import ToolMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI

    @tool
    def check_service_area(zone: str) -> str:
        """Check whether we service a given postal/zip code area."""
        z = zone.replace(" ", "").upper()
        return json.dumps({"serviced": True, "region": "Metro Vancouver", "zone": z})

    tools = [check_service_area]
    tools_by_name = {t.name: t for t in tools}

    lc_messages = platform_to_langchain(body.messages)
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    contract_messages: list[ChatMessage] = []
    usage_acc: TokenUsage | None = None

    for _ in range(MAX_TOOL_ROUNDS):
        ai_msg = await llm_with_tools.ainvoke(lc_messages)
        lc_messages.append(ai_msg)
        contract_messages.append(ai_message_to_contract(ai_msg))
        usage_acc = merge_usage(usage_acc, ai_msg)

        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        if not tool_calls:
            break

        for tc in tool_calls:
            if isinstance(tc, dict):
                name = tc.get("name", "")
                tid = tc.get("id", "")
                args = tc.get("args", {})
            else:
                name = getattr(tc, "name", "") or ""
                tid = getattr(tc, "id", "") or ""
                args = getattr(tc, "args", {}) or {}
            tcallable = tools_by_name.get(name)
            if tcallable is None:
                out = json.dumps({"error": f"unknown tool: {name}"})
            else:
                invoked = tcallable.invoke(args)
                out = invoked if isinstance(invoked, str) else str(invoked)
            tm = ToolMessage(content=out, tool_call_id=tid, name=name)
            lc_messages.append(tm)
            contract_messages.append(
                ChatMessage(
                    role="tool",
                    content=out,
                    tool_call_id=tid,
                    name=name,
                )
            )

    if contract_messages and contract_messages[-1].tool_calls:
        contract_messages.append(
            ChatMessage(
                role="assistant",
                content="[Agent stopped: maximum tool rounds reached]",
            )
        )

    return AgentResponse(
        messages=contract_messages,
        model=MODEL_NAME,
        provider="openai",
        usage=usage_acc,
        metadata={},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("langchain_agent:app", host="0.0.0.0", port=8003, reload=True)
