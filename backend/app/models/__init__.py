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
    AgentCreate,
    AgentPublic,
    AgentsPublic,
    AgentUpdate,
)

# ── Agent HTTP contract (OpenAI-compatible) ────────────────────────
from app.models.agent_contract import (  # noqa: F401
    AgentRequest,
    AgentRequestMetadata,
    AgentResponse,
    ChatMessage,
    TokenUsage,
)
from app.models.agent_version import (  # noqa: F401
    AgentDraftUpdate,
    AgentRollbackRequest,
    AgentVersion,
    AgentVersionPublic,
    AgentVersionsPublic,
    PublishRequest,
)

# ── Common ─────────────────────────────────────────────────────────
from app.models.common import ConfigPublic, ErrorResponse  # noqa: F401

# ── Comparison / diff schemas (pure Pydantic) ────────────────────
from app.models.comparison import (  # noqa: F401
    AgentConfigDiff,
    AgentVersionDiff,
    AggregateComparison,
    CauseAnalysisItem,
    EvalSetDiff,
    FieldChange,
    ImprovementSuggestion,
    ImprovementSuggestions,
    MetricAggregateDelta,
    MetricDelta,
    PromptDiff,
    RegressionAnalysis,
    RegressionThresholds,
    RegressionVerdict,
    RunComparison,
    RunConfigDiff,
    SuggestionsRequest,
    TestCaseComparison,
    ToolDiff,
)

# ── Custom metric ──────────────────────────────────────────────────
from app.models.custom_metric import (  # noqa: F401
    CustomMetric,
    CustomMetricBase,
    CustomMetricCreate,
    CustomMetricPublic,
    CustomMetricsPublic,
    CustomMetricUpdate,
)

# ── Enums ──────────────────────────────────────────────────────────
from app.models.enums import (  # noqa: F401
    AgentMode,
    AgentVersionStatus,
    Difficulty,
    MetricTier,
    PromptEditorSessionStatus,
    PromptEditStatus,
    RunStatus,
    ScoreType,
    SimulatorMode,
    TestCaseStatus,
    TurnRole,
)

# ── Eval set ───────────────────────────────────────────────────────
from app.models.eval_set import (  # noqa: F401
    EvalSet,
    EvalSetBase,
    EvalSetCreate,
    EvalSetMember,
    EvalSetMemberEntry,
    EvalSetMemberPublic,
    EvalSetMembersPublic,
    EvalSetMembersUpdate,
    EvalSetPublic,
    EvalSetsPublic,
    EvalSetUpdate,
)

# ── Prompt editor (chat) ───────────────────────────────────────────
from app.models.prompt_editor import (  # noqa: F401
    PromptEdit,
    PromptEditBatchStatusUpdate,
    PromptEditCreate,
    PromptEditorMessage,
    PromptEditorMessageBase,
    PromptEditorMessageCreate,
    PromptEditorMessagePublic,
    PromptEditorMessagesPublic,
    PromptEditorSession,
    PromptEditorSessionBase,
    PromptEditorSessionCreate,
    PromptEditorSessionPublic,
    PromptEditorSessionsPublic,
    PromptEditorSessionUpdate,
    PromptEditPublic,
    PromptEditStatusUpdate,
)

# ── Run ────────────────────────────────────────────────────────────
from app.models.run import (  # noqa: F401
    Run,
    RunBase,
    RunCreate,
    RunPublic,
    RunsPublic,
    RunUpdate,
)

# ── JSONB nested schemas (pure Pydantic) ───────────────────────────
from app.models.schemas import (  # noqa: F401
    AgentSimulatorConfig,
    AggregateMetrics,
    ConversationTurn,
    ExpectedToolCall,
    HttpWebhookImplementation,
    JudgeConfig,
    JudgeVerdict,
    MetricScore,
    MetricSelection,
    MockResponse,
    Persona,
    PythonImplementation,
    RunConfig,
    TestCaseExecution,
    ToolCall,
    ToolCallFunction,
    ToolImplementation,
    ToolPlatformConfig,
    UserSimulatorConfig,
)

# ── Test case ──────────────────────────────────────────────────────
from app.models.test_case import (  # noqa: F401
    OnConflict,
    TestCase,
    TestCaseBase,
    TestCaseCreate,
    TestCaseImportItem,
    TestCaseImportResult,
    TestCasePublic,
    TestCasesExport,
    TestCasesPublic,
    TestCaseUpdate,
)

# ── Test case result ───────────────────────────────────────────────
from app.models.test_case_result import (  # noqa: F401
    TestCaseResult,
    TestCaseResultBase,
    TestCaseResultCreate,
    TestCaseResultPublic,
    TestCaseResultsPublic,
    TestCaseResultUpdate,
)

# ── Existing user models ──────────────────────────────────────────
from app.models.user import (  # noqa: F401
    AuthProvider,
    Message,
    NewPassword,
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
