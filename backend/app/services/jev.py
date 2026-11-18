"""TypeSafe AI's Jev: a decision model that answers typed questions with probabilities.

Jev writes no text. A request sends a ``state`` (the content) and named questions; the
answer gives, per question, a probability (yes/no), a choice with the probability of
each option, or a score over ordered levels. Docs: https://docs.typesafe.ai.

Connexity calls the REST API directly with ``httpx``, the same as its other providers,
rather than adding TypeSafe's SDK. The model is pinned (``JEV_MODEL``): a moving alias
such as ``jev-latest`` would change answers, and so thresholds, without notice.
"""

import logging
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field, JsonValue, TypeAdapter
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limited and overloaded: TypeSafe's docs say to back off and retry.
_RETRY_STATUSES = frozenset({429, 529})


class JevNotConfigured(Exception):
    """No ``TYPESAFE_API_KEY`` is set, so Jev cannot be asked."""


class JevError(Exception):
    """Jev refused the request or could not be reached."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


# Questions


class YesNo(BaseModel):
    """Answered with the probability of yes (TypeSafe calls this a "noul")."""

    type: Literal["noul"] = "noul"
    instructions: str
    # What counts as yes and as no, when the question alone is not clear enough.
    criteria: dict[Literal["true", "false"], str] | None = None


class Choice(BaseModel):
    """Answered with one option and the probability of each."""

    type: Literal["choice"] = "choice"
    instructions: str
    # Option name to when it applies. Jev leans towards the first option a little, so
    # put "none" or the most common answer anywhere but first only on purpose.
    criteria: dict[str, str] = Field(min_length=1, max_length=255)


class Score(BaseModel):
    """Answered with the expected level (0 = the first) and each level's probability."""

    type: Literal["score"] = "score"
    instructions: str
    criteria: list[str] = Field(min_length=1, max_length=10)


Question = Annotated[YesNo | Choice | Score, Field(discriminator="type")]


# Answers


class YesNoAnswer(BaseModel):
    type: Literal["noul"]
    # Probability of yes, from 0 to 1.
    noul: float


class ChoiceAnswer(BaseModel):
    type: Literal["choice"]
    choice: str
    confidence: float
    probabilities: dict[str, float]


class ScoreAnswer(BaseModel):
    type: Literal["score"]
    # Probability-weighted level; may fall between levels.
    score: float
    confidence: float
    legend: dict[str, JsonValue]
    probabilities: dict[str, float]


Answer = Annotated[
    YesNoAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")
]


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class Decision(BaseModel):
    """Jev's answers to one request, keyed by the question names that were sent."""

    # The versioned model that answered, which may differ from an alias that was sent.
    model: str
    answers: dict[str, Answer]
    usage: Usage

    @property
    def cost_usd(self) -> float:
        # Output tokens are free.
        return self.usage.input_tokens * settings.JEV_USD_PER_MILLION_INPUT / 1_000_000


_questions = TypeAdapter(dict[str, Question])


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, JevError):
        return exc.status in _RETRY_STATUSES or exc.status is None
    return False


async def _post(payload: dict[str, JsonValue], api_key: str) -> Decision:
    try:
        async with httpx.AsyncClient(
            base_url=settings.JEV_BASE_URL, timeout=settings.JEV_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(
                "/v1/systemone",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except httpx.HTTPError as exc:
        msg = f"Jev could not be reached: {type(exc).__name__}"
        raise JevError(msg) from exc
    if response.status_code != 200:
        # The body explains a refused request; it never echoes the key.
        msg = f"Jev answered {response.status_code}: {response.text[:500]}"
        raise JevError(msg, status=response.status_code)
    try:
        return Decision.model_validate(response.json())
    except ValueError as exc:
        msg = "Jev's answer did not match its documented shape"
        raise JevError(msg, status=response.status_code) from exc


async def decide(
    state: str | dict[str, JsonValue] | list[JsonValue],
    questions: dict[str, Question],
    *,
    model: str | None = None,
) -> Decision:
    """Ask Jev ``questions`` about ``state`` in one request.

    Each question gets an answer under the same name. Rate limits (429), overload (529)
    and network failures are retried with backoff; anything else fails at once.

    Raises:
        JevNotConfigured: no ``TYPESAFE_API_KEY``.
        JevError: Jev refused the request, kept failing, or answered something
            unexpected, including an answer missing for a question.
    """
    api_key = settings.TYPESAFE_API_KEY
    if not api_key:
        msg = "TYPESAFE_API_KEY is not set"
        raise JevNotConfigured(msg)
    if not questions:
        msg = "Jev needs at least one question"
        raise ValueError(msg)
    payload: dict[str, JsonValue] = {
        "model": model or settings.JEV_MODEL,
        "state": state,
        "questions": _questions.dump_python(questions, mode="json", exclude_none=True),
    }
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(_retryable),
        stop=stop_after_attempt(settings.JEV_RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(
            min=settings.JEV_RETRY_MIN_WAIT_SECONDS,
            max=settings.JEV_RETRY_MAX_WAIT_SECONDS,
        ),
        reraise=True,
    ):
        with attempt:
            decision = await _post(payload, api_key)
    missing = set(questions) - set(decision.answers)
    if missing:
        msg = f"Jev gave no answer for: {', '.join(sorted(missing))}"
        raise JevError(msg, status=200)
    for name, question in questions.items():
        if decision.answers[name].type != question.type:
            msg = f"Jev answered '{name}' as {decision.answers[name].type}"
            raise JevError(msg, status=200)
    return decision
