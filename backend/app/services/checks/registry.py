"""The built-in checks and fact sources."""

from app.services.checks.base import FactSource, RuleCheck
from app.services.checks.rules.tool_call_failed import TOOL_CALL_FAILED

CHECKS: tuple[RuleCheck, ...] = (TOOL_CALL_FAILED,)

FACT_SOURCES: tuple[FactSource, ...] = ()


def get_check(check_type: str) -> RuleCheck | None:
    return next((check for check in CHECKS if check.type == check_type), None)
