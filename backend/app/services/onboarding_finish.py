"""Onboarding's finish line: a complete Dashboard (roadmap 10.192, Dmytro 2026-11-18;
plan `plans/2026-11-18-onboarding-ends-with-dashboard.md`).

A workspace's onboarding is complete once every Readiness step is done, no agent waits
for a spec and no question is open (answered or parked). It is stored the first time
that holds (`Company.onboarding_completed_at`) and never goes back: a question raised
next month does not hide the score or bring the Dashboard's strip back.

It is stored where the assistant finishes onboarding's last step: answering the last
open questions (`answer_clarifications`), or asking for its next task after taking the
questions step and finding nothing to ask (`get_next_task`). Everything else reads the
stored moment.
"""

import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from sqlmodel import Session, select

from app import crud
from app.crud.clarification import state_counts
from app.models.assistant_task import AssistantTask
from app.models.company import Company
from app.models.enums import ClarificationState
from app.models.readiness import ReadinessStepKey, ReadinessStepState
from app.services.onboarding import ANSWERS
from app.services.spec import agents_needing_specs


class OnboardingProgress(NamedTuple):
    scanned: bool
    # No agent waits for a spec (after the first scan).
    specs: bool
    answered: int
    open: int
    parked: int
    readiness_done: bool

    @property
    def answers(self) -> bool:
        return self.specs and self.open == 0

    @property
    def done(self) -> bool:
        return self.readiness_done and self.answers


def progress(*, session: Session, company_id: uuid.UUID) -> OnboardingProgress:
    readiness = crud.get_readiness(session=session, company_id=company_id, mcp_url=None)
    scanned = any(
        step.key is ReadinessStepKey.FIRST_SCAN
        and step.state is ReadinessStepState.DONE
        for step in readiness.steps
    )
    counts = state_counts(session=session, company_id=company_id)
    return OnboardingProgress(
        scanned=scanned,
        specs=scanned
        and not agents_needing_specs(session=session, company_id=company_id),
        answered=counts[ClarificationState.ANSWERED],
        open=counts[ClarificationState.OPEN],
        parked=counts[ClarificationState.PARKED],
        readiness_done=all(
            step.state is ReadinessStepState.DONE for step in readiness.steps
        ),
    )


def onboarding_complete(*, session: Session, company_id: uuid.UUID) -> bool:
    """Onboarding was completed once (it stays complete)."""
    company = session.get(Company, company_id)
    return company is not None and company.onboarding_completed_at is not None


def finish_onboarding(*, session: Session, company_id: uuid.UUID) -> bool:
    """Store onboarding as complete if every condition holds now. True only when it
    was completed by this call. Commits when it stores."""
    company = session.get(Company, company_id)
    if company is None or company.onboarding_completed_at is not None:
        return False
    now = progress(session=session, company_id=company_id)
    if not now.done:
        return False
    # The questions step was gone through: questions were decided, or the assistant
    # took the step and found nothing to ask. Otherwise the last spec written would end
    # onboarding before the assistant could raise anything.
    asked = (
        now.answered + now.parked > 0
        or session.exec(
            select(AssistantTask.id).where(
                AssistantTask.company_id == company_id,
                AssistantTask.task_key == f"onboarding:{ANSWERS}",
            )
        ).first()
        is not None
    )
    if not asked:
        return False
    # Lock the workspace and look again: of two calls finishing at once, only the
    # first stores it and says so.
    locked = session.exec(
        select(Company).where(Company.id == company_id).with_for_update()
    ).one()
    if locked.onboarding_completed_at is not None:
        session.commit()
        return False
    locked.onboarding_completed_at = datetime.now(UTC)
    session.add(locked)
    session.commit()
    return True
