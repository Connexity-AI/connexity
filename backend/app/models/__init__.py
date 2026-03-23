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

# ── Enums ──────────────────────────────────────────────────────────
from app.models.enums import (  # noqa: F401
    Difficulty,
    ErrorCategory,
    RunStatus,
    ScenarioStatus,
    TurnRole,
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

# ── Scenario ───────────────────────────────────────────────────────
from app.models.scenario import (  # noqa: F401
    Scenario,
    ScenarioBase,
    ScenarioCreate,
    ScenarioPublic,
    ScenariosPublic,
    ScenarioUpdate,
)

# ── Scenario Result ────────────────────────────────────────────────
from app.models.scenario_result import (  # noqa: F401
    ScenarioResult,
    ScenarioResultBase,
    ScenarioResultCreate,
    ScenarioResultPublic,
    ScenarioResultsPublic,
    ScenarioResultUpdate,
)

# ── Scenario Set ───────────────────────────────────────────────────
from app.models.scenario_set import (  # noqa: F401
    ScenarioSet,
    ScenarioSetBase,
    ScenarioSetCreate,
    ScenarioSetMember,
    ScenarioSetMembersUpdate,
    ScenarioSetPublic,
    ScenarioSetsPublic,
    ScenarioSetUpdate,
)

# ── JSONB nested schemas (pure Pydantic) ───────────────────────────
from app.models.schemas import (  # noqa: F401
    AggregateMetrics,
    ConversationTurn,
    CriterionScore,
    ErrorCategoryCount,
    ExpectedToolCall,
    JudgeVerdict,
    Persona,
    RunConfig,
    ToolCall,
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
