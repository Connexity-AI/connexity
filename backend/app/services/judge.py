"""LLM judge that scores transcripts using the configured metric set."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.models.enums import TurnRole
from app.models.schemas import (
    ConversationTurn,
    ExpectedOutcomeResult,
    JudgeConfig,
    JudgeVerdict,
    MetricScore,
    ToolCall,
)
from app.models.test_case import TestCase
from app.services.agent_tool_definitions import agent_tool_definitions_as_prompt_dicts
from app.services.judge_metrics import (
    MetricDefinition,
    ScoreType,
    resolve_metrics,
)
from app.services.llm import LLMCallConfig, LLMMessage, call_llm

logger = logging.getLogger(__name__)

SCORED_LABELS: dict[int, str] = {
    0: "critical_fail",
    1: "fail",
    2: "poor",
    3: "acceptable",
    4: "good",
    5: "excellent",
}


@dataclass(frozen=True)
class JudgeInput:
    transcript: list[ConversationTurn]
    test_case: TestCase
    agent_system_prompt: str | None
    agent_tools: list[dict[str, Any]] | None
    judge_config: JudgeConfig | None


def _pretty_json_oneline(raw: str | Any) -> str:
    """Try to re-serialize as compact JSON; fall back to str()."""
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
        return json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))
    except (json.JSONDecodeError, TypeError):
        return str(raw)


def _format_tool_calls(tool_calls: list[ToolCall] | None) -> str:
    if not tool_calls:
        return ""
    parts: list[str] = []
    for tc in tool_calls:
        fn = tc.function
        args = _pretty_json_oneline(fn.arguments)
        parts.append(f"    call: {fn.name}({args})")
    return "\n".join(parts)


def _build_tool_name_index(
    transcript: list[ConversationTurn],
) -> dict[str, str]:
    """Map tool_call ids to function names for labeling tool-result turns."""
    index: dict[str, str] = {}
    for t in transcript:
        if not t.tool_calls:
            continue
        for tc in t.tool_calls:
            index[tc.id] = tc.function.name
    return index


def _format_transcript(transcript: list[ConversationTurn]) -> str:
    tool_name_index = _build_tool_name_index(transcript)
    lines: list[str] = []
    for t in transcript:
        role = t.role.value
        if t.role == TurnRole.TOOL:
            fn_name = tool_name_index.get(t.tool_call_id or "", "unknown")
            body = _pretty_json_oneline(t.content) if t.content else "(empty)"
            lines.append(f"Turn {t.index} [tool → {fn_name}]: {body}")
        else:
            body = (t.content or "").strip() or "(no text)"
            lines.append(f"Turn {t.index} [{role}]: {body}")
        if t.tool_calls:
            lines.append("  tool_calls:")
            lines.append(_format_tool_calls(t.tool_calls))
    return "\n".join(lines)


def build_judge_system_prompt(
    metrics: list[MetricDefinition],
) -> str:
    """Build the system prompt carrying the full evaluation framework.

    Rubrics and scoring rules live here (stable across calls with the same
    metric set) so they benefit from provider prompt-caching and receive
    higher instruction-following priority from the model.
    """
    rubric_blocks: list[str] = []
    for m in metrics:
        score_label = (
            "Binary (pass/fail)"
            if m.score_type == ScoreType.BINARY
            else "Scored (0-5 integer)"
        )
        rubric_blocks.append(
            f"### {m.display_name} (`{m.name}`) — {score_label}\n\n" f"{m.rubric}\n"
        )

    return f"""\
You are an expert evaluator for voice AI customer service agents.
You judge conversation transcripts against the rubrics below.

## Scoring Rules

- For **scored** metrics (0-5 integer): use the full range. Each score level
  has specific criteria in the rubric.
- For **binary** metrics (pass/fail): evaluate against the stated criteria.
- Score each metric **independently** — one metric's result must not influence another.
- Ground every judgment in **observable evidence** from the transcript.
  Cite specific turn indices and quote relevant text where helpful.
- Be strict but fair: penalize clear failures, do not invent problems not evidenced in the transcript.
- If the transcript lacks evidence to judge a metric, note that and score conservatively.

## Per-Metric Output Fields

