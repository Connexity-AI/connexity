"""custom_metric: add is_predefined / is_draft and seed built-in metrics

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-05-01 00:00:01.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "j7k8l9m0n1o2"
down_revision = "i6j7k8l9m0n1"
branch_labels = None
depends_on = None


# Rubrics and metric definitions are duplicated here so the seed is
# self-contained and stable across refactors of app.services.predefined_metrics
# / app.services.judge_metrics. A migration must replay deterministically on a
# clean DB years from now, even if the application module is renamed, removed,
# or refactored. Do not import application code from this file.
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
Pass: outcomes satisfied given the transcript and test case.
Fail: primary task not achieved."""


# Tier / score-type values mirror the MetricTier and ScoreType StrEnums in
# app.models.enums at the time this migration was written. Hard-coded as
# strings on purpose so the migration replays without depending on the
# current state of those enums.
_PREDEFINED: list[dict[str, object]] = [
    {
        "name": "tool_routing",
        "display_name": "Tool Routing",
        "description": "Correct tool names and call sequence.",
        "tier": "execution",
        "default_weight": 0.15,
        "score_type": "scored",
        "rubric": _RUBRIC_TOOL_ROUTING,
        "include_in_defaults": True,
    },
    {
        "name": "parameter_extraction",
        "display_name": "Parameter Extraction",
        "description": "Arguments correctly extracted from conversation for tools.",
        "tier": "execution",
        "default_weight": 0.15,
        "score_type": "scored",
        "rubric": _RUBRIC_PARAMETER_EXTRACTION,
        "include_in_defaults": True,
    },
    {
        "name": "result_interpretation",
        "display_name": "Result Interpretation",
        "description": "Tool outputs accurately reflected in agent responses.",
        "tier": "execution",
        "default_weight": 0.15,
        "score_type": "scored",
        "rubric": _RUBRIC_RESULT_INTERPRETATION,
        "include_in_defaults": True,
    },
    {
        "name": "grounding_fidelity",
        "display_name": "Grounding Fidelity",
        "description": "Claims traceable to context, tools, or business rules.",
        "tier": "knowledge",
        "default_weight": 0.125,
        "score_type": "scored",
        "rubric": _RUBRIC_GROUNDING_FIDELITY,
        "include_in_defaults": True,
    },
    {
        "name": "instruction_compliance",
        "display_name": "Instruction Compliance",
        "description": "Follows explicit system prompt and business rules.",
        "tier": "knowledge",
        "default_weight": 0.125,
        "score_type": "scored",
        "rubric": _RUBRIC_INSTRUCTION_COMPLIANCE,
        "include_in_defaults": True,
    },
    {
        "name": "information_gathering",
        "display_name": "Information Gathering",
        "description": "Required information collected before action; prior info reused.",
        "tier": "process",
        "default_weight": 0.10,
        "score_type": "scored",
        "rubric": _RUBRIC_INFORMATION_GATHERING,
        "include_in_defaults": True,
    },
    {
        "name": "conversation_management",
        "display_name": "Conversation Management",
        "description": "Ambiguity handling, error recovery, conversation closure.",
        "tier": "process",
        "default_weight": 0.10,
        "score_type": "scored",
        "rubric": _RUBRIC_CONVERSATION_MANAGEMENT,
        "include_in_defaults": True,
    },
    {
        "name": "response_delivery",
        "display_name": "Response Delivery",
        "description": "Concise, natural, TTS-friendly, non-repetitive responses.",
        "tier": "delivery",
        "default_weight": 0.10,
        "score_type": "scored",
        "rubric": _RUBRIC_RESPONSE_DELIVERY,
        "include_in_defaults": True,
    },
    {
        "name": "task_completion",
        "display_name": "Task Completion (binary example)",
        "description": "Primary task from expected_outcomes achieved (pass/fail).",
        "tier": "execution",
        "default_weight": 0.0,
        "score_type": "binary",
        "rubric": _RUBRIC_TASK_COMPLETION,
        "include_in_defaults": False,
    },
]


def upgrade() -> None:
    op.add_column(
        "custom_metric",
        sa.Column(
            "is_predefined",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "custom_metric",
        sa.Column(
            "is_draft",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # Predefined metrics have no human owner; allow NULL on created_by.
    op.alter_column("custom_metric", "created_by", nullable=True)

    bind = op.get_bind()

    # Reference the existing native PG enum types so bulk_insert emits the
    # proper ``::metrictier`` / ``::scoretype`` casts. Values are listed
    # explicitly (not pulled from the Python enum) so this migration replays
    # even if the enum classes are later renamed or extended.
    metric_tier_enum = postgresql.ENUM(
        "execution",
        "knowledge",
        "process",
        "delivery",
        name="metrictier",
        create_type=False,
    )
    score_type_enum = postgresql.ENUM(
        "scored",
        "binary",
        name="scoretype",
        create_type=False,
    )

    custom_metric = sa.table(
        "custom_metric",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("tier", metric_tier_enum),
        sa.column("default_weight", sa.Float),
        sa.column("score_type", score_type_enum),
        sa.column("rubric", sa.Text),
        sa.column("include_in_defaults", sa.Boolean),
        sa.column("is_predefined", sa.Boolean),
        sa.column("is_draft", sa.Boolean),
        sa.column("created_by", postgresql.UUID(as_uuid=True)),
    )

    existing_names = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT name FROM custom_metric WHERE deleted_at IS NULL")
        ).fetchall()
    }

    rows_to_insert = [
        {
            "id": uuid.uuid4(),
            "name": m["name"],
            "display_name": m["display_name"],
            "description": m["description"],
            "tier": m["tier"],
            "default_weight": m["default_weight"],
            "score_type": m["score_type"],
            "rubric": m["rubric"],
            "include_in_defaults": m["include_in_defaults"],
            "is_predefined": True,
            "is_draft": False,
            "created_by": None,
        }
        for m in _PREDEFINED
        if m["name"] not in existing_names
    ]
    if rows_to_insert:
        op.bulk_insert(custom_metric, rows_to_insert)


def downgrade() -> None:
    bind = op.get_bind()
    # Predefined rows are the only ones permitted to have NULL created_by, so
    # purge them before restoring the NOT NULL constraint.
    bind.execute(sa.text("DELETE FROM custom_metric WHERE is_predefined = TRUE"))
    op.alter_column("custom_metric", "created_by", nullable=False)
    op.drop_column("custom_metric", "is_draft")
    op.drop_column("custom_metric", "is_predefined")
