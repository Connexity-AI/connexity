"""Data models package — re-exports all models for backward compatibility.

Existing ``from app.models import X`` imports continue to work unchanged.
Alembic's ``from app.models import SQLModel`` also resolves here so that
all table models are registered on ``SQLModel.metadata`` before autogenerate.
"""

# Re-export SQLModel so Alembic metadata discovery works
from sqlmodel import SQLModel  # noqa: F401

# ── Agent ──────────────────────────────────────────────────────────
from app.models.agent import (  # noqa: F401
    Agent,
    AgentBase,
)

# ── Agent HTTP contract (OpenAI-compatible) ────────────────────────
from app.models.agent_contract import (  # noqa: F401
    AgentResponse,
    ChatMessage,
    TokenUsage,
)
from app.models.assistant_task import AssistantTask  # noqa: F401

# ── Call (Observer) ────────────────────────────────────────────────
from app.models.call import (  # noqa: F401
    Call,
    CallComponent,
    CallEvent,
    CallLabelUpdate,
    CallPublic,
    CallRefreshResult,
    CallsPublic,
    CallTracePublic,
)
from app.models.call_list import (  # noqa: F401
    CallFilterOption,
    CallListItemPublic,
    CallListPublic,
    CallTilesPublic,
    WorstFindingPublic,
)
from app.models.call_pull import CallPullAccount, CallPullLease  # noqa: F401
from app.models.call_screen import (  # noqa: F401
    CallScreenEntry,
    CallScreenFinding,
    CallScreenPublic,
    KeyValue,
)
from app.models.category import Category, CategoryPublic  # noqa: F401
from app.models.check import (  # noqa: F401
    AgentCheckPublic,
    CallCheck,
    CallCheckPublic,
    CheckModeUpdate,
    CheckRelease,
    ChecksRunResult,
    DecisionRecord,
    DecisionRecordPublic,
    Finding,
    FindingPublic,
    Issue,
    IssuePublic,
    IssueStateUpdate,
)
from app.models.clarification import Clarification  # noqa: F401

# ── Common ─────────────────────────────────────────────────────────
from app.models.common import (  # noqa: F401
    ErrorResponse,
)

# ── Company (multi-tenancy) ────────────────────────────────────────
from app.models.company import (  # noqa: F401
    Company,
)

# ── Comparison / diff schemas (pure Pydantic) ────────────────────
from app.models.component_version import (  # noqa: F401
    ComponentVersion,
    ComponentVersionPublic,
    ComponentVersionSummary,
    ServedBy,
    VersionResolveResult,
)

# ── Custom metric ──────────────────────────────────────────────────
# ── Enums ──────────────────────────────────────────────────────────
from app.models.enums import (  # noqa: F401
    AgentMode,
    FirstTurn,
    IntegrationProvider,
    Platform,
    RunMode,
    RunStatus,
    SimulatorMode,
    TestCaseStatus,
    TextRuntimeKind,
    TurnRole,
)

# ── Eval config ────────────────────────────────────────────────────
from app.models.eval_config import (  # noqa: F401
    EvalConfig,
    EvalConfigBase,
    EvalConfigMember,
)
from app.models.execution import (  # noqa: F401
    CallExecution,
    CallExecutionStep,
    Execution,
    ExecutionStep,
    ExecutionSyncResult,
)
from app.models.feedback import FeedbackReport  # noqa: F401

# ── Ingest ─────────────────────────────────────────────────────────
from app.models.ingest_token import (  # noqa: F401
    IngestToken,
    IngestTokenCreate,
    IngestTokenCreated,
    IngestTokenPublic,
    IngestTokensPublic,
    IngestTraceRequest,
    IngestTraceResult,
)

# ── Integration ────────────────────────────────────────────────────
from app.models.integration import (  # noqa: F401
    AgentToolBackend,
    AgentToolPublic,
    Integration,
    IntegrationCreate,
    IntegrationPublic,
    IntegrationsPublic,
    ToolBackendPublic,
    ToolBackendSet,
    WorkflowSummary,
)
from app.models.model_answer import ModelAnswer  # noqa: F401
from app.models.oauth import (  # noqa: F401
    OAuthAuthorizationCode,
    OAuthClient,
    OAuthClientRegistrationRequest,
    OAuthClientRegistrationResponse,
    OAuthRefreshToken,
)

# ── Personal access tokens ─────────────────────────────────────────
from app.models.personal_access_token import (  # noqa: F401
    PersonalAccessToken,
    PersonalAccessTokenCreated,
    PersonalAccessTokenPublic,
    PersonalAccessTokensPublic,
)
from app.models.readiness import (  # noqa: F401
    ReadinessPublic,
    ReadinessStep,
    ReadinessStepKey,
    ReadinessStepState,
)

# ── Run ────────────────────────────────────────────────────────────
from app.models.run import (  # noqa: F401
    Run,
    RunBase,
)
from app.models.scenario import ScenarioRule  # noqa: F401

# ── JSONB nested schemas (pure Pydantic) ───────────────────────────
from app.models.schemas import (  # noqa: F401
    ConversationTurn,
    RetellRuntimeConfig,
    RunConfig,
    RuntimeConfig,
    ToolCall,
    ToolCallFunction,
    UserSimulatorConfig,
)
from app.models.spec import Spec, SpecRule  # noqa: F401
from app.models.task_order import TaskOrder  # noqa: F401

# ── Test case ──────────────────────────────────────────────────────
from app.models.test_case import (  # noqa: F401
    TestCase,
    TestCaseBase,
)

# ── Test case result ───────────────────────────────────────────────
from app.models.test_case_result import (  # noqa: F401
    TestCaseResult,
    TestCaseResultBase,
)
from app.models.test_run import RuleVerdict  # noqa: F401
from app.models.usage import UsageRecord  # noqa: F401

# ── Existing user models ──────────────────────────────────────────
from app.models.user import (  # noqa: F401
    Message,
    Token,
    TokenPayload,
    UpdatePassword,
    User,
    UserBase,
    UserCreate,
    UserPublic,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
)
from app.models.workspace_member import (  # noqa: F401
    WorkspaceCreate,
    WorkspaceMember,
    WorkspacePublic,
)
