"""The rule judge's answer: the reason is written before the verdict, and an answer in
that order is read (plan `plans/2026-11-20-trustworthy-test-runs.md`)."""

import json
from typing import Any

import pytest

from app.models.enums import RuleOutcome
from app.services.rule_judge import (
    JudgeFailed,
    RuleToJudge,
    _response_format,
    parse_verdicts,
)

RULES = [
    RuleToJudge(key="r1", text="Quote the price."),
    RuleToJudge(key="r2", text="x"),
]


def test_the_judge_writes_its_reason_before_its_verdict() -> None:
    schema: Any = _response_format(["r1", "r2"])
    verdict = schema["json_schema"]["schema"]["properties"]["rules"]["items"]

    # A verdict written first was contradicted by the reason that followed it.
    assert list(verdict["properties"]) == ["key", "reason", "turns", "outcome"]
    assert verdict["required"] == ["key", "reason", "turns", "outcome"]
    assert verdict["properties"]["key"]["enum"] == ["r1", "r2"]


def test_an_answer_in_that_order_is_read_in_the_rules_order() -> None:
    raw = json.dumps(
        {
            "rules": [
                {
                    "key": "r2",
                    "reason": "Never got there.",
                    "turns": [],
                    "outcome": "did_not_come_up",
                },
                {"key": "r1", "reason": "Said 80.", "turns": [4], "outcome": "passed"},
            ]
        }
    )

    verdicts = parse_verdicts(raw, RULES)

    assert [(v.key, v.outcome, v.turns) for v in verdicts] == [
        ("r1", RuleOutcome.PASSED, [4]),
        ("r2", RuleOutcome.DID_NOT_COME_UP, []),
    ]


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        json.dumps({"rules": "none"}),
        json.dumps(
            {"rules": [{"key": "r1", "reason": "x", "turns": [], "outcome": "maybe"}]}
        ),
        json.dumps(
            {"rules": [{"key": "r1", "reason": "x", "turns": [], "outcome": "passed"}]}
        ),
    ],
)
def test_an_answer_that_cannot_be_read_gives_no_verdicts(raw: str) -> None:
    with pytest.raises(JudgeFailed):
        parse_verdicts(raw, RULES)
