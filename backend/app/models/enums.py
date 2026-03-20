from enum import StrEnum


class Difficulty(StrEnum):
    NORMAL = "normal"
    HARD = "hard"


class ScenarioStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SimulationMode(StrEnum):
    SCRIPTED = "scripted"
    LLM_DRIVEN = "llm_driven"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ErrorCategory(StrEnum):
    NONE = "none"
    OFF_TOPIC = "off_topic"
    HALLUCINATION = "hallucination"
    REFUSAL = "refusal"
    TOOL_MISUSE = "tool_misuse"
    SAFETY_VIOLATION = "safety_violation"
    PROMPT_VIOLATION = "prompt_violation"
    INCOMPLETE = "incomplete"
    LATENCY_TIMEOUT = "latency_timeout"
    AGENT_ERROR = "agent_error"
    OTHER = "other"


class TurnRole(StrEnum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
