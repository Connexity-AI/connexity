from enum import StrEnum


class Difficulty(StrEnum):
    NORMAL = "normal"
    HARD = "hard"


class TestCaseStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentMode(StrEnum):
    ENDPOINT = "endpoint"
    PLATFORM = "platform"


class AgentVersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class SimulatorMode(StrEnum):
    LLM = "llm"
    SCRIPTED = "scripted"


class TurnRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ScoreType(StrEnum):
    SCORED = "scored"
    BINARY = "binary"


class MetricTier(StrEnum):
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"
    PROCESS = "process"
    DELIVERY = "delivery"


class PromptEditorSessionStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PromptSuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