For each metric, return a JSON object with these fields:
- **score** (scored) or **passed** (binary): the numeric score or boolean result.
- **justification**: cite specific turn numbers and explain your reasoning.
- **failure_code**: a short `snake_case` label describing the failure mode when the metric
  scored poorly (score <= 2 for scored, or failed for binary). Set to `null` when the metric
  is acceptable or better. Examples: `wrong_tool_selected`, `hallucinated_result`,
  `missing_confirmation`, `skipped_required_field`. These are suggestions — use whatever
  label best describes the specific issue observed. You are not limited to these examples.
- **turns**: a list of integer turn indices where the issue was observed. Empty list if no issue.

## Metric Rubrics

{"".join(rubric_blocks)}
## Output Format

Return a single JSON object with one key per metric id listed above (snake_case).
Keys must match the metric ids exactly.
"""


def _build_user_prompt(inp: JudgeInput, metric_names: list[str]) -> str:
    """Build the user prompt carrying only per-evaluation evidence."""
    expected_outcomes = inp.test_case.expected_outcomes or []
    if expected_outcomes:
        outcomes_block = "\n".join(
            f"{i + 1}. {stmt}" for i, stmt in enumerate(expected_outcomes)
        )
    else:
        outcomes_block = "(none)"

    tools_expected = json.dumps(
        inp.test_case.expected_tool_calls or [],
        indent=2,
        ensure_ascii=False,
    )
    agent_prompt = (inp.agent_system_prompt or "(not captured for this run)").strip()
    tools_for_prompt = agent_tool_definitions_as_prompt_dicts(inp.agent_tools)
    tools_snapshot = (
        json.dumps(tools_for_prompt, indent=2, ensure_ascii=False)
        if tools_for_prompt
        else "(not captured)"
    )
    override = (inp.test_case.evaluation_criteria_override or "").strip()

    override_section = ""
    if override:
        override_section = f"\n## Test case-specific evaluation emphasis\n{override}\n"

    outcomes_eval_section = ""
    if expected_outcomes:
        outcomes_eval_section = """
## Expected Outcomes Evaluation

For each expected outcome listed above, determine whether it was met based on
the transcript evidence. Return your evaluation in the `expected_outcomes` key
as a JSON array of objects, each with:
- **statement**: the outcome text (copy verbatim from above)
- **passed**: boolean
- **justification**: cite specific turns and explain
"""

    return f"""\
## Test Case Context

**Expected outcomes:**
{outcomes_block}

**Expected tool calls:**
```json
{tools_expected}
```

**Agent system prompt / business rules:**
```
{agent_prompt}
```

**Agent tools:**
```json
{tools_snapshot}
```
{override_section}{outcomes_eval_section}
## Transcript

{_format_transcript(inp.transcript)}

## Score These Metrics

