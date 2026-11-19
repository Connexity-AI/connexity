"""Assistant feedback reports (`plans/2026-11-19-assistant-feedback.md`)."""

import uuid
from datetime import datetime

from sqlalchemy import or_, update
from sqlmodel import Session, col, func, select

from app.models.feedback import FeedbackReport


def reports_since(*, session: Session, company_id: uuid.UUID, since: datetime) -> int:
    """How many reports the workspace sent since ``since``."""
    return session.exec(
        select(func.count()).where(
            FeedbackReport.company_id == company_id,
            col(FeedbackReport.received_at) >= since,
        )
    ).one()


def unsent_reports(
    *, session: Session, max_tries: int, limit: int
) -> list[FeedbackReport]:
    """Reports not yet in Notion with tries left, oldest first, at most ``limit``."""
    return list(
        session.exec(
            select(FeedbackReport)
            .where(
                col(FeedbackReport.notion_page_id).is_(None),
                col(FeedbackReport.tries) < max_tries,
            )
            .order_by(col(FeedbackReport.received_at))
            .limit(limit)
        ).all()
    )


def claim_report(
    *, session: Session, report_id: uuid.UUID, now: datetime, stale_before: datetime
) -> bool:
    """Take a report for one post, counting the try: false when it is already in
    Notion or another post took it since ``stale_before``. One statement, so two
    posts never both win."""
    claimed = session.exec(  # type: ignore[call-overload]
        update(FeedbackReport)
        .where(
            col(FeedbackReport.id) == report_id,
            col(FeedbackReport.notion_page_id).is_(None),
            or_(
                col(FeedbackReport.claimed_at).is_(None),
                col(FeedbackReport.claimed_at) < stale_before,
            ),
        )
        .values(claimed_at=now, tries=FeedbackReport.tries + 1)
    )
    session.commit()
    return bool(claimed.rowcount)
