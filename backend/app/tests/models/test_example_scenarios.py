"""Validate that all example scenario JSON files conform to the ScenarioCreate schema."""

import json
from pathlib import Path

import pytest

from app.models.scenario import ScenarioCreate

EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "examples" / "scenarios"


def _example_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.json"))


@pytest.fixture(params=_example_files(), ids=lambda p: p.stem)
def example_path(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_example_validates_against_schema(example_path: Path) -> None:
    raw = json.loads(example_path.read_text())
    scenario = ScenarioCreate.model_validate(raw)
    assert scenario.name, f"{example_path.name}: name must not be empty"


def test_examples_directory_has_at_least_five() -> None:
    files = _example_files()
    assert len(files) >= 5, f"Expected ≥5 example scenarios, found {len(files)}"
