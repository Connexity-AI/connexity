"""The issue type library lists every check Connexity runs."""

from pathlib import Path

from app.models.enums import CheckKind, CheckMode
from app.services.checks.registry import CHECKS

DOC = Path(__file__).resolve().parents[4] / "docs-internal" / "issue-types.md"


def test_every_check_is_in_the_issue_type_library() -> None:
    text = DOC.read_text(encoding="utf-8")
    rows = {
        line.split("|")[1].strip().strip("`"): [
            c.strip() for c in line.split("|")[1:-1]
        ]
        for line in text.splitlines()
        if line.startswith("| `")
    }

    for check in CHECKS:
        assert (
            check.type in rows
        ), f"{check.type} is not in docs-internal/issue-types.md"
        _, title, found_by, _, default, _ = rows[check.type]
        assert title == check.title
        assert found_by == ("Rule" if check.kind is CheckKind.RULE else "Model")
        assert default == (
            "Critical" if check.default_mode is CheckMode.FAILS else "Warning"
        )
