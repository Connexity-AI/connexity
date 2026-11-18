import json

import httpx
import pytest
import respx

from app.core.config import settings
from app.services import jev
from app.services.jev import (
    Choice,
    ChoiceAnswer,
    JevError,
    JevNotConfigured,
    Score,
    YesNo,
    YesNoAnswer,
)

URL = f"{settings.JEV_BASE_URL}/v1/systemone"


@pytest.fixture(autouse=True)
def _jev_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(settings, "JEV_RETRY_MIN_WAIT_SECONDS", 0)
    monkeypatch.setattr(settings, "JEV_RETRY_MAX_WAIT_SECONDS", 0)


def _answer(
    answers: dict[str, object], *, input_tokens: int = 1000
) -> dict[str, object]:
    return {
        "model": "jev-1.14.0",
        "answers": answers,
        "usage": {"input_tokens": input_tokens, "output_tokens": 3},
    }


CLAIM = Choice(
    instructions="What does the agent tell the caller it has done?",
    criteria={"cancelled": "Says it cancelled", "none": "Claims nothing"},
)


@respx.mock
async def test_sends_pinned_model_key_and_questions() -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json=_answer(
                {
                    "claim": {
                        "type": "choice",
                        "choice": "cancelled",
                        "confidence": 0.9,
                        "probabilities": {"cancelled": 0.95, "none": 0.05},
                    }
                }
            ),
        )
    )
    decision = await jev.decide("Agent: I've cancelled it.", {"claim": CLAIM})

    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer test-key"
    body = json.loads(sent.content)
    assert body["model"] == settings.JEV_MODEL
    assert body["questions"]["claim"]["type"] == "choice"
    assert body["questions"]["claim"]["criteria"]["none"] == "Claims nothing"
    answer = decision.answers["claim"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice == "cancelled"
    assert decision.cost_usd == pytest.approx(1000 * 0.042 / 1_000_000)


@respx.mock
async def test_yes_no_and_score_round_trip() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json=_answer(
                {
                    "voicemail": {"type": "noul", "noul": 0.12},
                    "urgency": {
                        "type": "score",
                        "score": 1.7,
                        "confidence": 0.5,
                        "legend": {"0": "Low", "1": "Mid", "2": "High"},
                        "probabilities": {"0": 0.1, "1": 0.1, "2": 0.8},
                    },
                }
            ),
        )
    )
    decision = await jev.decide(
        {"turns": ["Hello?"]},
        {
            "voicemail": YesNo(instructions="Is this a voicemail greeting?"),
            "urgency": Score(
                instructions="How urgent?", criteria=["Low", "Mid", "High"]
            ),
        },
    )
    voicemail = decision.answers["voicemail"]
    assert isinstance(voicemail, YesNoAnswer)
    assert voicemail.noul == pytest.approx(0.12)


async def test_no_key_raises_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TYPESAFE_API_KEY", None)
    with pytest.raises(JevNotConfigured):
        await jev.decide("x", {"claim": CLAIM})


async def test_no_questions_is_refused() -> None:
    with pytest.raises(ValueError):
        await jev.decide("x", {})


@respx.mock
async def test_retries_rate_limit_then_succeeds() -> None:
    ok = _answer({"q": {"type": "noul", "noul": 0.9}})
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(429, json={"detail": "slow down"}),
            httpx.Response(529, json={"detail": "overloaded"}),
            httpx.Response(200, json=ok),
        ]
    )
    decision = await jev.decide("x", {"q": YesNo(instructions="?")})
    assert route.call_count == 3
    assert decision.answers["q"].type == "noul"


@respx.mock
async def test_bad_request_fails_at_once() -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(422, json={"detail": [{"msg": "Field required"}]})
    )
    with pytest.raises(JevError) as raised:
        await jev.decide("x", {"q": YesNo(instructions="?")})
    assert raised.value.status == 422
    assert route.call_count == 1


@respx.mock
async def test_timeout_is_retried_then_raised() -> None:
    route = respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(JevError) as raised:
        await jev.decide("x", {"q": YesNo(instructions="?")})
    assert raised.value.status is None
    assert route.call_count == settings.JEV_RETRY_MAX_ATTEMPTS


@respx.mock
async def test_empty_body_is_an_error() -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, content=b""))
    with pytest.raises(JevError):
        await jev.decide("x", {"q": YesNo(instructions="?")})


@respx.mock
async def test_malformed_answer_is_an_error() -> None:
    respx.post(URL).mock(return_value=httpx.Response(200, json={"answers": "nope"}))
    with pytest.raises(JevError):
        await jev.decide("x", {"q": YesNo(instructions="?")})


@respx.mock
async def test_missing_answer_is_an_error() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, json=_answer({"other": {"type": "noul", "noul": 1}})
        )
    )
    with pytest.raises(JevError, match="no answer for: q"):
        await jev.decide("x", {"q": YesNo(instructions="?")})


@respx.mock
async def test_answer_of_wrong_type_is_an_error() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            200, json=_answer({"claim": {"type": "noul", "noul": 1}})
        )
    )
    with pytest.raises(JevError, match="answered 'claim' as noul"):
        await jev.decide("x", {"claim": CLAIM})