{", ".join(metric_names)}
"""


def build_judge_response_format(
    metrics: list[MetricDefinition],
    *,
    has_expected_outcomes: bool = False,
) -> dict[str, object]:
    """OpenAI-compatible ``response_format`` for structured judge output."""

    def scored_props() -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 5},
                "justification": {"type": "string"},
                "failure_code": {
                    "type": ["string", "null"],
                    "description": (
                        "Short snake_case label for the failure mode when score <= 2. "
                        "Examples: wrong_tool_selected, hallucinated_result, missing_confirmation. "
                        "These are suggestions — use whatever best describes the issue. "
                        "null when score >= 3."
                    ),
                },
                "turns": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Turn indices where the issue was observed. Empty if no issue.",
                },
            },
            "required": ["score", "justification", "failure_code", "turns"],
            "additionalProperties": False,
        }

    def binary_props() -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "justification": {"type": "string"},
                "failure_code": {
                    "type": ["string", "null"],
                    "description": (
                        "Short snake_case label for the failure mode when not passed. "
                        "null when passed."
                    ),
                },
                "turns": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Turn indices where the issue was observed. Empty if no issue.",
                },
            },
            "required": ["passed", "justification", "failure_code", "turns"],
            "additionalProperties": False,
        }

    properties: dict[str, object] = {}
    for m in metrics:
        properties[m.name] = (
            binary_props() if m.score_type == ScoreType.BINARY else scored_props()
        )

    if has_expected_outcomes:
        properties["expected_outcomes"] = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "justification": {"type": "string"},
                },
                "required": ["statement", "passed", "justification"],
                "additionalProperties": False,
            },
        }

    required = sorted(properties.keys())
    schema: dict[str, object] = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "judge_metric_scores",
            "strict": True,
            "schema": schema,
        },
    }


def _build_summary(
    metric_scores: list[MetricScore],
    *,
    passed: bool,
    overall_score: float,
) -> str:
    """Build a concise human-readable summary from the scored metrics."""
    status = "PASSED" if passed else "FAILED"
    parts: list[str] = [f"{status} ({overall_score:.1f}/100)."]

    # Highlight lowest and highest scoring non-binary metrics
    scored = [ms for ms in metric_scores if not ms.is_binary]
    if scored:
        lowest = min(scored, key=lambda ms: ms.score)
        highest = max(scored, key=lambda ms: ms.score)
        if lowest.score < 3:
            parts.append(f"Weakest: {lowest.metric} ({lowest.score}/5).")
        if highest.score >= 4 and highest.metric != lowest.metric:
            parts.append(f"Strongest: {highest.metric} ({highest.score}/5).")

    # Note any failed binary metrics
    failed_binary = [ms for ms in metric_scores if ms.is_binary and ms.score == 0]
    for fb in failed_binary:
        parts.append(f"{fb.metric}: FAIL.")

    return " ".join(parts)


def _error_verdict(
    *,
    raw_output: str | None,
    judge_model: str,
    judge_provider: str,
    judge_latency_ms: int | None,
    judge_token_usage: dict[str, int] | None,
    error_message: str,
    judge_cost_usd: float | None = None,
) -> JudgeVerdict:
    """Construct a failed verdict when judge evaluation cannot complete."""
    return JudgeVerdict(
        passed=False,
        overall_score=0.0,
        metric_scores=[],
        summary=f"Judge evaluation failed: {error_message}",
        raw_judge_output=raw_output,
        judge_model=judge_model,
        judge_provider=judge_provider,
        judge_latency_ms=judge_latency_ms,
        judge_token_usage=judge_token_usage,
        judge_cost_usd=judge_cost_usd,
    )


async def evaluate_transcript(inp: JudgeInput) -> JudgeVerdict:
    """Run the judge LLM on a completed transcript; return a structured verdict.

    Returns a failed :class:`JudgeVerdict` (instead of raising) when the LLM
    call fails or returns unparseable output, so callers always receive a
    verdict they can persist.  Only raises :class:`ValueError` for truly
    invalid inputs (e.g. empty transcript) that indicate a programming error.
    """
    if not inp.transcript:
        msg = "Cannot evaluate an empty transcript"
        raise ValueError(msg)

    judge_cfg = inp.judge_config
    try:
        resolved = resolve_metrics(judge_cfg)
    except ValueError as e:
        logger.error("Metric resolution failed: %s", e)
        judge_model = (
            (judge_cfg.model if judge_cfg else None)
            or settings.LLM_DEFAULT_MODEL
            or "unknown"
        )
        judge_provider = (
            (judge_cfg.provider if judge_cfg else None)
            or settings.LLM_DEFAULT_PROVIDER
            or "openai"
        )
        return _error_verdict(
            raw_output=None,
            judge_model=judge_model,
            judge_provider=judge_provider,
            judge_latency_ms=None,
            judge_token_usage=None,
            error_message=f"Metric resolution failed: {e}",
        )
    metric_defs = [m for m, _ in resolved]

    has_outcomes = bool(inp.test_case.expected_outcomes)
    metric_names = [m.name for m in metric_defs]
    system_prompt = build_judge_system_prompt(metric_defs)
    user_prompt = _build_user_prompt(inp, metric_names)
    response_format = build_judge_response_format(
        metric_defs, has_expected_outcomes=has_outcomes
    )

    llm_cfg = LLMCallConfig(
        model=judge_cfg.model if judge_cfg else None,
        provider=judge_cfg.provider if judge_cfg else None,
        temperature=settings.JUDGE_TEMPERATURE,
        max_tokens=settings.JUDGE_MAX_TOKENS,
        response_format=response_format,
    )

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    judge_provider = (
        (judge_cfg.provider if judge_cfg else None)
        or settings.LLM_DEFAULT_PROVIDER
        or "openai"
    )

    # --- LLM call with graceful error handling ---
    try:
        response = await call_llm(messages, config=llm_cfg, app_settings=settings)
    except Exception:
        logger.exception("Judge LLM call failed")
        return _error_verdict(
            raw_output=None,
            judge_model=llm_cfg.model or settings.default_llm_id,
            judge_provider=judge_provider,
            judge_latency_ms=None,
            judge_token_usage=None,
            error_message="LLM call failed",
        )

    raw = (response.content or "").strip()
    token_usage = dict(response.usage) if response.usage else None

    try:
        payload: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Judge returned non-JSON: %s", raw[:500])
        return _error_verdict(
            raw_output=raw,
            judge_model=response.model,
            judge_provider=judge_provider,
            judge_latency_ms=response.latency_ms,
            judge_token_usage=token_usage,
            error_message="Judge model did not return valid JSON",
            judge_cost_usd=response.response_cost_usd,
        )

    effective_judge = judge_cfg or JudgeConfig()
    pass_threshold = effective_judge.pass_threshold

    metric_scores: list[MetricScore] = []
    overall_accum = 0.0

    try:
        for m, weight in resolved:
            block = payload.get(m.name)
            if not isinstance(block, dict):
                msg = f"Judge output missing or invalid block for metric {m.name}"
                raise ValueError(msg)

            failure_code = block.get("failure_code") or None
            turns = block.get("turns") or []

            if m.score_type == ScoreType.BINARY:
                passed_flag = block.get("passed")
                justification = block.get("justification")
                if not isinstance(passed_flag, bool) or not isinstance(
                    justification, str
                ):
                    msg = f"Invalid binary payload for metric {m.name}"
                    raise ValueError(msg)
                score_int = 5 if passed_flag else 0
                label = "pass" if passed_flag else "fail"
                metric_scores.append(
                    MetricScore(
                        metric=m.name,
                        score=score_int,
                        label=label,
                        weight=weight,
                        justification=justification,
                        is_binary=True,
                        tier=m.tier.value,
                        failure_code=failure_code,
                        turns=turns,
                    )
                )
                overall_accum += (score_int / 5.0) * weight
            else:
                raw_score = block.get("score")
                justification = block.get("justification")
                if not isinstance(justification, str):
                    msg = f"Invalid justification for metric {m.name}"
                    raise ValueError(msg)
                try:
                    score_int = int(raw_score)
                except (TypeError, ValueError) as e:
                    msg = f"Invalid score for metric {m.name}"
                    raise ValueError(msg) from e
                score_int = max(0, min(5, score_int))
                label = SCORED_LABELS.get(score_int, "acceptable")
                metric_scores.append(
                    MetricScore(
                        metric=m.name,
                        score=score_int,
                        label=label,
                        weight=weight,
                        justification=justification,
                        is_binary=False,
                        tier=m.tier.value,
                        failure_code=failure_code,
                        turns=turns,
                    )
                )
                overall_accum += (score_int / 5.0) * weight
    except ValueError as e:
        logger.exception("Failed to parse judge output")
        return _error_verdict(
            raw_output=raw,
            judge_model=response.model,
            judge_provider=judge_provider,
            judge_latency_ms=response.latency_ms,
            judge_token_usage=token_usage,
            error_message=str(e),
            judge_cost_usd=response.response_cost_usd,
        )

    # Parse expected outcome results
    outcome_results: list[ExpectedOutcomeResult] | None = None
    if has_outcomes:
        raw_outcomes = payload.get("expected_outcomes")
        if isinstance(raw_outcomes, list):
            outcome_results = []
            for item in raw_outcomes:
                if isinstance(item, dict):
                    outcome_results.append(
                        ExpectedOutcomeResult(
                            statement=str(item.get("statement", "")),
                            passed=bool(item.get("passed", False)),
                            justification=str(item.get("justification", "")),
                        )
                    )

    overall_score = round(overall_accum * 100.0, 2)
    passed = overall_score >= pass_threshold

    summary = _build_summary(
        metric_scores,
        passed=passed,
        overall_score=overall_score,
    )

    return JudgeVerdict(
        passed=passed,
        overall_score=overall_score,
        metric_scores=metric_scores,
        expected_outcome_results=outcome_results,
        summary=summary,
        raw_judge_output=raw,
        judge_model=response.model,
        judge_provider=judge_provider,
        judge_latency_ms=response.latency_ms,
        judge_token_usage=token_usage,
        judge_cost_usd=response.response_cost_usd,
    )
