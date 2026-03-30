"""LLM judge that scores transcripts using the configured metric set."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.models.enums import ErrorCategory, TurnRole
from app.models.scenario import Scenario
from app.models.schemas import (
    ConversationTurn,
    JudgeConfig,
    JudgeVerdict,
    MetricScore,
    ToolCall,
)
from app.services.judge_metrics import (
    METRIC_REGISTRY,
    MetricDefinition,
    MetricTier,
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
    scenario: Scenario
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
  has specific criteria in the rubric. Output `{{ "score": <0-5>, "justification": "<cite turn numbers>" }}`.
- For **binary** metrics (pass/fail): evaluate against the stated criteria.
  Output `{{ "passed": <true|false>, "justification": "<cite turn numbers>" }}`.
- Score each metric **independently** — one metric's result must not influence another.
- Ground every judgment in **observable evidence** from the transcript.
  Cite specific turn indices and quote relevant text where helpful.
- Be strict but fair: penalize clear failures, do not invent problems not evidenced in the transcript.
- If the transcript lacks evidence to judge a metric, note that and score conservatively.

## Metric Rubrics

{"".join(rubric_blocks)}
## Output Format

Return a single JSON object with one key per metric id listed above (snake_case).
Keys must match the metric ids exactly.
"""


def _build_user_prompt(inp: JudgeInput, metric_names: list[str]) -> str:
    """Build the user prompt carrying only per-evaluation evidence."""
    outcomes = json.dumps(
        inp.scenario.expected_outcomes or {}, indent=2, ensure_ascii=False
    )
    tools_expected = json.dumps(
        inp.scenario.expected_tool_calls or [],
        indent=2,
        ensure_ascii=False,
    )
    agent_prompt = (inp.agent_system_prompt or "(not captured for this run)").strip()
    tools_snapshot = (
        json.dumps(inp.agent_tools or [], indent=2, ensure_ascii=False)
        if inp.agent_tools
        else "(not captured)"
    )
    override = (inp.scenario.evaluation_criteria_override or "").strip()

    override_section = ""
    if override:
        override_section = f"\n## Scenario-specific evaluation emphasis\n{override}\n"

    return f"""\
## Scenario Context

**Expected outcomes:**
```json
{outcomes}
```

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
{override_section}
## Transcript

{_format_transcript(inp.transcript)}

## Score These Metrics

{", ".join(metric_names)}
"""


def build_judge_response_format(
    metrics: list[MetricDefinition],
) -> dict[str, object]:
    """OpenAI-compatible ``response_format`` for structured judge output."""

    def scored_props() -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 5},
                "justification": {"type": "string"},
            },
            "required": ["score", "justification"],
            "additionalProperties": False,
        }

    def binary_props() -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "justification": {"type": "string"},
            },
            "required": ["passed", "justification"],
            "additionalProperties": False,
        }

    properties: dict[str, object] = {}
    for m in metrics:
        properties[m.name] = (
            binary_props() if m.score_type == ScoreType.BINARY else scored_props()
        )

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


def _effective_numeric_score(score: int, *, is_binary: bool) -> int:
    if is_binary:
        return 5 if score >= 5 else 0
    return max(0, min(5, score))


def _critical_failure(
    metric_scores: list[MetricScore],
    threshold: int,
) -> bool:
    for c in metric_scores:
        if c.is_binary:
            continue
        if c.tier != MetricTier.EXECUTION.value:
            continue
        if c.score <= threshold:
            return True
    return False


def _derive_error_category(
    metric_scores: list[MetricScore],
    *,
    passed: bool,
) -> ErrorCategory:
    if passed:
        return ErrorCategory.NONE
    if not metric_scores:
        return ErrorCategory.OTHER

    best: tuple[int, MetricScore] | None = None
    for c in metric_scores:
        eff = _effective_numeric_score(c.score, is_binary=c.is_binary)
        if best is None or eff < best[0]:
            best = (eff, c)
    if best is None:
        return ErrorCategory.OTHER
    lowest = best[1]
    definition = METRIC_REGISTRY.get(lowest.metric)
    if definition is None:
        return ErrorCategory.OTHER
    return definition.failure_error_category


def _build_summary(
    metric_scores: list[MetricScore],
    *,
    passed: bool,
    overall_score: float,
    critical_failure: bool,
) -> str:
    """Build a concise human-readable summary from the scored metrics."""
    status = "PASSED" if passed else "FAILED"
    parts: list[str] = [f"{status} ({overall_score:.1f}/100)."]

    if critical_failure:
        parts.append("Critical failure detected on an execution-tier metric.")

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
) -> JudgeVerdict:
    """Construct a failed verdict when judge evaluation cannot complete."""
    return JudgeVerdict(
        passed=False,
        overall_score=0.0,
        critical_failure=False,
        metric_scores=[],
        error_category=ErrorCategory.OTHER,
        summary=f"Judge evaluation failed: {error_message}",
        raw_judge_output=raw_output,
        judge_model=judge_model,
        judge_provider=judge_provider,
        judge_latency_ms=judge_latency_ms,
        judge_token_usage=judge_token_usage,
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
    resolved = resolve_metrics(judge_cfg)
    metric_defs = [m for m, _ in resolved]

    metric_names = [m.name for m in metric_defs]
    system_prompt = build_judge_system_prompt(metric_defs)
    user_prompt = _build_user_prompt(inp, metric_names)
    response_format = build_judge_response_format(metric_defs)

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
            judge_model=llm_cfg.model or settings.LLM_DEFAULT_MODEL or "unknown",
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
        )

    effective_judge = judge_cfg or JudgeConfig()
    pass_threshold = effective_judge.pass_threshold
    critical_threshold = effective_judge.critical_failure_threshold

    metric_scores: list[MetricScore] = []
    overall_accum = 0.0

    try:
        for m, weight in resolved:
            block = payload.get(m.name)
            if not isinstance(block, dict):
                msg = f"Judge output missing or invalid block for metric {m.name}"
                raise ValueError(msg)

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
        )

    overall_score = round(overall_accum * 100.0, 2)
    critical = _critical_failure(metric_scores, critical_threshold)
    tentative_pass = overall_score >= pass_threshold and not critical
    error_cat = _derive_error_category(
        metric_scores,
        passed=tentative_pass,
    )
    passed = tentative_pass

    summary = _build_summary(
        metric_scores,
        passed=passed,
        overall_score=overall_score,
        critical_failure=critical,
    )

    return JudgeVerdict(
        passed=passed,
        overall_score=overall_score,
        critical_failure=critical,
        metric_scores=metric_scores,
        error_category=error_cat,
        summary=summary,
        raw_judge_output=raw,
        judge_model=response.model,
        judge_provider=judge_provider,
        judge_latency_ms=response.latency_ms,
        judge_token_usage=token_usage,
    )
