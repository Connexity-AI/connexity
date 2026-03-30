"""Judge metric definitions, rubrics, and selection/weight resolution.

The default set is eight scored metrics. Opt-in-only metrics are included only
when listed in :class:`~app.models.schemas.JudgeConfig`.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import ErrorCategory
from app.models.schemas import JudgeConfig, MetricSelection


class ScoreType(StrEnum):
    SCORED = "scored"
    BINARY = "binary"


class MetricTier(StrEnum):
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"
    PROCESS = "process"
    DELIVERY = "delivery"


class MetricDefinition(BaseModel):
    name: str = Field(description="Stable metric id (snake_case)")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="What this metric measures")
    what_to_fix: str = Field(description="What to fix when the score is low")
    tier: MetricTier
    default_weight: float = Field(
        ge=0.0,
        description="Default weight before renormalization (0 for opt-in-only metrics)",
    )
    score_type: ScoreType
    rubric: str = Field(description="Rubric and examples for the judge prompt")
    failure_error_category: ErrorCategory = Field(
        description="ErrorCategory when this metric is the lowest scorer on failure"
    )
    include_in_defaults: bool = Field(
        default=True,
        description="If False, metric is omitted unless explicitly selected",
    )


_RUBRIC_TOOL_ROUTING = """\
Scored 0-5 integer. Measures: correct tool names and call sequence.

5: All expected tools called in correct sequence. No unnecessary calls.
   Example: Agent calls check_availability then book_appointment exactly as expected.
4: All critical tools called. Minor sequence deviation or one redundant call.
   Example: Agent called check_availability twice (redundant) but still booked correctly.
3: One expected tool missed OR one wrong tool called, but core flow mostly intact.
   Example: Skipped check_availability, went straight to book_appointment.
2: Multiple tool errors. Flow significantly impacted but partially functional.
   Example: Wrong tool called + one required tool missed entirely.
1: Most tool calls incorrect or missing. Only 1 of N expected tools called.
   Example: Agent called only end_call, skipped all business logic tools.
0: No tools called when required, or entirely wrong tool set used.
   Example: Agent improvised answers without invoking any tools."""

_RUBRIC_PARAMETER_EXTRACTION = """\
Scored 0-5 integer. Measures: argument values correctly extracted from conversation for tools.
Only evaluate tools that were actually called — never score hypothetical calls.

5: All parameters correct. Values accurately extracted from user input.
   Example: User said "next Tuesday at 2pm" — agent passed correct date and time.
4: All critical parameters correct. One minor parameter slightly off but doesn't affect outcome.
   Example: Name passed as "Bob" instead of "Bobby" (user used both).
3: One critical parameter wrong or missing, affecting tool outcome.
   Example: Date extracted as March 30 when user said March 31.
2: Multiple parameter errors. Tool may have returned wrong results or failed.
   Example: Wrong date + wrong service type passed to booking tool.
1: Most parameters fabricated or missing. Values not grounded in conversation.
   Example: Agent invented a phone number not mentioned by user.
0: No parameters extracted from conversation. All values fabricated or empty.
   Example: Tool called with all default/placeholder values."""

_RUBRIC_RESULT_INTERPRETATION = """\
Scored 0-5 integer. Measures: tool output accurately reflected in agent response.

5: Tool output accurately and completely reflected. Errors handled gracefully. No internal metadata exposed.
   Example: Tool returned 3 available slots — agent offered all 3 clearly.
4: Tool output mostly accurate. Minor omission that doesn't mislead user.
   Example: Tool returned 3 slots, agent mentioned 2 (the most relevant ones).
3: One meaningful inaccuracy in conveying tool results, or partial mishandling of an error response.
   Example: Tool returned "no availability on Monday" — agent said "limited availability on Monday".
2: Significant misrepresentation of tool output. User would make a wrong decision based on this.
   Example: Tool returned error — agent told user booking was successful.
1: Tool output largely ignored or contradicted. Response fabricates details not in output.
   Example: Tool returned appointment at 2pm — agent confirmed 3pm.
