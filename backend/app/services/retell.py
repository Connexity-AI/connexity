import asyncio
import logging
import time
from collections import deque
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Literal

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_RETELL_PLAYGROUND_MAX_ATTEMPTS = 4

# A caller that wants to know how often Retell throttled it sets a one-item list here;
# each "too many requests" answer from the playground adds one. Per task, so calls
# running side by side count their own.
PLAYGROUND_THROTTLED: ContextVar[list[int] | None] = ContextVar(
    "retell_playground_throttled", default=None
)
_RETELL_PLAYGROUND_BACKOFF_SECONDS = (1.0, 2.0, 4.0)


class RequestPacer:
    """Lets at most ``limit`` requests start in any ``window`` seconds, per key.

    Retell allows 8 playground completions per 2 seconds per organization; a run of
    many simulated calls would start more than that at once. Requests over the limit
    wait their turn here instead of being refused by Retell (Dmytro, 2026-11-20: "we
    can just throttle them 8 requests per two seconds"). It paces this process only:
    another server, or someone using Retell's own playground, shares the same limit,
    so a refusal is still retried.
    """

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self.enabled = True
        self._starts: dict[str, deque[float]] = {}

    async def wait(self, key: str) -> None:
        if not self.enabled:
            return
        starts = self._starts.setdefault(key, deque())
        while True:
            now = time.monotonic()
            while starts and now - starts[0] >= self.window:
                starts.popleft()
            if len(starts) < self.limit:
                # No await between the check and here, so two requests never take
                # the same slot.
                starts.append(now)
                return
            await asyncio.sleep(self.window - (now - starts[0]))


# Retell's documented limit for agent playground completions, per organization.
PLAYGROUND_PACER = RequestPacer(limit=8, window=2.0)


class RetellAgentSummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    is_published: bool = False
    version: int | None = None


class RetellChatMessage(BaseModel):
    role: str
    content: str | None = None
    message_id: str | None = None
    created_timestamp: int | None = None
    tool_call_id: str | None = None
    name: str | None = None
    arguments: str | None = None
    raw: dict[str, Any] | None = None


class RetellAgentPlaygroundCompletionResult(BaseModel):
    success: bool
    messages: list[RetellChatMessage] = Field(default_factory=list)
    latency_ms: int | None = None
    error_message: str | None = None
    current_state: str | None = None
    current_node_id: str | None = None
    dynamic_variables: dict[str, Any] = Field(default_factory=dict)
    call_ended: bool = False


class RetellCall(BaseModel):
    call_id: str
    agent_id: str | None = None
    start_timestamp: int | None = None
    end_timestamp: int | None = None
    call_status: str | None = None
    transcript_object: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


def _retell_response_detail(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text
    return str(detail)


def _parse_retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value.strip())
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _retell_duration_seconds(
    *, start_timestamp: int | None, end_timestamp: int | None
) -> int | None:
    if start_timestamp is None or end_timestamp is None:
        return None
    return (end_timestamp - start_timestamp) // 1000


