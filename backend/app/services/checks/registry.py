"""The built-in checks and fact sources: code-based checks first, then model checks
(classifiers and judges)."""

from app.services.checks.base import Check, FactSource
from app.services.checks.code.booking_details_missing import BOOKING_DETAILS_MISSING
from app.services.checks.code.booking_duplicated import BOOKING_DUPLICATED
from app.services.checks.code.tool_call_failed import TOOL_CALL_FAILED
from app.services.checks.model.action_claimed import ACTION_CLAIMED_WITHOUT_TOOL
from app.services.checks.model.spec_rule import SPEC_RULE_BROKEN

CHECKS: tuple[Check, ...] = (
    TOOL_CALL_FAILED,
    BOOKING_DETAILS_MISSING,
    BOOKING_DUPLICATED,
    ACTION_CLAIMED_WITHOUT_TOOL,
    SPEC_RULE_BROKEN,
)

FACT_SOURCES: tuple[FactSource, ...] = ()


def get_check(check_type: str) -> Check | None:
    return next((check for check in CHECKS if check.type == check_type), None)