0: Tool output completely ignored. Agent's response has no connection to what the tool returned.
   Example: Tool returned data — agent gave generic scripted response ignoring all results."""

_RUBRIC_GROUNDING_FIDELITY = """\
Scored 0-5 integer. Measures: every agent claim traceable to context, tools, or business rules.

5: Every specific claim grounded. Appropriate hedging for uncertain info. Admits gaps in knowledge.
   Example: "Based on our system, your appointment is confirmed for Tuesday at 2pm" (matches tool output).
4: All critical claims grounded. One minor unverifiable statement that doesn't affect user decisions.
   Example: "We're usually pretty quick with that" (not in rules, but harmless).
3: One meaningful ungrounded claim that could mislead user, OR invented a minor policy.
   Example: "We offer a 10% discount for first-time customers" (not in business rules).
2: Multiple ungrounded claims. Mix of fabricated facts and invented policies.
   Example: Stated wrong business hours + invented a cancellation policy.
1: Most claims ungrounded. Agent is largely confabulating.
   Example: Fabricated pricing, availability, and company policies.
0: Response is entirely fabricated with no connection to provided context or tool outputs.
   Example: Agent invented a complete service description not in any source."""

_RUBRIC_INSTRUCTION_COMPLIANCE = """\
Scored 0-5 integer. Measures: agent follows explicit rules from system prompt and business rules.

5: All instructions followed precisely. Stayed within role/scope. Applied all business rules correctly.
   Example: Agent deflected out-of-scope question per instructions, followed greeting script exactly.
4: All critical instructions followed. One minor deviation with negligible impact.
   Example: Greeting slightly rephrased but all required elements present.
3: One meaningful instruction violated. Core functionality intact but rule was clearly broken.
   Example: Instructions say "always confirm spelling of name" — agent skipped this step.
2: Multiple instructions violated. Agent partially operating outside defined boundaries.
   Example: Skipped required confirmation + answered an out-of-scope question.
1: Most instructions ignored. Agent is largely operating outside its defined role.
   Example: Agent provided medical advice when instructed to only handle scheduling.
0: Agent completely disregards system prompt and business rules.
   Example: Agent ignored all role boundaries and business logic."""

_RUBRIC_INFORMATION_GATHERING = """\
Scored 0-5 integer. Measures: required info collected before action; previously stated info reused.

5: All required info collected before action. Previously stated info reused correctly. No redundant questions.
   Example: User gave name, date, service type — agent used all three in tool call without re-asking.
4: All critical info collected. One redundant question or minor missed detail that didn't affect outcome.
   Example: Asked "And your name?" when user already introduced themselves, but correctly used it after.
3: One required field missing before action, OR forgot one previously stated detail and re-asked.
   Example: Booked appointment without confirming phone number (required field).
2: Multiple gaps in info collection. Agent acted on incomplete data or forgot multiple prior details.
   Example: Skipped phone number + re-asked for date that user already provided.
1: Most required info not collected. Agent took action with largely incomplete data.
   Example: Attempted booking with only a name — no date, time, or service type.
0: No info gathering attempted. Agent either acted immediately with no data or never progressed to action.
   Example: Agent booked with all placeholder data, or kept asking questions indefinitely without acting."""

_RUBRIC_CONVERSATION_MANAGEMENT = """\
Scored 0-5 integer. Measures: ambiguity handling, error recovery, and conversation closure.

5: Ambiguity clarified appropriately. Errors acknowledged and corrected smoothly. Proper goodbye sequence.
   Example: User said "sometime next week" — agent asked "morning or afternoon?" — recovered from wrong date — proper closing.
4: Good management overall. One minor missed clarification opportunity or slightly abrupt close.
   Example: Didn't clarify AM/PM ambiguity but picked a reasonable default and confirmed it.
3: One meaningful management failure: unresolved ambiguity, failed error recovery, or improper closing.
   Example: Tool returned error — agent got confused and repeated the same action instead of adjusting.
