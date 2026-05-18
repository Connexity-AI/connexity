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


class AgentPromptType(StrEnum):
    SINGLE_PROMPT = "single_prompt"
    MULTI_PROMPT = "multi_prompt"


class AgentVersionStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class FirstTurn(StrEnum):
    AGENT = "agent"
    USER = "user"


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


class Platform(StrEnum):
    RETELL = "retell"
    TELNYX = "telnyx"
    VAPI = "vapi"
    ELEVENLABS = "elevenlabs"
    WEBHOOK = "webhook"


class RunMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class TextRuntimeKind(StrEnum):
    CONNEXITY = "connexity"
    RETELL = "retell"
    CUSTOM_ENDPOINT = "custom_endpoint"


class IntegrationProvider(StrEnum):
    RETELL = "retell"
    TELNYX = "telnyx"
    VAPI = "vapi"
    ELEVENLABS = "elevenlabs"


class DeploymentStatus(StrEnum):
    PENDING = "pending"
    DEPLOYED = "deployed"
    FAILED = "failed"
