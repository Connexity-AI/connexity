# Evaluation runtimes

An **evaluation runtime** is the strategy that drives a single test case from start to finish: it produces a transcript (in-process simulator, external phone/web call, etc.). Runtimes are pluggable — adding a new one means writing a single class and registering it.

The orchestrator owns concurrency, judging, persistence, and aggregate metrics. The runtime owns the conversation loop. This separation is what lets text and voice runtimes coexist without churning the orchestrator.

## Built-in runtimes

| Kind | Used for | Available when |
|---|---|---|
| `connexity` | Native: in-process user simulator + agent ↔ user text loop | always |
| `retell` | Drives a Retell web call, then exposes the transcript for judging | agent is on the Retell platform with a configured Retell integration |
| `custom_endpoint` | Posts to a user-provided HTTP endpoint that honors the OpenAI-compatible [agent contract](./agent-contract.md) | Non-Retell agents (Custom/Webhook, Vapi, ElevenLabs, legacy rows without platform); agent must be in **endpoint** mode |

The active runtime is stored in `RunConfig.runtime` (inside `eval_config.config` JSONB). Absent value → `connexity`.

## Where things live

```
backend/app/services/eval_runtimes/
├── __init__.py             # re-exports
├── base.py                 # EvalRuntime ABC, RuntimeRunArgs, RuntimeTestResult
├── registry.py             # KIND → instance map; runtimes_for_platform; defaults
├── types.py                # AgentSnapshot, RunSnapshot, TestCaseRunResult
├── text/
│   ├── base.py             # TextRuntimeBase shared user-simulator loop
│   ├── connexity.py        # ConnexityRuntime
│   ├── retell.py           # RetellRuntime (placeholder)
│   └── custom_endpoint.py  # CustomEndpointRuntime
└── voice/                  # voice runtimes (Retell voice, Vapi, …)
```

Schema-side:

```
backend/app/models/enums.py        # RunMode, TextRuntimeKind
backend/app/models/schemas.py      # *RuntimeConfig discriminated union, RunConfig.runtime
```

CRUD + routes:

```
backend/app/crud/eval_config.py            # _validate_runtime
backend/app/api/routes/eval_configs.py     # POST /eval-configs/test-runtime
backend/app/api/routes/agents.py           # GET /agents/{id}/runtimes
```

## How an eval run uses the runtime

1. `crud.create_eval_config` / `update_eval_config` calls `_validate_runtime(...)`. The runtime's own `validate_config` runs, and tool-call-using test cases are rejected if the runtime is not Connexity.
2. `services.orchestrator.execute_run` loads the snapshotted `RunConfig`, builds an `AgentSnapshot` and `RunSnapshot` once, then dispatches each test case through `runtime.run_test_case(...)` under a `Semaphore(config.concurrency)`.
3. After the runtime returns a transcript, the orchestrator calls `judge.evaluate_transcript(...)` to produce the verdict, computes per-case metrics, and persists `TestCaseResult`.
4. Per-test-case failures land in `TestCaseResult.error_message`; the run continues.

## Snapshots

`AgentSnapshot` and `RunSnapshot` are frozen captures taken once per run. They hold everything a runtime needs to know about the agent and the run, so that `RuntimeRunArgs` stays a three-field struct:

```python
@dataclass(frozen=True)
class RuntimeRunArgs:
    test_case: TestCase
    agent_snapshot: AgentSnapshot      # agent_id, platform, endpoint_url, system_prompt, tools, mode, model, provider, …
    run_snapshot: RunSnapshot          # run_id, run_config, cancel_event
```

Runtimes pull whatever they need from these structs (`args.agent_snapshot.endpoint_url`, `args.run_snapshot.run_config`, etc.) without the orchestrator passing 13 kwargs.

## Adding a new runtime

Worked example: add a `myvoice` voice runtime.

### 1. Add the enum value

`backend/app/models/enums.py`:

```python
class TextRuntimeKind(StrEnum):
    CONNEXITY = "connexity"
    RETELL = "retell"
    CUSTOM_ENDPOINT = "custom_endpoint"
    MYVOICE = "myvoice"        # ← new
```

### 2. Add a config class and extend the discriminated union

`backend/app/models/schemas.py`:

```python
class MyVoiceRuntimeConfig(BaseModel):
    kind: Literal[TextRuntimeKind.MYVOICE] = TextRuntimeKind.MYVOICE
    voice_id: str = Field(min_length=1, max_length=255)


RuntimeConfig = Annotated[
    ConnexityRuntimeConfig
    | RetellRuntimeConfig
    | CustomEndpointRuntimeConfig
    | MyVoiceRuntimeConfig,                   # ← new
    Field(discriminator="kind"),
]
```

Re-export `MyVoiceRuntimeConfig` from `app.models.__init__` if it should be importable as `from app.models import …`.

### 3. Implement the runtime