2: Multiple management failures. Conversation felt disjointed or poorly controlled.
   Example: Didn't clarify ambiguous request + abrupt end_call without goodbye.
1: Conversation poorly managed throughout. Agent struggled with basic flow control.
   Example: Got stuck in a loop, never recovered, ended call mid-conversation.
0: No conversation management. Agent froze, crashed, or produced incoherent turn sequence.
   Example: Agent stopped responding, or fired end_call immediately."""

_RUBRIC_RESPONSE_DELIVERY = """\
Scored 0-5 integer. Measures: concision, natural phrasing, TTS-friendliness, non-repetition.

5: All responses concise. Natural phrasing. No TTS-hostile formatting. No repetition. One question per turn.
   Example: "Great, I've got Tuesday at 2pm for a windshield repair. Does that work for you?"
4: Mostly natural and concise. One minor issue: slightly verbose turn or one repeated phrase.
   Example: One turn hit 45 words but was a necessary summary; slight repetition of "I'd be happy to help".
3: One meaningful delivery issue: a turn with 2+ questions, notably robotic phrasing, or noticeable repetition pattern.
   Example: "What date works for you? And what time? Morning or afternoon?" (triple question in one turn).
2: Multiple delivery issues. Conversation feels robotic or verbose. Repeated phrases or templates obvious.
   Example: Multiple 50+ word turns + "Thank you for providing that" repeated 4 times.
1: Pervasive delivery problems. Most turns are too long, robotic, or repetitive.
   Example: Every turn starts with "Absolutely!" + bullet points (TTS-hostile) + same closing phrase.