def _is_finished_retell_call(
    *,
    status: str | None,
    start_timestamp: int | None,
    end_timestamp: int | None,
) -> bool:
    duration_seconds = _retell_duration_seconds(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    if duration_seconds is None or duration_seconds <= 0:
        return False
    normalized_status = (status or "").lower()
    return normalized_status in {"ended", "completed", "finished"}


_LIST_AGENTS_URL = "https://api.retellai.com/v2/list-agents"
_LIST_AGENTS_MAX_PAGES = 50


async def retell_key_status(api_key: str) -> Literal["ok", "refused", "unreachable"]:
    """Whether Retell accepts the key, refuses it, or could not be asked."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _LIST_AGENTS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                params={"limit": 1},
                json={},
                timeout=10.0,
            )
    except httpx.HTTPError:
        return "unreachable"
    if response.status_code == 200:
        return "ok"
    if response.status_code in (401, 403):
        return "refused"
    return "unreachable"


async def test_retell_connection(api_key: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _LIST_AGENTS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                params={"limit": 1},
                json={},
                timeout=10.0,
            )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def dedupe_retell_agents(agents: list[RetellAgentSummary]) -> list[RetellAgentSummary]:
    """One row per agent: Retell lists an agent once per version. The published, then
    the newest, version wins."""

    def priority(agent: RetellAgentSummary) -> tuple[int, int]:
        return (
            1 if agent.is_published else 0,
            agent.version if agent.version is not None else -1,
        )

    by_id: dict[str, RetellAgentSummary] = {}
    for agent in agents:
        existing = by_id.get(agent.agent_id)
        if existing is None or priority(agent) > priority(existing):
            by_id[agent.agent_id] = agent
    return list(by_id.values())


async def list_retell_agents(api_key: str) -> list[RetellAgentSummary]:
    """Every agent in the account, read page by page from Retell's agent list.

    The list carries no version or "published" flag per agent; an agent counts as
    published when it has a latest published version, and that is the version shown.
    """
    agents: list[RetellAgentSummary] = []
    pagination_key: str | None = None
    async with httpx.AsyncClient() as client:
        for _ in range(_LIST_AGENTS_MAX_PAGES):
            params: dict[str, Any] = {"limit": 1000}
            if pagination_key:
                params["pagination_key"] = pagination_key
            try:
                response = await client.post(
                    _LIST_AGENTS_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    params=params,
                    json={},
                    timeout=10.0,
                )
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502, detail="Failed to reach Retell API"
                ) from exc
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502, detail="Retell API returned an error"
                )
            body = _json_or_none(response)
            items = body.get("items") if isinstance(body, dict) else None
            if not isinstance(items, list):
                raise HTTPException(
                    status_code=502, detail="Retell API returned an unexpected answer"
                )
            for item in items:
                if not isinstance(item, dict) or not item.get("agent_id"):
                    continue
                published = item.get("latest_published_version")
                agents.append(
                    RetellAgentSummary(
                        agent_id=str(item["agent_id"]),
                        agent_name=item.get("agent_name"),
                        is_published=published is not None,
                        version=published if isinstance(published, int) else None,
                    )
                )
            next_key = body.get("pagination_key")
            if (
                not body.get("has_more")
                or not isinstance(next_key, str)
                or not next_key
            ):
                break
            pagination_key = next_key
    return agents


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


_LIST_CALLS_URL = "https://api.retellai.com/v3/list-calls"
# Full call records read at the same time during a pull.
_CALL_READ_CONCURRENCY = 5
# Calls Retell has not finished yet. A pull stops at the first one it lists.
_RETELL_IN_PROGRESS = {"registered", "ongoing"}


async def list_retell_calls(
    api_key: str,
    *,
    agent_id: str,
    start_after: datetime | None = None,
    limit: int = 100,
) -> list[RetellCall]:
    """Finished calls of one Retell agent, oldest first, each with its full record.

    Retell's call list no longer carries transcripts or recordings, so every finished
    call it lists is read once in full. If reading one fails, the result stops just
    before it, so the next pull, which starts after the newest call returned, asks for
    it again. A call Retell no longer has is skipped.

    If ``start_after`` is given, only calls that started strictly after it are listed.
    """
    filter_criteria: dict[str, Any] = {"agent": [{"agent_id": agent_id}]}
    if start_after is not None:
        # Retell timestamps are epoch milliseconds.
        filter_criteria["start_timestamp"] = {
            "type": "number",
            "op": "gt",
            "value": int(start_after.timestamp() * 1000),
        }
    body = {
        "filter_criteria": filter_criteria,
        "limit": limit,
        "sort_order": "ascending",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _LIST_CALLS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Retell API"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Retell API returned an error")

    payload = _json_or_none(response)
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise HTTPException(
            status_code=502, detail="Retell API returned an unexpected answer"
        )

    finished: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("call_id"):
            continue
        if str(item.get("call_status") or "").lower() in _RETELL_IN_PROGRESS:
            # Stop here: returning later calls would move the next pull past this one
            # before it ends.
            break
        if _is_finished_retell_call(
            status=item.get("call_status"),
            start_timestamp=item.get("start_timestamp"),
            end_timestamp=item.get("end_timestamp"),
        ):
            finished.append(item)

    calls = await read_retell_calls(
        api_key, [str(item["call_id"]) for item in finished]
    )
    return [call for call in calls if call is not None]


async def read_retell_calls(
    api_key: str, call_ids: list[str]
) -> list[RetellCall | None]:
    """Read calls in full, a few at a time, in the order given.

    ``None`` stands for a call Retell no longer has. If reading one fails, the result
    stops just before it, so the caller asks for it again.

    Raises:
        HTTPException: 502 when the first call could not be read.
    """
    semaphore = asyncio.Semaphore(_CALL_READ_CONCURRENCY)

    async def read(call_id: str) -> RetellCall | None:
        async with semaphore:
            return await get_retell_call(api_key, call_id)

    results = await asyncio.gather(
        *(read(call_id) for call_id in call_ids), return_exceptions=True
    )
    calls: list[RetellCall | None] = []
    for result in results:
        if isinstance(result, BaseException):
            # Stop before the call that could not be read, so it is asked for again.
            logger.warning("Reading a Retell call in full failed: %s", result)
            if not calls:
                # Nothing could be read: say so, rather than look like "no new calls".
                raise HTTPException(
                    status_code=502,
                    detail="Retell API returned an error reading a call",
                ) from result
            break
        calls.append(result)
    return calls


class RetellRateLimited(HTTPException):
    """Retell answered 429. ``retry_after`` is how long it asked to wait, if it said."""

    def __init__(self, retry_after: float | None) -> None:
        super().__init__(status_code=502, detail="Retell rate limited the request")
        self.retry_after = retry_after


def _retry_after(response: httpx.Response) -> float | None:
    for header in ("retry-after", "ratelimit-reset", "x-ratelimit-reset"):
        seconds = _parse_retry_after_seconds(response.headers.get(header))
        if seconds is not None:
            # A reset given as a Unix time, not a number of seconds.
            return seconds - time.time() if seconds > 10**9 else seconds
    return None


class RetellCallSummary(BaseModel):
    """One call as Retell's call list shows it: no transcript."""

    call_id: str
    agent_id: str
    start_timestamp: int
    finished: bool
    # Registered or ongoing: it may still end and be worth storing.
    in_progress: bool


async def list_retell_call_summaries(
    api_key: str,
    *,
    agent_ids: list[str],
    after: datetime,
    until: datetime,
    limit: int,
) -> list[RetellCallSummary]:
    """Calls of these Retell agents that started after ``after`` and by ``until``.

    Oldest first, at most ``limit``. Listing carries no transcripts, so it is cheap.

    Raises:
        HTTPException: 502 when Retell cannot be reached or answers unexpectedly.
    """
    body = {
        "filter_criteria": {
            "agent": [{"agent_id": agent_id} for agent_id in agent_ids],
            # Retell timestamps are epoch milliseconds.
            "start_timestamp": {
                "type": "number",
                "op": "gt",
                "value": int(after.timestamp() * 1000),
            },
        },
        "limit": limit,
        "sort_order": "ascending",
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _LIST_CALLS_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=15.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail="Failed to reach Retell API"
        ) from exc
    if response.status_code == 429:
        raise RetellRateLimited(_retry_after(response))
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Retell API returned an error")
    payload = _json_or_none(response)
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise HTTPException(
            status_code=502, detail="Retell API returned an unexpected answer"
        )

    last = int(until.timestamp() * 1000)
    summaries: list[RetellCallSummary] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("call_id"):
            continue
        started = item.get("start_timestamp")
        if not isinstance(started, int):
            continue
        if started > last:
            break
        summaries.append(
            RetellCallSummary(
                call_id=str(item["call_id"]),
                agent_id=str(item.get("agent_id") or ""),
                start_timestamp=started,
                in_progress=str(item.get("call_status") or "").lower()
                in _RETELL_IN_PROGRESS,
                finished=_is_finished_retell_call(
                    status=item.get("call_status"),
                    start_timestamp=started,
                    end_timestamp=item.get("end_timestamp"),
                ),
            )
        )
    return summaries


_RETELL_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


# ── Web call initiation (eval engine) ─────────────────────────────


def _parse_retell_chat_messages(raw_messages: Any) -> list[RetellChatMessage]:
    if not isinstance(raw_messages, list):
        return []

    out: list[RetellChatMessage] = []
    for item in raw_messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        if not role:
            continue
        out.append(
            RetellChatMessage(
                role=role,
                content=(
                    str(item["content"]) if item.get("content") is not None else None
                ),
                message_id=(
                    str(item["message_id"])
                    if item.get("message_id") is not None
                    else None
                ),
                created_timestamp=(
                    int(item["created_timestamp"])
                    if item.get("created_timestamp") is not None
                    else None
                ),
                tool_call_id=(
                    str(item["tool_call_id"])
                    if item.get("tool_call_id") is not None
                    else None
                ),
                name=str(item["name"]) if item.get("name") is not None else None,
                arguments=(
                    str(item["arguments"])
                    if item.get("arguments") is not None
                    else None
                ),
                raw=item,
            )
        )
    return out


async def create_retell_agent_playground_completion(
    *,
    api_key: str,
    retell_agent_id: str,
    messages: list[dict[str, Any]],
    dynamic_variables: dict[str, Any] | None = None,
    current_state: str | None = None,
    current_node_id: str | None = None,
    component_id: str | None = None,
    tool_mocks: list[dict[str, Any]] | None = None,
    version: int | None = None,
) -> RetellAgentPlaygroundCompletionResult:
    """One turn of Retell's agent playground.

    ``tool_mocks`` answer tool calls in place of the real tools; a call no mock matches
    reaches the real tool. ``version`` picks the agent version; none is the latest.
    """
    body: dict[str, Any] = {"messages": messages}
    if dynamic_variables is not None:
        body["dynamic_variables"] = dynamic_variables
    if tool_mocks is not None:
        body["tool_mocks"] = tool_mocks
    if current_state is not None:
        body["current_state"] = current_state
    if current_node_id is not None:
        body["current_node_id"] = current_node_id
    if component_id is not None:
        body["component_id"] = component_id

    started = time.perf_counter()
    response: httpx.Response | None = None
    network_error: httpx.HTTPError | None = None
    for attempt in range(1, _RETELL_PLAYGROUND_MAX_ATTEMPTS + 1):
        # One organization per key: every request, a retry included, takes a slot.
        await PLAYGROUND_PACER.wait(api_key)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.retellai.com/agent-playground-completion/{retell_agent_id}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    params={"version": version} if version is not None else None,
                    json=body,
                    timeout=15.0,
                )
            network_error = None
        except httpx.HTTPError as exc:
            network_error = exc
            response = None
            if attempt >= _RETELL_PLAYGROUND_MAX_ATTEMPTS:
                latency_ms = int((time.perf_counter() - started) * 1000)
                return RetellAgentPlaygroundCompletionResult(
                    success=False,
                    latency_ms=latency_ms,
                    error_message=f"Network error: {exc}",
                )
            wait_seconds = _RETELL_PLAYGROUND_BACKOFF_SECONDS[
                min(attempt - 1, len(_RETELL_PLAYGROUND_BACKOFF_SECONDS) - 1)
            ]
            logger.warning(
                "Retell playground request failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt,
                _RETELL_PLAYGROUND_MAX_ATTEMPTS,
                wait_seconds,
                exc,
            )
            await asyncio.sleep(wait_seconds)
            continue

        if response.status_code == 429:
            counter = PLAYGROUND_THROTTLED.get()
            if counter is not None:
                counter[0] += 1
        if response.status_code == 429 and attempt < _RETELL_PLAYGROUND_MAX_ATTEMPTS:
            wait_seconds = (
                _parse_retry_after_seconds(response.headers.get("Retry-After"))
                or _RETELL_PLAYGROUND_BACKOFF_SECONDS[
                    min(attempt - 1, len(_RETELL_PLAYGROUND_BACKOFF_SECONDS) - 1)
                ]
            )
            logger.warning(
                "Retell playground throttled (attempt %d/%d), retrying in %.1fs: %s",
                attempt,
                _RETELL_PLAYGROUND_MAX_ATTEMPTS,
                wait_seconds,
                _retell_response_detail(response),
            )
            await asyncio.sleep(wait_seconds)
            continue

        if response.status_code >= 500 and attempt < _RETELL_PLAYGROUND_MAX_ATTEMPTS:
            wait_seconds = _RETELL_PLAYGROUND_BACKOFF_SECONDS[
                min(attempt - 1, len(_RETELL_PLAYGROUND_BACKOFF_SECONDS) - 1)
            ]
            logger.warning(
                "Retell playground returned %d (attempt %d/%d), retrying in %.1fs: %s",
                response.status_code,
                attempt,
                _RETELL_PLAYGROUND_MAX_ATTEMPTS,
                wait_seconds,
                _retell_response_detail(response),
            )
            await asyncio.sleep(wait_seconds)
            continue

        break

    latency_ms = int((time.perf_counter() - started) * 1000)

    if network_error is not None:
        return RetellAgentPlaygroundCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message=f"Network error: {network_error}",
        )

    if response is None:
        return RetellAgentPlaygroundCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message="Retell playground request did not return a response",
        )

    if response.status_code >= 400:
        return RetellAgentPlaygroundCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message=(
                "Retell agent-playground-completion returned "
                f"{response.status_code}: {_retell_response_detail(response)}"
            ),
        )

    try:
        payload = response.json()
    except ValueError as exc:
        return RetellAgentPlaygroundCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message=f"Malformed Retell response: {exc}",
        )

    if not isinstance(payload, dict):
        return RetellAgentPlaygroundCompletionResult(
            success=False,
            latency_ms=latency_ms,
            error_message="Retell agent-playground-completion returned invalid JSON",
        )

    dynamic_variable_values = payload.get("dynamic_variables")
    dynamic_variables_payload = (
        dict(dynamic_variable_values)
        if isinstance(dynamic_variable_values, dict)
        else {}
    )

    return RetellAgentPlaygroundCompletionResult(
        success=True,
        messages=_parse_retell_chat_messages(payload.get("messages")),
        latency_ms=latency_ms,
        current_state=(
            str(payload["current_state"])
            if payload.get("current_state") is not None
            else None
        ),
        current_node_id=(
            str(payload["current_node_id"])
            if payload.get("current_node_id") is not None
            else None
        ),
        dynamic_variables=dynamic_variables_payload,
        call_ended=bool(payload.get("call_ended", False)),
    )


async def get_retell_call(api_key: str, call_id: str) -> RetellCall | None:
    """Fetch a single Retell call by id. Returns ``None`` for a call Retell will never
    return (404, or the id refused with 400 or 422)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.retellai.com/v2/get-call/{call_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach Retell API: {exc}"
        ) from exc

    if response.status_code == 429:
        raise RetellRateLimited(_retry_after(response))
    # Retell will never return this call: it no longer has it, or refuses the id.
    if response.status_code in (400, 404, 422):
        return None
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Retell get-call returned {response.status_code}",
        )

    item = response.json()
    if not isinstance(item, dict):
        return None
    return RetellCall(
        call_id=item.get("call_id", call_id),
        agent_id=item.get("agent_id"),
        start_timestamp=item.get("start_timestamp"),
        end_timestamp=item.get("end_timestamp"),
        call_status=item.get("call_status"),
        transcript_object=item.get("transcript_object"),
        raw=item,
    )