`backend/app/services/eval_runtimes/voice/myvoice.py`:

```python
from typing import ClassVar

from sqlmodel import Session

from app.models.agent import Agent
from app.models.enums import Platform, RunMode, TextRuntimeKind
from app.models.schemas import (
    MyVoiceRuntimeConfig,
    RuntimeConfig,
)
from app.services.eval_runtimes.base import (
    EvalRuntime,
    RuntimeRunArgs,
    RuntimeTestResult,
)
from app.services.eval_runtimes.types import TestCaseRunResult


class MyVoiceRuntime(EvalRuntime):
    MODE: ClassVar[RunMode] = RunMode.VOICE
    KIND: ClassVar[TextRuntimeKind] = TextRuntimeKind.MYVOICE
    LABEL: ClassVar[str] = "MyVoice"
    DESCRIPTION: ClassVar[str] = "Run evaluations on MyVoice"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return platform == Platform.RETELL

    def validate_config(self, runtime_config, agent, session) -> None:
        if not isinstance(runtime_config, MyVoiceRuntimeConfig):
            raise ValueError("myvoice runtime requires a MyVoiceRuntimeConfig")

    async def test_connection(self, runtime_config, agent, session) -> RuntimeTestResult:
        return RuntimeTestResult(ok=True, message="reachable")

    async def run_test_case(
        self,
        runtime_config: RuntimeConfig,
        args: RuntimeRunArgs,
        session: Session,
    ) -> TestCaseRunResult:
        # 1. drive the external system to produce a transcript
        # 2. map to ConversationTurn[]
        # 3. return TestCaseRunResult — DO NOT call the judge here.
        ...
```

Runtimes must be safe to instantiate without arguments — the registry creates one shared instance per process.

### 4. Register it

`backend/app/services/eval_runtimes/registry.py`:

```python
from app.services.eval_runtimes.voice.myvoice import MyVoiceRuntime

_TEXT_RUNTIMES: dict[TextRuntimeKind, EvalRuntime] = {
    ConnexityRuntime.KIND: ConnexityRuntime(),
    RetellRuntime.KIND: RetellRuntime(),
    CustomEndpointRuntime.KIND: CustomEndpointRuntime(),
    MyVoiceRuntime.KIND: MyVoiceRuntime(),     # ← new
}
```

Append the runtime to the iteration order tuple in `runtimes_for_platform` so the dropdown order is stable.

### 5. Update tests

Add coverage in `backend/app/tests/services/eval_runtimes/`:

- `test_<name>.py` — runtime-local: `supported_for_platform`, `validate_config`, `test_connection`, and `run_test_case` happy path.
- Add a case to `test_dispatch.py` proving `_execute_single_test_case` routes to the new runtime when configured.

### 6. Regenerate the API client

The new runtime config kind shows up in the OpenAPI schema; the frontend SDK must be re-generated:

```
bash scripts/generate-client.sh
```

CI fails if the generated client is stale.

## Contract for `run_test_case`

`runtime.run_test_case(runtime_config, args, session)` returns a `TestCaseRunResult`:

- `TestCaseRunResult.transcript: list[ConversationTurn]` is consumed for latency/turn metrics and is fed into the Connexity judge by the orchestrator. An empty transcript signals a no-op (e.g. transcript fetch failed); the orchestrator skips the judge and marks the case failed.
- `TestCaseRunResult.agent_token_usage` / `platform_token_usage` / `agent_cost_usd` / `platform_cost_usd` are merged with the judge's own usage/cost by the orchestrator. Runtimes that don't have meaningful values can leave them empty.
- `TestCaseRunResult.runtime_metadata: dict[str, Any] | None` is an opaque per-runtime escape hatch. Voice runtimes use it to attach platform call ids, recording URLs, etc. Text runtimes typically leave it `None`.
- Raise to mark the case errored — the exception message becomes `TestCaseResult.error_message`.

Runtimes **must not** call the judge themselves. The orchestrator always runs the Connexity judge on the returned transcript.

## Sharing the text loop

`TextRuntimeBase` owns the runtime-agnostic loop: user simulator turns, turn ordering, terminating tool calls, timeouts, cancellation, and result assembly. It does **not** know how to call a Connexity endpoint, a custom endpoint, or Retell.

Text runtimes provide the agent side:

- `build_text_agent_config(...)` resolves the per-runtime agent settings.
- `do_agent_turn(...)` executes one agent turn and appends the assistant/tool turns to the transcript.

`ConnexityRuntime` drives agent turns **only** through
:class:`~app.services.agent_simulator.AgentSimulator` (platform-mode agents).
`CustomEndpointRuntime` drives agent turns **only** through HTTP POST to your
endpoint (endpoint-mode agents). They share `TextRuntimeBase` for the user
simulator loop only — not agent inference. Retell will implement its own
`do_agent_turn(...)`.
