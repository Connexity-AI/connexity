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


class Platform(StrEnum):
    RETELL = "retell"
    VAPI = "vapi"
    ELEVENLABS = "elevenlabs"
    WEBHOOK = "webhook"


class RunMode(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class TextRuntimeKind(StrEnum):
    RETELL = "retell"
    CUSTOM_ENDPOINT = "custom_endpoint"


class IntegrationProvider(StrEnum):
    RETELL = "retell"
    VAPI = "vapi"
    ELEVENLABS = "elevenlabs"


class CallLabel(StrEnum):
    GOOD = "good"
    BAD = "bad"


class TraceSource(StrEnum):
    PRODUCTION = "production"
    TEST_CALL = "test_call"
    SIMULATION = "simulation"


class CallChannel(StrEnum):
    PHONE = "phone"
    WEB = "web"
    TEXT = "text"


class CallDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallEndReason(StrEnum):
    CALLER_HANGUP = "caller_hangup"
    AGENT_HANGUP = "agent_hangup"
    TRANSFER = "transfer"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    ERROR = "error"
    LIMIT = "limit"
    UNKNOWN = "unknown"


class CallEventType(StrEnum):
    UTTERANCE = "utterance"
    TOOL_CALL = "tool_call"
    MARKER = "marker"


class Speaker(StrEnum):
    AGENT = "agent"
    CALLER = "caller"


class ToolCallStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    NO_RESULT = "no_result"


class TraceCapability(StrEnum):
    TOOL_CALLS = "tool_calls"
    TOOL_RESULTS = "tool_results"
    TIMING = "timing"
    INPUTS = "inputs"
    COMPONENTS = "components"
    RECORDING = "recording"
    OUTPUTS = "outputs"
