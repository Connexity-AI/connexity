# Evaluation engines

An **evaluation engine** is the strategy that drives a single test case from start to finish: it produces a transcript (in-process simulator, external phone/web call, etc.) and optionally a judge verdict. Engines are pluggable — adding a new one means writing a single class and registering it.

This doc explains the moving parts and the exact steps to add a new engine.

## Built-in engines

| Kind | Used for | Available when |
|---|---|---|
| `connexity` | Native: in-process user simulator + Connexity judge | always |
| `retell` | Drives a Retell web call, then judges the resulting transcript | agent is on the Retell platform with a configured Retell integration |
| `custom_url` | Posts to a user-provided HTTP endpoint that honors the OpenAI-compatible [agent contract](./agent-contract.md) | "Custom" agents (`Agent.platform == webhook`) |

The active engine is stored in `RunConfig.evaluation_engine` (inside `eval_config.config` JSONB). Absent value → `connexity`.

## Where things live

```
backend/app/services/eval_engines/
├── __init__.py        # re-exports
├── base.py            # EvalEngine ABC, EngineRunArgs, EngineTestResult
├── registry.py        # KIND → instance map; engines_for_platform; defaults
├── connexity.py       # ConnexityEngine
├── retell.py          # RetellEngine
└── custom_url.py      # CustomUrlEngine
```

Schema-side:

```
backend/app/models/enums.py        # EvaluationEngineKind
backend/app/models/schemas.py      # *EngineConfig discriminated union, RunConfig.evaluation_engine
```

CRUD + routes:

```
backend/app/crud/eval_config.py            # _validate_evaluation_engine
backend/app/api/routes/eval_configs.py     # POST /eval-configs/test-evaluation-engine
backend/app/api/routes/agents.py           # GET /agents/{id}/evaluation-engines
```

## How an eval run uses the engine

1. `crud.create_eval_config` / `update_eval_config` calls `_validate_evaluation_engine(...)`. The engine's own `validate_config` runs, and tool-call-using test cases are rejected if the engine is not Connexity.
2. `services.orchestrator.execute_run` loads the snapshotted `RunConfig`, picks `engine = get_engine(config.evaluation_engine.kind)`, and hands every test case to `engine.run_test_case(...)`.
3. Per-test-case failures land in `TestCaseResult.error_message`; the run continues.

## Adding a new engine

Worked example: add a `myvoice` engine.

### 1. Add the enum value

`backend/app/models/enums.py`:

```python
class EvaluationEngineKind(StrEnum):
    CONNEXITY = "connexity"
    RETELL = "retell"
    CUSTOM_URL = "custom_url"
    MYVOICE = "myvoice"        # ← new
```

### 2. Add a config class and extend the discriminated union

`backend/app/models/schemas.py`:

```python
class MyVoiceEngineConfig(BaseModel):
    kind: Literal[EvaluationEngineKind.MYVOICE] = EvaluationEngineKind.MYVOICE
    # add fields specific to this engine, e.g.:
    voice_id: str = Field(min_length=1, max_length=255)


EvaluationEngineConfig = Annotated[
    ConnexityEngineConfig
    | RetellEngineConfig
    | CustomUrlEngineConfig
    | MyVoiceEngineConfig,                   # ← new
    Field(discriminator="kind"),
]
```

Re-export `MyVoiceEngineConfig` from `app.models.__init__` if it should be importable as `from app.models import …`.

### 3. Implement the engine

`backend/app/services/eval_engines/myvoice.py`:

```python
from typing import ClassVar

from sqlmodel import Session

from app.models.agent import Agent
from app.models.enums import EvaluationEngineKind, Platform
from app.models.schemas import (
    EvaluationEngineConfig,
    JudgeVerdict,
    MyVoiceEngineConfig,
)
from app.services.eval_engines.base import (
    EngineRunArgs,
    EngineTestResult,
    EvalEngine,
)


class MyVoiceEngine(EvalEngine):
    KIND: ClassVar[EvaluationEngineKind] = EvaluationEngineKind.MYVOICE
    LABEL: ClassVar[str] = "MyVoice"
    DESCRIPTION: ClassVar[str] = "Run evaluations on MyVoice"

    def supported_for_platform(self, platform: Platform | None) -> bool:
        return platform == Platform.RETELL  # or whatever fits

    def validate_config(self, engine_config, agent, session) -> None:
        if not isinstance(engine_config, MyVoiceEngineConfig):
            raise ValueError("myvoice engine requires a MyVoiceEngineConfig")
        # any agent-context checks (integration present, etc.)

    async def test_connection(self, engine_config, agent, session) -> EngineTestResult:
        # smoke-test API key / endpoint reachability
        return EngineTestResult(ok=True, message="reachable")

    async def run_test_case(
        self,
        engine_config: EvaluationEngineConfig,
        args: EngineRunArgs,
        session: Session,
    ) -> tuple["TestCaseRunResult", JudgeVerdict | None]:
        from app.services.orchestrator import TestCaseRunResult
        # 1. drive the external system to produce a transcript
        # 2. map to ConversationTurn[]
        # 3. (optionally) run app.services.judge.evaluate_transcript
        ...
```

Engines must be safe to instantiate without arguments — the registry creates one shared instance per process.

### 4. Register it

`backend/app/services/eval_engines/registry.py`:

```python
from app.services.eval_engines.myvoice import MyVoiceEngine

_ENGINES: dict[EvaluationEngineKind, EvalEngine] = {
    ConnexityEngine.KIND: ConnexityEngine(),
    RetellEngine.KIND: RetellEngine(),
    CustomUrlEngine.KIND: CustomUrlEngine(),
    MyVoiceEngine.KIND: MyVoiceEngine(),     # ← new
}

# Optional: make this the default for some platform
_DEFAULTS_BY_PLATFORM[Platform.RETELL] = EvaluationEngineKind.MYVOICE
```

Append the engine to the iteration order tuple in `engines_for_platform` so the dropdown order is stable.

### 5. Update tests

Add coverage in `backend/app/tests/services/eval_engines/`:

- `test_<name>.py` — engine-local: `supported_for_platform`, `validate_config`, `test_connection`, and `run_test_case` happy path.
- Add a case to `test_orchestrator_engine_dispatch.py` proving `execute_run` routes to the new engine when configured.

### 6. Regenerate the API client

The new engine config kind shows up in the OpenAPI schema; the frontend SDK must be re-generated:

```
bash scripts/generate-client.sh
```

CI fails if the generated client is stale.

## Contract for `run_test_case`

`engine.run_test_case` returns `(TestCaseRunResult, JudgeVerdict | None)`:

- `TestCaseRunResult.transcript: list[ConversationTurn]` is consumed for latency/turn metrics. An empty transcript signals a no-op (e.g. transcript fetch failed) and the orchestrator marks the case failed.
- `JudgeVerdict` is what feeds `TestCaseResult.passed` and aggregate metric scores. Engines that have their own judging may build a `JudgeVerdict` directly; engines that defer to Connexity should call `app.services.judge.evaluate_transcript(...)`.
- Raise to mark the case errored — the exception message becomes `TestCaseResult.error_message`.
