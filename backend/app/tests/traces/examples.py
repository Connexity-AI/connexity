"""Load the published example traces from ``docs/traces/examples``."""

import json
from pathlib import Path

from app.models.trace import Trace

EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "docs" / "traces" / "examples"

EXAMPLE_NAMES = sorted(path.stem for path in EXAMPLES_DIR.glob("*.json"))


def load_example_json(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def load_example(name: str) -> Trace:
    return Trace.model_validate(load_example_json(name))