0: Responses are entirely unsuitable for voice delivery. Markdown formatting, URLs, or completely unnatural output.
   Example: Agent outputs markdown tables, code blocks, or walls of text."""

_RUBRIC_TASK_COMPLETION = """\
Binary pass/fail. Measures whether the agent completed the primary task described in expected_outcomes.
Pass: outcomes satisfied given the transcript and scenario.
Fail: primary task not achieved."""


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "tool_routing": MetricDefinition(
        name="tool_routing",
        display_name="Tool Routing",
        description="Correct tool names and call sequence.",
        what_to_fix="Tool descriptions, selection logic, flow graph.",
        tier=MetricTier.EXECUTION,
        default_weight=0.15,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_TOOL_ROUTING,
        failure_error_category=ErrorCategory.TOOL_MISUSE,
    ),
    "parameter_extraction": MetricDefinition(
        name="parameter_extraction",
        display_name="Parameter Extraction",
        description="Arguments correctly extracted from conversation for tools.",
        what_to_fix="Slot-filling prompts, parameter parsing, formatting.",
        tier=MetricTier.EXECUTION,
        default_weight=0.15,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_PARAMETER_EXTRACTION,
        failure_error_category=ErrorCategory.TOOL_MISUSE,
    ),
    "result_interpretation": MetricDefinition(
        name="result_interpretation",
        display_name="Result Interpretation",
        description="Tool outputs accurately reflected in agent responses.",
        what_to_fix="Response generation prompt, output formatting rules.",
        tier=MetricTier.EXECUTION,
        default_weight=0.15,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_RESULT_INTERPRETATION,
        failure_error_category=ErrorCategory.HALLUCINATION,
    ),
    "grounding_fidelity": MetricDefinition(
        name="grounding_fidelity",
        display_name="Grounding Fidelity",
        description="Claims traceable to context, tools, or business rules.",
        what_to_fix="Grounding instructions, retrieval, citation rules.",
        tier=MetricTier.KNOWLEDGE,
        default_weight=0.125,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_GROUNDING_FIDELITY,
        failure_error_category=ErrorCategory.HALLUCINATION,
    ),
    "instruction_compliance": MetricDefinition(
        name="instruction_compliance",
        display_name="Instruction Compliance",
        description="Follows explicit system prompt and business rules.",
        what_to_fix="The specific violated rule; clarify ambiguous instructions.",
        tier=MetricTier.KNOWLEDGE,
        default_weight=0.125,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_INSTRUCTION_COMPLIANCE,
        failure_error_category=ErrorCategory.PROMPT_VIOLATION,
    ),
    "information_gathering": MetricDefinition(
        name="information_gathering",
        display_name="Information Gathering",
        description="Required information collected before action; prior info reused.",
        what_to_fix="Required-fields checklist, context window, slot prompts.",
        tier=MetricTier.PROCESS,
        default_weight=0.10,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_INFORMATION_GATHERING,
        failure_error_category=ErrorCategory.INCOMPLETE,
    ),
    "conversation_management": MetricDefinition(
        name="conversation_management",
        display_name="Conversation Management",
        description="Ambiguity handling, error recovery, conversation closure.",
        what_to_fix="Flow logic, clarification prompts, closing sequence.",
        tier=MetricTier.PROCESS,
        default_weight=0.10,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_CONVERSATION_MANAGEMENT,
        failure_error_category=ErrorCategory.INCOMPLETE,
    ),
    "response_delivery": MetricDefinition(
        name="response_delivery",
        display_name="Response Delivery",
        description="Concise, natural, TTS-friendly, non-repetitive responses.",
        what_to_fix="Output formatting, max length, style instructions.",
        tier=MetricTier.DELIVERY,
        default_weight=0.10,
        score_type=ScoreType.SCORED,
        rubric=_RUBRIC_RESPONSE_DELIVERY,
        failure_error_category=ErrorCategory.OTHER,
    ),
    "task_completion": MetricDefinition(
        name="task_completion",
        display_name="Task Completion (binary example)",
        description="Primary task from expected_outcomes achieved (pass/fail).",
        what_to_fix="End-to-end flow against scenario success criteria.",
        tier=MetricTier.EXECUTION,
        default_weight=0.0,
        score_type=ScoreType.BINARY,
        rubric=_RUBRIC_TASK_COMPLETION,
        failure_error_category=ErrorCategory.INCOMPLETE,
        include_in_defaults=False,
    ),
}


def get_default_metrics() -> list[MetricDefinition]:
    """Default scored metrics (``include_in_defaults``; excludes opt-in-only)."""
    return [
        m
        for m in METRIC_REGISTRY.values()
        if m.include_in_defaults and m.score_type == ScoreType.SCORED
    ]


def get_metrics_for_api() -> list[MetricDefinition]:
    """All registered metrics for UI / config discovery."""
    return list(METRIC_REGISTRY.values())


def _normalize_weights(
    pairs: list[tuple[MetricDefinition, float]],
) -> list[tuple[MetricDefinition, float]]:
    total = sum(w for _, w in pairs)
    if total <= 0:
        msg = "Metric weights must sum to a positive value"
        raise ValueError(msg)
    return [(m, w / total) for m, w in pairs]


def resolve_metrics(
    judge_config: JudgeConfig | None,
) -> list[tuple[MetricDefinition, float]]:
    """Resolve selected metrics and weights; weights renormalized to sum to 1.0."""
    if judge_config is None or judge_config.metrics is None:
        defaults = get_default_metrics()
        pairs = [(m, m.default_weight) for m in defaults]
        return _normalize_weights(pairs)

    selections: list[MetricSelection] = judge_config.metrics
    if not selections:
        defaults = get_default_metrics()
        pairs = [(m, m.default_weight) for m in defaults]
        return _normalize_weights(pairs)

    pairs: list[tuple[MetricDefinition, float]] = []
    for sel in selections:
        if sel.metric not in METRIC_REGISTRY:
            msg = f"Unknown metric: {sel.metric}"
            raise ValueError(msg)
        definition = METRIC_REGISTRY[sel.metric]
        if sel.metric == "task_completion" and sel.weight is None:
            msg = "task_completion requires an explicit weight when selected"
            raise ValueError(msg)
        weight = sel.weight if sel.weight is not None else definition.default_weight
        if weight < 0:
            msg = f"Negative weight for metric {sel.metric}"
            raise ValueError(msg)
        pairs.append((definition, weight))

    return _normalize_weights(pairs)
